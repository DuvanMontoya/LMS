import { LockKeyhole, Video } from 'lucide-react';
import { redirect } from 'next/navigation';

import { AttemptRunner } from '@/components/assessments/attempt-runner';
import { CourseAssessmentBriefing } from '@/components/assessments/course-assessment-briefing';
import {
  LearningPlayerNavigation,
  LearningPlayerShell,
} from '@/components/learning/learning-player-shell';
import { LiveClassroom } from '@/components/scheduling/live-classroom';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
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
  const previousItem =
    previous && typeof previous.href === 'string'
      ? {
          href: previous.href,
          title: String(previous.title ?? 'Actividad anterior'),
        }
      : null;
  const nextItem =
    next && typeof next.href === 'string'
      ? {
          href: next.href,
          title: String(next.title ?? 'Actividad siguiente'),
        }
      : null;
  const stageMode = activeAttempt ? 'active' : 'briefing';
  const usesDedicatedBriefing =
    status !== 'locked' &&
    (type === 'assessment' || (type === 'live_class' && primarySession));

  return (
    <LearningPlayerShell
      courseTitle={enrollment.course.title}
      currentActivityId={activityId}
      outline={outlineData.outline}
      outlineHref={outlineHref}
      positionLabel={`Actividad ${Math.max(1, activityNumber + 1)} de ${allActivities.length}`}
      releaseNumber={data.payload.release_number}
      stageMode={stageMode}
      title={title}
    >
      {activeAttempt ? (
        <section
          aria-label={`Intento activo: ${title}`}
          className="learning-player__active-surface"
          data-activity-kind="assessment"
        >
          <AttemptRunner
            initialAttempt={activeAttempt}
            returnHref={activityHref}
            slug={slug}
          />
        </section>
      ) : (
        <>
          <article
            className={`learning-player__lesson learning-player__activity${
              usesDedicatedBriefing
                ? ' learning-player__activity--dedicated-briefing'
                : ''
            }`}
          >
            {!usesDedicatedBriefing ? (
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
                  <Badge variant="secondary">
                    {activityStatusLabel(status)}
                  </Badge>
                </span>
                <h1>{title}</h1>
                {typeof activity.summary === 'string' && activity.summary ? (
                  <div>{activity.summary}</div>
                ) : null}
              </header>
            ) : null}

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
                <CourseAssessmentBriefing
                  assignment={matchingDeliveries[0] ?? null}
                  returnHref={activityHref}
                  slug={slug}
                />
              ) : primarySession ? (
                <LiveClassroom detail={primarySession} slug={slug} />
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
          <LearningPlayerNavigation
            label="Navegación entre actividades"
            next={nextItem}
            previous={previousItem}
          />
        </>
      )}
    </LearningPlayerShell>
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
