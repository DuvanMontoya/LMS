import { AcademicHelpCenter } from '@/components/help/academic-help-center';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationForPage } from '@/lib/organizations/server';

export default async function OrganizationHelpPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access } = await getOrganizationForPage(slug);
  return (
    <main className="academic-page">
      <PageHeader
        description="Guía operativa para crear y relacionar cada componente académico sin perder contexto, permisos ni historia."
        eyebrow="Ayuda y conocimiento"
        title="Cómo funciona la plataforma"
      />
      <div className="mt-6">
        <AcademicHelpCenter
          capabilities={access.capabilities}
          organizationSlug={slug}
        />
      </div>
    </main>
  );
}
