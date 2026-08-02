import { AcademicPeriodsPanel } from '@/components/learning/academic-periods-panel';
import { PageHeader } from '@/components/platform/page-header';
import { getAcademicPeriods } from '@/lib/learning/server';

export default async function AcademicPeriodsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAcademicPeriods(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Periodos académicos' },
        ]}
        description="Define ventanas institucionales explícitas antes de crear secciones, calendarizar actividades o consolidar calificaciones."
        eyebrow="Gobierno académico"
        title="Periodos académicos"
      />
      <AcademicPeriodsPanel
        canManage={data.access.capabilities.includes('learning.cohort.manage')}
        periods={data.periods.results}
        slug={slug}
      />
    </main>
  );
}
