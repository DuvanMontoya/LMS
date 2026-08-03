import {
  ArrowLeft,
  ArrowRight,
  BookOpenText,
  CalendarClock,
  ChevronLeft,
  ClipboardCheck,
  ListTree,
  LockKeyhole,
  PanelLeftClose,
  UserRound,
  Video,
} from 'lucide-react';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { AttemptRunner } from '@/components/assessments/attempt-runner';
import { LearnerDeliveryList } from '@/components/assessments/learner-deliveries';
import { CourseCurriculum } from '@/components/learning/course-curriculum';
import { LearningProgress } from '@/components/learning/learning-progress';
import { LiveClassroom } from '@/components/scheduling/live-classroom';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  getAssessmentAttempt,
  getMyAssessmentDeliveries,
} from '@/lib/assessments/server';
import {
  getEnrollmentForCourse,
  getLearningActivity,
  getLearningOutline,
} from '@/lib/learning/server';
import { getLiveSessions } from '@/lib/scheduling/server';

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export default async function LearningActivityPage({
  params,
}: Readonly<{
  params: Promise<{
    activityId: string;
    courseSlug: string;
    slug: string;
  }>;
}>) {
  const { activityId, courseSlug, slug } = await params;
  const { enrollment } = await getEnrollmentForCourse(slug, courseSlug);
  const data = await getLearningActivity(
    slug,
    enrollment.enrollment_id,
    activityId,
  );
  const activity = record(data.payload.activity) ? data.payload.activity : {};
  const type = typeof activity.type === 'string' ? activity.type : '';
  const binding = record(activity.binding) ? activity.binding : {};
  if (type === 'lesson' && typeof binding.unit_id === 'string') {
    redirect(
      `/organizaciones/${slug}/aprender/${courseSlug}/unidades/${binding.unit_id}`,
    );
  }

  const [outlineData, assessmentData, liveData] = await Promise.all([
    getLearningOutline(slug, enrollment.enrollment_id),
    getMyAssessmentDeliveries(slug),
    getLiveSessions(slug, { courseSlug }),
  ]);
  const matchingDeliveries = assessmentData.deliveries.filter(
    (assignment) => assignment.delivery.course_group_activity_id === activityId,
  );
  const matchingSessions = liveData.sessions.filter(
    (session) => session.course_group_activity_id === activityId,
  );
  const activeAttemptId = matchingDeliveries.find(
    (assignment) => assignment.in_progress_attempt_id,
  )?.in_progress_attempt_id;
  const activeAttempt = activeAttemptId
    ? (await getAssessmentAttempt(slug, activeAttemptId)).attempt
    : null;
  const primarySession =
    matchingSessions.find((session) => session.status === 'live') ??
    matchingSessions.find((session) => session.canJoin || session.canStart) ??
    matchingSessions.find((session) => session.status === 'scheduled') ??
    matchingSessions[0];

  const status = typeof activity.status === 'string' ? activity.status : '';
  const title =
    typeof activity.title === 'string'
      ? activity.title
      : 'Actividad curricular';
  const navigation = record(data.payload.navigation)
    ? data.payload.navigation
    : {};
  const previous = record(navigation.previous) ? navigation.previous : null;
  const next = record(navigation.next) ? navigation.next : null;
  const outlineHref = `/organizaciones/${slug}/aprender/${courseSlug}`;
  const activityHref = `${outlineHref}/actividades/${activityId}`;
  const allActivities = outlineData.outline.modules.flatMap(
    (module) => module.activities,
  );
  const activityNumber = allActivities.findIndex(
    (item) => item.id === activityId,
  );
  const currentModule = outlineData.outline.modules.find((module) =>
    module.activities.some((item) => item.id === activityId),
  );
  const totalActivities =
    outlineData.outline.progress.completion.total_required;
  const completedActivities =
    outlineData.outline.progress.completion.completed_required;

  return (
    <main
      className="learning-player"
      data-release-number={data.payload.release_number}
      id="contenido-principal"
    >
      <header className="learning-player__topbar">
        <Link
          aria-label={`Volver a ${enrollment.course.title}`}
          className="learning-player__brand"
          href={outlineHref}
        >
          <span>
            <BookOpenText />
          </span>
          <span>
            <small>Curso</small>
            <strong>{enrollment.course.title}</strong>
          </span>
        </Link>
        <div className="learning-player__position">
          <span>
            Actividad {Math.max(1, activityNumber + 1)} de{' '}
            {allActivities.length}
          </span>
          <p>{title}</p>
        </div>
        <Badge className="learning-player__release" variant="outline">
          Release {data.payload.release_number}
        </Badge>
        <Button asChild size="sm" variant="ghost">
          <Link
            aria-label={`Salir del aula y volver a ${enrollment.course.title}`}
            href={outlineHref}
          >
            <PanelLeftClose />
            <span className="hidden sm:inline">Salir del aula</span>
          </Link>
        </Button>
      </header>

      <details className="learning-player__mobile-outline">
        <summary>
          <ListTree />
          Contenido del curso
          <progress
            aria-label={`${completedActivities} de ${totalActivities} actividades completadas`}
            max={totalActivities}
            value={completedActivities}
          />
          <span>
            {completedActivities}/{totalActivities}
          </span>
        </summary>
        <div>
          <LearningProgress progress={outlineData.outline.progress} />
          <CourseCurriculum
            currentActivityId={activityId}
            modules={outlineData.outline.modules}
            variant="player"
          />
        </div>
      </details>

      <div className="learning-player__layout">
        <aside className="learning-player__sidebar">
          <header>
            <div>
              <span>Contenido del curso</span>
              <small>
                {completedActivities}/{totalActivities} completadas
              </small>
            </div>
            <LearningProgress progress={outlineData.outline.progress} />
          </header>
          <div className="learning-player__curriculum-scroll">
            <CourseCurriculum
              currentActivityId={activityId}
              modules={outlineData.outline.modules}
              variant="player"
            />
          </div>
          <footer>
            <Button asChild size="sm" variant="ghost">
              <Link href={outlineHref}>
                <ChevronLeft />
                Vista general del curso
              </Link>
            </Button>
          </footer>
        </aside>

        <div className="learning-player__stage">
          <article className="learning-player__lesson learning-player__activity">
            <header className="learning-player__lesson-heading">
              <p>
                {currentModule
                  ? `Módulo ${currentModule.position} · ${currentModule.title}`
                  : type === 'assessment'
                    ? 'Evaluación del curso'
                    : 'Clase en vivo del curso'}
              </p>
              <span className="mt-2 flex flex-wrap items-center gap-2">
                <Badge variant="outline">
                  {type === 'assessment' ? 'Evaluación' : 'Clase en vivo'}
                </Badge>
                {activity.required ? <Badge>Obligatoria</Badge> : null}
                <Badge variant="secondary">{activityStatusLabel(status)}</Badge>
              </span>
              <h1>{title}</h1>
              {typeof activity.summary === 'string' && activity.summary ? (
                <div>{activity.summary}</div>
              ) : null}
            </header>

            <div className="learning-player__activity-body">
              {status === 'locked' ? (
                <Alert>
                  <LockKeyhole />
                  <AlertTitle>Actividad bloqueada</AlertTitle>
                  <AlertDescription>
                    {typeof activity.blocked_reason === 'string'
                      ? activity.blocked_reason
                      : 'Completa primero las condiciones académicas previas.'}
                  </AlertDescription>
                </Alert>
              ) : type === 'assessment' ? (
                activeAttempt ? (
                  <AttemptRunner
                    initialAttempt={activeAttempt}
                    returnHref={activityHref}
                    slug={slug}
                  />
                ) : (
                  <section aria-labelledby="entrega-evaluacion">
                    <div className="mb-5 flex items-start gap-3">
                      <ClipboardCheck className="mt-1 text-primary" />
                      <div>
                        <h2
                          className="text-xl font-semibold"
                          id="entrega-evaluacion"
                        >
                          Resolver evaluación
                        </h2>
                        <p className="text-sm text-muted-foreground">
                          Inicia o continúa el intento sin salir del aula del
                          curso.
                        </p>
                      </div>
                    </div>
                    <LearnerDeliveryList
                      deliveries={matchingDeliveries}
                      slug={slug}
                      stayOnHref={activityHref}
                    />
                  </section>
                )
              ) : primarySession ? (
                <section aria-labelledby="aula-en-vivo">
                  <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
                    <div className="flex items-start gap-3">
                      <Video className="mt-1 text-primary" />
                      <div>
                        <h2 className="text-xl font-semibold" id="aula-en-vivo">
                          Aula en vivo
                        </h2>
                        <p className="text-sm text-muted-foreground">
                          Entra a LiveKit desde esta actividad; la asistencia y
                          el progreso permanecen vinculados al grupo.
                        </p>
                      </div>
                    </div>
                    <dl className="grid gap-2 text-sm sm:grid-cols-2">
                      <div className="flex items-center gap-2">
                        <CalendarClock className="size-4 text-primary" />
                        <dd>
                          {new Intl.DateTimeFormat('es-CO', {
                            dateStyle: 'medium',
                            timeStyle: 'short',
                          }).format(new Date(primarySession.scheduledStart))}
                        </dd>
                      </div>
                      <div className="flex items-center gap-2">
                        <UserRound className="size-4 text-primary" />
                        <dd>{primarySession.hostName}</dd>
                      </div>
                    </dl>
                  </div>
                  <LiveClassroom detail={primarySession} slug={slug} />
                </section>
              ) : (
                <Alert>
                  <Video />
                  <AlertTitle>Clase aún no programada</AlertTitle>
                  <AlertDescription>
                    La actividad existe en el release, pero todavía no tiene una
                    sesión LiveKit vinculada a este grupo.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          </article>

          <nav
            aria-label="Navegación entre actividades"
            className="learning-player__navigation"
          >
            {previous && typeof previous.href === 'string' ? (
              <Button
                asChild
                className="h-auto justify-start py-3"
                variant="outline"
              >
                <Link href={previous.href}>
                  <ArrowLeft data-icon="inline-start" />
                  <span>
                    <small>Anterior</small>
                    {String(previous.title ?? 'Actividad anterior')}
                  </span>
                </Link>
              </Button>
            ) : (
              <span />
            )}
            {next && typeof next.href === 'string' ? (
              <Button asChild className="h-auto justify-end py-3">
                <Link href={next.href}>
                  <span>
                    <small>Siguiente</small>
                    {String(next.title ?? 'Actividad siguiente')}
                  </span>
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            ) : null}
          </nav>
        </div>
      </div>
    </main>
  );
}

function activityStatusLabel(status: string) {
  const labels: Record<string, string> = {
    available: 'Disponible',
    completed: 'Completada',
    failed: 'No aprobada',
    in_progress: 'En progreso',
    locked: 'Bloqueada',
    missed: 'No realizada',
    passed: 'Aprobada',
    waived: 'Eximida',
  };
  return labels[status] ?? status;
}
