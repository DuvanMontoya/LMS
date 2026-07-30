import type { NextConfig } from 'next';

import { requireInternalOrigin } from './src/lib/env/origin';

const djangoInternalOrigin = requireInternalOrigin(
  process.env.DJANGO_INTERNAL_ORIGIN,
);

const nextConfig: NextConfig = {
  distDir: process.env.NEXT_DIST_DIR ?? '.next',
  // Next dev blocks client assets when the application is opened through the
  // loopback host documented for local review instead of its localhost default.
  allowedDevOrigins: ['127.0.0.1'],
  // Django's canonical API contract requires terminal slashes. Preserve them
  // before external rewrites so unsafe requests never follow a 301 redirect.
  skipTrailingSlashRedirect: true,
  async rewrites() {
    return [
      {
        source: '/_allauth/:path*',
        destination: `${djangoInternalOrigin}/_allauth/:path*`,
      },
      {
        source: '/api/v1/:path*/',
        destination: `${djangoInternalOrigin}/api/v1/:path*/`,
      },
      {
        source: '/health/:path*',
        destination: `${djangoInternalOrigin}/health/:path*/`,
      },
    ];
  },
  async headers() {
    return [
      {
        source: '/auth/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
      {
        source: '/estudiar/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
      {
        source: '/organizaciones/:path*',
        headers: [
          { key: 'Cache-Control', value: 'no-store' },
          { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          {
            key: 'Permissions-Policy',
            value: 'camera=(), microphone=(), geolocation=()',
          },
        ],
      },
    ];
  },
};

export default nextConfig;
