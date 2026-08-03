'use client';

import { ArrowUpRight, FileText } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { useState } from 'react';

import { AssetMedia } from '@/components/assets/asset-media';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import type { components } from '@/lib/api/generated/platform';
import {
  assetKindLabel,
  assetStatusLabel,
  formatBytes,
} from '@/lib/assets/labels';

type AssetKind = components['schemas']['AssetKind'];
type AssetLibraryItem = {
  current_version: {
    declared_mime_type: string;
    detected_mime_type?: string;
    id: string;
    number: number;
    original_filename: string;
    size_bytes?: number | null;
    status?: string;
    technical_metadata?: unknown;
  } | null;
  description?: string;
  id: string;
  kind: AssetKind;
  name: string;
  status?: string;
};

export function AssetLibraryDialog({
  asset,
  canManage,
  children,
  slug,
}: Readonly<{
  asset: AssetLibraryItem;
  canManage: boolean;
  children: ReactNode;
  slug: string;
}>) {
  const [open, setOpen] = useState(false);
  const current = asset.current_version;
  const hasStructuredPreview =
    asset.kind === 'dataset' && hasDatasetPreview(current?.technical_metadata);
  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <button
          aria-label={`Vista previa de ${asset.name}`}
          className="asset-resource-card__trigger"
          type="button"
        >
          {children}
        </button>
      </DialogTrigger>
      <DialogContent className="asset-library-dialog max-h-[94vh] overflow-y-auto sm:max-w-6xl">
        <DialogHeader className="pr-10">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="secondary">{assetKindLabel(asset.kind)}</Badge>
            <Badge variant="outline">
              {assetStatusLabel(current?.status ?? asset.status ?? '')}
            </Badge>
          </div>
          <DialogTitle>{asset.name}</DialogTitle>
          <DialogDescription>
            {asset.description ||
              'Recurso académico sin descripción editorial.'}
          </DialogDescription>
        </DialogHeader>

        <div className="asset-library-dialog__viewer">
          {current?.status === 'ready' ? (
            <>
              {asset.kind === 'dataset' ? (
                <DatasetPreview metadata={current.technical_metadata} />
              ) : null}
              {!hasStructuredPreview ? (
                <AssetMedia
                  assetId={asset.id}
                  description={asset.description ?? ''}
                  kind={asset.kind}
                  name={asset.name}
                  slug={slug}
                  versionId={current.id}
                />
              ) : null}
            </>
          ) : (
            <div className="asset-library-dialog__unavailable">
              <FileText />
              <strong>Vista todavía no disponible</strong>
              <p>
                El archivo debe finalizar su procesamiento antes de abrirse.
              </p>
            </div>
          )}
        </div>

        {current ? (
          <dl className="asset-library-dialog__facts">
            <div>
              <dt>Versión</dt>
              <dd>v{current.number}</dd>
            </div>
            <div>
              <dt>Archivo</dt>
              <dd>{current.original_filename}</dd>
            </div>
            <div>
              <dt>Formato</dt>
              <dd>
                {current.detected_mime_type || current.declared_mime_type}
              </dd>
            </div>
            <div>
              <dt>Tamaño</dt>
              <dd>{formatBytes(current.size_bytes)}</dd>
            </div>
          </dl>
        ) : null}

        {canManage ? (
          <DialogFooter>
            <Button asChild variant="outline">
              <Link href={`/organizaciones/${slug}/recursos/${asset.id}`}>
                Administrar versiones
                <ArrowUpRight data-icon="inline-end" />
              </Link>
            </Button>
          </DialogFooter>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function DatasetPreview({ metadata }: Readonly<{ metadata: unknown }>) {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata))
    return null;
  const source = metadata as Record<string, unknown>;
  const columns = Array.isArray(source.columns)
    ? source.columns.filter(
        (value): value is string => typeof value === 'string',
      )
    : [];
  const rows = Array.isArray(source.sample_rows)
    ? source.sample_rows.filter((value): value is unknown[] =>
        Array.isArray(value),
      )
    : [];
  if (columns.length && rows.length) {
    return (
      <div className="asset-library-dialog__dataset">
        <table>
          <caption className="sr-only">
            Primeras filas procesadas del dataset
          </caption>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column}>{column}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={`row-${rowIndex}`}>
                {columns.map((column, columnIndex) => (
                  <td key={`${column}-${columnIndex}`}>
                    {String(row[columnIndex] ?? '')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  if (typeof source.sample === 'string' && source.sample) {
    return (
      <pre className="asset-library-dialog__text-preview">{source.sample}</pre>
    );
  }
  return null;
}

function hasDatasetPreview(metadata: unknown) {
  if (!metadata || typeof metadata !== 'object' || Array.isArray(metadata))
    return false;
  const source = metadata as Record<string, unknown>;
  return (
    (Array.isArray(source.columns) && Array.isArray(source.sample_rows)) ||
    (typeof source.sample === 'string' && Boolean(source.sample))
  );
}
