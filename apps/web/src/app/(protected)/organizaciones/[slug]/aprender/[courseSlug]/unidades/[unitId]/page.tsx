import { ArrowLeft, ArrowRight, BookOpenText } from 'lucide-react';
import Link from 'next/link';

import { AcademicDocument } from '@/components/content/academic-document';
import { LearningPositionTracker } from '@/components/learning/learning-position-tracker';
import { LearningProgress } from '@/components/learning/learning-progress';
import { LearningUnitControls } from '@/components/learning/learning-unit-controls';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getEnrollmentForCourse, getLearningUnit } from '@/lib/learning/server';
import { requirePublishedUnit } from '@/lib/publishing/snapshot';

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export default async function LearningUnitPage({
  params,
}: Readonly<{
  params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
}>) {
  const { courseSlug, slug, unitId } = await params;
  const { enrollment } = await getEnrollmentForCourse(slug, courseSlug);
  const data = await getLearningUnit(slug, enrollment.enrollment_id, unitId);
  const publishedUnit = requirePublishedUnit({
    ...data.payload.unit,
    content: { document: data.payload.content },
    learning_objectives: data.payload.learning_objectives,
    module: data.payload.module,
    topics: data.payload.topics,
  });
  const navigation = data.payload.navigation;
  const previous = record(navigation.previous) ? navigation.previous : null;
  const next = record(navigation.next) ? navigation.next : null;
  const outlineHref =
    typeof navigation.outline === 'string'
      ? navigation.outline
      : `/organizaciones/${slug}/aprender/${courseSlug}`;
  const unitStatus =
    record(data.payload.unit) && typeof data.payload.unit.status === 'string'
      ? data.payload.unit.status
      : 'not_started';
  return (
    <main
      aria-live="polite"
      className="academic-page"
      data-release-number={data.payload.release_number}
      id="contenido-principal"
    >
      <PageHeader
        actions={
          <Badge variant="outline">Release {data.payload.release_number}</Badge>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/aprendizaje`,
            label: 'Mi aprendizaje',
          },
          { href: outlineHref, label: enrollment.course.title },
          { label: publishedUnit.title },
        ]}
        description={publishedUnit.summary}
        eyebrow={`Módulo ${publishedUnit.module.position} · ${publishedUnit.module.title}`}
        title={publishedUnit.title}
      />
      <section className="mt-5 border p-5" aria-label="Progreso del curso">
        <LearningProgress progress={data.payload.progress} />
      </section>
      <div className="mt-5 grid gap-6 xl:grid-cols-[minmax(0,1fr)_19rem]">
        <article className="min-w-0 border">
          <header className="flex flex-wrap gap-2 border-b bg-muted/15 px-5 py-3">
            {publishedUnit.topics.map((topic) => (
              <Badge key={topic.id} variant="outline">
                {topic.title}
              </Badge>
            ))}
          </header>
          <div className="px-5 py-6 sm:px-8 lg:px-12">
            <AcademicDocument document={publishedUnit.content.document} />
          </div>
        </article>
        <aside className="grid content-start gap-4">
          <section className="border p-5">
            <div className="flex items-center gap-2">
              <BookOpenText className="size-4 text-primary" />
              <h2 className="font-semibold">Objetivos</h2>
            </div>
            <ul className="mt-3 space-y-3 text-sm">
              {publishedUnit.learning_objectives.map((objective) => (
                <li
                  className="border-l-2 border-primary pl-3"
                  key={objective.id}
                >
                  {objective.statement}
                </li>
              ))}
            </ul>
          </section>
          <LearningUnitControls
            enrollmentId={enrollment.enrollment_id}
            progress={data.payload.progress}
            slug={slug}
            unitId={unitId}
            unitStatus={unitStatus}
          />
          <Button asChild variant="outline">
            <Link href={outlineHref}>Volver a la ruta del curso</Link>
          </Button>
        </aside>
      </div>
      <nav
        aria-label="Navegación entre unidades"
        className="mt-6 grid gap-3 border-t pt-5 sm:grid-cols-2"
      >
        {previous && typeof previous.href === 'string' ? (
          <Button
            asChild
            className="h-auto justify-start py-3"
            variant="outline"
          >
            <Link href={previous.href}>
              <ArrowLeft data-icon="inline-start" />
              <span>{String(previous.title ?? 'Unidad anterior')}</span>
            </Link>
          </Button>
        ) : (
          <span />
        )}
        {next && typeof next.href === 'string' ? (
          <Button asChild className="h-auto justify-end py-3" variant="outline">
            <Link href={next.href}>
              <span>{String(next.title ?? 'Unidad siguiente')}</span>
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        ) : null}
      </nav>
      <LearningPositionTracker
        enrollmentId={enrollment.enrollment_id}
        slug={slug}
        unitId={unitId}
      />
    </main>
  );
}
