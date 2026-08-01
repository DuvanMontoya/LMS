import 'server-only';

import { createPlatformServerClient } from '@/lib/api/platform-server-client';

export async function isSignupAvailable(): Promise<boolean> {
  try {
    const client = await createPlatformServerClient();
    const { data, response } = await client.GET(
      '/api/v1/platform/registration-settings/public/',
    );
    return response.ok && data?.signup_available === true;
  } catch {
    // Registration visibility fails closed when the policy cannot be read.
    return false;
  }
}
