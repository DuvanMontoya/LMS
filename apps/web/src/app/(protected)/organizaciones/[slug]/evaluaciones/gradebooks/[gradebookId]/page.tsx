import {
  ActivateGradebookButton,
  AddGradebookColumnForm,
  GradebookColumnManager,
} from '@/components/assessments/advanced-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { getGradebook } from '@/lib/assessments/server';

export default async function GradebookDetailPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ gradebookId: string; slug: string }>;
  searchParams: Promise<{ cohort?: string }>;
}>) {
  const [{ gradebookId, slug }, query] = await Promise.all([
    params,
    searchParams,
  ]);
  const data = await getGradebook(slug, gradebookId);
  const { gradebook } = data;
  const activeColumns = gradebook.columns
    .filter((column) => column.status === 'active')
    .sort((left, right) => left.position - right.position);
  const activeWeight = activeColumns.reduce(
    (total, column) => total + column.weight_basis_points,
    0,
  );
  const activationReady =
    activeColumns.length > 0 &&
    activeWeight === 10_000 &&
    activeColumns.every((column, index) => column.position === index + 1);
  const cohorts = [
    ...new Map(
      data.summaries
        .filter((summary) => summary.cohort_id)
        .map((summary) => [
          summary.cohort_id!,
          summary.cohort_name ?? summary.cohort_id!,
        ]),
    ),
  ];
  const summaries = query.cohort
    ? data.summaries.filter((summary) => summary.cohort_id === query.cohort)
    : data.summaries;
  const entries = new Map(
    data.entries.map((entry) => [
      `${entry.release_assignment_id}:${entry.column_id}`,
      entry,
    ]),
  );
  const deliveries = data.deliveries
    .filter(
      (delivery) =>
        delivery.course_release_id === gradebook.course_release_id &&
        !gradebook.columns.some((column) => column.delivery_id === delivery.id),
    )
    .map((delivery) => ({
      id: delivery.id,
      label: `${delivery.assessment_title} · ${delivery.name}`,
    }));
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          data.canManage && gradebook.status === 'draft' ? (
            <ActivateGradebookButton
              expectedVersion={gradebook.lock_version}
              gradebookId={gradebook.id}
              ready={activationReady}
              slug={slug}
            />
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/gradebooks`,
            label: 'Libros de calificaciones',
          },
          {
            label: `${gradebook.course_title} · release ${gradebook.release_number}`,
          },
        ]}
        description="La tabla es de consulta: ninguna calificación se edita directamente en una celda."
        eyebrow="Resumen ponderado del release"
        title={`${gradebook.course_title} · libro de calificaciones`}
      />
      <section className="assessment-results-summary assessment-results-summary--gradebook">
        <div>
          <p className="assessment-rail-kicker">Configuración</p>
          <h2>
            <Badge variant="outline">
              {gradebook.status === 'active' ? 'Activo' : 'Borrador'}
            </Badge>
          </h2>
          <p>
            {activeColumns.length}{' '}
            {activeColumns.length === 1 ? 'columna activa' : 'columnas activas'}{' '}
            · peso configurado {(activeWeight / 100).toFixed(2)}%
          </p>
        </div>
        <dl>
          <Metric label="Estudiantes" value={data.summaries.length} />
          <Metric
            label="Completos"
            value={
              data.summaries.filter((summary) => summary.status === 'complete')
                .length
            }
          />
          <Metric label="Columnas activas" value={activeColumns.length} />
        </dl>
      </section>
      {data.canManage && gradebook.status === 'draft' ? (
        <>
          <GradebookColumnManager
            columns={gradebook.columns}
            expectedVersion={gradebook.lock_version}
            gradebookId={gradebook.id}
            slug={slug}
          />
          <section className="assessment-builder-section">
            <header className="assessment-builder-section__header">
              <div>
                <h2>Añadir columna</h2>
                <p>
                  Selecciona una entrega del mismo release, su peso y la regla
                  highest/latest.
                </p>
              </div>
            </header>
            <AddGradebookColumnForm
              deliveries={deliveries}
              expectedVersion={gradebook.lock_version}
              gradebookId={gradebook.id}
              slug={slug}
            />
          </section>
        </>
      ) : null}
      <section className="assessment-results-ledger">
        <header>
          <div>
            <p className="assessment-rail-kicker">Vista por estudiante</p>
            <h2>Resultados ponderados</h2>
          </div>
          <form>
            <label className="flex items-center gap-2 text-sm">
              <span>Sección</span>
              <select
                className="academic-control"
                defaultValue={query.cohort ?? ''}
                name="cohort"
              >
                <option value="">Todas</option>
                {cohorts.map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
          </form>
        </header>
        <div className="overflow-x-auto" tabIndex={0}>
          <table className="w-full min-w-4xl text-left text-sm">
            <caption className="sr-only">
              Calificaciones por estudiante, evaluación y resumen ponderado
            </caption>
            <thead>
              <tr>
                <th className="sticky left-0 bg-background px-4 py-3">
                  Estudiante
                </th>
                {activeColumns.map((column) => (
                  <th className="px-4 py-3" key={column.id}>
                    {column.title}
                    <span className="block text-xs font-normal">
                      {(column.weight_basis_points / 100).toFixed(2)} % ·{' '}
                      {column.attempt_aggregation === 'highest'
                        ? 'mejor intento'
                        : 'último intento'}
                    </span>
                  </th>
                ))}
                <th className="px-4 py-3">Resumen</th>
                <th className="px-4 py-3">Estado</th>
              </tr>
            </thead>
            <tbody>
              {summaries.map((summary) => (
                <tr key={summary.id}>
                  <th
                    className="sticky left-0 bg-background px-4 py-4 font-medium"
                    scope="row"
                  >
                    {summary.learner_name}
                    <span className="block text-xs text-muted-foreground">
                      {summary.cohort_name ?? 'Sin sección'}
                    </span>
                  </th>
                  {activeColumns.map((column) => {
                    const entry = entries.get(
                      `${summary.release_assignment_id}:${column.id}`,
                    );
                    return (
                      <td className="px-4 py-4" key={column.id}>
                        {entry?.status === 'graded' &&
                        entry.percent_basis_points !== null
                          ? `${(entry.percent_basis_points / 100).toFixed(2)} %`
                          : entry?.status === 'pending'
                            ? 'Pendiente'
                            : 'Sin resultado'}
                      </td>
                    );
                  })}
                  <td className="px-4 py-4 font-semibold">
                    {(summary.weighted_percent_basis_points / 100).toFixed(2)} %
                  </td>
                  <td className="px-4 py-4">
                    {summary.status === 'complete' ? 'Completo' : 'Incompleto'}
                  </td>
                </tr>
              ))}
              {!summaries.length ? (
                <tr>
                  <td
                    className="px-4 py-10 text-center"
                    colSpan={activeColumns.length + 3}
                  >
                    No hay estudiantes para este filtro.
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

function Metric({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
