import { MemberManagement } from '@/components/organizations/member-management';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationMembersForPage } from '@/lib/organizations/server';

export default async function OrganizationMembersPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization, members } =
    await getOrganizationMembersForPage(slug);
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { label: 'Miembros' },
        ]}
        description="Administra el acceso institucional y las responsabilidades derivadas de las membresías."
        eyebrow="Gobierno institucional"
        title="Miembros"
      />
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
