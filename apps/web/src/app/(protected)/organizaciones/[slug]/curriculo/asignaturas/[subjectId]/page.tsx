import { notFound } from 'next/navigation';
import { BookOpenCheck, GitBranch, Link2, Target } from 'lucide-react';

import { ConceptAssociationEditor } from '@/components/catalog/concept-association-editor';
import { TopicActions } from '@/components/catalog/topic-actions';
import { TopicForm } from '@/components/catalog/topic-form';
import { PageHeader } from '@/components/platform/page-header';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { conceptIdsBySubjectTopic } from '@/lib/catalog/subject-topics';
import { getOrganizationForPage } from '@/lib/organizations/server';

export default async function SubjectWorkspace({
  params,
}: Readonly<{ params: Promise<{ slug: string; subjectId: string }> }>) {
  const { slug, subjectId } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('catalog.view')) notFound();
  const client = await createPlatformServerClient();
  const { data: subject } = await client.GET(
    '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/',
    { params: { path: { slug, subject_id: subjectId } } },
  );
  if (!subject) notFound();
  const [
    { data: topics },
    { data: concepts },
    { data: topicAssociations },
    { data: objectives },
    { data: subjects },
    { data: prerequisites },
  ] = await Promise.all([
    client.GET(
      '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/topics/',
      { params: { path: { slug, subject_id: subjectId } } },
    ),
    client.GET('/api/v1/organizations/{slug}/catalog/concepts/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/topic-concepts/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/learning-objectives/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
      params: { path: { slug } },
    }),
    client.GET('/api/v1/organizations/{slug}/catalog/subject-prerequisites/', {
      params: { path: { slug } },
    }),
  ]);
  const flattenedTopics = flattenTopics(topics ?? []);
  const subjectTopicIds = new Set(flattenedTopics.map((topic) => topic.id));
  const conceptIdsByTopic = conceptIdsBySubjectTopic(
    subjectTopicIds,
    topicAssociations ?? [],
  );
  const conceptsById = new Map(
    (concepts ?? []).map((concept) => [concept.id, concept]),
  );
  const associatedConcepts = Array.from(
    new Set(
      Array.from(conceptIdsByTopic.values()).flatMap(
        (conceptIds) => conceptIds,
      ),
    ),
  ).flatMap((conceptId) => {
    const concept = conceptsById.get(conceptId);
    return concept ? [concept] : [];
  });
  const subjectsById = new Map((subjects ?? []).map((item) => [item.id, item]));
  const directPrerequisites = (prerequisites ?? [])
    .filter((link) => link.entity_id === subject.id)
    .flatMap((link) => {
      const prerequisite = subjectsById.get(link.prerequisite_id);
      return prerequisite ? [prerequisite] : [];
    });
  const dependents = (prerequisites ?? [])
    .filter((link) => link.prerequisite_id === subject.id)
    .flatMap((link) => {
      const dependent = subjectsById.get(link.entity_id);
      return dependent ? [dependent] : [];
    });
  const subjectObjectives = (objectives ?? []).filter(
    (objective) => objective.subject_id === subject.id,
  );
  const associationCount = flattenedTopics.reduce(
    (total, topic) => total + (conceptIdsByTopic.get(topic.id)?.length ?? 0),
    0,
  );
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: subject.name },
        ]}
        description={subject.description}
        eyebrow="Asignatura"
        title={subject.name}
      />
      <section className="mt-6" aria-labelledby="topic-tree">
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          <SubjectMetric
            icon={BookOpenCheck}
            label="Temas activos"
            value={flattenedTopics.length}
          />
          <SubjectMetric
            icon={GitBranch}
            label="Subtemas"
            value={Math.max(0, flattenedTopics.length - (topics?.length ?? 0))}
          />
          <SubjectMetric
            icon={Link2}
            label="Vínculos conceptuales"
            value={associationCount}
          />
          <SubjectMetric
            icon={Target}
            label="Objetivos activos"
            value={subjectObjectives.length}
          />
        </div>
        <div className="mt-6 flex flex-wrap items-end justify-between gap-3">
          <div>
            <h2 id="topic-tree" className="text-base font-semibold">
              Estructura temática
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Recorre la jerarquía completa. Las herramientas se abren solo al
              necesitarlas para mantener el mapa legible.
            </p>
          </div>
          {access.capabilities.includes('catalog.manage') ? (
            <TopicForm
              slug={slug}
              subjectId={subjectId}
              topics={flattenedTopics}
            />
          ) : null}
        </div>
        <TopicTree
          canManage={access.capabilities.includes('catalog.manage')}
          concepts={concepts ?? []}
          conceptIdsByTopic={conceptIdsByTopic}
          items={topics ?? []}
          slug={slug}
          topics={flattenedTopics}
        />
      </section>
      <section className="mt-6 border-t pt-5">
        <h2 className="text-base font-semibold">Contexto académico</h2>
        <div className="mt-3 grid overflow-hidden rounded-md border bg-card [&>*]:p-4 [&>*+*]:border-t md:grid-cols-2 md:[&>*+*]:border-t-0 md:[&>*:nth-child(odd)]:border-r md:[&>*:nth-child(n+3)]:border-t">
          <ContextList
            empty="No hay conceptos asociados a sus temas."
            items={associatedConcepts.map((concept) => concept.name)}
            title="Conceptos asociados"
          />
          <ContextList
            empty="No hay objetivos activos en esta asignatura."
            items={subjectObjectives.map(
              (objective) => `${objective.code}: ${objective.statement}`,
            )}
            title="Objetivos de aprendizaje"
          />
          <ContextList
            empty="No hay prerrequisitos directos."
            items={directPrerequisites.map((item) => item.name)}
            title="Prerrequisitos directos"
          />
          <ContextList
            empty="Ninguna asignatura depende directamente de esta."
            items={dependents.map((item) => item.name)}
            title="Asignaturas dependientes"
          />
        </div>
      </section>
    </main>
  );
}

function SubjectMetric({
  icon: Icon,
  label,
  value,
}: Readonly<{
  icon: typeof Target;
  label: string;
  value: number;
}>) {
  return (
    <div className="flex items-center gap-3 rounded-lg border bg-card px-3.5 py-3 shadow-xs">
      <span className="rounded-md bg-primary/10 p-2 text-primary">
        <Icon className="size-4" />
      </span>
      <div>
        <p className="text-lg font-semibold leading-none tabular-nums">
          {value}
        </p>
        <p className="mt-1 text-xs text-muted-foreground">{label}</p>
      </div>
    </div>
  );
}

function ContextList({
  empty,
  items,
  title,
}: Readonly<{ empty: string; items: readonly string[]; title: string }>) {
  return (
    <section aria-label={title}>
      <h3 className="text-sm font-semibold text-foreground">{title}</h3>
      {items.length ? (
        <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-foreground/80">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p className="mt-2 text-sm text-muted-foreground">{empty}</p>
      )}
    </section>
  );
}

function TopicTree({
  canManage,
  concepts,
  conceptIdsByTopic,
  items,
  parentId,
  slug,
  topics,
}: Readonly<{
  canManage: boolean;
  concepts: Array<{
    id: string;
    name: string;
    slug: string;
    definition: string;
    status: string;
  }>;
  conceptIdsByTopic: ReadonlyMap<string, string[]>;
  items: Array<{
    id: string;
    status?: string;
    title: string;
    children: unknown;
  }>;
  parentId?: string | undefined;
  slug: string;
  topics: Array<{
    ancestorIds: string[];
    parentId?: string | undefined;
    id: string;
    status?: string;
    title: string;
    children: unknown;
  }>;
}>) {
  return items.length ? (
    <ul
      className={
        parentId
          ? 'space-y-2 border-l border-primary/20 pl-3'
          : 'mt-3 space-y-2'
      }
      aria-label="Temas de la asignatura"
    >
      {items.map((topic) => (
        <li
          className="overflow-hidden rounded-lg border bg-card shadow-[0_1px_2px_rgb(0_0_0_/_0.025)]"
          data-topic-title={topic.title}
          key={topic.id}
        >
          <div className="flex min-h-12 items-center justify-between gap-3 px-3.5 py-2.5">
            <div className="flex min-w-0 items-center gap-2.5">
              <span
                aria-hidden="true"
                className="size-2 shrink-0 rounded-full bg-primary/70"
              />
              <span className="truncate font-medium">{topic.title}</span>
            </div>
            <div className="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
              {Array.isArray(topic.children) && topic.children.length ? (
                <span>
                  {topic.children.length}{' '}
                  {topic.children.length === 1 ? 'subtema' : 'subtemas'}
                </span>
              ) : null}
              <span>
                {conceptIdsByTopic.get(topic.id)?.length ?? 0}{' '}
                {(conceptIdsByTopic.get(topic.id)?.length ?? 0) === 1
                  ? 'concepto'
                  : 'conceptos'}
              </span>
            </div>
          </div>
          {canManage ? (
            <fieldset className="border-t bg-muted/[0.06]">
              <legend className="sr-only">Administrar {topic.title}</legend>
              <details>
                <summary className="cursor-pointer list-none px-3.5 py-2 text-xs font-semibold text-primary marker:hidden hover:bg-muted/25">
                  Gestionar tema
                </summary>
                <div className="border-t px-3 py-2.5">
                  <TopicActions
                    slug={slug}
                    topic={{ ...topic, parentId }}
                    topics={topics}
                  />
                </div>
              </details>
            </fieldset>
          ) : null}
          {canManage ? (
            <section
              aria-label="Editor de conceptos del tema"
              className="border-t bg-muted/[0.03]"
            >
              <details>
                <summary className="cursor-pointer list-none px-3.5 py-2 text-xs font-semibold text-primary marker:hidden hover:bg-muted/25">
                  Conceptos asociados ·{' '}
                  {conceptIdsByTopic.get(topic.id)?.length ?? 0}
                </summary>
                <div className="border-t">
                  <ConceptAssociationEditor
                    concepts={concepts}
                    embedded
                    entity="topic"
                    entityId={topic.id}
                    initialIds={conceptIdsByTopic.get(topic.id) ?? []}
                    slug={slug}
                  />
                </div>
              </details>
            </section>
          ) : null}
          {Array.isArray(topic.children) && topic.children.length ? (
            <div className="border-t bg-muted/10 py-2 pr-2 pl-3">
              <TopicTree
                items={
                  topic.children as Array<{
                    id: string;
                    status?: string;
                    title: string;
                    children: unknown;
                  }>
                }
                parentId={topic.id}
                canManage={canManage}
                concepts={concepts}
                conceptIdsByTopic={conceptIdsByTopic}
                slug={slug}
                topics={topics}
              />
            </div>
          ) : null}
        </li>
      ))}
    </ul>
  ) : (
    <p className="mt-3 text-muted-foreground">No hay temas activos.</p>
  );
}

function flattenTopics(
  items: Array<{
    id: string;
    status?: string;
    title: string;
    children: unknown;
  }>,
  ancestorIds: string[] = [],
  parentId?: string | undefined,
): Array<{
  ancestorIds: string[];
  children: unknown;
  id: string;
  parentId?: string | undefined;
  status?: string;
  title: string;
}> {
  return items.flatMap((topic) => [
    { ...topic, ancestorIds, parentId },
    ...flattenTopics(
      Array.isArray(topic.children)
        ? (topic.children as Array<{
            id: string;
            status?: string;
            title: string;
            children: unknown;
          }>)
        : [],
      [...ancestorIds, topic.id],
      topic.id,
    ),
  ]);
}
