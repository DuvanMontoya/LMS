import { IntegrationCenter } from '@/components/organizations/integration-center';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationConfigurationForPage } from '@/lib/organizations/server';
import { notFound } from 'next/navigation';

export default async function OrganizationIntegrationsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, integrations, organization } =
    await getOrganizationConfigurationForPage(slug);
  if (!access.capabilities.includes('integration.view')) notFound();
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          {
            href: `/organizaciones/${slug}/configuracion`,
            label: 'Configuración',
          },
          { label: 'Integraciones' },
        ]}
        description="Conecta, prueba, rota y desconecta servicios externos con estados verificables."
        eyebrow="Configuración"
        title="Integraciones"
      />
      <div className="mt-6">
        <IntegrationCenter connections={integrations} slug={slug} />
      </div>
    </main>
  );
}
