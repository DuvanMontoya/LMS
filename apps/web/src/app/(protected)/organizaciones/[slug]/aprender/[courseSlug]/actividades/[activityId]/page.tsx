import {
  ArrowLeft,
  ArrowRight,
  ClipboardCheck,
  LockKeyhole,
  Video,
} from 'lucide-react';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { LearnerDeliveryList } from '@/components/assessments/learner-deliveries';
import { CourseCurriculum } from '@/components/learning/course-curriculum';
import { LearningProgress } from '@/components/learning/learning-progress';
import { LiveSessionList } from '@/components/scheduling/live-session-list';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getMyAssessmentDeliveries } from '@/lib/assessments/server';
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

  return (
    <main className="academic-page" id="contenido-principal">
      <div className="grid gap-6 xl:grid-cols-[19rem_minmax(0,1fr)]">
        <aside className="academic-panel h-fit p-4 xl:sticky xl:top-4">
          <div className="mb-4">
            <p className="academic-kicker">Ruta del release</p>
            <h2 className="font-semibold">{enrollment.course.title}</h2>
          </div>
          <LearningProgress progress={data.payload.progress} />
          <div className="mt-4 max-h-[65vh] overflow-y-auto">
            <CourseCurriculum
              currentActivityId={activityId}
              modules={outlineData.outline.modules}
              variant="player"
            />
          </div>
        </aside>
        <section className="min-w-0">
          <Button asChild className="mb-4" size="sm" variant="ghost">
            <Link href={outlineHref}>
              <ArrowLeft /> Volver al curso
            </Link>
          </Button>
          <header className="academic-panel p-6">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">
                {type === 'assessment' ? 'Evaluación' : 'Clase en vivo'}
              </Badge>
              {activity.required ? <Badge>Obligatoria</Badge> : null}
              <Badge variant="secondary">{activityStatusLabel(status)}</Badge>
            </div>
            <h1 className="mt-4 text-3xl font-semibold tracking-tight">
              {title}
            </h1>
            {typeof activity.summary === 'string' && activity.summary ? (
              <p className="mt-2 max-w-3xl text-muted-foreground">
                {activity.summary}
              </p>
            ) : null}
          </header>

          <div className="mt-5">
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
              <section className="academic-panel p-6">
                <div className="mb-5 flex items-start gap-3">
                  <ClipboardCheck className="mt-1 text-primary" />
                  <div>
                    <h2 className="text-xl font-semibold">
                      Entrega de evaluación
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      El intento y la calificación corresponden a este grupo,
                      periodo y release.
                    </p>
                  </div>
                </div>
                <LearnerDeliveryList
                  deliveries={matchingDeliveries}
                  slug={slug}
                />
              </section>
            ) : (
              <section className="academic-panel p-6">
                <div className="mb-5 flex items-start gap-3">
                  <Video className="mt-1 text-primary" />
                  <div>
                    <h2 className="text-xl font-semibold">
                      Sesiones programadas
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      La asistencia se registra solamente en las sesiones
                      vinculadas a esta actividad del grupo.
                    </p>
                  </div>
                </div>
                <LiveSessionList sessions={matchingSessions} slug={slug} />
              </section>
            )}
          </div>

          <nav
            aria-label="Navegación entre actividades"
            className="mt-6 flex justify-between gap-3"
          >
            {previous && typeof previous.href === 'string' ? (
              <Button asChild variant="outline">
                <Link href={previous.href}>
                  <ArrowLeft /> Anterior
                </Link>
              </Button>
            ) : (
              <span />
            )}
            {next && typeof next.href === 'string' ? (
              <Button asChild>
                <Link href={next.href}>
                  Siguiente <ArrowRight />
                </Link>
              </Button>
            ) : null}
          </nav>
        </section>
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
