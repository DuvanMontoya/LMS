export const accessKeys = {
  context: () => ['access', 'context'] as const,
};

export const organizationKeys = {
  all: () => ['organizations'] as const,
  detail: (slug: string) => ['organizations', slug] as const,
  membersRoot: (slug: string) => ['organizations', slug, 'members'] as const,
  members: (slug: string, filters: { email?: string; page?: number }) =>
    ['organizations', slug, 'members', filters] as const,
  member: (slug: string, membershipId: string) =>
    ['organizations', slug, 'members', membershipId] as const,
  events: (slug: string, membershipId: string) =>
    ['organizations', slug, 'members', membershipId, 'events'] as const,
};
