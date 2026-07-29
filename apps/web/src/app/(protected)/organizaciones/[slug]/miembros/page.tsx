import Link from 'next/link';

import { MemberManagement } from '@/components/organizations/member-management';
import { getOrganizationMembersForPage } from '@/lib/organizations/server';

export default async function OrganizationMembersPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization, members } =
    await getOrganizationMembersForPage(slug);
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-12">
      <Link
        className="text-sm font-medium text-slate-700 underline"
        href={`/organizaciones/${slug}`}
      >
        Volver a {organization.name}
      </Link>
      <div className="mt-6">
        <MemberManagement
          capabilities={access.capabilities}
          members={members}
          organizationName={organization.name}
          slug={slug}
        />
      </div>
    </main>
  );
}
