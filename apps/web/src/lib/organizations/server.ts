import 'server-only';

import { notFound } from 'next/navigation';

import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import type { operations } from '@/lib/api/generated/platform';

type AccessContext =
  operations['access_context_retrieve']['responses'][200]['content']['application/json'];
type AccessOrganization = AccessContext['organizations'][number];
type Organization =
  operations['organizations_retrieve']['responses'][200]['content']['application/json'];
type MemberList =
  operations['organizations_memberships_list']['responses'][200]['content']['application/json'];

async function requirePayload<T>(
  request: Promise<{ response: Response; data?: T }>,
) {
  const { response, data } = await request;
  if (response.status === 404) notFound();
  if (!response.ok || !data) {
    throw new Error('No fue posible consultar el contexto institucional.');
  }
  return data;
}

export async function getAccessContext(): Promise<AccessContext> {
  const client = await createPlatformServerClient();
  return (await requirePayload(
    client.GET('/api/v1/access/context/'),
  )) as AccessContext;
}

export function organizationInContext(
  context: AccessContext,
  slug: string,
): AccessOrganization | undefined {
  return context.organizations.find(
    (organization) => organization.slug === slug,
  );
}

export async function getOrganizationForPage(slug: string) {
  const [context, client] = await Promise.all([
    getAccessContext(),
    createPlatformServerClient(),
  ]);
  const access = organizationInContext(context, slug);
  if (!access) notFound();
  const organization = (await requirePayload(
    client.GET('/api/v1/organizations/{slug}/', { params: { path: { slug } } }),
  )) as Organization;
  return { access, context, organization };
}

export async function getOrganizationMembersForPage(slug: string, page = 1) {
  const { access, context, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('membership.view')) notFound();
  const client = await createPlatformServerClient();
  const members = (await requirePayload(
    client.GET('/api/v1/organizations/{slug}/memberships/', {
      params: { path: { slug }, query: { page } },
    }),
  )) as MemberList;
  return { access, context, organization, members };
}
