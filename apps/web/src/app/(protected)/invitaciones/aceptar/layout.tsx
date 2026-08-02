import { redirect } from 'next/navigation';

import { getServerAuthSession } from '@/lib/auth/server-session';

/**
 * The proxy can only see that a session cookie exists. Confirm it against
 * Django before accepting an invitation so a revoked cookie is redirected to
 * sign-in while preserving the one-time invitation flow.
 */
export default async function InvitationAcceptanceLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await getServerAuthSession();
  if (!session) {
    redirect('/auth/iniciar-sesion?next=/invitaciones/aceptar');
  }
  return children;
}
