import 'server-only';

import { createServerClient } from '@/lib/api/server-client';

import type { components } from '@/lib/api/generated/allauth';

export type ServerAuthSession = components['schemas']['User'] | null;

export async function getServerAuthSession(): Promise<ServerAuthSession> {
  const client = await createServerClient();
  const { response, data } = await client.GET(
    '/_allauth/browser/v1/auth/session',
  );
  if (response.status === 401 || response.status === 410) return null;
  if (!response.ok || !data) {
    throw new Error('No fue posible consultar la sesión con Django.');
  }
  return data.data.user;
}
