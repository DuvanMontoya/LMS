'use client';

import { useQuery } from '@tanstack/react-query';
import { Images, Search } from 'lucide-react';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { AssetPreview } from '@/components/assets/asset-preview';
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
type InsertableKind = Exclude<AssetKind, 'caption'>;

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
    throw new Error(
      apiErrorMessage(error, 'No fue posible abrir la biblioteca.'),
    );
  return data as unknown as AssetSummary[];
}

export function AssetPickerDialog({
  onInsert,
  slug,
}: Readonly<{
  onInsert: (node: Record<string, unknown>) => void;
  slug: string;
}>) {
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState<InsertableKind>('image');
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
    const attrs =
      kind === 'image'
        ? {
            ...common,
            altText: decorative ? '' : altText.trim(),
            caption: caption.trim(),
            decorative,
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
    onInsert({
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
    });
    setOpen(false);
  }
  const accessibilityValid =
    selected &&
    (kind === 'image'
      ? decorative || Boolean(altText.trim())
      : kind === 'audio'
        ? Boolean(title.trim() && transcript.trim())
        : kind === 'video'
          ? Boolean(
              title.trim() && transcript.trim() && (silent || captionVersionId),
            )
          : Boolean(label.trim()));
  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button size="sm" type="button" variant="ghost">
          <Images />
          Recurso
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>Insertar recurso académico</DialogTitle>
          <DialogDescription>
            Elige una versión lista. La referencia quedará fijada y no cambiará
            cuando exista una versión más reciente.
          </DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 md:grid-cols-[1fr_1.15fr]">
          <div>
            <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-1">
              <div className="space-y-1.5">
                <Label htmlFor="picker-kind">Tipo</Label>
                <select
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                  id="picker-kind"
                  onChange={(event) => {
                    setKind(event.target.value as InsertableKind);
                    setSelectedId('');
                  }}
                  value={kind}
                >
                  <option value="image">Imagen</option>
                  <option value="audio">Audio</option>
                  <option value="video">Video</option>
                  <option value="document">Documento</option>
                  <option value="dataset">Dataset</option>
                </select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="picker-search">Buscar</Label>
                <div className="relative">
                  <Search className="absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    className="pl-9"
                    id="picker-search"
                    onChange={(event) => setSearch(event.target.value)}
                    value={search}
                  />
                </div>
              </div>
            </div>
            <div
              aria-label={`Recursos listos de tipo ${assetKindLabel(kind)}`}
              className="mt-3 max-h-72 space-y-2 overflow-y-auto"
              role="listbox"
            >
              {candidates.map((asset) => (
                <button
                  aria-selected={selectedId === asset.id}
                  className="grid w-full grid-cols-[4rem_1fr] gap-3 rounded-md border p-2 text-left aria-selected:border-primary aria-selected:bg-primary/5"
                  key={asset.id}
                  onClick={() => {
                    setSelectedId(asset.id);
                    setTitle(asset.name);
                    setLabel(asset.name);
                  }}
                  role="option"
                  type="button"
                >
                  <span className="h-12 overflow-hidden rounded">
                    <AssetPreview
                      assetId={asset.id}
                      kind={asset.kind}
                      name={asset.name}
                      slug={slug}
                      versionId={asset.current_version?.id}
                    />
                  </span>
                  <span className="min-w-0">
                    <strong className="block truncate">{asset.name}</strong>
                    <small className="text-muted-foreground">
                      v{asset.current_version?.number} ·{' '}
                      {formatBytes(asset.current_version?.size_bytes)}
                    </small>
                  </span>
                </button>
              ))}
              {!query.isPending && !candidates.length ? (
                <p className="rounded-md border border-dashed p-4 text-sm text-muted-foreground">
                  No hay versiones listas.{' '}
                  <Link
                    className="underline"
                    href={`/organizaciones/${slug}/recursos/nuevo`}
                    target="_blank"
                  >
                    Cargar en otra pestaña
                  </Link>
                </p>
              ) : null}
            </div>
          </div>
          <div className="space-y-3 rounded-md border bg-muted/20 p-3">
            <p className="font-medium">Accesibilidad y presentación</p>
            {kind === 'image' ? (
              <>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    checked={decorative}
                    onChange={(event) => setDecorative(event.target.checked)}
                    type="checkbox"
                  />
                  Es decorativa
                </label>
                <div className="space-y-1.5">
                  <Label htmlFor="picker-alt">Texto alternativo</Label>
                  <Input
                    disabled={decorative}
                    id="picker-alt"
                    maxLength={500}
                    onChange={(event) => setAltText(event.target.value)}
                    required={!decorative}
                    value={altText}
                  />
                </div>
              </>
            ) : null}
            {kind === 'audio' || kind === 'video' ? (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="picker-title">Título</Label>
                  <Input
                    id="picker-title"
                    maxLength={300}
                    onChange={(event) => setTitle(event.target.value)}
                    value={title}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="picker-transcript">Transcripción</Label>
                  <textarea
                    className="min-h-28 w-full rounded-md border bg-background px-3 py-2"
                    id="picker-transcript"
                    onChange={(event) => setTranscript(event.target.value)}
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
                    <Label htmlFor="picker-captions">Subtítulos WebVTT</Label>
                    <select
                      className="h-9 w-full rounded-md border bg-background px-3 text-sm"
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
                    onChange={(event) => setDescription(event.target.value)}
                    value={description}
                  />
                </div>
              </>
            ) : (
              <div className="space-y-1.5">
                <Label htmlFor="picker-caption">Pie de recurso</Label>
                <Input
                  id="picker-caption"
                  onChange={(event) => setCaption(event.target.value)}
                  value={caption}
                />
              </div>
            )}
          </div>
        </div>
        <DialogFooter showCloseButton>
          <Button disabled={!accessibilityValid} onClick={insert} type="button">
            Insertar versión seleccionada
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
