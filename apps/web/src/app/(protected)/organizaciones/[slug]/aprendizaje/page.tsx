import {
  ArrowRight,
  BookOpenCheck,
  CirclePause,
  GraduationCap,
} from 'lucide-react';
import Link from 'next/link';

import { LearnerDeliveryList } from '@/components/assessments/learner-deliveries';
import { LearningProgress } from '@/components/learning/learning-progress';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { accessStateLabel } from '@/lib/learning/labels';
import { getMyAssessmentDeliveries } from '@/lib/assessments/server';
import { getMyLearning } from '@/lib/learning/server';

export default async function MyLearningPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const [data, assessmentData] = await Promise.all([
    getMyLearning(slug),
    getMyAssessmentDeliveries(slug),
  ]);
  const pendingAssessments = assessmentData.deliveries.filter(
    (assignment) =>
      assignment.status === 'active' &&
      (assignment.in_progress_attempt_id ||
        assignment.attempts_used < assignment.attempt_limit),
  );
  const completedAssessments = assessmentData.deliveries.filter(
    (assignment) =>
      assignment.latest_attempt_id &&
      assignment.latest_attempt_status !== 'in_progress',
  );
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Mi aprendizaje' },
        ]}
        description="Cursos vinculados a tus matrículas institucionales y al release que te fue asignado."
        eyebrow="Experiencia del estudiante"
        title="Mi aprendizaje"
      />
      <section className="learning-overview">
        <div>
          <p className="academic-kicker">Resumen personal</p>
          <h2>Tu actividad académica</h2>
          <p>
            Cursos, evaluaciones y resultados reunidos en una sola experiencia
            de seguimiento.
          </p>
        </div>
        <dl>
          <LearningMetric label="Matrículas" value={data.enrollments.length} />
          <LearningMetric
            label="Pendientes"
            value={pendingAssessments.length}
          />
          <LearningMetric
            label="Completadas"
            value={completedAssessments.length}
          />
        </dl>
      </section>
      {data.enrollments.length ? (
        <ul className="learning-course-grid">
          {data.enrollments.map((enrollment) => {
            const available = enrollment.access_state === 'available';
            return (
              <li
                className="learning-course-card"
                key={enrollment.enrollment_id}
              >
                <div className="flex items-start gap-3">
                  <span className="learning-course-card__icon">
                    {available ? (
                      <GraduationCap className="size-5 text-primary" />
                    ) : (
                      <CirclePause className="size-5 text-muted-foreground" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold">
                        {enrollment.course.title}
                      </h2>
                      <Badge variant={available ? 'secondary' : 'outline'}>
                        {accessStateLabel(enrollment.access_state)}
                      </Badge>
                    </div>
                    <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                      {enrollment.course.summary}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Release {enrollment.release_number}
                      {enrollment.cohort ? ` · ${enrollment.cohort.name}` : ''}
                    </p>
                  </div>
                </div>
                <div className="mt-5 border-y py-4">
                  <LearningProgress progress={enrollment.progress} />
                </div>
                {available && enrollment.resume.href ? (
                  <Button asChild className="mt-4" size="sm">
                    <Link href={enrollment.resume.href}>
                      {enrollment.progress.status === 'not_started'
                        ? 'Comenzar'
                        : 'Continuar'}
                      <ArrowRight data-icon="inline-end" />
                    </Link>
                  </Button>
                ) : (
                  <p className="mt-4 text-sm text-muted-foreground">
                    El contenido no puede abrirse mientras este estado esté
                    vigente.
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <section className="platform-empty-state">
          <BookOpenCheck className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">Aún no tienes matrículas</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Los cursos aparecerán aquí cuando una institución te matricule.
          </p>
        </section>
      )}
      <section className="learning-assessment-section">
        <header>
          <div>
            <p className="academic-kicker">Próximas acciones</p>
            <h2>Evaluaciones pendientes</h2>
            <p>
              Instrumentos vinculados a tu release vigente; no alteran el
              porcentaje de progreso del curso.
            </p>
          </div>
          <span>{pendingAssessments.length}</span>
        </header>
        <LearnerDeliveryList deliveries={pendingAssessments} slug={slug} />
      </section>
      <section className="learning-assessment-section">
        <header>
          <div>
            <p className="academic-kicker">Historial</p>
            <h2>Evaluaciones completadas</h2>
            <p>Consulta los intentos enviados y el feedback disponible.</p>
          </div>
          <span>{completedAssessments.length}</span>
        </header>
        {completedAssessments.length ? (
          <ul className="learning-completed-list">
            {completedAssessments.map((assignment) => (
              <li
                className="flex flex-wrap items-center gap-3 py-4"
                key={assignment.id}
              >
                <div className="min-w-0 flex-1">
                  <h3 className="font-semibold">
                    {assignment.delivery.assessment_title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    Intento {assignment.attempts_used} ·{' '}
                    {assignment.latest_attempt_status}
                  </p>
                </div>
                <Button asChild size="sm" variant="outline">
                  <Link
                    href={`/organizaciones/${slug}/evaluaciones/intentos/${assignment.latest_attempt_id}/resultado`}
                  >
                    Ver resultado
                  </Link>
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="learning-assessment-section__empty">
            <GraduationCap />
            <p>Aún no hay intentos enviados.</p>
          </div>
        )}
      </section>
    </main>
  );
}

function LearningMetric({
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
