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
type MembershipSettings =
  operations['organizations_membership_settings_retrieve']['responses'][200]['content']['application/json'];
type IntegrationList =
  operations['organizations_integrations_list']['responses'][200]['content']['application/json'];
type InvitationList =
  operations['organizations_invitations_list']['responses'][200]['content']['application/json'];
type JoinRequestList =
  operations['organizations_join_requests_list']['responses'][200]['content']['application/json'];
type Membership =
  operations['organizations_memberships_retrieve']['responses'][200]['content']['application/json'];
type MemberProfile =
  operations['organizations_memberships_profile_retrieve']['responses'][200]['content']['application/json'];
type MembershipEventList =
  operations['organizations_memberships_events_list']['responses'][200]['content']['application/json'];

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

export async function getPlatformOrganizations(): Promise<Organization[]> {
  const client = await createPlatformServerClient();
  return (await requirePayload(
    client.GET('/api/v1/organizations/'),
  )) as Organization[];
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

export async function getOrganizationConfigurationForPage(slug: string) {
  const { access, context, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('membership.settings.view')) notFound();
  const client = await createPlatformServerClient();
  const settingsRequest = client.GET(
    '/api/v1/organizations/{slug}/membership-settings/',
    { params: { path: { slug } } },
  );
  const integrationsRequest = access.capabilities.includes('integration.view')
    ? client.GET('/api/v1/organizations/{slug}/integrations/', {
        params: { path: { slug } },
      })
    : Promise.resolve({
        response: new Response(null, { status: 200 }),
        data: [],
      });
  const [membershipSettings, integrations] = await Promise.all([
    requirePayload(settingsRequest) as Promise<MembershipSettings>,
    requirePayload(integrationsRequest) as Promise<IntegrationList>,
  ]);
  return { access, context, organization, integrations, membershipSettings };
}

export async function getOrganizationInvitationsForPage(slug: string) {
  const { access, context, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('membership.invitation.manage')) notFound();
  const client = await createPlatformServerClient();
  const invitations = (await requirePayload(
    client.GET('/api/v1/organizations/{slug}/invitations/', {
      params: { path: { slug }, query: { page: 1, page_size: 100 } },
    }),
  )) as InvitationList;
  return { access, context, invitations, organization };
}

export async function getOrganizationJoinRequestsForPage(slug: string) {
  const { access, context, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('membership.join_request.manage'))
    notFound();
  const client = await createPlatformServerClient();
  const requests = (await requirePayload(
    client.GET('/api/v1/organizations/{slug}/join-requests/', {
      params: { path: { slug }, query: { page: 1, page_size: 100 } },
    }),
  )) as JoinRequestList;
  return { access, context, organization, requests };
}

export async function getOrganizationMemberForPage(
  slug: string,
  membershipId: string,
) {
  const { access, context, organization } = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const memberRequest = client.GET(
    '/api/v1/organizations/{slug}/memberships/{membership_id}/',
    { params: { path: { slug, membership_id: membershipId } } },
  );
  const profileRequest = client.GET(
    '/api/v1/organizations/{slug}/memberships/{membership_id}/profile/',
    { params: { path: { slug, membership_id: membershipId } } },
  );
  const eventsRequest = access.capabilities.includes('membership_event.view')
    ? client.GET(
        '/api/v1/organizations/{slug}/memberships/{membership_id}/events/',
        { params: { path: { slug, membership_id: membershipId } } },
      )
    : undefined;
  const [member, profile, events] = await Promise.all([
    requirePayload(memberRequest) as Promise<Membership>,
    requirePayload(profileRequest) as Promise<MemberProfile>,
    eventsRequest
      ? (requirePayload(eventsRequest) as Promise<MembershipEventList>)
      : Promise.resolve(undefined),
  ]);
  return { access, context, events, member, organization, profile };
}
