export const accessKeys = {
  context: () => ['access', 'context'] as const,
};

export const organizationKeys = {
  all: () => ['organizations'] as const,
  detail: (slug: string) => ['organizations', slug] as const,
  membersRoot: (slug: string) => ['organizations', slug, 'members'] as const,
  members: (
    slug: string,
    filters: {
      member_type?: string;
      ordering?: string;
      page?: number;
      q?: string;
      role?: string;
      status?: string;
    },
  ) => ['organizations', slug, 'members', filters] as const,
  member: (slug: string, membershipId: string) =>
    ['organizations', slug, 'members', membershipId] as const,
  events: (slug: string, membershipId: string) =>
    ['organizations', slug, 'members', membershipId, 'events'] as const,
  invitations: (
    slug: string,
    filters: {
      invitation_type?: string;
      page?: number;
      q?: string;
      status?: string;
    } = {},
  ) => ['organizations', slug, 'invitations', filters] as const,
  invitation: (slug: string, invitationId: string) =>
    ['organizations', slug, 'invitations', invitationId] as const,
  joinRequests: (slug: string) =>
    ['organizations', slug, 'join-requests'] as const,
  profile: (slug: string, membershipId: string) =>
    ['organizations', slug, 'members', membershipId, 'profile'] as const,
  membershipSettings: (slug: string) =>
    ['organizations', slug, 'membership-settings'] as const,
  integrations: (slug: string) =>
    ['organizations', slug, 'integrations'] as const,
  integrationHealth: (slug: string, connectionId: string) =>
    ['organizations', slug, 'integrations', connectionId, 'health'] as const,
};
