'use client';

import { useQuery } from '@tanstack/react-query';
import { FolderOpen, ImagePlus, Search, Upload } from 'lucide-react';
import { useMemo, useState } from 'react';

import { AssetPreview } from '@/components/assets/asset-preview';
import { AssetUploadForm } from '@/components/assets/asset-upload-form';
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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { apiErrorMessage } from '@/lib/api/api-error';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import { assetKindLabel, formatBytes } from '@/lib/assets/labels';

type AssetKind = components['schemas']['AssetKind'];
type AssetSummary = components['schemas']['AssetSummary'];
export type InsertableAssetKind = Exclude<AssetKind, 'caption'>;

async function listAssets(slug: string): Promise<AssetSummary[]> {
  const { data, error, response } = await platformBrowserClient.GET(
    '/api/v1/organizations/{organization_slug}/assets/',
    {
      params: {
        path: { organization_slug: slug },
        query: { status: 'active' },
      },
    },
  );
  if (!response.ok || !data)
    throw new Error(apiErrorMessage(error, 'No fue posible abrir Recursos.'));
  return data as unknown as AssetSummary[];
}

export function AssetPickerDialog({
  allowDecorative = true,
  allowedKinds = ['image', 'audio', 'video', 'document', 'dataset'],
  iconOnly = false,
  onInsert,
  resourceOnly = false,
  slug,
  triggerLabel = 'Imagen o recurso',
}: Readonly<{
  allowDecorative?: boolean;
  allowedKinds?: readonly InsertableAssetKind[];
  iconOnly?: boolean;
  onInsert: (node: Record<string, unknown>) => void;
  resourceOnly?: boolean;
  slug: string;
  triggerLabel?: string;
}>) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState<'computer' | 'resources'>('computer');
  const [kind, setKind] = useState<InsertableAssetKind>(
    allowedKinds[0] ?? 'image',
  );
  const [search, setSearch] = useState('');
  const [selectedId, setSelectedId] = useState('');
  const [altText, setAltText] = useState('');
  const [decorative, setDecorative] = useState(false);
  const [title, setTitle] = useState('');
  const [transcript, setTranscript] = useState('');
  const [caption, setCaption] = useState('');
  const [description, setDescription] = useState('');
  const [label, setLabel] = useState('');
  const [silent, setSilent] = useState(false);
  const [captionVersionId, setCaptionVersionId] = useState('');
  const query = useQuery({
    enabled: open,
    queryFn: () => listAssets(slug),
    queryKey: ['asset-picker', slug],
    staleTime: 30_000,
  });
  const candidates = useMemo(
    () =>
      (query.data ?? []).filter(
        (asset) =>
          asset.kind === kind &&
          asset.current_version?.status === 'ready' &&
          asset.name.toLocaleLowerCase().includes(search.toLocaleLowerCase()),
      ),
    [kind, query.data, search],
  );
  const captions = (query.data ?? []).filter(
    (asset) =>
      asset.kind === 'caption' && asset.current_version?.status === 'ready',
  );
  const selected = candidates.find((asset) => asset.id === selectedId);

  function insert() {
    const versionId = selected?.current_version?.id;
    if (!selected || !versionId) return;
    const common = { assetVersionId: versionId, nodeId: crypto.randomUUID() };
    const attrs = resourceOnly
      ? common
      : kind === 'image'
        ? {
            ...common,
            altText: allowDecorative && decorative ? '' : altText.trim(),
            caption: caption.trim(),
            decorative: allowDecorative && decorative,
            displaySize: 'large',
          }
        : kind === 'audio'
          ? {
              ...common,
              caption: caption.trim(),
              title: title.trim(),
              transcript: transcript.trim(),
            }
          : kind === 'video'
            ? {
                ...common,
                caption: caption.trim(),
                ...(silent ? {} : { captionsAssetVersionId: captionVersionId }),
                silent,
                title: title.trim(),
                transcript: transcript.trim(),
              }
            : {
                ...common,
                description: description.trim(),
                label: label.trim(),
              };
    onInsert(
      resourceOnly
        ? { attrs, type: 'lessonResource' }
        : {
            attrs,
            type:
              kind === 'image'
                ? 'imageAsset'
                : kind === 'audio'
                  ? 'audioAsset'
                  : kind === 'video'
                    ? 'videoAsset'
                    : kind === 'document'
                      ? 'documentAsset'
                      : 'datasetAsset',
          },
    );
    setOpen(false);
  }

  const accessibilityValid =
    selected &&
    (resourceOnly ||
      (kind === 'image'
        ? (allowDecorative && decorative) || Boolean(altText.trim())
        : kind === 'audio'
          ? Boolean(title.trim() && transcript.trim())
          : kind === 'video'
            ? Boolean(
                title.trim() &&
                transcript.trim() &&
                (silent || captionVersionId),
              )
            : Boolean(label.trim())));

  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button
          aria-label={iconOnly ? triggerLabel : undefined}
          size={iconOnly ? 'icon-sm' : 'sm'}
          type="button"
          variant="ghost"
        >
          <ImagePlus />
          {iconOnly ? null : triggerLabel}
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[92vh] overflow-y-auto sm:max-w-4xl">
        <DialogHeader>
          <DialogTitle>
            {resourceOnly
              ? 'Seleccionar archivo de la lección'
              : 'Añadir archivo'}
          </DialogTitle>
          <DialogDescription>
            {resourceOnly
              ? 'Selecciona una versión lista. La lección entregará sólo este archivo.'
              : 'Sube uno desde este equipo o reutiliza una versión lista de Recursos.'}
          </DialogDescription>
        </DialogHeader>

        <div
          aria-label="Origen del archivo"
          className="asset-picker-source"
          role="tablist"
        >
          <button
            aria-selected={source === 'computer'}
            data-active={source === 'computer'}
            onClick={() => setSource('computer')}
            role="tab"
            type="button"
          >
            <Upload /> Desde mi equipo
          </button>
          <button
            aria-selected={source === 'resources'}
            data-active={source === 'resources'}
            onClick={() => setSource('resources')}
            role="tab"
            type="button"
          >
            <FolderOpen /> Recursos
          </button>
        </div>

        {source === 'computer' ? (
          <AssetUploadForm
            allowedKinds={allowedKinds}
            compact
            onReady={(assetId, uploadedKind) => {
              setKind(uploadedKind as InsertableAssetKind);
              setSelectedId(assetId);
              setSource('resources');
              void query.refetch();
            }}
            slug={slug}
          />
        ) : (
          <div className="asset-picker-layout">
            <section className="asset-picker-browser">
              <div className="asset-picker-filters">
                <label>
                  <span className="sr-only">Tipo</span>
                  <select
                    className="academic-control"
                    onChange={(event) => {
                      setKind(event.target.value as InsertableAssetKind);
                      setSelectedId('');
                    }}
                    value={kind}
                  >
                    {allowedKinds.map((value) => (
                      <option key={value} value={value}>
                        {assetKindLabel(value)}
                      </option>
                    ))}
                  </select>
                </label>
                <label className="relative">
                  <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                  <span className="sr-only">Buscar en Recursos</span>
                  <Input
                    className="pl-9"
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Buscar en Recursos"
                    value={search}
                  />
                </label>
              </div>
              {query.isLoading ? (
                <p className="asset-picker-empty">Cargando recursos…</p>
              ) : query.error ? (
                <p className="asset-picker-error">
                  {query.error instanceof Error
                    ? query.error.message
                    : 'No fue posible cargar Recursos.'}
                </p>
              ) : candidates.length ? (
                <ul className="asset-picker-results">
                  {candidates.map((asset) => (
                    <li key={asset.id}>
                      <button
                        aria-pressed={selectedId === asset.id}
                        data-active={selectedId === asset.id}
                        onClick={() => setSelectedId(asset.id)}
                        type="button"
                      >
                        <span className="asset-picker-results__preview">
                          <AssetPreview
                            assetId={asset.id}
                            kind={asset.kind}
                            name={asset.name}
                            slug={slug}
                            versionId={asset.current_version?.id}
                          />
                        </span>
                        <span>
                          <strong>{asset.name}</strong>
                          <small>
                            v{asset.current_version?.number} ·{' '}
                            {formatBytes(asset.current_version?.size_bytes)}
                          </small>
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="asset-picker-empty">
                  No hay archivos listos con este filtro.
                </p>
              )}
            </section>

            <section className="asset-picker-metadata">
              <h3>{selected ? selected.name : 'Selecciona un archivo'}</h3>
              {selected ? (
                <>
                  {kind === 'image' ? (
                    <>
                      {allowDecorative ? (
                        <label className="flex items-center gap-2 text-sm">
                          <input
                            checked={decorative}
                            onChange={(event) =>
                              setDecorative(event.target.checked)
                            }
                            type="checkbox"
                          />
                          Imagen decorativa
                        </label>
                      ) : null}
                      {!decorative || !allowDecorative ? (
                        <div className="space-y-1.5">
                          <Label htmlFor="picker-alt">Texto alternativo</Label>
                          <Input
                            id="picker-alt"
                            maxLength={500}
                            onChange={(event) => setAltText(event.target.value)}
                            value={altText}
                          />
                        </div>
                      ) : null}
                    </>
                  ) : null}
                  {kind === 'audio' || kind === 'video' ? (
                    <>
                      <div className="space-y-1.5">
                        <Label htmlFor="picker-title">Título accesible</Label>
                        <Input
                          id="picker-title"
                          onChange={(event) => setTitle(event.target.value)}
                          value={title}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="picker-transcript">Transcripción</Label>
                        <textarea
                          className="academic-control min-h-28"
                          id="picker-transcript"
                          onChange={(event) =>
                            setTranscript(event.target.value)
                          }
                          value={transcript}
                        />
                      </div>
                    </>
                  ) : null}
                  {kind === 'video' ? (
                    <>
                      <label className="flex items-center gap-2 text-sm">
                        <input
                          checked={silent}
                          onChange={(event) => setSilent(event.target.checked)}
                          type="checkbox"
                        />
                        Video sin audio
                      </label>
                      {!silent ? (
                        <div className="space-y-1.5">
                          <Label htmlFor="picker-captions">
                            Subtítulos WebVTT
                          </Label>
                          <select
                            className="academic-control"
                            id="picker-captions"
                            onChange={(event) =>
                              setCaptionVersionId(event.target.value)
                            }
                            value={captionVersionId}
                          >
                            <option value="">Selecciona una versión</option>
                            {captions.map((asset) => (
                              <option
                                key={asset.id}
                                value={asset.current_version?.id}
                              >
                                {asset.name} · v{asset.current_version?.number}
                              </option>
                            ))}
                          </select>
                        </div>
                      ) : null}
                    </>
                  ) : null}
                  {kind === 'document' || kind === 'dataset' ? (
                    <>
                      <div className="space-y-1.5">
                        <Label htmlFor="picker-label">Texto del enlace</Label>
                        <Input
                          id="picker-label"
                          maxLength={300}
                          onChange={(event) => setLabel(event.target.value)}
                          value={label}
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor="picker-description">Descripción</Label>
                        <Input
                          id="picker-description"
                          onChange={(event) =>
                            setDescription(event.target.value)
                          }
                          value={description}
                        />
                      </div>
                    </>
                  ) : (
                    <div className="space-y-1.5">
                      <Label htmlFor="picker-caption">Pie del recurso</Label>
                      <Input
                        id="picker-caption"
                        onChange={(event) => setCaption(event.target.value)}
                        value={caption}
                      />
                    </div>
                  )}
                </>
              ) : (
                <p>
                  Elige un recurso para completar sus datos de accesibilidad.
                </p>
              )}
            </section>
          </div>
        )}

        <DialogFooter showCloseButton>
          {source === 'resources' ? (
            <Button
              disabled={!accessibilityValid}
              onClick={insert}
              type="button"
            >
              {resourceOnly
                ? 'Usar como archivo de la lección'
                : 'Añadir al contenido'}
            </Button>
          ) : null}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
