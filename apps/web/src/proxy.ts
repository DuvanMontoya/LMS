import { NextResponse, type NextRequest } from 'next/server';

const sessionCookieName = process.env.AUTH_SESSION_COOKIE_NAME ?? 'sessionid';

export function proxy(request: NextRequest) {
  const { pathname } = request.nextUrl;
  const isInvitationActivation =
    pathname === '/invitaciones/activar' ||
    pathname.startsWith('/invitaciones/activar/') ||
    pathname === '/invitaciones/activar-cuenta' ||
    pathname.startsWith('/invitaciones/activar-cuenta/') ||
    pathname === '/invitaciones/crear-cuenta' ||
    pathname.startsWith('/invitaciones/crear-cuenta/');
  const isPublicIdentityRoute =
    pathname.startsWith('/auth/') || isInvitationActivation;

  if (pathname === '/livekit/egress') {
    const isDevelopment = process.env.NODE_ENV === 'development';
    const livekitOrigin = safeLiveKitOrigin(
      process.env.LIVEKIT_EGRESS_CONNECT_URL ??
        (isDevelopment
          ? (request.nextUrl.searchParams.get('url') ?? undefined)
          : undefined),
      isDevelopment,
    );
    const response = setSensitivePageHeaders(
      NextResponse.next(),
      'no-referrer',
    );
    response.headers.set(
      'Content-Security-Policy',
      [
        "default-src 'self'",
        `script-src 'self'${isDevelopment ? " 'unsafe-eval' 'unsafe-inline'" : ''}`,
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "media-src 'self' blob:",
        `connect-src 'self'${livekitOrigin ? ` ${livekitOrigin}` : ''}`,
        "object-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
      ].join('; '),
    );
    return response;
  }

  if (isPublicIdentityRoute) {
    return setSensitivePageHeaders(
      NextResponse.next(),
      isInvitationActivation
        ? 'no-referrer'
        : 'strict-origin-when-cross-origin',
    );
  }

  if (request.cookies.has(sessionCookieName)) {
    const response = setSensitivePageHeaders(NextResponse.next());
    const isLiveClass = /^\/organizaciones\/[^/]+\/clases\/[^/]+\/?$/.test(
      pathname,
    );
    const isCourseActivity =
      /^\/organizaciones\/[^/]+\/aprender\/[^/]+\/actividades\/[^/]+\/?$/.test(
        pathname,
      );
    const allowsRealtimeMedia = isLiveClass || isCourseActivity;
    response.headers.set(
      'Permissions-Policy',
      allowsRealtimeMedia
        ? 'camera=(self), microphone=(self), display-capture=(self), geolocation=()'
        : 'camera=(), microphone=(), display-capture=(), geolocation=()',
    );
    if (allowsRealtimeMedia) {
      const isDevelopment = process.env.NODE_ENV === 'development';
      const livekitOrigin = safeLiveKitOrigin(
        process.env.NEXT_PUBLIC_LIVEKIT_URL,
        isDevelopment,
      );
      response.headers.set(
        'Content-Security-Policy',
        [
          "default-src 'self'",
          `script-src 'self'${isDevelopment ? " 'unsafe-eval' 'unsafe-inline'" : ''}`,
          "style-src 'self' 'unsafe-inline'",
          "img-src 'self' data: blob:",
          "media-src 'self' blob:",
          `connect-src 'self'${livekitOrigin ? ` ${livekitOrigin}` : ''}`,
          "object-src 'none'",
          "base-uri 'self'",
          "frame-ancestors 'none'",
        ].join('; '),
      );
    }
    return response;
  }
  const loginUrl = new URL('/auth/iniciar-sesion', request.url);
  loginUrl.searchParams.set('next', `${pathname}${request.nextUrl.search}`);
  return setSensitivePageHeaders(NextResponse.redirect(loginUrl));
}

function setSensitivePageHeaders(
  response: NextResponse,
  referrerPolicy = 'strict-origin-when-cross-origin',
) {
  response.headers.set('Cache-Control', 'no-store');
  response.headers.set('Referrer-Policy', referrerPolicy);
  response.headers.set('X-Content-Type-Options', 'nosniff');
  response.headers.set('X-Frame-Options', 'DENY');
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), display-capture=(), geolocation=()',
  );
  return response;
}

function safeLiveKitOrigin(value: string | undefined, allowInsecure = false) {
  if (!value) return '';
  try {
    const url = new URL(value);
    const protocols = allowInsecure
      ? ['http:', 'https:', 'ws:', 'wss:']
      : ['https:', 'wss:'];
    if (!protocols.includes(url.protocol)) return '';
    return url.origin;
  } catch {
    return '';
  }
}

export const config = {
  matcher: [
    '/auth/:path*',
    '/administracion/:path*',
    '/estudiar/:path*',
    '/invitaciones/aceptar/:path*',
    '/invitaciones/activar/:path*',
    '/invitaciones/activar-cuenta/:path*',
    '/invitaciones/crear-cuenta/:path*',
    '/livekit/:path*',
    '/organizaciones/:path*',
  ],
};
