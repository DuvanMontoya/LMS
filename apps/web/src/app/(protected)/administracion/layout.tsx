import { notFound, redirect } from 'next/navigation';

import { PlatformShell } from '@/components/platform/platform-shell';
import { getServerAuthSession } from '@/lib/auth/server-session';
import { getAccessContext } from '@/lib/organizations/server';

export default async function PlatformAdministrationLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  const session = await getServerAuthSession();
  if (!session)
    redirect('/auth/iniciar-sesion?next=/administracion/organizaciones');
  const context = await getAccessContext();
  if (!context.is_platform_operator) notFound();
  return (
    <PlatformShell
      displayName={context.user.display}
      isPlatformOperator={context.is_platform_operator}
      organizations={context.organizations}
    >
      {children}
    </PlatformShell>
  );
}
