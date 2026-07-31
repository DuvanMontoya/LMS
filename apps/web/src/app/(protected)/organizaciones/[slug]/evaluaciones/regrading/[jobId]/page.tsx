import { RetryRegradeButton } from '@/components/assessments/advanced-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { getRegradeJob } from '@/lib/assessments/server';

export default async function RegradingDetailPage({
  params,
}: Readonly<{ params: Promise<{ jobId: string; slug: string }> }>) {
  const { jobId, slug } = await params;
  const data = await getRegradeJob(slug, jobId);
  const { job } = data;
  const canManage = data.access.capabilities.includes(
    'assessment.regrading.manage',
  );
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          canManage && job.failed_attempts > 0 ? (
            <RetryRegradeButton
              expectedVersion={job.lock_version}
              jobId={job.id}
              slug={slug}
            />
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/regrading`,
            label: 'Recalificación',
          },
          { label: 'Detalle' },
        ]}
        description={job.reason}
        eyebrow="Trabajo durable y auditable"
        title={`Recalificación · ${job.assessment_title}`}
      />
      <section className="assessment-results-summary">
        <div>
          <p className="assessment-rail-kicker">Estado durable</p>
          <h2>
            <Badge variant="outline">{jobStatusLabel(job.status)}</Badge>
          </h2>
          <p>
            Origen: última calificación histórica de cada intento. Destino:
            revisión {job.grading_revision_number} de la versión{' '}
            {job.assessment_version_number}. Alcance:{' '}
            {job.delivery_id ? 'una entrega específica' : 'todos los intentos'}.
          </p>
        </div>
        <dl>
          <Metric label="Total" value={job.total_attempts} />
          <Metric label="Procesados" value={job.processed_attempts} />
          <Metric label="Exitosos" value={job.succeeded_attempts} />
          <Metric
            label="Sin cambios"
            value={
              data.attempts.filter((attempt) => attempt.status === 'skipped')
                .length
            }
          />
          <Metric label="Fallidos" value={job.failed_attempts} />
        </dl>
      </section>
      <section className="assessment-results-ledger">
        <header>
          <div>
            <p className="assessment-rail-kicker">
              Trazabilidad sin respuestas
            </p>
            <h2>Intentos procesados</h2>
          </div>
        </header>
        <div className="overflow-x-auto" tabIndex={0}>
          <table className="w-full min-w-3xl text-left text-sm">
            <caption className="sr-only">
              Intentos del trabajo de recalificación
            </caption>
            <thead>
              <tr>
                <th className="px-4 py-3">Intento</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Calificación anterior</th>
                <th className="px-4 py-3">Nueva calificación</th>
                <th className="px-4 py-3">Error seguro</th>
              </tr>
            </thead>
            <tbody>
              {data.attempts.map((attempt) => (
                <tr key={attempt.id}>
                  <td className="px-4 py-4 font-mono text-xs">
                    {shortIdentifier(attempt.attempt_id)}
                  </td>
                  <td className="px-4 py-4">
                    {attemptStatusLabel(attempt.status)}
                  </td>
                  <td className="px-4 py-4 font-mono text-xs">
                    {shortIdentifier(attempt.previous_grade_id)}
                  </td>
                  <td className="px-4 py-4 font-mono text-xs">
                    {shortIdentifier(attempt.new_grade_id)}
                  </td>
                  <td className="px-4 py-4">
                    {attempt.error_code || 'Sin error'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <footer className="border-t border-border bg-muted/15 px-5 py-3 text-xs text-muted-foreground sm:px-6">
          Creado {formatDate(job.created_at)} · iniciado{' '}
          {formatDate(job.started_at)}
          {' · '}completado {formatDate(job.completed_at)}
        </footer>
      </section>
    </main>
  );
}

function Metric({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function formatDate(value: string | null) {
  return value
    ? new Intl.DateTimeFormat('es-CO', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(value))
    : '—';
}

function jobStatusLabel(status: string) {
  return (
    {
      completed: 'Completada',
      failed: 'Fallida',
      queued: 'En cola',
      running: 'En proceso',
    }[status] ?? status
  );
}

function attemptStatusLabel(status: string) {
  return (
    {
      failed: 'Fallido',
      pending: 'Pendiente',
      processed: 'Recalculado',
      skipped: 'Sin cambios (ya vigente)',
    }[status] ?? status
  );
}

function shortIdentifier(value: string | null) {
  return value ? value.slice(0, 8) : '—';
}
