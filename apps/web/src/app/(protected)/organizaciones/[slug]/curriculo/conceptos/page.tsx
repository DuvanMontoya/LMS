import Link from 'next/link';

import { ConceptForm } from '@/components/catalog/concept-form';
import { ConceptList } from '@/components/catalog/concept-list';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
export default async function ConceptsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access } = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const { data } = await client.GET(
    '/api/v1/organizations/{slug}/catalog/concepts/',
    { params: { path: { slug } } },
  );
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-12">
      <Link
        className="text-sm underline"
        href={`/organizaciones/${slug}/curriculo`}
      >
        Volver al currículo
      </Link>
      <h1 className="mt-4 text-3xl font-semibold">Conceptos</h1>
      <p className="mt-2 text-slate-700">
        Conceptos reutilizables de la organización.
      </p>
      <ConceptList
        canManage={access.capabilities.includes('catalog.manage')}
        concepts={data ?? []}
        slug={slug}
      />
      {access.capabilities.includes('catalog.manage') ? (
        <ConceptForm slug={slug} />
      ) : null}
    </main>
  );
}
