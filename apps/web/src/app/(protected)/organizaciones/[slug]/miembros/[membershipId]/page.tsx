import { MemberDetailPanel } from '@/components/organizations/member-detail-panel';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationMemberForPage } from '@/lib/organizations/server';

export default async function OrganizationMemberDetailPage({
  params,
}: Readonly<{ params: Promise<{ membershipId: string; slug: string }> }>) {
  const { membershipId, slug } = await params;
  const { access, events, member, organization, profile } =
    await getOrganizationMemberForPage(slug, membershipId);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/miembros`, label: 'Miembros' },
          { label: member.user.display },
        ]}
        description="Gestiona la identidad institucional, responsabilidades, seguridad y trazabilidad de esta persona."
        eyebrow="Miembros"
        title={member.user.display}
      />
      <div className="mt-6">
        <MemberDetailPanel
          capabilities={access.capabilities}
          events={events}
          initialMember={member}
          initialProfile={profile}
          slug={slug}
        />
      </div>
    </main>
  );
}
