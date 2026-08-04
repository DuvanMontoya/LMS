'use client';

import { Download, RefreshCcw } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { PdfDocumentReader } from '@/components/content/pdf-document-reader';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { AssetAccessDescriptor } from '@/lib/assets/api';
import { formatBytes } from '@/lib/assets/labels';

type RefreshContext = {
  enrollmentId: string;
  slug: string;
  unitId: string;
};

type AssessmentRefreshContext = {
  attemptId: string;
  slug: string;
};

function item(descriptor: AssetAccessDescriptor, roles: readonly string[]) {
  return descriptor.variants.find((variant) => roles.includes(variant.role));
}

export function AcademicAsset({
  assessmentRefreshContext,
  attrs,
  captionDescriptor,
  descriptor: initialDescriptor,
  kind,
  refreshContext,
}: Readonly<{
  assessmentRefreshContext?: AssessmentRefreshContext;
  attrs: Record<string, unknown>;
  captionDescriptor?: AssetAccessDescriptor;
  descriptor?: AssetAccessDescriptor;
  kind: 'audio' | 'dataset' | 'document' | 'image' | 'video';
  refreshContext?: RefreshContext;
}>) {
  const [descriptor, setDescriptor] = useState(initialDescriptor);
  const [refreshed, setRefreshed] = useState(false);
  const [error, setError] = useState('');
  const assetVersionId = String(attrs.assetVersionId ?? '');
  async function refresh() {
    if ((!refreshContext && !assessmentRefreshContext) || refreshed) {
      setError(
        'La URL temporal expiró. Recarga la unidad para intentarlo de nuevo.',
      );
      return;
    }
    setRefreshed(true);
    const ids = [
      assetVersionId,
      ...(typeof attrs.captionsAssetVersionId === 'string'
        ? [attrs.captionsAssetVersionId]
        : []),
    ];
    const result = assessmentRefreshContext
      ? await platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/assessments/attempts/{attempt_id}/assets/access/',
          {
            body: { asset_version_ids: ids },
            params: {
              path: {
                attempt_id: assessmentRefreshContext.attemptId,
                slug: assessmentRefreshContext.slug,
              },
            },
          },
        )
      : await platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/assets/access/',
          {
            body: {
              asset_version_ids: ids,
              unit_id: refreshContext!.unitId,
            },
            params: {
              path: {
                enrollment_id: refreshContext!.enrollmentId,
                slug: refreshContext!.slug,
              },
            },
          },
        );
    const { data, response } = result;
    if (!response.ok || !data) {
      setError('No fue posible renovar el acceso temporal.');
      return;
    }
    const next = data.assets.find(
      (entry) =>
        typeof entry === 'object' &&
        entry !== null &&
        entry.asset_version_id === assetVersionId,
    ) as AssetAccessDescriptor | undefined;
    if (!next) {
      setError('El recurso ya no está autorizado para esta unidad.');
      return;
    }
    setDescriptor(next);
    setError('');
  }
  if (!descriptor) {
    return (
      <figure className="rounded-lg border border-dashed p-4">
        <figcaption className="font-medium">
          Recurso {kind} fijado a la versión {assetVersionId}
        </figcaption>
        <p className="mt-1 text-sm text-muted-foreground">
          La vista temporal estará disponible en la entrega publicada.
        </p>
      </figure>
    );
  }
  const source =
    kind === 'image'
      ? item(descriptor, ['image_large', 'image_medium', 'image_web_fallback'])
      : kind === 'audio'
        ? item(descriptor, ['audio_playback'])
        : kind === 'video'
          ? item(descriptor, ['video_playback'])
          : descriptor.source;
  const poster = item(descriptor, ['video_poster']);
  const captionSource = captionDescriptor
    ? item(captionDescriptor, ['caption_normalized'])
    : undefined;
  const onMediaError = () => void refresh();
  if (!source)
    return <p role="alert">El recurso no tiene una variante entregable.</p>;
  const integratedPdf =
    kind === 'document' && source.mime_type === 'application/pdf';
  return (
    <figure
      className={
        integratedPdf
          ? 'my-5 overflow-hidden rounded-xl bg-transparent'
          : 'my-5 overflow-hidden rounded-lg border bg-card'
      }
    >
      {kind === 'image' ? (
        // Signed URLs intentionally bypass the Next image proxy.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          alt={Boolean(attrs.decorative) ? '' : String(attrs.altText ?? '')}
          className="max-h-[40rem] w-full object-contain"
          height={source.height ?? 720}
          loading="lazy"
          onError={onMediaError}
          src={source.url}
          width={source.width ?? 1280}
        />
      ) : null}
      {kind === 'audio' ? (
        <audio
          className="m-4 w-[calc(100%-2rem)]"
          controls
          onError={onMediaError}
          preload="metadata"
          src={source.url}
        >
          Tu navegador no puede reproducir este audio.
        </audio>
      ) : null}
      {kind === 'video' ? (
        <video
          className="aspect-video w-full bg-black"
          controls
          crossOrigin={captionSource ? 'anonymous' : undefined}
          onError={onMediaError}
          poster={poster?.url}
          preload="metadata"
          src={source.url}
        >
          {captionSource ? (
            <track
              default
              kind="captions"
              label="Español"
              src={captionSource.url}
              srcLang="es"
            />
          ) : null}
          Tu navegador no puede reproducir este video.
        </video>
      ) : null}
      {integratedPdf ? (
        <PdfDocumentReader
          key={source.url}
          onError={onMediaError}
          source={source.url}
          title={String(attrs.label ?? 'Documento PDF')}
        />
      ) : null}
      {kind === 'dataset' ||
      (kind === 'document' && source.mime_type !== 'application/pdf') ? (
        <div className="flex flex-wrap items-center justify-between gap-4 p-4">
          <div>
            <p className="font-medium">
              {String(attrs.label ?? 'Descargar recurso')}
            </p>
            <p className="text-sm text-muted-foreground">
              {source.mime_type} · {formatBytes(source.size_bytes)}
            </p>
          </div>
          <Button asChild>
            <a href={source.url}>
              <Download data-icon="inline-start" />
              Descargar
            </a>
          </Button>
        </div>
      ) : null}
      {attrs.caption || attrs.description ? (
        <figcaption className="border-t px-4 py-3 text-sm text-muted-foreground">
          {String(attrs.caption ?? attrs.description)}
        </figcaption>
      ) : null}
      {(kind === 'audio' || kind === 'video') && attrs.transcript ? (
        <details className="border-t px-4 py-3">
          <summary className="cursor-pointer font-medium">
            Transcripción
          </summary>
          <p className="mt-2 whitespace-pre-wrap text-sm text-muted-foreground">
            {String(attrs.transcript)}
          </p>
        </details>
      ) : null}
      {error ? (
        <div className="border-t p-3 text-sm text-destructive">
          <p>{error}</p>
          {!refreshed ? (
            <Button
              className="mt-2"
              onClick={refresh}
              size="sm"
              variant="outline"
            >
              <RefreshCcw data-icon="inline-start" />
              Renovar acceso
            </Button>
          ) : null}
        </div>
      ) : null}
    </figure>
  );
}
