import { PlatformOrganizationProvisioner } from '@/components/organizations/platform-organization-provisioner';
import { PageHeader } from '@/components/platform/page-header';
import {
  getAccessContext,
  getPlatformOrganizations,
} from '@/lib/organizations/server';
import { notFound } from 'next/navigation';

export default async function PlatformOrganizationsPage() {
  const context = await getAccessContext();
  if (!context.is_platform_operator) notFound();
  const organizations = await getPlatformOrganizations();
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[{ label: 'Instituciones' }]}
        description="Controla las instituciones que usan la plataforma sin mezclar esta responsabilidad global con los roles de sus miembros."
        eyebrow="Administración de plataforma"
        title="Instituciones"
      />
      <div className="mt-6">
        <PlatformOrganizationProvisioner
          organizations={organizations}
          membershipOrganizationSlugs={context.organizations.map(
            (organization) => organization.slug,
          )}
        />
      </div>
    </main>
  );
}
