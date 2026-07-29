import Link from 'next/link';
import { notFound } from 'next/navigation';
import { PrerequisiteEditor } from '@/components/catalog/prerequisite-editor';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
export default async function PrerequisitesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('catalog.view')) notFound();
  const client = await createPlatformServerClient();
  const [
    { data: subjects },
    { data: concepts },
    { data: subjectEntries },
    { data: conceptEntries },
  ] = await Promise.all([
    client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/concepts/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/subject-prerequisites/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/concept-prerequisites/', {
      params: { path: { slug } },
    }),
  ]);
  const activeSubjects = (subjects ?? []).filter(
    (subject) => subject.status === 'active',
  );
  const activeConcepts = (concepts ?? []).filter(
    (concept) => concept.status === 'active',
  );
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-12">
      <Link
        className="text-sm underline"
        href={`/organizaciones/${slug}/curriculo`}
      >
        Volver al currículo
      </Link>
      <h1 className="mt-4 text-3xl font-semibold">Prerrequisitos</h1>
      <section className="mt-6 rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-semibold">Relaciones académicas</h2>
        <p className="mt-2 text-slate-700">
          Las listas muestran qué requiere cada entidad y de qué entidades es
          requisito. El servidor rechaza relaciones que produzcan un ciclo.
        </p>
        {access.capabilities.includes('catalog.manage_prerequisites') ? (
          <>
            <PrerequisiteEditor
              entity="subject"
              initial={groupPrerequisites(subjectEntries ?? [])}
              items={activeSubjects}
              slug={slug}
            />
            <PrerequisiteEditor
              entity="concept"
              initial={groupPrerequisites(conceptEntries ?? [])}
              items={activeConcepts}
              slug={slug}
            />
          </>
        ) : (
          <p className="mt-4 text-sm text-slate-600">Solo lectura.</p>
        )}
      </section>
    </main>
  );
}

function groupPrerequisites(
  entries: ReadonlyArray<{
    entity_id: string;
    kind: 'recommended' | 'required';
    prerequisite_id: string;
    rationale?: string;
  }>,
) {
  type Link = {
    kind: 'recommended' | 'required';
    prerequisite_id: string;
    rationale?: string;
  };
  return entries.reduce<Record<string, Link[]>>(
    (grouped, { entity_id, kind, prerequisite_id, rationale }) => {
      const link: Link = rationale
        ? { kind, prerequisite_id, rationale }
        : { kind, prerequisite_id };
      grouped[entity_id] = [...(grouped[entity_id] ?? []), link];
      return grouped;
    },
    {},
  );
}
