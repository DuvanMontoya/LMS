import { Plus, Search } from 'lucide-react';
import Link from 'next/link';

import { AssetPreview } from '@/components/assets/asset-preview';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
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
        actions={
          canUpload ? (
            <Button asChild>
              <Link href={`/organizaciones/${slug}/recursos/nuevo`}>
                <Plus data-icon="inline-start" />
                Cargar recurso
              </Link>
            </Button>
          ) : null
        }
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
        <ul
          aria-label="Biblioteca de recursos"
          className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-3"
        >
          {assets.map((asset) => (
            <li
              className="group min-w-0 overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm shadow-slate-900/[0.025] transition-all duration-200 hover:-translate-y-0.5 hover:border-primary/25 hover:shadow-md hover:shadow-slate-900/[0.06]"
              key={asset.id}
            >
              <div className="h-28 border-b border-border/70 sm:h-32">
                <AssetPreview
                  assetId={asset.id}
                  kind={asset.kind}
                  name={asset.name}
                  slug={slug}
                  versionId={asset.current_version?.id}
                />
              </div>
              <div className="p-3.5">
                <div className="flex flex-wrap gap-1.5">
                  <Badge
                    className="px-2 py-0.5 text-[0.65rem]"
                    variant="outline"
                  >
                    {assetKindLabel(asset.kind)}
                  </Badge>
                  <Badge
                    className="px-2 py-0.5 text-[0.65rem]"
                    variant={
                      asset.status === 'active' ? 'secondary' : 'outline'
                    }
                  >
                    {assetStatusLabel(asset.status)}
                  </Badge>
                  {asset.current_version ? (
                    <Badge
                      className="px-2 py-0.5 text-[0.65rem]"
                      variant="secondary"
                    >
                      {assetStatusLabel(asset.current_version.status ?? '')}
                    </Badge>
                  ) : null}
                </div>
                <h2 className="mt-2 line-clamp-2 min-h-10 text-sm leading-5 font-semibold">
                  <Link
                    className="underline-offset-4 hover:text-primary hover:underline"
                    href={`/organizaciones/${slug}/recursos/${asset.id}`}
                  >
                    {asset.name}
                  </Link>
                </h2>
                <p className="mt-1 line-clamp-2 min-h-9 text-xs leading-5 text-muted-foreground">
                  {asset.description || 'Sin descripción.'}
                </p>
                <dl className="mt-2 flex justify-between gap-4 border-t border-border/70 pt-2 text-[0.68rem] text-muted-foreground">
                  <div>
                    <dt>Versión</dt>
                    <dd className="font-medium text-foreground">
                      {asset.current_version
                        ? `v${asset.current_version.number}`
                        : 'Sin versión lista'}
                    </dd>
                  </div>
                  <div className="text-right">
                    <dt>Tamaño</dt>
                    <dd className="font-medium text-foreground">
                      {formatBytes(asset.current_version?.size_bytes)}
                    </dd>
                  </div>
                </dl>
              </div>
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
