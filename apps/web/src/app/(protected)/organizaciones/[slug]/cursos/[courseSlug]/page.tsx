import Link from 'next/link';
import { ArrowRight, FileCheck2, ListTree, Send } from 'lucide-react';

import { AlignmentEditor } from '@/components/courses/alignment-editor';
import { CourseMetadataForm } from '@/components/courses/course-metadata-form';
import { ReviewPanel } from '@/components/courses/review-panel';
import { PageHeader } from '@/components/platform/page-header';
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
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          <nav aria-label="Secciones del curso" className="flex gap-2">
            <Button asChild size="sm" variant="outline">
              <Link
                href={`/organizaciones/${slug}/cursos/${courseSlug}/estructura`}
              >
                <ListTree data-icon="inline-start" />
                Estructura
              </Link>
            </Button>
            {capabilities.includes('course.release.history.view') ? (
              <Button asChild size="sm" variant="outline">
                <Link
                  href={`/organizaciones/${slug}/cursos/${courseSlug}/publicacion`}
                >
                  <Send data-icon="inline-start" />
                  Publicación
                </Link>
              </Button>
            ) : null}
            {data.canAuthor ? (
              <Button asChild size="sm" variant="outline">
                <Link
                  href={`/organizaciones/${slug}/cursos/${courseSlug}/revision`}
                >
                  <FileCheck2 data-icon="inline-start" />
                  Revisión
                </Link>
              </Button>
            ) : null}
          </nav>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          { label: data.revision.title },
        ]}
        description={
          data.canAuthor
            ? data.revision.summary
            : 'Consulta la estructura académica aprobada para tus responsabilidades docentes.'
        }
        eyebrow={data.canAuthor ? 'Espacio de autoría' : 'Curso asignado'}
        title={data.revision.title}
      />
      <dl className="mt-5 grid border-y sm:grid-cols-2 lg:grid-cols-4">
        <CourseFact
          label="Estado del curso"
          value={courseStatusLabel(data.course.status)}
        />
        <CourseFact
          badge
          label="Estado de autoría"
          value={courseStatusLabel(data.revision.authoring_status)}
        />
        <CourseFact
          label="Revisión estructural"
          value={`Número ${data.revision.number}`}
        />
        <CourseFact
          label="Estructura"
          value={`${data.outline.modules.length} módulos`}
        />
      </dl>
      {data.canAuthor && data.readiness ? (
        <>
          <CourseMetadataForm
            canManage={canManage}
            courseSlug={courseSlug}
            key={data.revision.lock_version}
            revision={data.revision}
            slug={slug}
          />
          <div className="mt-7 grid gap-6 lg:grid-cols-2">
            <AlignmentEditor
              canManage={canManage}
              courseSlug={courseSlug}
              objectives={data.objectives}
              outline={data.outline}
              slug={slug}
              subjects={data.subjects}
            />
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
        </>
      ) : null}
      <section className="mt-7 border-y">
        <header className="border-b px-5 py-4">
          <h2 className="font-semibold">Estructura del curso</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {data.outline.modules.length} módulos en la revisión actual.
          </p>
        </header>
        <ol className="divide-y">
          {data.outline.modules.map((module) => (
            <li
              className="grid lg:grid-cols-[17rem_minmax(0,1fr)]"
              key={module.id}
            >
              <div className="border-b bg-muted/15 px-5 py-4 lg:border-r lg:border-b-0">
                <span className="text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase">
                  Módulo
                </span>
                <strong className="mt-1 block text-sm">{module.title}</strong>
              </div>
              <ul className="divide-y text-sm">
                {module.units.map((unit) => (
                  <li
                    className="flex flex-wrap items-center gap-3 px-5 py-3 hover:bg-muted/20"
                    key={unit.id}
                  >
                    <span className="min-w-0 flex-1 font-medium">
                      {unit.title}
                    </span>
                    <Badge
                      className="rounded"
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
                      <Button
                        asChild
                        className="ml-auto"
                        size="xs"
                        variant="ghost"
                      >
                        <Link
                          href={`/organizaciones/${slug}/cursos/${courseSlug}/unidades/${unit.id}/contenido`}
                        >
                          Abrir
                          <ArrowRight data-icon="inline-end" />
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
      {data.canAuthor ? (
        <section className="mt-7 border-t pt-5">
          <h2 className="text-sm font-semibold">Historial de transiciones</h2>
          <ol className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {data.transitions.map((transition) => (
              <li
                className="border-l-2 border-primary pl-3 text-sm"
                key={transition.id}
              >
                <strong>{courseStatusLabel(transition.to_status)}</strong> por{' '}
                {transition.actor_display}
                {transition.note ? (
                  <p className="text-foreground/80">{transition.note}</p>
                ) : null}
              </li>
            ))}
          </ol>
        </section>
      ) : null}
    </main>
  );
}

function CourseFact({
  badge = false,
  label,
  value,
}: Readonly<{ badge?: boolean; label: string; value: string }>) {
  return (
    <div className="border-b px-5 py-4 last:border-b-0 sm:border-r sm:nth-[2n]:border-r-0 lg:border-b-0 lg:nth-[2n]:border-r lg:last:border-r-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm font-semibold">
        {badge ? (
          <Badge className="rounded" variant="secondary">
            {value}
          </Badge>
        ) : (
          value
        )}
      </dd>
    </div>
  );
}
