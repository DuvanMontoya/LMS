import { PageHeader } from '@/components/platform/page-header';
import { AssetDetailActions } from '@/components/assets/asset-detail-actions';
import { AssetMedia } from '@/components/assets/asset-media';
import { Badge } from '@/components/ui/badge';
import {
  assetKindLabel,
  assetStatusLabel,
  formatBytes,
} from '@/lib/assets/labels';
import { getAssetForPage } from '@/lib/assets/server';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function DatasetPreview({
  metadata,
}: Readonly<{ metadata: Record<string, unknown> }>) {
  const rawColumns = metadata.columns;
  const rawRows = metadata.sample_rows;
  const columns = Array.isArray(rawColumns)
    ? rawColumns.filter((value): value is string => typeof value === 'string')
    : [];
  const rows = Array.isArray(rawRows)
    ? rawRows
        .filter((value): value is unknown[] => Array.isArray(value))
        .map((row) =>
          row.map((value) =>
            typeof value === 'string' ? value : String(value),
          ),
        )
    : [];
  if (columns.length && rows.length) {
    return (
      <div className="mb-4 overflow-x-auto rounded-lg border">
        <table className="w-full min-w-[32rem] text-left text-sm">
          <caption className="sr-only">
            Vista previa segura de las primeras filas
          </caption>
          <thead className="border-b bg-muted/30">
            <tr>
              {columns.map((column) => (
                <th className="px-3 py-2 font-medium" key={column}>
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((row, rowIndex) => (
              <tr key={`preview-row-${rowIndex}`}>
                {columns.map((column, columnIndex) => (
                  <td className="px-3 py-2" key={`${column}-${columnIndex}`}>
                    {row[columnIndex] ?? ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }
  const sample = metadata.sample;
  if (typeof sample === 'string' && sample) {
    return (
      <pre className="mb-4 max-h-64 overflow-auto rounded-lg border bg-muted/20 p-4 text-sm whitespace-pre-wrap">
        {sample}
      </pre>
    );
  }
  const keys = metadata.sample_keys;
  if (Array.isArray(keys) && keys.length) {
    return (
      <p className="mb-4 rounded-lg border bg-muted/20 p-4 text-sm">
        Claves de nivel superior:{' '}
        {keys.filter((value) => typeof value === 'string').join(', ')}
      </p>
    );
  }
  return null;
}

export default async function AssetDetailPage({
  params,
}: Readonly<{ params: Promise<{ assetId: string; slug: string }> }>) {
  const { assetId, slug } = await params;
  const { access, asset, organization, usage } = await getAssetForPage(
    slug,
    assetId,
  );
  const current = asset.current_version;
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          <AssetDetailActions
            assetId={asset.id}
            canDownload={access.capabilities.includes(
              'asset.original.download',
            )}
            canManage={access.capabilities.includes('asset.library.manage')}
            canReprocess={access.capabilities.includes('asset.reprocess')}
            currentVersionId={current?.id}
            lockVersion={asset.lock_version ?? 1}
            slug={slug}
            status={asset.status ?? 'active'}
            versions={asset.versions}
          />
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/recursos`, label: 'Recursos' },
          { label: asset.name },
        ]}
        description={asset.description || 'Recurso académico versionado.'}
        eyebrow={assetKindLabel(asset.kind)}
        title={asset.name}
      />
      <div className="mt-5 flex flex-wrap gap-2">
        <Badge>{assetKindLabel(asset.kind)}</Badge>
        <Badge variant="outline">{assetStatusLabel(asset.status ?? '')}</Badge>
        {current ? (
          <Badge variant="secondary">
            v{current.number} · {assetStatusLabel(current.status ?? '')}
          </Badge>
        ) : null}
      </div>
      {current?.status === 'ready' ? (
        <section aria-labelledby="asset-preview-heading" className="mt-6">
          <h2 className="sr-only" id="asset-preview-heading">
            Vista previa
          </h2>
          {asset.kind === 'dataset' && isRecord(current.technical_metadata) ? (
            <DatasetPreview metadata={current.technical_metadata} />
          ) : null}
          <AssetMedia
            assetId={asset.id}
            description={asset.description ?? ''}
            kind={asset.kind}
            name={asset.name}
            slug={slug}
            versionId={current.id}
          />
        </section>
      ) : null}
      <section aria-labelledby="versions-heading" className="mt-8">
        <h2 className="text-lg font-semibold" id="versions-heading">
          Versiones
        </h2>
        <div className="mt-3 overflow-x-auto rounded-lg border">
          <table className="w-full min-w-[48rem] text-left text-sm">
            <thead className="border-b bg-muted/30 text-xs text-muted-foreground">
              <tr>
                <th className="px-4 py-3">Versión</th>
                <th className="px-4 py-3">Estado</th>
                <th className="px-4 py-3">Archivo</th>
                <th className="px-4 py-3">Metadatos</th>
                <th className="px-4 py-3">Variantes</th>
                <th className="px-4 py-3">Procesamiento</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {asset.versions.map((version) => (
                <tr key={version.id}>
                  <td className="px-4 py-3 font-medium">v{version.number}</td>
                  <td className="px-4 py-3">
                    {assetStatusLabel(version.status ?? '')}
                  </td>
                  <td className="px-4 py-3">
                    <span className="block max-w-64 truncate">
                      {version.original_filename}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {version.detected_mime_type || version.declared_mime_type}{' '}
                      · {formatBytes(version.size_bytes)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-muted-foreground">
                    {version.width && version.height
                      ? `${version.width}×${version.height}`
                      : version.duration_milliseconds
                        ? `${Math.round(version.duration_milliseconds / 1000)} s`
                        : version.page_count
                          ? `${version.page_count} páginas`
                          : version.row_count
                            ? `${version.row_count} filas`
                            : '—'}
                  </td>
                  <td className="px-4 py-3">{version.variants.length}</td>
                  <td className="px-4 py-3 text-xs">
                    {version.processing_jobs?.map((job) => (
                      <p key={job.id}>
                        {assetStatusLabel(job.stage)} · {job.pipeline_version}
                      </p>
                    ))}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {usage ? (
        <section
          aria-labelledby="usage-heading"
          className="mt-8 rounded-lg border p-5"
        >
          <h2 className="font-semibold" id="usage-heading">
            Uso del recurso
          </h2>
          <dl className="mt-3 grid gap-3 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-muted-foreground">Referencias vigentes</dt>
              <dd className="text-lg font-semibold">
                {usage.current_reference_count}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Versiones de contenido</dt>
              <dd className="text-lg font-semibold">
                {usage.content_versions.length}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Publicaciones</dt>
              <dd className="text-lg font-semibold">{usage.releases.length}</dd>
            </div>
          </dl>
        </section>
      ) : null}
    </main>
  );
}
