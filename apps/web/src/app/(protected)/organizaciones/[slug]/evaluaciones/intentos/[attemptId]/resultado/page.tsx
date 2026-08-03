import { PageHeader } from '@/components/platform/page-header';
import { AssessmentResultSummary } from '@/components/assessments/assessment-result-summary';
import { getAssessmentResult } from '@/lib/assessments/server';

export default async function AssessmentResultPage({
  params,
}: Readonly<{ params: Promise<{ attemptId: string; slug: string }> }>) {
  const { attemptId, slug } = await params;
  const data = await getAssessmentResult(slug, attemptId);
  const result = data.result;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/asignadas`,
            label: 'Mis evaluaciones',
          },
          { label: 'Resultado' },
        ]}
        description="Resultado sujeto a la política de feedback fijada en la versión de evaluación."
        eyebrow="Resultado del intento"
        title={
          result.status === 'grading_pending'
            ? 'Calificación matemática en proceso'
            : result.status === 'pending_manual'
              ? 'Calificación manual pendiente'
              : 'Intento calificado'
        }
      />
      <AssessmentResultSummary
        attemptId={attemptId}
        footerHref={`/organizaciones/${slug}/evaluaciones/asignadas`}
        footerLabel="Volver a mis evaluaciones"
        result={result}
        slug={slug}
      />
    </main>
  );
}
