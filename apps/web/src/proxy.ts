import { NextResponse, type NextRequest } from 'next/server';

const sessionCookieName = process.env.AUTH_SESSION_COOKIE_NAME ?? 'sessionid';

export function proxy(request: NextRequest) {
  if (request.cookies.has(sessionCookieName)) {
    const response = NextResponse.next();
    const isLiveClass = /^\/organizaciones\/[^/]+\/clases\/[^/]+\/?$/.test(
      request.nextUrl.pathname,
    );
    response.headers.set(
      'Permissions-Policy',
      isLiveClass
        ? 'camera=(self), microphone=(self), display-capture=(self), geolocation=()'
        : 'camera=(), microphone=(), display-capture=(), geolocation=()',
    );
    if (isLiveClass) {
      const livekitOrigin = safeLiveKitOrigin(
        process.env.NEXT_PUBLIC_LIVEKIT_URL,
      );
      response.headers.set(
        'Content-Security-Policy',
        [
          "default-src 'self'",
          "script-src 'self'",
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
  loginUrl.searchParams.set(
    'next',
    `${request.nextUrl.pathname}${request.nextUrl.search}`,
  );
  return NextResponse.redirect(loginUrl);
}

function safeLiveKitOrigin(value: string | undefined) {
  if (!value) return '';
  try {
    const url = new URL(value);
    if (!['https:', 'wss:'].includes(url.protocol)) return '';
    return url.origin;
  } catch {
    return '';
  }
}

export const config = {
  matcher: [
    '/administracion/:path*',
    '/estudiar/:path*',
    '/invitaciones/aceptar/:path*',
    '/organizaciones/:path*',
  ],
};
