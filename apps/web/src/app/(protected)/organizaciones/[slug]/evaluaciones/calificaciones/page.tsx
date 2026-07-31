import { Award, BookOpenCheck, CheckCircle2, Clock3 } from 'lucide-react';

import { LearnerAssessmentNavigation } from '@/components/assessments/learner-assessment-navigation';
import { CourseGradebook } from '@/components/learning/course-gradebook';
import { PageHeader } from '@/components/platform/page-header';
import { getMyGradebookResults } from '@/lib/assessments/server';

export default async function LearnerGradesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getMyGradebookResults(slug);
  const completedActivities = data.gradebooks.reduce(
    (total, payload) => total + payload.summary.completed_columns,
    0,
  );
  const totalActivities = data.gradebooks.reduce(
    (total, payload) => total + payload.summary.total_columns,
    0,
  );
  const completeBooks = data.gradebooks.filter(
    (payload) => payload.summary.status === 'complete',
  );
  const consolidatedAverage = completeBooks.length
    ? completeBooks.reduce(
        (total, payload) =>
          total + payload.summary.weighted_percent_basis_points,
        0,
      ) /
      completeBooks.length /
      100
    : null;

  return (
    <main
      className="academic-page learner-grades-page"
      id="contenido-principal"
    >
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Mis calificaciones' },
        ]}
        description="Resultados por curso, pesos evaluativos y consolidado de los libros activos asociados a tus releases."
        eyebrow="Rendimiento académico"
        title="Mis calificaciones"
      />
      <LearnerAssessmentNavigation active="grades" slug={slug} />

      <section className="learner-grade-summary">
        <div>
          <p className="academic-kicker">Resumen personal</p>
          <h2>Estado de tus resultados</h2>
          <p>
            El consolidado usa únicamente libros completos. Los resultados
            pendientes permanecen visibles dentro de cada curso.
          </p>
        </div>
        <dl>
          <GradeMetric
            icon={<BookOpenCheck />}
            label="Cursos con libro"
            value={String(data.gradebooks.length)}
          />
          <GradeMetric
            icon={<CheckCircle2 />}
            label="Actividades calificadas"
            value={`${completedActivities}/${totalActivities}`}
          />
          <GradeMetric
            icon={<Clock3 />}
            label="Libros pendientes"
            value={String(data.gradebooks.length - completeBooks.length)}
          />
          <GradeMetric
            icon={<Award />}
            label="Promedio consolidado"
            value={
              consolidatedAverage === null
                ? 'Provisional'
                : `${consolidatedAverage.toFixed(2)} %`
            }
          />
        </dl>
      </section>

      <section className="learner-grade-detail">
        <header>
          <div>
            <p className="academic-kicker">Detalle por curso</p>
            <h2>Libros de calificaciones</h2>
            <p>
              Cada actividad conserva su peso, estado y resultado individual.
            </p>
          </div>
          <span>{data.gradebooks.length}</span>
        </header>
        <CourseGradebook gradebooks={data.gradebooks} />
      </section>
    </main>
  );
}

function GradeMetric({
  icon,
  label,
  value,
}: Readonly<{ icon: React.ReactNode; label: string; value: string }>) {
  return (
    <div>
      <dt>
        {icon}
        {label}
      </dt>
      <dd>{value}</dd>
    </div>
  );
}
