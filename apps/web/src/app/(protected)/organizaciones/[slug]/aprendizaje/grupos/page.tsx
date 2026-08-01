import { AcademicGroupsPanel } from '@/components/learning/academic-groups-panel';
import { PageHeader } from '@/components/platform/page-header';
import { getAcademicGroups } from '@/lib/learning/server';

export default async function AcademicGroupsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAcademicGroups(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Grupos académicos' },
        ]}
        description="Agrupa estudiantes, docentes y acompañantes por año y nivel; luego vincula el grupo con cohortes concretas de curso."
        eyebrow="Organización del aprendizaje"
        title="Grupos académicos"
      />
      <AcademicGroupsPanel
        canManage={data.access.capabilities.includes('learning.cohort.manage')}
        groups={data.groups.results}
        members={data.members}
        slug={slug}
      />
    </main>
  );
}
