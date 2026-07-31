import Link from 'next/link';

import { CreateRegradeJobForm } from '@/components/assessments/advanced-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getRegradeJobs } from '@/lib/assessments/server';

export default async function RegradingPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getRegradeJobs(slug);
  const canManage = data.access.capabilities.includes(
    'assessment.regrading.manage',
  );
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: 'Recalificación' },
        ]}
        description="Recalificación asíncrona, idempotente y auditable sin sobrescribir calificaciones históricas."
        eyebrow="Recalificación institucional"
        title="Consola de recalificación"
      />
      {canManage ? (
        <section className="assessment-builder-section">
          <header className="assessment-builder-section__header">
            <div>
              <h2>Nueva recalificación</h2>
              <p>
                Se recalcularán resultados conservando todas las calificaciones
                históricas y decisiones manuales.
              </p>
            </div>
          </header>
          <CreateRegradeJobForm
            slug={slug}
            versionOptions={data.versionOptions}
          />
        </section>
      ) : null}
      <section className="assessment-results-ledger">
        <header>
          <div>
            <p className="assessment-rail-kicker">Trabajos durables</p>
            <h2>Historial de recalificaciones</h2>
          </div>
          <span>
            {data.jobs.length} {data.jobs.length === 1 ? 'trabajo' : 'trabajos'}
          </span>
        </header>
        <div className="overflow-x-auto" tabIndex={0}>
          <table className="w-full min-w-3xl text-left text-sm">
            <caption className="sr-only">
              Recalificaciones de evaluaciones y su progreso
            </caption>
            <thead>
              <tr>
                <th className="px-4 py-3">Evaluación / revisión</th>
                <th className="px-4 py-3">Alcance</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Progreso</th>
                <th className="px-4 py-3">Creado</th>
                <th className="px-4 py-3">Acción</th>
              </tr>
            </thead>
            <tbody>
              {data.jobs.map((job) => (
                <tr key={job.id}>
                  <td className="px-4 py-4">
                    <strong className="block">{job.assessment_title}</strong>
                    <span className="text-muted-foreground">
                      versión {job.assessment_version_number} · revisión de
                      destino {job.grading_revision_number}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    {job.delivery_name
                      ? `Entrega «${job.delivery_name}»`
                      : 'Todos los intentos'}
                  </td>
                  <td className="px-4 py-4">
                    <Badge variant="outline">{statusLabel(job.status)}</Badge>
                  </td>
                  <td className="px-4 py-4">
                    <div
                      aria-label={`Progreso: ${job.processed_attempts} de ${job.total_attempts}`}
                      aria-valuemax={Math.max(1, job.total_attempts)}
                      aria-valuemin={0}
                      aria-valuenow={job.processed_attempts}
                      className="h-2 w-28 overflow-hidden rounded-full bg-muted"
                      role="progressbar"
                    >
                      <span
                        className="block h-full rounded-full bg-primary transition-[width]"
                        style={{
                          width: `${Math.min(
                            100,
                            (job.processed_attempts /
                              Math.max(1, job.total_attempts)) *
                              100,
                          )}%`,
                        }}
                      />
                    </div>
                    <span className="mt-1 block text-xs text-muted-foreground">
                      {job.processed_attempts}/{job.total_attempts}
                    </span>
                  </td>
                  <td className="px-4 py-4">
                    {new Intl.DateTimeFormat('es-CO', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    }).format(new Date(job.created_at))}
                  </td>
                  <td className="px-4 py-4">
                    <Button asChild size="sm" variant="outline">
                      <Link
                        href={`/organizaciones/${slug}/evaluaciones/regrading/${job.id}`}
                      >
                        Ver detalle
                      </Link>
                    </Button>
                  </td>
                </tr>
              ))}
              {!data.jobs.length ? (
                <tr>
                  <td className="px-4 py-10 text-center" colSpan={6}>
                    No hay recalificaciones registradas.
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

function statusLabel(status: string) {
  return (
    {
      completed: 'Completado',
      failed: 'Fallido',
      queued: 'En cola',
      running: 'En proceso',
    }[status] ?? status
  );
}
