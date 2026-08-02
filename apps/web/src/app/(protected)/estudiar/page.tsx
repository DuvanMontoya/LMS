import { redirect } from 'next/navigation';

import { getServerAuthSession } from '@/lib/auth/server-session';
import { getAccessContext } from '@/lib/organizations/server';
import { primaryWorkspaceHref } from '@/lib/organizations/workspace-route';

export default async function StudyPage() {
  const session = await getServerAuthSession();
  if (!session) redirect('/auth/iniciar-sesion?next=/estudiar');
  const context = await getAccessContext();
  const organization = context.organizations[0];
  if (organization) {
    redirect(primaryWorkspaceHref(organization.slug, organization.roles));
  }
  if (context.is_platform_operator) redirect('/administracion/organizaciones');
  redirect('/auth/iniciar-sesion');
}
