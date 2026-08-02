import { redirect } from 'next/navigation';

import { getOrganizationForPage } from '@/lib/organizations/server';
import { primaryWorkspaceHref } from '@/lib/organizations/workspace-route';

export default async function OrganizationEntryPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access } = await getOrganizationForPage(slug);
  redirect(primaryWorkspaceHref(slug, access.roles));
}
