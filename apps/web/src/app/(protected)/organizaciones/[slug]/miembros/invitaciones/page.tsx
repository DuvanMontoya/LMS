import { InvitationManagement } from '@/components/organizations/invitation-management';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationInvitationsForPage } from '@/lib/organizations/server';

export default async function OrganizationInvitationsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { invitations, organization } =
    await getOrganizationInvitationsForPage(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/miembros`, label: 'Miembros' },
          { label: 'Invitaciones' },
        ]}
        description="Controla invitaciones, activaciones administradas y vencimientos sin exponer enlaces ni credenciales."
        eyebrow="Miembros"
        title="Invitaciones"
      />
      <div className="mt-6">
        <InvitationManagement initial={invitations} slug={slug} />
      </div>
    </main>
  );
}
