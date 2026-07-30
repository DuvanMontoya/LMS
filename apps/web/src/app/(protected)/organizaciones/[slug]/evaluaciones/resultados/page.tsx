import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getAssessmentResults } from '@/lib/assessments/server';

export default async function AssessmentResultsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAssessmentResults(slug);
  const results = data.results.results;
  const graded = results.filter((result) => result.status === 'graded').length;
  const pending = results.filter(
    (result) => result.status === 'pending_manual',
  ).length;
  const passed = results.filter((result) => result.passed === true).length;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          <Button asChild size="sm" variant="outline">
            <Link
              href={`/organizaciones/${slug}/evaluaciones/calificacion-manual`}
            >
              Calificación manual
            </Link>
          </Button>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Resultados' },
        ]}
        description="Vista institucional de intentos y estados de calificación."
        eyebrow="Assessment results"
        title="Resultados de evaluaciones"
      />
      <section className="assessment-results-summary">
        <div>
          <p className="assessment-rail-kicker">Operación académica</p>
          <h2>Panorama de calificación</h2>
          <p>
            Seguimiento consolidado de intentos, decisiones automáticas y
            trabajo pendiente del equipo evaluador.
          </p>
        </div>
        <dl>
          <ResultMetric label="Intentos" value={results.length} />
          <ResultMetric label="Calificados" value={graded} />
          <ResultMetric label="Revisión manual" value={pending} />
          <ResultMetric label="Aprobados" value={passed} />
        </dl>
      </section>
      <section className="assessment-results-ledger">
        <header>
          <div>
            <p className="assessment-rail-kicker">Registro auditable</p>
            <h2>Libro de resultados</h2>
          </div>
          <span>{results.length} registros</span>
        </header>
        <div className="overflow-x-auto">
          <table className="w-full min-w-3xl text-left text-sm">
            <thead>
              <tr>
                <th className="px-4 py-3">Intento</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Puntaje</th>
                <th className="px-4 py-3">Basis points</th>
                <th className="px-4 py-3">Aprobación</th>
              </tr>
            </thead>
            <tbody>
              {results.map((result) => (
                <tr key={result.id}>
                  <td className="px-4 py-4 font-medium">
                    <span className="assessment-attempt-number">
                      #{result.attempt_number}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    <Badge variant="outline">{result.status}</Badge>
                  </td>
                  <td className="px-4 py-4 font-semibold">
                    {result.total_score} / {result.maximum_score}
                  </td>
                  <td className="px-4 py-4">
                    {result.basis_points === null
                      ? '—'
                      : `${(result.basis_points / 100).toFixed(2)} %`}
                  </td>
                  <td className="px-4 py-4">
                    {result.passed === null
                      ? 'Pendiente'
                      : result.passed
                        ? 'Sí'
                        : 'No'}
                  </td>
                </tr>
              ))}
              {!results.length ? (
                <tr>
                  <td className="px-4 py-12 text-center" colSpan={5}>
                    <strong>Aún no hay intentos registrados.</strong>
                    <p className="mt-1 text-muted-foreground">
                      Los resultados aparecerán aquí cuando los learners envíen
                      sus evaluaciones.
                    </p>
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  );
}

function ResultMetric({
  label,
  value,
}: Readonly<{ label: string; value: number }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
