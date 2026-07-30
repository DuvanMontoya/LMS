import { AttemptRunner } from '@/components/assessments/attempt-runner';
import { PageHeader } from '@/components/platform/page-header';
import { getAssessmentAttempt } from '@/lib/assessments/server';

export default async function AssessmentAttemptPage({
  params,
}: Readonly<{ params: Promise<{ attemptId: string; slug: string }> }>) {
  const { attemptId, slug } = await params;
  const data = await getAssessmentAttempt(slug, attemptId);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/asignadas`,
            label: 'Mis evaluaciones',
          },
          { label: `Intento ${data.attempt.attempt_number}` },
        ]}
        description="Las respuestas se guardan sólo cuando pulsas Guardar; el envío es definitivo."
        eyebrow="Intento en curso"
        title={`Intento ${data.attempt.attempt_number}`}
      />
      <AttemptRunner initialAttempt={data.attempt} slug={slug} />
    </main>
  );
}
