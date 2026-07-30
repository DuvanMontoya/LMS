import { Target } from 'lucide-react';
import { notFound } from 'next/navigation';
import { ConceptAssociationEditor } from '@/components/catalog/concept-association-editor';
import { ObjectiveActions } from '@/components/catalog/objective-actions';
import { ObjectiveForm } from '@/components/catalog/objective-form';
import { PageHeader } from '@/components/platform/page-header';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
export default async function ObjectivesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
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
    <main className="academic-page">
      <PageHeader
        actions={
          access.capabilities.includes('catalog.manage') ? (
            <ObjectiveForm slug={slug} subjects={subjects ?? []} />
          ) : undefined
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: 'Objetivos' },
        ]}
        description="Resultados observables que orientan la alineación curricular de los cursos."
        eyebrow="Currículo"
        title="Objetivos de aprendizaje"
      />
      <ul className="mt-6 divide-y border-y">
        {data?.length ? (
          data.map((objective) => (
            <li key={objective.id} className="px-1 py-5 sm:px-3">
              <p className="font-mono text-sm text-muted-foreground">
                {objective.code}
              </p>
              <p className="mt-2 font-medium">{objective.statement}</p>
              {objective.description ? (
                <p className="mt-2 text-foreground/80">
                  {objective.description}
                </p>
              ) : null}
              {objective.cognitive_level ? (
                <p className="mt-2 text-sm text-muted-foreground">
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
          ))
        ) : (
          <li className="py-10 text-center">
            <span className="mx-auto grid size-10 place-items-center rounded-md bg-primary/8 text-primary">
              <Target className="size-5" />
            </span>
            <p className="mt-3 text-sm font-medium text-foreground">
              Aún no hay objetivos
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Registra el primer resultado de aprendizaje observable.
            </p>
          </li>
        )}
      </ul>
    </main>
  );
}
