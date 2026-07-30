import { notFound } from 'next/navigation';
import { PrerequisiteEditor } from '@/components/catalog/prerequisite-editor';
import { PageHeader } from '@/components/platform/page-header';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
export default async function PrerequisitesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
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
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: 'Prerrequisitos' },
        ]}
        description="Define dependencias obligatorias o recomendadas. Las relaciones cíclicas se rechazan automáticamente."
        eyebrow="Currículo"
        title="Prerrequisitos"
      />
      <section className="mt-6">
        {access.capabilities.includes('catalog.manage_prerequisites') ? (
          <div className="grid gap-6 xl:grid-cols-2">
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
          </div>
        ) : (
          <p className="border-y px-4 py-6 text-sm text-muted-foreground">
            No tienes permiso para modificar estas relaciones.
          </p>
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
