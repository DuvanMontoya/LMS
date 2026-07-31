import { LearnerAssessmentNavigation } from '@/components/assessments/learner-assessment-navigation';
import { LearnerDeliveryList } from '@/components/assessments/learner-deliveries';
import { PageHeader } from '@/components/platform/page-header';
import { getMyDeliveries } from '@/lib/assessments/server';

export default async function AssignedAssessmentsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getMyDeliveries(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Mis evaluaciones' },
        ]}
        description="Actividades disponibles, intentos en curso y fechas de cierre de tus evaluaciones asignadas."
        eyebrow="Experiencia del estudiante"
        title="Mis evaluaciones"
      />
      <LearnerAssessmentNavigation active="assessments" slug={slug} />
      <section className="learner-assessment-catalog">
        <header>
          <div>
            <p className="academic-kicker">Actividades asignadas</p>
            <h2>Evaluaciones disponibles</h2>
            <p>
              Esta pantalla contiene únicamente evaluaciones. Tus resultados
              ponderados están en Calificaciones.
            </p>
          </div>
          <span>{data.deliveries.length}</span>
        </header>
        <LearnerDeliveryList deliveries={data.deliveries} slug={slug} />
      </section>
    </main>
  );
}
