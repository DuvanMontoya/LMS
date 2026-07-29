import { NextResponse, type NextRequest } from 'next/server';

const sessionCookieName = process.env.AUTH_SESSION_COOKIE_NAME ?? 'sessionid';

export function proxy(request: NextRequest) {
  if (request.cookies.has(sessionCookieName)) return NextResponse.next();
  const loginUrl = new URL('/auth/iniciar-sesion', request.url);
  loginUrl.searchParams.set(
    'next',
    `${request.nextUrl.pathname}${request.nextUrl.search}`,
  );
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/estudiar/:path*', '/organizaciones/:path*'],
};
