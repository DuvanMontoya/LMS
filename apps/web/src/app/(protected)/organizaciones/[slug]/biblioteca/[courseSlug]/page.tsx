import {
  ArrowRight,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  Clock3,
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
import { formatDuration, languageLabel } from '@/lib/publishing/labels';
import { getLibraryCourse } from '@/lib/publishing/server';

export default async function LibraryCoursePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getLibraryCourse(slug, courseSlug);
  const firstUnit = data.course.outline[0]?.units[0];
  const firstUnitHref = firstUnit
    ? `/organizaciones/${slug}/biblioteca/${courseSlug}/unidades/${firstUnit.id}`
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
              <Link href={`/organizaciones/${slug}/biblioteca`}>
                Biblioteca
              </Link>
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
          <p className="academic-kicker">Curso publicado</p>
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
            {firstUnitHref ? (
              <Button asChild size="lg">
                <Link href={firstUnitHref}>
                  <Play />
                  Comenzar curso
                </Link>
              </Button>
            ) : null}
            <Button asChild size="lg" variant="outline">
              <Link href="#contenido-del-curso">Explorar contenido</Link>
            </Button>
          </div>
        </div>
        <div aria-hidden="true" className="library-course-hero__visual">
          <div>
            <BookOpen />
            <span>{String(data.course.module_count).padStart(2, '0')}</span>
            <small>Módulos</small>
          </div>
          <span />
          <span />
        </div>
      </section>

      <div className="library-course-layout">
        <div className="library-course-main">
          {data.course.description ? (
            <section className="library-course-about">
              <p className="academic-kicker">Presentación</p>
              <h2>Acerca de este curso</h2>
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

          <section
            className="library-course-curriculum"
            id="contenido-del-curso"
          >
            <header>
              <div>
                <p className="academic-kicker">Plan de estudios</p>
                <h2>Contenido del curso</h2>
                <p>
                  {data.course.module_count} módulos · {data.course.unit_count}{' '}
                  lecciones en el release {data.course.release_number}
                </p>
              </div>
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
                        <Link
                          href={`/organizaciones/${slug}/biblioteca/${courseSlug}/unidades/${unit.id}`}
                        >
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
        </div>

        <aside className="library-course-card-sticky">
          <div className="library-course-card-sticky__cover">
            <Layers3 />
            <span>Ruta académica</span>
            <small>Release {data.course.release_number}</small>
          </div>
          <div className="library-course-card-sticky__body">
            {firstUnitHref ? (
              <Button asChild className="w-full" size="lg">
                <Link href={firstUnitHref}>
                  Comenzar ahora
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            ) : null}
            <p>Este curso incluye</p>
            <dl>
              <CourseFact
                icon={<Clock3 />}
                label="Duración estimada"
                value={formatDuration(data.course.estimated_duration_minutes)}
              />
              <CourseFact
                icon={<Layers3 />}
                label="Módulos"
                value={String(data.course.module_count)}
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
        </aside>
      </div>
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
