import Link from 'next/link';
import { notFound } from 'next/navigation';
import { ConceptAssociationEditor } from '@/components/catalog/concept-association-editor';
import { ObjectiveActions } from '@/components/catalog/objective-actions';
import { ObjectiveForm } from '@/components/catalog/objective-form';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
export default async function ObjectivesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('catalog.view')) notFound();
  const client = await createPlatformServerClient();
  const [
    { data },
    { data: subjects },
    { data: concepts },
    { data: associations },
  ] = await Promise.all([
    client.GET('/api/v1/organizations/{slug}/catalog/learning-objectives/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/concepts/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/objective-concepts/', {
      params: { path: { slug } },
    }),
  ]);
  const conceptIdsByObjective = new Map(
    (associations ?? []).map((association) => [
      association.entity_id,
      association.concept_ids,
    ]),
  );
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-12">
      <Link
        className="text-sm underline"
        href={`/organizaciones/${slug}/curriculo`}
      >
        Volver al currículo
      </Link>
      <h1 className="mt-4 text-3xl font-semibold">Objetivos de aprendizaje</h1>
      <ul className="mt-6 space-y-3">
        {data?.map((objective) => (
          <li
            key={objective.id}
            className="rounded-xl border border-slate-200 bg-white p-4"
          >
            <p className="font-mono text-sm text-slate-600">{objective.code}</p>
            <p className="mt-2 font-medium">{objective.statement}</p>
            {objective.description ? (
              <p className="mt-2 text-slate-700">{objective.description}</p>
            ) : null}
            {objective.cognitive_level ? (
              <p className="mt-2 text-sm text-slate-600">
                Nivel cognitivo: {objective.cognitive_level}
              </p>
            ) : null}
            {access.capabilities.includes('catalog.manage') ? (
              <>
                <ObjectiveActions objective={objective} slug={slug} />
                <ConceptAssociationEditor
                  concepts={concepts ?? []}
                  entity="objective"
                  entityId={objective.id}
                  initialIds={conceptIdsByObjective.get(objective.id) ?? []}
                  slug={slug}
                />
              </>
            ) : null}
          </li>
        ))}
      </ul>
      {access.capabilities.includes('catalog.manage') ? (
        <ObjectiveForm slug={slug} subjects={subjects ?? []} />
      ) : null}
    </main>
  );
}
