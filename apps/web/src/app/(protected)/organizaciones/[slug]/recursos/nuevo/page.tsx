import { notFound } from 'next/navigation';

import { AssetUploadForm } from '@/components/assets/asset-upload-form';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationForPage } from '@/lib/organizations/server';

export default async function NewAssetPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('asset.upload')) notFound();
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/recursos`, label: 'Recursos' },
          { label: 'Nueva carga' },
        ]}
        description="Carga directa, verificación de integridad y procesamiento asíncrono."
        eyebrow="Activos académicos"
        title="Cargar recurso"
      />
      <AssetUploadForm slug={slug} />
    </main>
  );
}
