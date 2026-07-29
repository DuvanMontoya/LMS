import type { NextConfig } from 'next';

import { requireInternalOrigin } from './src/lib/env/origin';

const djangoInternalOrigin = requireInternalOrigin(
  process.env.DJANGO_INTERNAL_ORIGIN,
);

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/_allauth/:path*',
        destination: `${djangoInternalOrigin}/_allauth/:path*`,
      },
      {
        source: '/api/v1/:path*',
        destination: `${djangoInternalOrigin}/api/v1/:path*`,
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
    ];
  },
};

export default nextConfig;
