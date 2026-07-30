import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
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
          result.status === 'pending_manual'
            ? 'Calificación manual pendiente'
            : 'Intento calificado'
        }
      />
      <section className="assessment-result-hero">
        <div className="assessment-result-hero__heading">
          <Badge variant={result.status === 'graded' ? 'secondary' : 'outline'}>
            {result.status}
          </Badge>
          <p>Intento {result.attempt_number}</p>
          <h2>
            {result.status === 'pending_manual'
              ? 'Tu envío está en revisión'
              : result.passed
                ? 'Objetivo alcanzado'
                : 'Resultado disponible'}
          </h2>
          <p>
            {result.status === 'pending_manual'
              ? 'El equipo docente completará la rúbrica pendiente antes de publicar el resultado definitivo.'
              : 'La información visible respeta la política de feedback fijada al momento de la entrega.'}
          </p>
        </div>
        <dl className="assessment-result-scorecard">
          <ResultFact
            label="Puntaje"
            value={`${result.total_score} / ${result.maximum_score}`}
          />
          <ResultFact
            label="Porcentaje"
            value={
              result.basis_points === null
                ? 'Pendiente'
                : `${(result.basis_points / 100).toFixed(2)} %`
            }
          />
          <ResultFact
            label="Estado"
            value={
              result.passed === null
                ? 'Pendiente'
                : result.passed
                  ? 'Aprobado'
                  : 'No aprobado'
            }
          />
        </dl>
      </section>
      <section className="assessment-result-detail">
        <header>
          <div>
            <p className="assessment-rail-kicker">Trazabilidad del intento</p>
            <h2>Detalle de retroalimentación</h2>
          </div>
          <span>{result.feedback.length} ítems visibles</span>
        </header>
        {result.feedback.length ? (
          <ol>
            {result.feedback.map((entry, index) => (
              <li key={String(entry.attempt_item_id ?? index)}>
                <span>{String(index + 1).padStart(2, '0')}</span>
                <div>
                  <strong>
                    {String(entry.score ?? '0')} /{' '}
                    {String(entry.maximum ?? '0')} puntos
                  </strong>
                  {entry.message ? <p>{String(entry.message)}</p> : null}
                  {entry.manual_feedback ? (
                    <blockquote>{String(entry.manual_feedback)}</blockquote>
                  ) : null}
                </div>
              </li>
            ))}
          </ol>
        ) : (
          <div className="assessment-result-detail__empty">
            <strong>No hay retroalimentación pública para mostrar.</strong>
            <p>
              La política de esta evaluación limita el detalle visible del
              intento.
            </p>
          </div>
        )}
        <footer>
          <Button asChild variant="outline">
            <Link href={`/organizaciones/${slug}/evaluaciones/asignadas`}>
              Volver a mis evaluaciones
            </Link>
          </Button>
        </footer>
      </section>
    </main>
  );
}

function ResultFact({
  label,
  value,
}: Readonly<{ label: string; value: string }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
