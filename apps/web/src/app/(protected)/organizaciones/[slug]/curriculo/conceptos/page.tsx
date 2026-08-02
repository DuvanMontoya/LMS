import { ConceptForm } from '@/components/catalog/concept-form';
import { notFound } from 'next/navigation';
import { ConceptList } from '@/components/catalog/concept-list';
import { PageHeader } from '@/components/platform/page-header';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
export default async function ConceptsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('catalog.view')) notFound();
  const client = await createPlatformServerClient();
  const { data } = await client.GET(
    '/api/v1/organizations/{slug}/catalog/concepts/',
    { params: { path: { slug } } },
  );
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          access.capabilities.includes('catalog.manage') ? (
            <ConceptForm slug={slug} />
          ) : undefined
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: 'Conceptos' },
        ]}
        description="Definiciones canónicas que pueden reutilizarse en temas y objetivos."
        eyebrow="Currículo"
        title="Conceptos"
      />
      <ConceptList
        canManage={access.capabilities.includes('catalog.manage')}
        concepts={data ?? []}
        slug={slug}
      />
    </main>
  );
}
