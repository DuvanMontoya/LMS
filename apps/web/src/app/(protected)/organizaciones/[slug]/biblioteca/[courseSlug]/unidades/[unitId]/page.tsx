import { BookOpenText } from 'lucide-react';

import { AcademicDocument } from '@/components/content/academic-document';
import {
  LearningPlayerNavigation,
  type LearningPlayerNavigationItem,
} from '@/components/learning/learning-player-shell';
import { CoursePreviewPlayer } from '@/components/publishing/course-preview-player';
import { Badge } from '@/components/ui/badge';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';
import { getLibraryUnit } from '@/lib/publishing/server';

type PublishedUnitPageProps = Readonly<{
  params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
}>;

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export default async function PublishedUnitView({
  params,
}: PublishedUnitPageProps) {
  const { courseSlug, slug, unitId } = await params;
  const data = await getLibraryUnit(slug, courseSlug, unitId);
  const { navigation } = data.payload;
  const base = `/organizaciones/${slug}/cursos/publicados/${courseSlug}`;
  const previous = navigation.previous
    ? {
        href: `${base}/unidades/${navigation.previous.id}`,
        title: navigation.previous.title,
      }
    : null;
  const next = navigation.next
    ? {
        href: `${base}/unidades/${navigation.next.id}`,
        title: navigation.next.title,
      }
    : null;
  const deliveryContent = record(data.unit.delivery.content)
    ? data.unit.delivery.content
    : null;
  const isDocument =
    data.unit.delivery.kind === 'document' &&
    deliveryContent !== null &&
    record(deliveryContent.document);
  const document =
    isDocument && deliveryContent
      ? (deliveryContent.document as unknown as LMSUnitAcademicDocumentVersion2)
      : null;

  return (
    <CoursePreviewPlayer
      courseHref={base}
      courseTitle={data.course.title}
      currentUnitId={unitId}
      modules={data.outline}
      positionLabel={`Lección ${navigation.position} de ${navigation.total}`}
      releaseNumber={data.payload.release_number}
      title={data.unit.title}
    >
      <article className="learning-player__lesson">
        <header className="learning-player__lesson-heading">
          <p>
            Módulo {data.unit.module.position} · {data.unit.module.title}
          </p>
          <h1>{data.unit.title}</h1>
          {isDocument && data.unit.summary ? (
            <div>{data.unit.summary}</div>
          ) : null}
          {isDocument && data.unit.topics.length ? (
            <div className="learning-player__topics">
              {data.unit.topics.map((topic) => (
                <Badge key={topic.id} variant="outline">
                  {topic.title}
                </Badge>
              ))}
            </div>
          ) : null}
        </header>

        {document ? (
          <div className="learning-player__document">
            <AcademicDocument document={document} />
          </div>
        ) : null}

        {isDocument && data.unit.learning_objectives.length ? (
          <details className="learning-player__objectives">
            <summary>
              <BookOpenText />
              <div>
                <strong>Objetivos de esta lección</strong>
                <small>Información académica complementaria</small>
              </div>
            </summary>
            <ul>
              {data.unit.learning_objectives.map((objective) => (
                <li key={objective.id}>{objective.statement}</li>
              ))}
            </ul>
          </details>
        ) : null}
      </article>

      <LearningPlayerNavigation
        label="Navegación entre lecciones de la vista previa"
        next={next satisfies LearningPlayerNavigationItem | null}
        previous={previous satisfies LearningPlayerNavigationItem | null}
      />
    </CoursePreviewPlayer>
  );
}
