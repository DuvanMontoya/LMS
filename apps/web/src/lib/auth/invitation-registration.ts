import 'server-only';

import { createPlatformServerClient } from '@/lib/api/platform-server-client';

export type InvitationRegistrationContext = {
  email: string;
  invitationType: 'initial_owner' | 'new_user';
  organizationName: string;
};

export async function getInvitationRegistrationContext(): Promise<
  InvitationRegistrationContext | undefined
> {
  try {
    const client = await createPlatformServerClient();
    const { data, response } = await client.GET(
      '/api/v1/public/invitations/signup-context/',
    );
    if (!response.ok || !data) return undefined;
    if (
      data.invitation_type !== 'initial_owner' &&
      data.invitation_type !== 'new_user'
    ) {
      return undefined;
    }
    return {
      email: data.email,
      invitationType: data.invitation_type,
      organizationName: data.organization_name,
    };
  } catch {
    return undefined;
  }
}
