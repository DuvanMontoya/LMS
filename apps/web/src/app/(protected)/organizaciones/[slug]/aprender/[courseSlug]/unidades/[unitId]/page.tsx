import { AcademicDocument } from '@/components/content/academic-document';
import { AcademicAsset } from '@/components/content/academic-asset';
import { LearningPositionTracker } from '@/components/learning/learning-position-tracker';
import { MediaCMSVideoPlayer } from '@/components/learning/mediacms-video-player';
import { SourceLessonRenderer } from '@/components/learning/source-lesson-renderer';
import {
  LearningPlayerNavigation,
  LearningPlayerShell,
} from '@/components/learning/learning-player-shell';
import { LearningUnitControls } from '@/components/learning/learning-unit-controls';
import { parseAssetDescriptors } from '@/lib/assets/descriptors';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';
import {
  getEnrollmentForCourse,
  getLearningOutline,
  getLearningUnit,
} from '@/lib/learning/server';

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

type AcademicDocumentValue = Parameters<typeof AcademicDocument>[0]['document'];

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
  const unit = record(data.payload.unit) ? data.payload.unit : null;
  const delivery = record(data.payload.delivery) ? data.payload.delivery : null;
  if (!unit || !delivery || typeof unit.title !== 'string') {
    throw new Error('El contrato de entrega de la lección es inválido.');
  }
  const lessonKind =
    typeof unit.lesson_kind === 'string' ? unit.lesson_kind : '';
  const isDocument = delivery.kind === 'document';
  const isMediaCMSVideo =
    delivery.kind === 'mediacms_lti' &&
    record(delivery.media) &&
    delivery.media.provider === 'mediacms_lti';
  const isAsset =
    delivery.kind === 'asset' && typeof delivery.asset_version_id === 'string';
  const document =
    isDocument && record(delivery.content) && record(delivery.content.document)
      ? (delivery.content
          .document as unknown as LMSUnitAcademicDocumentVersion2)
      : null;
  const assetVersionId = isAsset ? String(delivery.asset_version_id) : null;
  const assetDescriptors = parseAssetDescriptors(data.payload.assets);
  const assetDescriptor = assetVersionId
    ? assetDescriptors.find(
        (asset) => asset.asset_version_id === assetVersionId,
      )
    : undefined;
  if (assetVersionId && !assetDescriptor) {
    throw new Error(
      'No se encontró el descriptor privado del archivo de la lección.',
    );
  }
  const assetDelivery =
    assetVersionId && assetDescriptor
      ? { assetVersionId, descriptor: assetDescriptor }
      : null;
  const isSourceLesson =
    lessonKind === 'latex_source' || lessonKind === 'markdown_source';
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
        outline={outlineData.outline}
        outlineHref={outlineHref}
        positionLabel={`Lección ${Math.max(1, unitNumber + 1)} de ${totalUnits}`}
        releaseNumber={data.payload.release_number}
        title={unit.title}
      >
        <article className="learning-player__lesson">
          {isMediaCMSVideo ? (
            <MediaCMSVideoPlayer
              enrollmentId={enrollment.enrollment_id}
              slug={slug}
              unitId={unitId}
            />
          ) : null}

          {isDocument && document ? (
            <div className="learning-player__document">
              <AcademicDocument
                assets={assetDescriptors}
                document={document as AcademicDocumentValue}
                refreshContext={{
                  enrollmentId: enrollment.enrollment_id,
                  slug,
                  unitId,
                }}
              />
            </div>
          ) : null}

          {assetDelivery && isSourceLesson ? (
            <SourceLessonRenderer
              descriptor={assetDelivery.descriptor}
              lessonKind={lessonKind}
              title={unit.title}
            />
          ) : null}

          {assetDelivery && !isSourceLesson ? (
            <div className="learning-player__delivery-resource">
              <AcademicAsset
                attrs={{
                  assetVersionId: assetDelivery.assetVersionId,
                  label: unit.title,
                }}
                descriptor={assetDelivery.descriptor}
                kind={lessonKind === 'audio' ? 'audio' : 'document'}
                refreshContext={{
                  enrollmentId: enrollment.enrollment_id,
                  slug,
                  unitId,
                }}
              />
            </div>
          ) : null}
        </article>

        <LearningPlayerNavigation
          label="Navegación entre lecciones"
          next={nextItem}
          previous={previousItem}
        >
          <LearningUnitControls
            enrollmentId={enrollment.enrollment_id}
            presentation="navigation"
            progress={data.payload.progress}
            slug={slug}
            unitId={unitId}
            unitStatus={unitStatus}
          />
        </LearningPlayerNavigation>
      </LearningPlayerShell>
      <LearningPositionTracker
        enrollmentId={enrollment.enrollment_id}
        slug={slug}
        unitId={unitId}
      />
    </>
  );
}
