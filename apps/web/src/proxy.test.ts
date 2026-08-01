import { NextRequest } from 'next/server';
import { afterEach, describe, expect, it } from 'vitest';

import { proxy } from './proxy';

function authenticatedRequest(path: string) {
  return new NextRequest(`https://lms.example.test${path}`, {
    headers: { cookie: 'sessionid=test-session' },
  });
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
});
