import { BookOpenText } from 'lucide-react';

import { AcademicDocument } from '@/components/content/academic-document';
import { LearningPositionTracker } from '@/components/learning/learning-position-tracker';
import {
  LearningPlayerNavigation,
  LearningPlayerShell,
} from '@/components/learning/learning-player-shell';
import { LearningUnitControls } from '@/components/learning/learning-unit-controls';
import { Badge } from '@/components/ui/badge';
import { parseAssetDescriptors } from '@/lib/assets/descriptors';
import {
  getEnrollmentForCourse,
  getLearningOutline,
  getLearningUnit,
} from '@/lib/learning/server';
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
  const [data, outlineData] = await Promise.all([
    getLearningUnit(slug, enrollment.enrollment_id, unitId),
    getLearningOutline(slug, enrollment.enrollment_id),
  ]);
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
  const unitNumber = outlineData.outline.modules
    .flatMap((module) => module.units)
    .findIndex((unit) => unit.id === unitId);
  const totalUnits = outlineData.outline.progress.total_units;
  const previousItem =
    previous && typeof previous.href === 'string'
      ? {
          href: previous.href,
          title: String(previous.title ?? 'Unidad anterior'),
        }
      : null;
  const nextItem =
    next && typeof next.href === 'string'
      ? {
          href: next.href,
          title: String(next.title ?? 'Unidad siguiente'),
        }
      : null;

  return (
    <>
      <LearningPlayerShell
        courseTitle={enrollment.course.title}
        currentUnitId={unitId}
        headerActions={
          <LearningUnitControls
            compact
            enrollmentId={enrollment.enrollment_id}
            progress={data.payload.progress}
            slug={slug}
            unitId={unitId}
            unitStatus={unitStatus}
          />
        }
        outline={outlineData.outline}
        outlineHref={outlineHref}
        positionLabel={`Lección ${Math.max(1, unitNumber + 1)} de ${totalUnits}`}
        releaseNumber={data.payload.release_number}
        title={publishedUnit.title}
      >
        <article className="learning-player__lesson">
          <header className="learning-player__lesson-heading">
            <p>
              Módulo {publishedUnit.module.position} ·{' '}
              {publishedUnit.module.title}
            </p>
            <h1>{publishedUnit.title}</h1>
            {publishedUnit.summary ? <div>{publishedUnit.summary}</div> : null}
            {publishedUnit.topics.length ? (
              <div className="learning-player__topics">
                {publishedUnit.topics.map((topic) => (
                  <Badge key={topic.id} variant="outline">
                    {topic.title}
                  </Badge>
                ))}
              </div>
            ) : null}
          </header>

          <div className="learning-player__document">
            <AcademicDocument
              assets={parseAssetDescriptors(data.payload.assets)}
              document={publishedUnit.content.document}
              refreshContext={{
                enrollmentId: enrollment.enrollment_id,
                slug,
                unitId,
              }}
            />
          </div>

          {publishedUnit.learning_objectives.length ? (
            <details className="learning-player__objectives">
              <summary>
                <BookOpenText />
                <div>
                  <strong>Objetivos de esta lección</strong>
                  <small>Información académica complementaria</small>
                </div>
              </summary>
              <ul>
                {publishedUnit.learning_objectives.map((objective) => (
                  <li key={objective.id}>{objective.statement}</li>
                ))}
              </ul>
            </details>
          ) : null}
        </article>

        <LearningPlayerNavigation
          label="Navegación entre lecciones"
          next={nextItem}
          previous={previousItem}
        />
      </LearningPlayerShell>
      <LearningPositionTracker
        enrollmentId={enrollment.enrollment_id}
        slug={slug}
        unitId={unitId}
      />
    </>
  );
}
