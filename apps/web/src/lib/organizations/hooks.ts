'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiErrorMessage } from '@/lib/api/api-error';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { components } from '@/lib/api/generated/platform';
import { accessKeys, organizationKeys } from '@/lib/query/organization-keys';

type OrganizationRole = components['schemas']['OrganizationRole'];

async function requireData<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
): Promise<T> {
  const { response, data, error } = await request;
  if (response.ok && data !== undefined) return data;
  throw new Error(
    apiErrorMessage(
      error,
      'No fue posible completar la operación institucional.',
    ),
  );
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

export function useProvisionPlatformOrganization() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      provision: components['schemas']['PlatformOrganizationProvision'],
    ) =>
      requireData(
        platformBrowserClient.POST('/api/v1/platform/organizations/', {
          body: provision,
        }),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.all(),
      });
      await queryClient.invalidateQueries({ queryKey: accessKeys.context() });
    },
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
  filters: {
    member_type?: string;
    ordering?: 'email' | '-email' | 'joined_at' | '-joined_at';
    page?: number;
    q?: string;
    role?: OrganizationRole;
    status?: 'active' | 'suspended' | 'revoked';
  },
) {
  return useQuery({
    queryKey: organizationKeys.members(slug, filters),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET('/api/v1/organizations/{slug}/memberships/', {
          params: {
            path: { slug },
            query: {
              ...(filters.q === undefined ? {} : { q: filters.q }),
              ...(filters.status === undefined
                ? {}
                : { status: filters.status }),
              ...(filters.role === undefined ? {} : { role: filters.role }),
              ...(filters.member_type === undefined
                ? {}
                : { member_type: filters.member_type }),
              ...(filters.ordering === undefined
                ? {}
                : { ordering: filters.ordering }),
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

export function useCreateOrganizationInvitation(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: components['schemas']['InvitationCreate']) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/invitations/',
          {
            params: { path: { slug } },
            body,
          },
        ),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      });
    },
  });
}

export function useCreateManagedAccount(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: components['schemas']['ManagedAccountCreate']) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/managed-accounts/',
          { params: { path: { slug } }, body },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      }),
  });
}

export function useOrganizationInvitations(slug: string) {
  return useOrganizationInvitationsWithFilters(slug, {});
}

export function useOrganizationInvitationsWithFilters(
  slug: string,
  filters: {
    invitation_type?: 'existing_user' | 'managed_account' | 'new_user';
    page?: number;
    q?: string;
    status?: 'accepted' | 'expired' | 'pending' | 'revoked';
  },
) {
  return useQuery({
    queryKey: organizationKeys.invitations(slug, filters),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET('/api/v1/organizations/{slug}/invitations/', {
          params: {
            path: { slug },
            query: {
              ...(filters.q === undefined ? {} : { q: filters.q }),
              ...(filters.status === undefined
                ? {}
                : { status: filters.status }),
              ...(filters.invitation_type === undefined
                ? {}
                : { invitation_type: filters.invitation_type }),
              page: filters.page ?? 1,
              page_size: 25,
            },
          },
        }),
      ),
  });
}

export function useResendInvitation(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/invitations/{invitation_id}/resend/',
          { params: { path: { slug, invitation_id: invitationId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      }),
  });
}

export function useRevokeInvitation(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (invitationId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/invitations/{invitation_id}/revoke/',
          { params: { path: { slug, invitation_id: invitationId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      }),
  });
}

export function useCorrectManagedAccountEmail(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      email,
      invitationId,
    }: {
      email: string;
      invitationId: string;
    }) =>
      requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/invitations/{invitation_id}/managed-email/',
          {
            params: { path: { slug, invitation_id: invitationId } },
            body: { email },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      }),
  });
}

export function useManuallyActivateManagedAccount(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      confirmIdentity,
      invitationId,
      temporaryPassword,
    }: {
      confirmIdentity: boolean;
      invitationId: string;
      temporaryPassword: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/invitations/{invitation_id}/manual-activation/',
          {
            params: { path: { slug, invitation_id: invitationId } },
            body: {
              confirm_identity: confirmIdentity,
              temporary_password: temporaryPassword,
            },
          },
        ),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.membersRoot(slug),
      });
    },
  });
}

export function useBulkMembershipTransition(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      action,
      membershipIds,
    }: {
      action: 'reactivate' | 'revoke' | 'suspend';
      membershipIds: string[];
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/memberships/bulk-transition/',
          {
            params: { path: { slug } },
            body: { action, membership_ids: membershipIds },
          },
        ),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.membersRoot(slug),
      });
    },
  });
}

export function useOrganizationJoinRequests(slug: string) {
  return useQuery({
    queryKey: organizationKeys.joinRequests(slug),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET(
          '/api/v1/organizations/{slug}/join-requests/',
          {
            params: { path: { slug }, query: { page: 1, page_size: 100 } },
          },
        ),
      ),
  });
}

export function useReviewJoinRequest(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      joinRequestId,
      action,
    }: {
      joinRequestId: string;
      action: 'approve' | 'reject';
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/join-requests/{join_request_id}/{action}/',
          {
            params: {
              path: { slug, join_request_id: joinRequestId, action },
            },
          },
        ),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.joinRequests(slug),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.membersRoot(slug),
      });
    },
  });
}

export function useConfirmBulkInvitations(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (previewId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/invitations/bulk/confirm/',
          { params: { path: { slug } }, body: { preview_id: previewId } },
        ),
      ),
    onSuccess: async () => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.invitations(slug),
      });
    },
  });
}

export function useMembershipSettings(slug: string) {
  return useQuery({
    queryKey: organizationKeys.membershipSettings(slug),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET(
          '/api/v1/organizations/{slug}/membership-settings/',
          { params: { path: { slug } } },
        ),
      ),
  });
}

export function useUpdateMembershipSettings(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (
      body: components['schemas']['OrganizationMembershipSettingsUpdate'],
    ) =>
      requireData(
        platformBrowserClient.PUT(
          '/api/v1/organizations/{slug}/membership-settings/',
          { params: { path: { slug } }, body },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.membershipSettings(slug),
      }),
  });
}

export function useIntegrations(slug: string) {
  return useQuery({
    queryKey: organizationKeys.integrations(slug),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET(
          '/api/v1/organizations/{slug}/integrations/',
          {
            params: { path: { slug } },
          },
        ),
      ),
  });
}

export function useConnectApiKey(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      provider,
      api_key,
    }: {
      provider: 'openai' | 'gemini' | 'deepseek';
      api_key: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/integrations/api-key/',
          { params: { path: { slug } }, body: { provider, api_key } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.integrations(slug),
      }),
  });
}

export function useDisconnectIntegration(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/integrations/{connection_id}/disconnect/',
          { params: { path: { slug, connection_id: connectionId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: organizationKeys.integrations(slug),
      }),
  });
}

export function useIntegrationHealthChecks(slug: string, connectionId: string) {
  return useQuery({
    queryKey: organizationKeys.integrationHealth(slug, connectionId),
    queryFn: () =>
      requireData(
        platformBrowserClient.GET(
          '/api/v1/organizations/{slug}/integrations/{connection_id}/health-checks/',
          { params: { path: { slug, connection_id: connectionId } } },
        ),
      ),
    refetchInterval: (query) => {
      const status = query.state.data?.[0]?.status;
      return status === 'queued' || status === 'running' ? 3_000 : false;
    },
  });
}

export function useQueueIntegrationHealthCheck(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (connectionId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/integrations/{connection_id}/health-checks/',
          { params: { path: { slug, connection_id: connectionId } } },
        ),
      ),
    onSuccess: async (_, connectionId) => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.integrationHealth(slug, connectionId),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.integrations(slug),
      });
    },
  });
}

export function useRotateIntegrationApiKey(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      apiKey,
      connectionId,
      expectedVersion,
    }: {
      apiKey: string;
      connectionId: string;
      expectedVersion: number;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/integrations/{connection_id}/rotate-key/',
          {
            params: { path: { slug, connection_id: connectionId } },
            body: { api_key: apiKey, expected_version: expectedVersion },
          },
        ),
      ),
    onSuccess: async (_, { connectionId }) => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.integrations(slug),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.integrationHealth(slug, connectionId),
      });
    },
  });
}

export function useCreateGoogleTestMeeting(slug: string) {
  return useMutation({
    mutationFn: (connectionId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/integrations/{connection_id}/test-meeting/',
          { params: { path: { slug, connection_id: connectionId } } },
        ),
      ),
  });
}

export function useStartGoogleOAuth(slug: string) {
  return useMutation({
    mutationFn: (
      capabilities: Array<'calendar' | 'meet' | 'drive' | 'youtube'>,
    ) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/integrations/google/authorize/',
          { params: { path: { slug } }, body: { capabilities } },
        ),
      ),
  });
}

export function useUpdatePlatformRegistrationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: components['schemas']['RegistrationSettingsUpdate']) =>
      requireData(
        platformBrowserClient.PUT('/api/v1/platform/registration-settings/', {
          body,
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: ['platform', 'registration-settings'],
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

export function useUpdateMemberProfile(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      membershipId,
      profile,
    }: {
      membershipId: string;
      profile: components['schemas']['MemberProfileUpdate'];
    }) =>
      requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/memberships/{membership_id}/profile/',
          {
            params: { path: { slug, membership_id: membershipId } },
            body: profile,
          },
        ),
      ),
    onSuccess: async (_, { membershipId }) => {
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.profile(slug, membershipId),
      });
      await queryClient.invalidateQueries({
        queryKey: organizationKeys.member(slug, membershipId),
      });
    },
  });
}

export function useRevokeMemberSessions(slug: string) {
  return useMutation({
    mutationFn: (membershipId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/memberships/{membership_id}/revoke-sessions/',
          { params: { path: { slug, membership_id: membershipId } } },
        ),
      ),
  });
}

export function useSendMemberPasswordRecovery(slug: string) {
  return useMutation({
    mutationFn: (membershipId: string) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/memberships/{membership_id}/password-recovery/',
          { params: { path: { slug, membership_id: membershipId } } },
        ),
      ),
  });
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
