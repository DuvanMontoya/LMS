'use client';

import { Archive, ArchiveRestore, Download, RefreshCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import {
  getAssetAccess,
  mutateAssetState,
  promoteAssetVersion,
  reprocessAssetVersion,
} from '@/lib/assets/api';

export function AssetDetailActions({
  assetId,
  canDownload,
  canManage,
  canReprocess,
  currentVersionId,
  lockVersion,
  slug,
  status,
  versions,
}: Readonly<{
  assetId: string;
  canDownload: boolean;
  canManage: boolean;
  canReprocess: boolean;
  currentVersionId?: string | null;
  lockVersion: number;
  slug: string;
  status: string;
  versions: readonly { id: string; number: number; status?: string }[];
}>) {
  const router = useRouter();
  const [busy, setBusy] = useState('');
  const [message, setMessage] = useState('');
  async function perform(name: string, operation: () => Promise<unknown>) {
    setBusy(name);
    setMessage('');
    try {
      await operation();
      router.refresh();
    } catch (error) {
      setMessage(
        error instanceof Error ? error.message : 'La operación falló.',
      );
    } finally {
      setBusy('');
    }
  }
  const promotable = versions.find(
    (version) => version.status === 'ready' && version.id !== currentVersionId,
  );
  return (
    <div>
      <div className="flex flex-wrap gap-2">
        {canDownload && currentVersionId ? (
          <Button
            disabled={Boolean(busy)}
            onClick={() =>
              perform('download', async () => {
                const descriptor = await getAssetAccess(
                  slug,
                  assetId,
                  currentVersionId,
                  true,
                );
                if (!descriptor.source)
                  throw new Error('El original no está disponible.');
                window.location.assign(descriptor.source.url);
              })
            }
            variant="outline"
          >
            <Download data-icon="inline-start" />
            Original
          </Button>
        ) : null}
        {canReprocess && currentVersionId ? (
          <Button
            disabled={Boolean(busy)}
            onClick={() =>
              perform('reprocess', () =>
                reprocessAssetVersion(slug, assetId, currentVersionId),
              )
            }
            variant="outline"
          >
            <RefreshCcw data-icon="inline-start" />
            Reprocesar
          </Button>
        ) : null}
        {canManage && promotable ? (
          <Button
            disabled={Boolean(busy)}
            onClick={() =>
              perform('promote', () =>
                promoteAssetVersion(slug, assetId, promotable.id, lockVersion),
              )
            }
            variant="outline"
          >
            Promover v{promotable.number}
          </Button>
        ) : null}
        {canManage ? (
          <Button
            disabled={Boolean(busy)}
            onClick={() =>
              perform('state', () =>
                mutateAssetState(
                  slug,
                  assetId,
                  status === 'archived' ? 'restore' : 'archive',
                  lockVersion,
                ),
              )
            }
            variant="outline"
          >
            {status === 'archived' ? (
              <ArchiveRestore data-icon="inline-start" />
            ) : (
              <Archive data-icon="inline-start" />
            )}
            {status === 'archived' ? 'Restaurar' : 'Archivar'}
          </Button>
        ) : null}
      </div>
      {message ? (
        <p aria-live="polite" className="mt-2 text-sm text-destructive">
          {message}
        </p>
      ) : null}
    </div>
  );
}
