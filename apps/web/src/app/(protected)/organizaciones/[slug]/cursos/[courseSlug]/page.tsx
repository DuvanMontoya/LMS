import {
  ArrowRight,
  BookOpenCheck,
  Eye,
  FileCheck2,
  Layers3,
  ListTree,
  Send,
} from 'lucide-react';
import Link from 'next/link';

import { AlignmentEditor } from '@/components/courses/alignment-editor';
import { CourseMetadataForm } from '@/components/courses/course-metadata-form';
import { ReviewPanel } from '@/components/courses/review-panel';
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
import { courseStatusLabel } from '@/lib/courses/labels';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseWorkspacePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  const capabilities = data.access.capabilities;
  const canManage = capabilities.includes('course.authoring.manage');
  const units = data.outline.modules.flatMap((module) => module.units);
  const readyUnits = units.filter(
    (unit) => unit.content_status === 'ready',
  ).length;

  return (
    <main className="academic-page course-workspace" id="contenido-principal">
      <Breadcrumb className="min-w-0 overflow-hidden">
        <BreadcrumbList className="min-w-0">
          <BreadcrumbItem>
            <BreadcrumbLink asChild>
              <Link href={`/organizaciones/${slug}/cursos/autoria`}>
                Autoría
              </Link>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem className="min-w-0">
            <BreadcrumbPage className="truncate">
              {data.revision.title}
            </BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <section className="course-workspace__hero">
        <div>
          <div className="course-workspace__eyebrow">
            <span>
              {data.canAuthor ? 'Espacio de autoría' : 'Curso asignado'}
            </span>
            <Badge variant="secondary">
              {courseStatusLabel(data.revision.authoring_status)}
            </Badge>
          </div>
          <h1>{data.revision.title}</h1>
          <p>
            {data.canAuthor
              ? data.revision.summary
              : 'Consulta la estructura académica aprobada para tus responsabilidades docentes.'}
          </p>
        </div>
        {capabilities.includes('course.published.view') ? (
          <Button asChild>
            <Link
              href={`/organizaciones/${slug}/cursos/publicados/${courseSlug}`}
            >
              <Eye />
              Vista publicada
            </Link>
          </Button>
        ) : null}
      </section>

      <nav aria-label="Secciones del curso" className="course-workspace__nav">
        <Link
          aria-current="page"
          href={`/organizaciones/${slug}/cursos/${courseSlug}`}
        >
          <BookOpenCheck />
          Resumen
        </Link>
        <Link href={`/organizaciones/${slug}/cursos/${courseSlug}/estructura`}>
          <ListTree />
          Estructura
        </Link>
        {capabilities.includes('course.release.history.view') ? (
          <Link
            href={`/organizaciones/${slug}/cursos/${courseSlug}/publicacion`}
          >
            <Send />
            Publicación
          </Link>
        ) : null}
        {data.canAuthor ? (
          <Link href={`/organizaciones/${slug}/cursos/${courseSlug}/revision`}>
            <FileCheck2 />
            Revisión
          </Link>
        ) : null}
      </nav>

      <dl className="course-workspace__facts">
        <CourseFact
          label="Curso"
          value={courseStatusLabel(data.course.status)}
        />
        <CourseFact label="Revisión" value={`Número ${data.revision.number}`} />
        <CourseFact
          label="Programa"
          value={`${data.outline.modules.length} módulos · ${units.length} unidades`}
        />
        <CourseFact
          label="Contenido listo"
          value={`${readyUnits} de ${units.length} unidades`}
        />
      </dl>

      {data.canAuthor && data.readiness ? (
        <>
          <div className="course-workspace__metadata">
            <CourseMetadataForm
              canManage={canManage}
              courseSlug={courseSlug}
              key={data.revision.lock_version}
              revision={data.revision}
              slug={slug}
            />
          </div>
          <div className="course-workspace__governance">
            <div className="course-workspace__panel">
              <AlignmentEditor
                canManage={canManage}
                courseSlug={courseSlug}
                objectives={data.objectives}
                outline={data.outline}
                slug={slug}
                subjects={data.subjects}
              />
            </div>
            <div className="course-workspace__panel">
              <ReviewPanel
                canApprove={capabilities.includes('course.authoring.approve')}
                canReview={capabilities.includes('course.authoring.review')}
                canSubmit={capabilities.includes('course.authoring.submit')}
                courseSlug={courseSlug}
                readiness={data.readiness}
                revision={data.revision}
                slug={slug}
              />
            </div>
          </div>
        </>
      ) : null}

      <section className="course-workspace__structure">
        <header>
          <div>
            <p className="academic-kicker">Programa actual</p>
            <h2>Estructura del curso</h2>
            <p>
              Abre una unidad para editar su documento académico, recursos y
              actividades.
            </p>
          </div>
          <span>
            <Layers3 />
            {data.outline.modules.length} módulos
          </span>
        </header>
        <ol>
          {data.outline.modules.map((module) => (
            <li key={module.id}>
              <header>
                <span>{String(module.position).padStart(2, '0')}</span>
                <div>
                  <small>Módulo {module.position}</small>
                  <strong>{module.title}</strong>
                </div>
              </header>
              <ul>
                {module.units.map((unit) => (
                  <li key={unit.id}>
                    <span className="course-workspace__unit-title">
                      {unit.title}
                    </span>
                    <Badge
                      className="course-workspace__unit-status"
                      variant={
                        unit.content_status === 'ready'
                          ? 'secondary'
                          : 'outline'
                      }
                    >
                      {unit.content_status === 'ready'
                        ? `Contenido v${unit.content_version}`
                        : unit.content_status === 'empty'
                          ? 'Contenido vacío'
                          : 'Sin contenido'}
                    </Badge>
                    {data.canAuthor ? (
                      <Button asChild size="icon-xs" variant="ghost">
                        <Link
                          aria-label={`Abrir ${unit.title}`}
                          href={`/organizaciones/${slug}/cursos/${courseSlug}/unidades/${unit.id}/contenido`}
                        >
                          <ArrowRight />
                        </Link>
                      </Button>
                    ) : null}
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </section>

      {data.canAuthor && data.transitions.length ? (
        <details className="course-workspace__history">
          <summary>
            Historial de la revisión · {data.transitions.length} movimientos
          </summary>
          <ol>
            {data.transitions.map((transition) => (
              <li key={transition.id}>
                <strong>{courseStatusLabel(transition.to_status)}</strong>
                <span>por {transition.actor_display}</span>
                {transition.note ? <p>{transition.note}</p> : null}
              </li>
            ))}
          </ol>
        </details>
      ) : null}
    </main>
  );
}

function CourseFact({
  label,
  value,
}: Readonly<{ label: string; value: string }>) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}
