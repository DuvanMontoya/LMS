import {
  ArrowRight,
  Award,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  Clock3,
  Layers3,
  Play,
  Sparkles,
  Users,
  Video,
} from 'lucide-react';
import Link from 'next/link';

import { LearnerDeliveryList } from '@/components/assessments/learner-deliveries';
import { CourseCurriculum } from '@/components/learning/course-curriculum';
import { CourseGradebook } from '@/components/learning/course-gradebook';
import { LearningProgress } from '@/components/learning/learning-progress';
import { LiveSessionList } from '@/components/scheduling/live-session-list';
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Button } from '@/components/ui/button';
import { getMyAssessmentDeliveries } from '@/lib/assessments/server';
import { getLiveSessions } from '@/lib/scheduling/server';
import {
  getEnrollmentForCourse,
  getLearningOutline,
} from '@/lib/learning/server';
import { cn } from '@/lib/utils';

const tabs = [
  { icon: Sparkles, id: 'resumen', label: 'Resumen' },
  { icon: Layers3, id: 'contenido', label: 'Contenido' },
  { icon: ClipboardCheck, id: 'evaluaciones', label: 'Evaluaciones' },
  { icon: Video, id: 'clases', label: 'Clases en vivo' },
  { icon: Award, id: 'calificaciones', label: 'Calificaciones' },
] as const;

type CourseTab = (typeof tabs)[number]['id'];

export default async function LearningOutlinePage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ courseSlug: string; slug: string }>;
  searchParams: Promise<{ tab?: string }>;
}>) {
  const [{ courseSlug, slug }, query] = await Promise.all([
    params,
    searchParams,
  ]);
  const { enrollment } = await getEnrollmentForCourse(slug, courseSlug);
  const [data, assessmentData, liveData] = await Promise.all([
    getLearningOutline(slug, enrollment.enrollment_id),
    getMyAssessmentDeliveries(slug),
    getLiveSessions(slug, { courseSlug }),
  ]);
  const activeTab = isCourseTab(query.tab) ? query.tab : 'resumen';
  const courseDeliveries = assessmentData.deliveries.filter(
    ({ delivery }) =>
      delivery.course_release_title === data.outline.course.title &&
      delivery.course_release_number === data.outline.release_number,
  );
  const courseGradebooks = assessmentData.gradebooks.filter(
    ({ gradebook }) =>
      gradebook.course_title === data.outline.course.title &&
      gradebook.release_number === data.outline.release_number,
  );
  const activities = data.outline.modules.flatMap(
    (module) => module.activities,
  );
  const duration = activities.reduce(
    (total, activity) => total + (activity.estimated_duration_minutes ?? 0),
    0,
  );
  const nextActivity =
    activities.find(
      (activity) => activity.id === data.outline.resume.activity_instance_id,
    ) ??
    activities.find(
      (activity) =>
        !['completed', 'passed', 'waived'].includes(activity.status) &&
        activity.status !== 'locked',
    ) ??
    activities[0];
  const baseHref = `/organizaciones/${slug}/aprender/${courseSlug}`;

  return (
    <main className="academic-page course-home" id="contenido-principal">
      <Breadcrumb className="mb-4 min-w-0 overflow-hidden">
        <BreadcrumbList className="min-w-0">
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={`/organizaciones/${slug}/aprendizaje`}>
                Mi aprendizaje
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem className="min-w-0">
            <BreadcrumbPage className="truncate">
              {data.outline.course.title}
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <section className="course-home-hero">
        <div className="course-home-hero__main">
          <p className="academic-kicker">Aula del curso</p>
          <div className="course-home-hero__release">
            Release {data.outline.release_number}
          </div>
          <h1>{data.outline.course.title}</h1>
          <p>{data.outline.course.summary}</p>
          <dl className="course-home-hero__facts">
            <CourseFact
              icon={<Layers3 />}
              label="Estructura"
              value={`${data.outline.modules.length} módulos`}
            />
            <CourseFact
              icon={<BookOpenCheck />}
              label="Actividades"
              value={`${activities.length} en secuencia`}
            />
            <CourseFact
              icon={<Clock3 />}
              label="Duración"
              value={duration ? formatMinutes(duration) : 'A tu ritmo'}
            />
            <CourseFact
              icon={<Users />}
              label="Grupo de curso"
              value={data.outline.cohort?.name ?? 'Matrícula individual'}
            />
          </dl>
        </div>
        <aside className="course-home-hero__progress">
          <span>Tu avance</span>
          <strong>
            {(data.outline.progress.percent_basis_points / 100).toFixed(0)}%
          </strong>
          <LearningProgress progress={data.outline.progress} />
          {data.outline.resume.href ? (
            <Button asChild className="w-full">
              <Link href={data.outline.resume.href}>
                <Play />
                {data.outline.progress.status === 'not_started'
                  ? 'Comenzar curso'
                  : 'Continuar aprendiendo'}
              </Link>
            </Button>
          ) : null}
          <small>
            {data.outline.progress.completion.completed_required} de{' '}
            {data.outline.progress.completion.total_required} actividades
            obligatorias completadas
          </small>
        </aside>
      </section>

      <nav aria-label="Secciones del curso" className="course-tab-nav">
        {tabs.map(({ icon: Icon, id, label }) => (
          <Link
            aria-current={activeTab === id ? 'page' : undefined}
            className={cn(activeTab === id && 'is-active')}
            href={id === 'resumen' ? baseHref : `${baseHref}?tab=${id}`}
            key={id}
          >
            <Icon />
            <span>{label}</span>
            {id === 'evaluaciones' && courseDeliveries.length ? (
              <small>{courseDeliveries.length}</small>
            ) : null}
          </Link>
        ))}
      </nav>

      <div className="course-tab-panel">
        {activeTab === 'resumen' ? (
          <CourseOverview
            nextActivity={nextActivity}
            outline={data.outline}
            tabHref={`${baseHref}?tab=contenido`}
          />
        ) : null}
        {activeTab === 'contenido' ? (
          <section className="course-curriculum-panel">
            <header>
              <div>
                <p className="academic-kicker">Plan de estudios</p>
                <h2>Contenido del curso</h2>
                <p>
                  Recorre las lecciones en el orden estable del release que
                  tienes asignado.
                </p>
              </div>
              <span>{activities.length} actividades</span>
            </header>
            <CourseCurriculum modules={data.outline.modules} />
          </section>
        ) : null}
        {activeTab === 'evaluaciones' ? (
          <section aria-labelledby="evaluaciones-curso">
            <header className="course-tab-heading">
              <div>
                <p className="academic-kicker">Aplicación y evidencia</p>
                <h2 id="evaluaciones-curso">Evaluaciones del curso</h2>
                <p>
                  Actividades asignadas específicamente a este release. Tus
                  notas se consultan en la pestaña Calificaciones.
                </p>
              </div>
              <span>{courseDeliveries.length}</span>
            </header>
            <LearnerDeliveryList deliveries={courseDeliveries} slug={slug} />
          </section>
        ) : null}
        {activeTab === 'clases' ? (
          <section aria-labelledby="clases-curso">
            <header className="course-tab-heading">
              <div>
                <p className="academic-kicker">Encuentros sincrónicos</p>
                <h2 id="clases-curso">Clases en vivo del curso</h2>
                <p>
                  Sesiones vinculadas a este curso. Las clases marcadas como
                  obligatorias se incorporan al cálculo del progreso.
                </p>
              </div>
              <span>{liveData.sessions.length}</span>
            </header>
            <LiveSessionList sessions={liveData.sessions} slug={slug} />
          </section>
        ) : null}
        {activeTab === 'calificaciones' ? (
          <section aria-labelledby="calificaciones-curso">
            <header className="course-tab-heading">
              <div>
                <p className="academic-kicker">Rendimiento académico</p>
                <h2 id="calificaciones-curso">Calificaciones</h2>
                <p>
                  Resultados ponderados del libro activo para este curso y
                  release.
                </p>
              </div>
              <span>{courseGradebooks.length}</span>
            </header>
            <CourseGradebook gradebooks={courseGradebooks} />
          </section>
        ) : null}
      </div>
    </main>
  );
}

function CourseOverview({
  nextActivity,
  outline,
  tabHref,
}: Readonly<{
  nextActivity:
    | Awaited<
        ReturnType<typeof getLearningOutline>
      >['outline']['modules'][number]['activities'][number]
    | undefined;
  outline: Awaited<ReturnType<typeof getLearningOutline>>['outline'];
  tabHref: string;
}>) {
  return (
    <div className="course-overview-grid">
      <section className="course-next-step">
        <div className="course-next-step__icon">
          {outline.progress.status === 'completed' ? (
            <CheckCircle2 />
          ) : (
            <Play />
          )}
        </div>
        <div>
          <p className="academic-kicker">
            {outline.progress.status === 'not_started'
              ? 'Tu punto de partida'
              : outline.progress.status === 'completed'
                ? 'Ruta completada'
                : 'Continúa donde quedaste'}
          </p>
          <h2>{nextActivity?.title ?? outline.course.title}</h2>
          <p>
            {nextActivity?.summary ||
              'Consulta la secuencia completa de lecciones, clases y evaluaciones.'}
          </p>
          {nextActivity ? (
            <Button asChild className="mt-5">
              <Link href={nextActivity.href}>
                Abrir actividad
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          ) : null}
        </div>
      </section>
      <section className="course-module-preview">
        <header>
          <div>
            <p className="academic-kicker">Recorrido</p>
            <h2>Ruta de aprendizaje</h2>
          </div>
          <Button asChild size="sm" variant="outline">
            <Link href={tabHref}>Ver contenido completo</Link>
          </Button>
        </header>
        <ol>
          {outline.modules.map((module) => {
            const completed = module.activities.filter((activity) =>
              ['completed', 'passed', 'waived'].includes(activity.status),
            ).length;
            return (
              <li key={module.id}>
                <span>{String(module.position).padStart(2, '0')}</span>
                <div>
                  <strong>{module.title}</strong>
                  <small>
                    {completed}/{module.activities.length} actividades
                    completadas
                  </small>
                </div>
                <div
                  aria-hidden="true"
                  className="course-module-preview__progress"
                >
                  <span
                    style={{
                      width: `${
                        module.activities.length
                          ? (completed / module.activities.length) * 100
                          : 0
                      }%`,
                    }}
                  />
                </div>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}

function CourseFact({
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

function isCourseTab(value: string | undefined): value is CourseTab {
  return tabs.some((tab) => tab.id === value);
}

function formatMinutes(value: number) {
  if (value < 60) return `${value} min`;
  const hours = Math.floor(value / 60);
  const minutes = value % 60;
  return minutes ? `${hours} h ${minutes} min` : `${hours} h`;
}
