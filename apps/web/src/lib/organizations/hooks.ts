'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { components } from '@/lib/api/generated/platform';
import { accessKeys, organizationKeys } from '@/lib/query/organization-keys';

type OrganizationRole = components['schemas']['OrganizationRole'];

async function requireData<T>(
  request: Promise<{ response: Response; data?: T }>,
): Promise<T> {
  const { response, data } = await request;
  if (response.ok && data) return data;
  let message = 'No fue posible completar la operación institucional.';
  try {
    const body: unknown = await response.clone().json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = body.detail;
      if (typeof detail === 'string') message = detail;
    }
  } catch {
    // Preserve the neutral error when the response has no compatible body.
  }
  throw new Error(message);
}

export function useAccessContext() {
  return useQuery({
    queryKey: accessKeys.context(),
    queryFn: () =>
      requireData(platformBrowserClient.GET('/api/v1/access/context/')),
  });
}

export function useOrganizations() {
  return useQuery({
    queryKey: organizationKeys.all(),
    queryFn: () =>
      requireData(platformBrowserClient.GET('/api/v1/organizations/')),
  });
}

export function useOrganization(slug: string) {
  return useQuery({
    queryKey: organizationKeys.detail(slug),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET('/api/v1/organizations/{slug}/', {
          params: { path: { slug } },
        }),
      ),
  });
}

export function useOrganizationMembers(
  slug: string,
  filters: { email?: string; page?: number },
) {
  return useQuery({
    queryKey: organizationKeys.members(slug, filters),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET('/api/v1/organizations/{slug}/memberships/', {
          params: {
            path: { slug },
            query: {
              ...(filters.page === undefined ? {} : { page: filters.page }),
              page_size: 25,
            },
          },
        }),
      ),
  });
}

export function useUpdateOrganization(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      requireData(
        platformBrowserClient.PATCH('/api/v1/organizations/{slug}/', {
          params: { path: { slug } },
          body: { name },
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.detail(slug),
      });
      await queryClient.invalidateQueries({ queryKey: organizationKeys.all() });
      await queryClient.invalidateQueries({ queryKey: accessKeys.context() });
    },
  });
}

export function useAddOrganizationMember(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      email,
      roles,
    }: {
      email: string;
      roles: OrganizationRole[];
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/memberships/',
          {
            params: { path: { slug } },
            body: { email, roles },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.membersRoot(slug),
      }),
  });
}

function useMembershipAction(
  slug: string,
  action: 'suspend' | 'reactivate' | 'revoke',
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (membershipId: string) =>
      requireData(
        platformBrowserClient.POST(
          `/api/v1/organizations/{slug}/memberships/{membership_id}/${action}/`,
          { params: { path: { slug, membership_id: membershipId } } },
        ),
      ),
    onSuccess: async (_, membershipId) => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.membersRoot(slug),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.member(slug, membershipId),
      });
      await queryClient.invalidateQueries({ queryKey: accessKeys.context() });
    },
  });
}

export function useSuspendMembership(slug: string) {
  return useMembershipAction(slug, 'suspend');
}

export function useReactivateMembership(slug: string) {
  return useMembershipAction(slug, 'reactivate');
}

export function useRevokeMembership(slug: string) {
  return useMembershipAction(slug, 'revoke');
}

export function useReplaceMembershipRoles(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      membershipId,
      roles,
    }: {
      membershipId: string;
      roles: OrganizationRole[];
    }) =>
      requireData(
        platformBrowserClient.PUT(
          '/api/v1/organizations/{slug}/memberships/{membership_id}/roles/',
          {
            params: { path: { slug, membership_id: membershipId } },
            body: { roles },
          },
        ),
      ),
    onSuccess: async (_, { membershipId }) => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.membersRoot(slug),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.member(slug, membershipId),
      });
      await queryClient.invalidateQueries({ queryKey: accessKeys.context() });
    },
  });
}
