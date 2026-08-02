import { BookOpen, GitBranch, Network, Search } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { CurriculumWorkspaceNav } from '@/components/catalog/curriculum-workspace-nav';
import { PrerequisiteEditor } from '@/components/catalog/prerequisite-editor';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { components } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

type Item = Pick<components['schemas']['Concept'], 'id' | 'name'>;
type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function PrerequisitesPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: SearchParams;
}>) {
  const { slug } = await params;
  const query = await searchParams;
  const { access, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('catalog.view')) notFound();
  const client = await createPlatformServerClient();
  const graph = single(query.graph) === 'concepts' ? 'concepts' : 'subjects';
  const entity = graph === 'concepts' ? 'concept' : 'subject';
  const targetSearch = single(query.q).trim();
  const requestedTargetId = single(query.target);

  const directoryRequest =
    graph === 'concepts'
      ? await client.GET('/api/v1/organizations/{slug}/catalog/concepts/', {
          params: {
            path: { slug },
            query: {
              limit: 50,
              ordering: 'name',
              status: 'active',
              ...(targetSearch ? { search: targetSearch } : {}),
            },
          },
        })
      : await client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
          params: {
            path: { slug },
            query: { ordering: 'name', status: 'active' },
          },
        });
  let directory: Item[] = directoryRequest.data ?? [];
  if (
    graph === 'concepts' &&
    requestedTargetId &&
    !directory.some((item) => item.id === requestedTargetId)
  ) {
    const { data } = await client.GET(
      '/api/v1/organizations/{slug}/catalog/concepts/',
      {
        params: {
          path: { slug },
          query: { ids: requestedTargetId },
        },
      },
    );
    directory = mergeItems(directory, data ?? []);
  }
  const target =
    directory.find((item) => item.id === requestedTargetId) ?? directory[0];
  const canManage = access.capabilities.includes(
    'catalog.manage_prerequisites',
  );

  let links: components['schemas']['SubjectPrerequisite'][] = [];
  let dependentItems: Item[] = [];
  let editorItems = directory;
  if (target) {
    const path =
      graph === 'concepts'
        ? '/api/v1/organizations/{slug}/catalog/concept-prerequisites/'
        : '/api/v1/organizations/{slug}/catalog/subject-prerequisites/';
    const [{ data: direct }, { data: reverse }] = await Promise.all([
      client.GET(path, {
        params: { path: { slug }, query: { entity: target.id } },
      }),
      client.GET(path, {
        params: { path: { slug }, query: { prerequisite: target.id } },
      }),
    ]);
    links = (direct ?? []).map(({ kind, prerequisite_id, rationale }) => ({
      kind,
      prerequisite_id,
      ...(rationale ? { rationale } : {}),
    }));
    const relatedIds = [
      ...new Set([
        ...links.map((item) => item.prerequisite_id),
        ...(reverse ?? []).map((item) => item.entity_id),
      ]),
    ];
    if (graph === 'concepts' && relatedIds.length) {
      const { data } = await client.GET(
        '/api/v1/organizations/{slug}/catalog/concepts/',
        {
          params: {
            path: { slug },
            query: { ids: relatedIds.join(','), ordering: 'name' },
          },
        },
      );
      editorItems = mergeItems(directory, data ?? []);
    }
    const itemById = new Map(editorItems.map((item) => [item.id, item]));
    dependentItems = (reverse ?? [])
      .map((item) => itemById.get(item.entity_id))
      .filter((item): item is Item => Boolean(item));
  }

  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: 'Prerrequisitos' },
        ]}
        description="Construye rutas académicas y dependencias conceptuales sin mezclar ambos grafos."
        eyebrow="Currículo"
        title="Prerrequisitos"
      />
      <CurriculumWorkspaceNav current="prerrequisitos" slug={slug} />

      <nav
        aria-label="Tipo de grafo"
        className="mt-4 grid grid-cols-2 gap-1 rounded-lg border bg-muted/20 p-1 sm:max-w-xl"
      >
        <GraphTab
          active={graph === 'subjects'}
          href={`/organizaciones/${slug}/curriculo/prerrequisitos?graph=subjects`}
          icon={BookOpen}
          label="Asignaturas"
        />
        <GraphTab
          active={graph === 'concepts'}
          href={`/organizaciones/${slug}/curriculo/prerrequisitos?graph=concepts`}
          icon={Network}
          label="Conceptos"
        />
      </nav>

      <section className="mt-4 rounded-xl border bg-muted/15 p-4">
        <div className="flex items-start gap-3">
          <GitBranch className="mt-0.5 size-5 shrink-0 text-primary" />
          <div>
            <h2 className="text-sm font-semibold">
              {graph === 'subjects'
                ? 'Ruta entre asignaturas'
                : 'Dependencias entre conceptos'}
            </h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              {graph === 'subjects'
                ? 'Aquí sí aparecen otras asignaturas porque son los posibles antecedentes académicos. Sólo se cargan como relación cuando las añades y guardas.'
                : 'Este grafo expresa qué conceptos deben comprenderse antes de otros; no representa temas ni cursos.'}
            </p>
          </div>
        </div>
      </section>

      <form
        key={`${graph}-${target?.id ?? 'none'}-${targetSearch}`}
        className="mt-4 grid gap-2 rounded-xl border bg-background p-3 shadow-xs sm:grid-cols-[minmax(14rem,0.8fr)_minmax(16rem,1fr)_auto]"
      >
        <input name="graph" type="hidden" value={graph} />
        {graph === 'concepts' ? (
          <label className="relative">
            <span className="sr-only">Buscar concepto</span>
            <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
            <Input
              className="pl-9"
              defaultValue={targetSearch}
              name="q"
              placeholder="Buscar concepto"
            />
          </label>
        ) : (
          <div className="hidden sm:block" />
        )}
        <label className="academic-field">
          <span className="sr-only">
            {graph === 'concepts' ? 'Concepto' : 'Asignatura'}
          </span>
          <select
            className="academic-control h-9"
            defaultValue={target?.id ?? ''}
            name="target"
          >
            {directory.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
              </option>
            ))}
          </select>
        </label>
        <Button size="sm" type="submit" variant="outline">
          Abrir grafo
        </Button>
      </form>

      <div className="mt-4">
        {!canManage ? (
          <p className="rounded-xl border px-4 py-6 text-sm text-muted-foreground">
            No tienes permiso para modificar estas relaciones.
          </p>
        ) : target ? (
          <PrerequisiteEditor
            key={`${graph}-${target.id}`}
            dependentItems={dependentItems}
            entity={entity}
            initialLinks={links}
            items={editorItems}
            slug={slug}
            target={target}
          />
        ) : (
          <div className="rounded-xl border border-dashed p-10 text-center">
            <p className="font-medium">No hay entidades disponibles.</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Crea primero una entidad activa para construir el grafo.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}

function GraphTab({
  active,
  href,
  icon: Icon,
  label,
}: Readonly<{
  active: boolean;
  href: string;
  icon: typeof BookOpen;
  label: string;
}>) {
  return (
    <Link
      aria-current={active ? 'page' : undefined}
      className={`inline-flex min-h-9 items-center justify-center gap-2 rounded-md px-3 text-sm font-medium ${
        active
          ? 'bg-background shadow-xs'
          : 'text-muted-foreground hover:bg-background/60'
      }`}
      href={href}
    >
      <Icon className="size-4" /> {label}
    </Link>
  );
}

function mergeItems(left: readonly Item[], right: readonly Item[]) {
  return [
    ...new Map([...left, ...right].map((item) => [item.id, item])).values(),
  ];
}

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '');
}
