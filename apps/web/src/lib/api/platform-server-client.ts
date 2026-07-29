import 'server-only';

import { cookies } from 'next/headers';
import createClient from 'openapi-fetch';

import { requireInternalOrigin } from '@/lib/env/origin';

import type { paths } from './generated/platform';

export async function createPlatformServerClient() {
  const cookieHeader = (await cookies()).toString();
  return createClient<paths>({
    baseUrl: requireInternalOrigin(process.env.DJANGO_INTERNAL_ORIGIN),
    credentials: 'include',
    fetch: async (request: Request) => {
      const headers = new Headers();
      if (cookieHeader) headers.set('Cookie', cookieHeader);
      return fetch(new Request(request, { headers, cache: 'no-store' }), {
        cache: 'no-store',
        credentials: 'include',
      });
    },
  });
}
