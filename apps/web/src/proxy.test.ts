import { NextRequest } from 'next/server';
import { afterEach, describe, expect, it } from 'vitest';

import { proxy } from './proxy';

function authenticatedRequest(path: string) {
  return new NextRequest(`https://lms.example.test${path}`, {
    headers: { cookie: 'sessionid=test-session' },
  });
}

function publicRequest(path: string) {
  return new NextRequest(`https://lms.example.test${path}`);
}

describe('route security headers', () => {
  afterEach(() => {
    delete process.env.NEXT_PUBLIC_LIVEKIT_URL;
  });

  it('allows capture only on a live-class route and pins the LiveKit origin', () => {
    process.env.NEXT_PUBLIC_LIVEKIT_URL = 'wss://media.example.test';
    const response = proxy(
      authenticatedRequest(
        '/organizaciones/institucion/clases/00000000-0000-0000-0000-000000000001',
      ),
    );
    expect(response.headers.get('Permissions-Policy')).toContain(
      'camera=(self)',
    );
    expect(response.headers.get('Content-Security-Policy')).toContain(
      "connect-src 'self' wss://media.example.test",
    );
  });

  it('denies camera, microphone and display capture on ordinary routes', () => {
    const response = proxy(
      authenticatedRequest('/organizaciones/institucion/calendario'),
    );
    expect(response.headers.get('Permissions-Policy')).toBe(
      'camera=(), microphone=(), display-capture=(), geolocation=()',
    );
    expect(response.headers.has('Content-Security-Policy')).toBe(false);
  });

  it('allows public invitation activation without retaining its bearer token in shared caches or referrers', () => {
    const response = proxy(
      publicRequest('/invitaciones/activar?token=one-use-token'),
    );
    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(response.headers.get('Referrer-Policy')).toBe('no-referrer');
    expect(response.headers.get('X-Frame-Options')).toBe('DENY');
  });

  it('keeps the session-bound invited signup route public and non-referring', () => {
    const response = proxy(publicRequest('/invitaciones/crear-cuenta'));
    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(response.headers.get('Referrer-Policy')).toBe('no-referrer');
  });

  it('keeps authentication pages public while applying sensitive-page headers', () => {
    const response = proxy(publicRequest('/auth/iniciar-sesion'));
    expect(response.status).toBe(200);
    expect(response.headers.get('Cache-Control')).toBe('no-store');
    expect(response.headers.get('Referrer-Policy')).toBe(
      'strict-origin-when-cross-origin',
    );
  });
});
