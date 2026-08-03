'use client';

import { useQuery } from '@tanstack/react-query';
import { Download, LoaderCircle, RefreshCcw } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { getAssetAccess } from '@/lib/assets/api';
import { formatBytes } from '@/lib/assets/labels';

export function AssetMedia({
  assetId,
  description,
  kind,
  name,
  slug,
  versionId,
}: Readonly<{
  assetId: string;
  description: string;
  kind: string;
  name: string;
  slug: string;
  versionId: string;
}>) {
  const query = useQuery({
    queryFn: () => getAssetAccess(slug, assetId, versionId),
    queryKey: ['asset-access', slug, assetId, versionId],
    staleTime: 8 * 60 * 1000,
  });
  if (query.isPending) {
    return (
      <div className="flex items-center gap-2 rounded-lg border p-5 text-sm text-muted-foreground">
        <LoaderCircle className="size-4 animate-spin" />
        Autorizando vista temporal…
      </div>
    );
  }
  if (query.isError || !query.data) {
    return (
      <div className="rounded-lg border p-5">
        <p className="text-sm text-destructive">
          No fue posible abrir la vista temporal.
        </p>
        <Button
          className="mt-3"
          onClick={() => query.refetch()}
          size="sm"
          variant="outline"
        >
          <RefreshCcw data-icon="inline-start" />
          Reintentar
        </Button>
      </div>
    );
  }
  const descriptor = query.data;
  const playback =
    descriptor.variants.find((item) =>
      kind === 'image'
        ? item.role === 'image_large'
        : kind === 'audio'
          ? item.role === 'audio_playback'
          : kind === 'video'
            ? item.role === 'video_playback'
            : item.role === 'caption_normalized',
    ) ??
    descriptor.variants[0] ??
    descriptor.source;
  const poster = descriptor.variants.find(
    (item) => item.role === 'video_poster',
  );
  if (!playback) return null;
  if (kind === 'image') {
    return (
      <figure className="overflow-hidden rounded-lg border bg-muted/20">
        {/* Signed URLs intentionally bypass the Next image proxy. */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          alt={description || name}
          className="max-h-[36rem] w-full object-contain"
          height={playback.height ?? 540}
          loading="lazy"
          src={playback.url}
          width={playback.width ?? 960}
        />
        {description ? (
          <figcaption className="border-t px-4 py-3 text-sm text-muted-foreground">
            {description}
          </figcaption>
        ) : null}
      </figure>
    );
  }
  if (kind === 'audio') {
    return (
      <figure className="rounded-lg border p-4">
        <figcaption className="mb-3 font-medium">{name}</figcaption>
        <audio
          className="w-full"
          controls
          preload="metadata"
          src={playback.url}
        >
          Tu navegador no puede reproducir este audio.
        </audio>
        {description ? (
          <details className="mt-3 text-sm">
            <summary className="cursor-pointer font-medium">
              Descripción
            </summary>
            <p className="mt-2 text-muted-foreground">{description}</p>
          </details>
        ) : null}
      </figure>
    );
  }
  if (kind === 'video') {
    return (
      <figure className="overflow-hidden rounded-lg border bg-black">
        <video
          className="aspect-video w-full"
          controls
          poster={poster?.url}
          preload="metadata"
          src={playback.url}
        >
          Tu navegador no puede reproducir este video.
        </video>
        {description ? (
          <figcaption className="bg-background px-4 py-3 text-sm text-muted-foreground">
            {description}
          </figcaption>
        ) : null}
      </figure>
    );
  }
  if (kind === 'document') {
    return (
      <div className="asset-media-document">
        <iframe src={playback.url} title={`Vista previa de ${name}`} />
        <Button asChild size="sm" variant="outline">
          <a href={playback.url} rel="noreferrer" target="_blank">
            <Download data-icon="inline-start" />
            Abrir PDF en otra pestaña
          </a>
        </Button>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-4 rounded-lg border p-4">
      <div>
        <p className="font-medium">{name}</p>
        <p className="text-sm text-muted-foreground">
          {playback.mime_type} · {formatBytes(playback.size_bytes)}
        </p>
      </div>
      <Button asChild>
        <a href={playback.url}>
          <Download data-icon="inline-start" />
          Descargar
        </a>
      </Button>
    </div>
  );
}
