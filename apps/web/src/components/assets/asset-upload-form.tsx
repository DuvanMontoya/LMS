'use client';

import { useQuery } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, LoaderCircle, Upload } from 'lucide-react';
import Link from 'next/link';
import { useRef, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { components } from '@/lib/api/generated/platform';
import { assetStatusLabel, formatBytes } from '@/lib/assets/labels';
import {
  abortUpload,
  completeUpload,
  initializeUpload,
  processingJob,
  uploadMultipart,
  uploadSingle,
  type ProcessingJob,
} from '@/lib/assets/upload-client';

type AssetKind = components['schemas']['AssetKind'];
type UploadStage =
  | 'idle'
  | 'preparing'
  | 'uploading'
  | 'verifying'
  | 'processing'
  | 'ready'
  | 'cancelled'
  | 'error';

const ACCEPT: Record<AssetKind, string> = {
  audio: '.mp3,.m4a,.mp4,.wav,.ogg',
  caption: '.vtt',
  dataset: '.csv,.json,.txt',
  document: '.pdf',
  image: '.jpg,.jpeg,.png,.webp',
  video: '.mp4,.mov,.webm',
};

const FALLBACK_MIME_BY_EXTENSION: Readonly<
  Record<AssetKind, Readonly<Record<string, string>>>
> = {
  audio: {
    '.m4a': 'audio/mp4',
    '.mp3': 'audio/mpeg',
    '.mp4': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.wav': 'audio/wav',
  },
  caption: { '.vtt': 'text/vtt' },
  dataset: {
    '.csv': 'text/csv',
    '.json': 'application/json',
    '.txt': 'text/plain',
  },
  document: { '.pdf': 'application/pdf' },
  image: {
    '.jpeg': 'image/jpeg',
    '.jpg': 'image/jpeg',
    '.png': 'image/png',
    '.webp': 'image/webp',
  },
  video: {
    '.mov': 'video/quicktime',
    '.mp4': 'video/mp4',
    '.webm': 'video/webm',
  },
};

function declaredMimeType(file: File, kind: AssetKind): string {
  const browserMime = file.type.trim().toLowerCase();
  if (browserMime) return browserMime;
  const extension = file.name.includes('.')
    ? file.name.slice(file.name.lastIndexOf('.')).toLowerCase()
    : '';
  return (
    FALLBACK_MIME_BY_EXTENSION[kind][extension] ?? 'application/octet-stream'
  );
}

export function AssetUploadForm({ slug }: Readonly<{ slug: string }>) {
  const [kind, setKind] = useState<AssetKind>('image');
  const [stage, setStage] = useState<UploadStage>('idle');
  const [loaded, setLoaded] = useState(0);
  const [size, setSize] = useState(0);
  const [error, setError] = useState('');
  const [assetId, setAssetId] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [job, setJob] = useState<ProcessingJob>();
  const activeRequests = useRef<Set<XMLHttpRequest>>(new Set());
  const jobQuery = useQuery({
    enabled: Boolean(job?.id && stage === 'processing'),
    queryFn: () => processingJob(slug, job!.id),
    queryKey: ['asset-processing-job', slug, job?.id],
    refetchInterval: (query) => {
      const value = query.state.data;
      return value &&
        ['completed', 'completed_with_errors', 'failed'].includes(
          value.status ?? '',
        )
        ? false
        : 2000;
    },
  });
  const currentJob = jobQuery.data ?? job;
  const terminal =
    currentJob &&
    ['completed', 'completed_with_errors', 'failed'].includes(
      currentJob.status ?? '',
    );
  if (terminal && stage === 'processing') {
    queueMicrotask(() =>
      setStage(currentJob.status === 'completed' ? 'ready' : 'error'),
    );
  }

  function register(xhr: XMLHttpRequest) {
    activeRequests.current.add(xhr);
    xhr.addEventListener('loadend', () => activeRequests.current.delete(xhr));
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const file = data.get('file');
    if (!(file instanceof File) || file.size === 0) {
      setError('Selecciona un archivo válido.');
      return;
    }
    setError('');
    setLoaded(0);
    setSize(file.size);
    setStage('preparing');
    try {
      const instructions = await initializeUpload(slug, {
        declared_mime_type: declaredMimeType(file, kind),
        description: String(data.get('description') ?? ''),
        filename: file.name,
        kind,
        name: String(data.get('name') ?? ''),
        size_bytes: file.size,
      });
      setAssetId(instructions.asset_id);
      setSessionId(instructions.session_id);
      setStage('uploading');
      const progress = (value: number) => setLoaded(value);
      if (instructions.upload_method === 'multipart') {
        await uploadMultipart({
          file,
          instructions,
          onProgress: progress,
          register,
          slug,
        });
      } else {
        await uploadSingle({
          file,
          instructions,
          onProgress: progress,
          register,
        });
      }
      setStage('verifying');
      const nextJob = await completeUpload(slug, instructions.session_id);
      setJob(nextJob);
      setStage('processing');
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') {
        setStage('cancelled');
      } else {
        setError(caught instanceof Error ? caught.message : 'La carga falló.');
        setStage('error');
      }
    }
  }

  async function cancel() {
    for (const request of activeRequests.current) request.abort();
    if (sessionId) {
      try {
        await abortUpload(slug, sessionId);
      } catch {
        // The visible cancellation state remains accurate even if cleanup is retried server-side.
      }
    }
    setStage('cancelled');
  }

  const percent = size ? Math.min(100, Math.round((loaded / size) * 100)) : 0;
  const stageText =
    stage === 'processing' && currentJob
      ? assetStatusLabel(currentJob.stage)
      : {
          cancelled: 'Cancelado',
          error: 'Error',
          idle: 'Esperando archivo',
          preparing: 'Preparando carga',
          processing: 'Procesando',
          ready: 'Listo',
          uploading: 'Cargando',
          verifying: 'Verificando',
        }[stage];

  return (
    <form className="mt-6 max-w-2xl space-y-6" onSubmit={submit}>
      <div className="space-y-2">
        <Label htmlFor="asset-kind">Tipo de recurso</Label>
        <select
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
          disabled={
            stage !== 'idle' && stage !== 'error' && stage !== 'cancelled'
          }
          id="asset-kind"
          onChange={(event) => setKind(event.target.value as AssetKind)}
          value={kind}
        >
          <option value="image">Imagen</option>
          <option value="document">Documento PDF</option>
          <option value="audio">Audio</option>
          <option value="video">Video</option>
          <option value="dataset">Dataset</option>
          <option value="caption">Subtítulos WebVTT</option>
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor="asset-name">Nombre</Label>
        <Input id="asset-name" maxLength={200} name="name" required />
      </div>
      <div className="space-y-2">
        <Label htmlFor="asset-description">Descripción</Label>
        <Textarea id="asset-description" maxLength={2000} name="description" />
      </div>
      <div className="space-y-2">
        <Label htmlFor="asset-file">Archivo</Label>
        <Input
          accept={ACCEPT[kind]}
          aria-describedby="asset-file-help"
          id="asset-file"
          name="file"
          required
          type="file"
        />
        <p className="text-sm text-muted-foreground" id="asset-file-help">
          Formatos permitidos: {ACCEPT[kind]}. El archivo se carga directamente
          al almacenamiento privado de cuarentena y sólo estará disponible al
          terminar el análisis.
        </p>
      </div>
      {stage !== 'idle' ? (
        <section
          aria-atomic="true"
          aria-live="polite"
          className="rounded-lg border bg-muted/20 p-4"
        >
          <div className="flex items-center gap-2 font-medium">
            {stage === 'ready' ? (
              <CheckCircle2 className="size-5 text-emerald-600" />
            ) : stage === 'error' ? (
              <AlertCircle className="size-5 text-destructive" />
            ) : (
              <LoaderCircle className="size-5 animate-spin" />
            )}
            {stageText}
          </div>
          {stage === 'uploading' ? (
            <>
              <progress
                aria-label="Progreso de carga"
                className="mt-3 h-2 w-full"
                max={100}
                value={percent}
              />
              <p className="mt-1 text-sm text-muted-foreground">
                {percent}% · {formatBytes(loaded)} de {formatBytes(size)}
              </p>
            </>
          ) : null}
          {stage === 'processing' && currentJob ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Etapa: {assetStatusLabel(currentJob.stage)}. Esta pantalla se
              actualiza automáticamente.
            </p>
          ) : null}
          {stage === 'ready' && assetId ? (
            <Button asChild className="mt-3" size="sm">
              <Link href={`/organizaciones/${slug}/recursos/${assetId}`}>
                Abrir recurso
              </Link>
            </Button>
          ) : null}
        </section>
      ) : null}
      {error ? (
        <Alert variant="destructive">
          <AlertCircle />
          <AlertTitle>No se pudo completar la carga</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <Button
          disabled={[
            'preparing',
            'uploading',
            'verifying',
            'processing',
          ].includes(stage)}
          type="submit"
        >
          <Upload data-icon="inline-start" />
          {stage === 'error' || stage === 'cancelled'
            ? 'Reintentar'
            : 'Iniciar carga'}
        </Button>
        {['preparing', 'uploading', 'verifying'].includes(stage) ? (
          <Button onClick={cancel} type="button" variant="outline">
            Cancelar
          </Button>
        ) : null}
      </div>
    </form>
  );
}
