import { AnalyticsRefreshForm } from '@/components/assessments/advanced-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { getAssessmentAnalytics } from '@/lib/assessments/server';

export default async function AssessmentAnalyticsDetailPage({
  params,
}: Readonly<{
  params: Promise<{ assessmentVersionId: string; slug: string }>;
}>) {
  const { assessmentVersionId, slug } = await params;
  const data = await getAssessmentAnalytics(slug, assessmentVersionId);
  const canRefresh =
    data.access.capabilities.includes('assessment.analytics.refresh') &&
    data.version.revisions.length > 0;
  const { snapshot } = data;
  const snapshotRevision = snapshot
    ? data.version.revisions.find(
        (revision) => revision.id === snapshot.grading_revision_id,
      )
    : null;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/analitica`,
            label: 'Analítica',
          },
          { label: `Versión ${data.version.number}` },
        ]}
        description="Las métricas son descriptivas, incorporan crédito parcial y no justifican por sí solas eliminar preguntas."
        eyebrow="Snapshot descriptivo por versión"
        title={`Analítica · ${data.version.title}`}
      />
      {canRefresh ? (
        <section className="assessment-builder-section">
          <header className="assessment-builder-section__header">
            <div>
              <h2>Regenerar snapshot</h2>
              <p>
                El trabajo se ejecuta de forma durable para una revisión de
                calificación explícita.
              </p>
            </div>
          </header>
          <AnalyticsRefreshForm
            assessmentVersionId={assessmentVersionId}
            revisions={data.version.revisions}
            slug={slug}
          />
        </section>
      ) : null}
      {!snapshot ? (
        <section className="assessment-results-summary">
          <div>
            <p className="assessment-rail-kicker">Sin snapshot</p>
            <h2>Aún no hay analítica agregada para esta versión</h2>
            <p>
              Solicita una actualización con una revisión válida o vuelve cuando
              finalice el trabajo durable.
            </p>
          </div>
        </section>
      ) : (
        <>
          <section className="assessment-results-summary">
            <div>
              <p className="assessment-rail-kicker">Muestra agregada</p>
              <h2>
                {snapshot.insufficient_sample ? (
                  <Badge variant="outline">Muestra pequeña</Badge>
                ) : (
                  <Badge variant="outline">Umbral satisfecho</Badge>
                )}
              </h2>
              <p>
                Snapshot generado · revisión{' '}
                {snapshotRevision?.number ?? 'histórica'}
              </p>
            </div>
            <dl>
              <Metric label="Muestra" value={String(snapshot.sample_size)} />
              <Metric
                label="Media"
                value={percent(snapshot.mean_percent_basis_points)}
              />
              <Metric
                label="Mediana"
                value={percent(snapshot.median_percent_basis_points)}
              />
              <Metric
                label="Aprobación"
                value={percent(snapshot.pass_rate_basis_points)}
              />
            </dl>
          </section>
          <section className="mt-5 grid gap-4 sm:grid-cols-2">
            <RangeBar
              maximum={snapshot.p75_percent_basis_points}
              minimum={snapshot.p25_percent_basis_points}
            />
            <article className="rounded-xl border border-border bg-card p-5 shadow-[0_10px_30px_rgb(15_23_42_/_0.04)]">
              <p className="assessment-rail-kicker">Uso responsable</p>
              <h2 className="mt-1 text-base font-semibold">Interpretación</h2>
              <p className="mt-2 text-sm leading-6 text-muted-foreground">
                P25 {percent(snapshot.p25_percent_basis_points)} · P75{' '}
                {percent(snapshot.p75_percent_basis_points)}. No representa
                causalidad ni reemplaza revisión pedagógica.
              </p>
            </article>
          </section>
          <section className="assessment-results-ledger">
            <header>
              <div>
                <p className="assessment-rail-kicker">Ítems</p>
                <h2>Facilidad, discriminación y omisiones</h2>
              </div>
            </header>
            <div className="overflow-x-auto" tabIndex={0}>
              <table className="w-full min-w-4xl text-left text-sm">
                <caption className="sr-only">
                  Analítica agregada por ítem y opciones seleccionadas
                </caption>
                <thead>
                  <tr>
                    <th className="px-4 py-3">Ítem</th>
                    <th className="px-4 py-3">Presentado</th>
                    <th className="px-4 py-3">Facilidad</th>
                    <th className="px-4 py-3">Discriminación</th>
                    <th className="px-4 py-3">Omisiones</th>
                    <th className="px-4 py-3">Opciones</th>
                  </tr>
                </thead>
                <tbody>
                  {snapshot.items.map((item) => (
                    <tr key={item.id}>
                      <td className="px-4 py-4">
                        <strong>{questionTypeLabel(item.question_type)}</strong>
                        <span className="block font-mono text-xs">
                          {item.assessment_item_id.slice(0, 8)}
                        </span>
                      </td>
                      <td className="px-4 py-4">{item.presented_count}</td>
                      <td className="px-4 py-4">
                        {percent(item.difficulty_basis_points)}
                        <Bar value={item.difficulty_basis_points} />
                      </td>
                      <td className="px-4 py-4">
                        {item.discrimination_suppressed
                          ? `Suprimida (n=${item.discrimination_sample_size})`
                          : item.discrimination}
                      </td>
                      <td className="px-4 py-4">
                        {item.omitted_count} de {item.presented_count}
                      </td>
                      <td className="px-4 py-4">
                        {item.options.length
                          ? item.options
                              .map(
                                (option) =>
                                  `${option.option_id}: ${percent(option.selected_rate_basis_points)}`,
                              )
                              .join(' · ')
                          : 'No aplica'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <p className="text-sm text-muted-foreground">
            Índice de facilidad alto → más crédito promedio. Discriminación
            positiva → el ítem tiende a distinguir resultados globales más altos
            y más bajos. No causal; no es una recomendación automática.
          </p>
        </>
      )}
    </main>
  );
}

function Metric({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function percent(value: number | null) {
  return value === null ? 'Suprimido' : `${(value / 100).toFixed(2)} %`;
}

function questionTypeLabel(type: string) {
  return (
    {
      long_text: 'Respuesta extensa',
      matching: 'Emparejamiento',
      mathematical_expression: 'Expresión matemática',
      multiple_choice: 'Selección múltiple',
      numeric: 'Respuesta numérica',
      ordering: 'Ordenamiento',
      short_text: 'Respuesta corta',
      single_choice: 'Selección única',
      true_false: 'Verdadero o falso',
    }[type] ?? type
  );
}

function Bar({ value }: Readonly<{ value: number }>) {
  return (
    <div
      aria-label={`${(value / 100).toFixed(2)} por ciento`}
      className="mt-2 h-2 w-36 max-w-full overflow-hidden rounded bg-muted"
      role="img"
    >
      <span
        className="block h-full bg-primary"
        style={{ width: `${Math.min(100, Math.max(0, value / 100))}%` }}
      />
    </div>
  );
}

function RangeBar({
  maximum,
  minimum,
}: Readonly<{ maximum: number | null; minimum: number | null }>) {
  if (minimum === null || maximum === null) {
    return (
      <article className="rounded-xl border border-border bg-card p-5 shadow-[0_10px_30px_rgb(15_23_42_/_0.04)]">
        <p className="assessment-rail-kicker">Privacidad estadística</p>
        <h2 className="mt-1 text-base font-semibold">
          Distribución intercuartílica
        </h2>
        <p className="mt-2 text-sm leading-6 text-muted-foreground">
          Suprimida por tamaño de muestra.
        </p>
      </article>
    );
  }
  return (
    <article className="rounded-xl border border-border bg-card p-5 shadow-[0_10px_30px_rgb(15_23_42_/_0.04)]">
      <p className="assessment-rail-kicker">Rango central</p>
      <h2 className="mt-1 text-base font-semibold">
        Distribución intercuartílica
      </h2>
      <div
        aria-label={`Entre ${(minimum / 100).toFixed(2)} y ${(maximum / 100).toFixed(2)} por ciento`}
        className="relative mt-4 h-4 rounded bg-muted"
        role="img"
      >
        <span
          className="absolute h-full rounded bg-primary"
          style={{
            left: `${minimum / 100}%`,
            width: `${Math.max(0, maximum - minimum) / 100}%`,
          }}
        />
      </div>
    </article>
  );
}
