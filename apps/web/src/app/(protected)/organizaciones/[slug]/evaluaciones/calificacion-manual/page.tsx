import { ManualGradingQueue } from '@/components/assessments/manual-grading';
import { PageHeader } from '@/components/platform/page-header';
import { getPendingManualGrades } from '@/lib/assessments/server';

export default async function ManualGradingPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getPendingManualGrades(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/resultados`,
            label: 'Resultados',
          },
          { label: 'Calificación manual' },
        ]}
        description="Registra decisiones append-only sobre respuestas abiertas y recalcula el resultado."
        eyebrow="Manual grading"
        title="Calificación manual"
      />
      <ManualGradingQueue responses={data.responses} slug={slug} />
    </main>
  );
}
