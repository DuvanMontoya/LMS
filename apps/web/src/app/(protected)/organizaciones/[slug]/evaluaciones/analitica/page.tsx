import { AnalyticsLookupForm } from '@/components/assessments/advanced-actions';
import { PageHeader } from '@/components/platform/page-header';
import { getAnalyticsContext } from '@/lib/assessments/server';

export default async function AssessmentAnalyticsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAnalyticsContext(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: 'Analítica' },
        ]}
        description="Snapshots agregados por versión y revisión de calificación, con umbrales de privacidad."
        eyebrow="Lectura institucional de resultados"
        title="Analítica de evaluaciones"
      />
      <section className="assessment-builder-section">
        <header className="assessment-builder-section__header">
          <div>
            <h2>Consultar versión</h2>
            <p>
              Selecciona una evaluación aprobada para abrir su último snapshot
              global por revisión de calificación.
            </p>
          </div>
        </header>
        <AnalyticsLookupForm slug={slug} versionOptions={data.versionOptions} />
      </section>
      <section className="assessment-results-summary">
        <div>
          <p className="assessment-rail-kicker">Lectura responsable</p>
          <h2>Indicadores descriptivos, no decisiones automáticas</h2>
          <p>
            La facilidad alta indica más crédito promedio. Una discriminación
            positiva indica asociación con resultados globales más altos, no
            causalidad.
          </p>
        </div>
        <ul className="space-y-2 text-sm">
          <li>Las muestras pequeñas se suprimen o advierten.</li>
          <li>El crédito parcial cambia la interpretación de facilidad.</li>
          <li>Revisa contenido y población antes de intervenir un ítem.</li>
        </ul>
      </section>
    </main>
  );
}
