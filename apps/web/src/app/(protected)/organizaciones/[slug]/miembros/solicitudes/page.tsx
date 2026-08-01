import { JoinRequestManagement } from '@/components/organizations/join-request-management';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationJoinRequestsForPage } from '@/lib/organizations/server';

export default async function OrganizationJoinRequestsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { organization, requests } =
    await getOrganizationJoinRequestsForPage(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/miembros`, label: 'Miembros' },
          { label: 'Solicitudes' },
        ]}
        description="Revisa los ingresos públicos sin conceder acceso antes de una decisión explícita."
        eyebrow="Miembros"
        title="Solicitudes de ingreso"
      />
      <div className="mt-6">
        <JoinRequestManagement initial={requests} slug={slug} />
      </div>
    </main>
  );
}
