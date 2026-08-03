import { Search } from 'lucide-react';

import { AssetLibraryDialog } from '@/components/assets/asset-library-dialog';
import { AssetPreview } from '@/components/assets/asset-preview';
import { AssetUploadDialog } from '@/components/assets/asset-upload-dialog';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  assetKindLabel,
  assetStatusLabel,
  formatBytes,
} from '@/lib/assets/labels';
import { getAssetsForPage } from '@/lib/assets/server';

export default async function AssetsPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ kind?: string; search?: string; status?: string }>;
}>) {
  const { slug } = await params;
  const filters = await searchParams;
  const query: { kind?: string; search?: string; status?: string } = {};
  if (filters.kind) query.kind = filters.kind;
  if (filters.search) query.search = filters.search;
  if (filters.status) query.status = filters.status;
  const { access, assets, organization } = await getAssetsForPage(slug, query);
  const canUpload = access.capabilities.includes('asset.upload');
  return (
    <main className="academic-page">
      <PageHeader
        actions={canUpload ? <AssetUploadDialog slug={slug} /> : null}
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { label: 'Recursos' },
        ]}
        description="Biblioteca privada de archivos académicos versionados y procesados."
        eyebrow="Activos académicos"
        title="Recursos"
      />
      <form
        className="mt-5 grid gap-3 border-b pb-4 md:grid-cols-[1.4fr_0.8fr_0.8fr_auto]"
        method="get"
      >
        <div className="space-y-1.5">
          <Label htmlFor="asset-search">Buscar</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              className="pl-9"
              defaultValue={filters.search}
              id="asset-search"
              name="search"
              placeholder="Nombre o descripción"
            />
          </div>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="asset-kind">Tipo</Label>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            defaultValue={filters.kind ?? ''}
            id="asset-kind"
            name="kind"
          >
            <option value="">Todos</option>
            <option value="image">Imagen</option>
            <option value="document">Documento</option>
            <option value="audio">Audio</option>
            <option value="video">Video</option>
            <option value="dataset">Dataset</option>
            <option value="caption">Subtítulos</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="asset-status">Estado</Label>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            defaultValue={filters.status ?? ''}
            id="asset-status"
            name="status"
          >
            <option value="">Todos</option>
            <option value="active">Activo</option>
            <option value="archived">Archivado</option>
          </select>
        </div>
        <Button className="self-end" type="submit" variant="outline">
          Aplicar
        </Button>
      </form>
      {assets.length ? (
        <ul aria-label="Recursos" className="asset-resource-grid">
          {assets.map((asset) => (
            <li key={asset.id}>
              <AssetLibraryDialog
                asset={asset}
                canManage={access.capabilities.includes('asset.library.manage')}
                slug={slug}
              >
                <div className="asset-resource-card__preview">
                  <AssetPreview
                    assetId={asset.id}
                    kind={asset.kind}
                    name={asset.name}
                    slug={slug}
                    versionId={asset.current_version?.id}
                  />
                </div>
                <div className="asset-resource-card__body">
                  <div className="asset-resource-card__eyebrow">
                    <span>{assetKindLabel(asset.kind)}</span>
                    <span data-status={asset.status}>
                      {assetStatusLabel(
                        asset.current_version?.status ?? asset.status,
                      )}
                    </span>
                  </div>
                  <h2>{asset.name}</h2>
                  <p>
                    {asset.description || 'Recurso académico sin descripción.'}
                  </p>
                  <dl>
                    <div>
                      <dt>Versión</dt>
                      <dd>
                        {asset.current_version
                          ? `v${asset.current_version.number}`
                          : '—'}
                      </dd>
                    </div>
                    <div>
                      <dt>Tamaño</dt>
                      <dd>{formatBytes(asset.current_version?.size_bytes)}</dd>
                    </div>
                  </dl>
                </div>
              </AssetLibraryDialog>
            </li>
          ))}
        </ul>
      ) : (
        <section className="mt-6 rounded-lg border border-dashed px-6 py-12 text-center">
          <h2 className="font-semibold">No hay recursos para mostrar</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Ajusta los filtros o carga el primer archivo académico.
          </p>
        </section>
      )}
    </main>
  );
}
