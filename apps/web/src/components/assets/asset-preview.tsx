'use client';

import { useQuery } from '@tanstack/react-query';
import { FileAudio, FileText, Film, ImageIcon, Table2 } from 'lucide-react';
import { useState } from 'react';

import { getAssetAccess } from '@/lib/assets/api';

const kindMeta: Record<
  string,
  { label: string; caption: string; surface: string; icon: string }
> = {
  image: {
    label: 'Imagen',
    caption: 'Vista visual · variantes responsivas',
    surface: 'from-sky-50 via-white to-indigo-50 text-sky-700',
    icon: 'border-sky-200/80 bg-white/85',
  },
  document: {
    label: 'Documento',
    caption: 'Documento académico · PDF',
    surface: 'from-amber-50 via-white to-orange-50 text-amber-700',
    icon: 'border-amber-200/80 bg-white/85',
  },
  audio: {
    label: 'Audio',
    caption: 'Audio académico · transcript',
    surface: 'from-violet-50 via-white to-fuchsia-50 text-violet-700',
    icon: 'border-violet-200/80 bg-white/85',
  },
  video: {
    label: 'Video',
    caption: 'Video académico · poster y captions',
    surface: 'from-rose-50 via-white to-orange-50 text-rose-700',
    icon: 'border-rose-200/80 bg-white/85',
  },
  dataset: {
    label: 'Dataset',
    caption: 'Datos estructurados · preview seguro',
    surface: 'from-emerald-50 via-white to-teal-50 text-emerald-700',
    icon: 'border-emerald-200/80 bg-white/85',
  },
  caption: {
    label: 'Subtítulos',
    caption: 'WebVTT · accesibilidad multimedia',
    surface: 'from-cyan-50 via-white to-blue-50 text-cyan-700',
    icon: 'border-cyan-200/80 bg-white/85',
  },
};

export function AssetPreview({
  assetId,
  kind,
  name,
  slug,
  versionId,
}: Readonly<{
  assetId: string;
  kind: string;
  name: string;
  slug: string;
  versionId?: string | null;
}>) {
  const [failedUrl, setFailedUrl] = useState('');
  const descriptor = useQuery({
    enabled: Boolean(versionId && ['image', 'video'].includes(kind)),
    queryFn: () => getAssetAccess(slug, assetId, versionId!),
    queryKey: ['asset-access', slug, assetId, versionId],
    staleTime: 8 * 60 * 1000,
  });
  const preview =
    descriptor.data?.variants.find((item) =>
      ['image_thumbnail', 'video_poster'].includes(item.role),
    ) ?? descriptor.data?.source;
  if (preview?.url && preview.url !== failedUrl) {
    return (
      // Signed S3 URLs intentionally bypass the Next image proxy.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        alt=""
        className="h-full w-full object-cover"
        height={preview.height ?? 160}
        loading="lazy"
        onError={() => setFailedUrl(preview.url)}
        src={preview.url}
        width={preview.width ?? 240}
      />
    );
  }
  const Icon =
    kind === 'image'
      ? ImageIcon
      : kind === 'video'
        ? Film
        : kind === 'audio'
          ? FileAudio
          : kind === 'dataset'
            ? Table2
            : FileText;
  // The document entry is the explicit fallback for unknown asset kinds.
  const meta = kindMeta[kind] ?? kindMeta.document!;
  return (
    <span
      aria-label={`Vista previa de ${name}`}
      className={`relative flex h-full w-full flex-col items-center justify-center gap-2 overflow-hidden bg-linear-to-br ${meta.surface}`}
      role="img"
    >
      <span className="absolute inset-x-3 top-3 flex items-center justify-between">
        <span className="rounded-full border border-white/80 bg-white/70 px-2 py-1 text-[0.6rem] font-bold tracking-[0.12em] uppercase backdrop-blur-sm">
          {meta.label}
        </span>
        <span className="font-mono text-[0.6rem] font-semibold tracking-widest opacity-60">
          LMS / ASSET
        </span>
      </span>
      <span
        className={`grid size-12 place-items-center rounded-2xl border shadow-sm shadow-slate-900/5 ${meta.icon}`}
      >
        <Icon className="size-6" strokeWidth={1.8} />
      </span>
      <span className="text-center text-[0.67rem] font-medium tracking-wide opacity-75">
        {meta.caption}
      </span>
    </span>
  );
}
