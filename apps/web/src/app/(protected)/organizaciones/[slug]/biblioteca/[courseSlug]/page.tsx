import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Clock3,
  Eye,
  Languages,
  Layers3,
  Play,
  Target,
} from 'lucide-react';
import Link from 'next/link';

import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator,
} from '@/components/ui/breadcrumb';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getOptionalEnrollmentForCourse } from '@/lib/learning/server';
import { formatDuration, languageLabel } from '@/lib/publishing/labels';
import { getLibraryCourse } from '@/lib/publishing/server';

type PublishedCoursePageProps = Readonly<{
  params: Promise<{ courseSlug: string; slug: string }>;
}>;

export default async function PublishedCourseView({
  params,
}: PublishedCoursePageProps) {
  const { courseSlug, slug } = await params;
  const [data, enrollment] = await Promise.all([
    getLibraryCourse(slug, courseSlug),
    getOptionalEnrollmentForCourse(slug, courseSlug),
  ]);
  const courseBase = `/organizaciones/${slug}/cursos/publicados/${courseSlug}`;
  const firstUnit = data.course.outline[0]?.units[0];
  const startHref = enrollment
    ? `/organizaciones/${slug}/aprender/${courseSlug}`
    : firstUnit
      ? `${courseBase}/unidades/${firstUnit.id}`
      : undefined;

  return (
    <main
      className="academic-page library-course-detail"
      id="contenido-principal"
    >
      <Breadcrumb className="mb-4 min-w-0 overflow-hidden">
        <BreadcrumbList className="min-w-0">
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={`/organizaciones/${slug}/cursos`}>Cursos</Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem className="min-w-0">
            <BreadcrumbPage className="truncate">
              {data.course.title}
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <section className="library-course-hero">
        <div className="library-course-hero__content">
          <div className="library-course-hero__meta">
            <span>Curso publicado</span>
            <span>Release {data.course.release_number}</span>
          </div>
          <div className="library-course-hero__subjects">
            {data.subjects.map((subject) => (
              <Badge key={subject.id} variant="outline">
                {subject.name}
              </Badge>
            ))}
          </div>
          <h1>{data.course.title}</h1>
          <p>{data.course.summary}</p>
          <div className="library-course-hero__actions">
            {startHref ? (
              <Button asChild size="lg">
                <Link href={startHref}>
                  {enrollment ? <Play /> : <Eye />}
                  {enrollment
                    ? 'Continuar aprendizaje'
                    : 'Vista previa del aula'}
                </Link>
              </Button>
            ) : null}
            <Button asChild size="lg" variant="outline">
              <Link href="#contenido-del-curso">Ver programa</Link>
            </Button>
          </div>
          <p className="library-course-hero__start-note">
            {enrollment
              ? 'Abrirás tu aula real; el progreso y las actividades quedan vinculados a tu matrícula.'
              : 'La vista previa reproduce el aula del estudiante sin crear una matrícula ni guardar progreso.'}
          </p>
        </div>

        <div className="library-course-hero__overview">
          <div>
            <BookOpen />
            <span>Ruta académica</span>
            <strong>{data.course.module_count} módulos</strong>
          </div>
          <dl>
            <CourseFact
              icon={<Clock3 />}
              label="Duración"
              value={formatDuration(data.course.estimated_duration_minutes)}
            />
            <CourseFact
              icon={<BookOpen />}
              label="Lecciones"
              value={String(data.course.unit_count)}
            />
            <CourseFact
              icon={<Languages />}
              label="Idioma"
              value={languageLabel(data.course.language_code)}
            />
            <CourseFact
              icon={<Target />}
              label="Objetivos"
              value={String(data.objectives.length)}
            />
          </dl>
        </div>
      </section>

      <div className="library-course-introduction">
        {data.course.description ? (
          <section className="library-course-about">
            <p className="academic-kicker">Presentación</p>
            <h2>Acerca del curso</h2>
            <p>{data.course.description}</p>
          </section>
        ) : null}

        {data.objectives.length ? (
          <section className="library-course-objectives">
            <header>
              <Target />
              <div>
                <p className="academic-kicker">Resultados esperados</p>
                <h2>Lo que aprenderás</h2>
              </div>
            </header>
            <ul>
              {data.objectives.map((objective) => (
                <li key={objective.id}>
                  <CheckCircle2 />
                  <span>
                    <strong>{objective.code}</strong>
                    {objective.statement}
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ) : null}
      </div>

      <section className="library-course-curriculum" id="contenido-del-curso">
        <header>
          <div>
            <p className="academic-kicker">Plan de estudios</p>
            <h2>Contenido del curso</h2>
            <p>
              {data.course.module_count} módulos · {data.course.unit_count}{' '}
              lecciones · release {data.course.release_number}
            </p>
          </div>
          <Layers3 aria-hidden="true" />
        </header>
        <div>
          {data.course.outline.map((module, index) => (
            <details key={module.id} open={index === 0}>
              <summary>
                <span>{String(module.position).padStart(2, '0')}</span>
                <span>
                  <strong>{module.title}</strong>
                  <small>
                    {module.units.length}{' '}
                    {module.units.length === 1 ? 'lección' : 'lecciones'}
                  </small>
                </span>
                <ChevronDown />
              </summary>
              {module.description ? <p>{module.description}</p> : null}
              <ol>
                {module.units.map((unit) => (
                  <li key={unit.id}>
                    <Link href={`${courseBase}/unidades/${unit.id}`}>
                      <span>
                        {module.position}.{unit.position}
                      </span>
                      <span>{unit.title}</span>
                      <ArrowRight />
                    </Link>
                  </li>
                ))}
              </ol>
            </details>
          ))}
        </div>
      </section>
    </main>
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
