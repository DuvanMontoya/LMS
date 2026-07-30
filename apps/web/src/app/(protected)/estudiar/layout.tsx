import { redirect } from 'next/navigation';

import { PlatformShell } from '@/components/platform/platform-shell';
import { getServerAuthSession } from '@/lib/auth/server-session';
import { getAccessContext } from '@/lib/organizations/server';

export default async function StudyLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await getServerAuthSession();
  if (!session) redirect('/auth/iniciar-sesion?next=/estudiar');
  const context = await getAccessContext();
  return (
    <PlatformShell email={session.email} organizations={context.organizations}>
      {children}
    </PlatformShell>
  );
}
