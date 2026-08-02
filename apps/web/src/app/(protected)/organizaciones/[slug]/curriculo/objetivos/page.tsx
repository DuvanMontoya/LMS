import { BookOpen, Filter, Search, Target } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { ConceptAssociationEditor } from '@/components/catalog/concept-association-editor';
import { CurriculumWorkspaceNav } from '@/components/catalog/curriculum-workspace-nav';
import { ObjectiveActions } from '@/components/catalog/objective-actions';
import { ObjectiveForm } from '@/components/catalog/objective-form';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

const PAGE_SIZE = 20;
const cognitiveLabels: Record<string, string> = {
  analyze: 'Analizar',
  apply: 'Aplicar',
  create: 'Crear',
  evaluate: 'Evaluar',
  remember: 'Recordar',
  understand: 'Comprender',
};

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function ObjectivesPage({
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
  const { data: subjects } = await client.GET(
    '/api/v1/organizations/{slug}/catalog/subjects/',
    { params: { path: { slug }, query: { status: 'active' } } },
  );
  const activeSubjects = subjects ?? [];
  const selectedSubject = activeSubjects.find(
    (item) => item.id === single(query.subject),
  );
  const search = single(query.q).trim();
  const status = single(query.status) === 'archived' ? 'archived' : 'active';
  const cognitiveLevel = single(query.level);
  const offset = safeOffset(single(query.offset));
  const canManage = access.capabilities.includes('catalog.manage');

  const objectiveRequest = selectedSubject
    ? await client.GET(
        '/api/v1/organizations/{slug}/catalog/learning-objectives/',
        {
          params: {
            path: { slug },
            query: {
              limit: PAGE_SIZE,
              offset,
              ordering: 'code',
              status,
              subject: selectedSubject.id,
              ...(search ? { search } : {}),
              ...(cognitiveLevel ? { cognitive_level: cognitiveLevel } : {}),
            },
          },
        },
      )
    : undefined;
  const objectives = objectiveRequest?.data ?? [];
  const totalHeader = Number(
    objectiveRequest?.response.headers.get('X-Total-Count'),
  );
  const total = Number.isFinite(totalHeader) ? totalHeader : objectives.length;
  const { data: associations } =
    selectedSubject && objectives.length
      ? await client.GET(
          '/api/v1/organizations/{slug}/catalog/objective-concepts/',
          {
            params: {
              path: { slug },
              query: {
                objectives: objectives.map((item) => item.id).join(','),
                subject: selectedSubject.id,
              },
            },
          },
        )
      : { data: [] };
  const conceptIdsByObjective = new Map(
    (associations ?? []).map((association) => [
      association.entity_id,
      association.concept_ids,
    ]),
  );
  const selectedConceptIds = [
    ...new Set((associations ?? []).flatMap((item) => item.concept_ids)),
  ];
  const conceptResponses = await Promise.all(
    chunks(selectedConceptIds, 100).map((ids) =>
      client.GET('/api/v1/organizations/{slug}/catalog/concepts/', {
        params: {
          path: { slug },
          query: { ids: ids.join(','), ordering: 'name' },
        },
      }),
    ),
  );
  const selectedConcepts = conceptResponses.flatMap(
    (response) => response.data ?? [],
  );

  return (
    <main className="academic-page">
      <PageHeader
        actions={
          canManage ? (
            <ObjectiveForm
              key={selectedSubject?.id ?? 'objective-without-subject'}
              selectedSubjectId={selectedSubject?.id}
              slug={slug}
              subjects={activeSubjects}
            />
          ) : undefined
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: 'Objetivos' },
        ]}
        description="Resultados observables organizados por asignatura, sin mezclar catálogos académicos."
        eyebrow="Currículo"
        title="Objetivos de aprendizaje"
      />
      <CurriculumWorkspaceNav current="objetivos" slug={slug} />

      <section className="mt-4 rounded-xl border bg-background p-4 shadow-xs">
        <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h2 className="text-sm font-semibold">Contexto de asignatura</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Selecciona una asignatura para consultar o editar únicamente sus
              objetivos.
            </p>
          </div>
          <form
            key={`${selectedSubject?.id ?? 'none'}-${cognitiveLevel}-${status}`}
            className="grid gap-2 sm:grid-cols-[minmax(15rem,1fr)_minmax(13rem,1fr)_10rem_10rem_auto] lg:min-w-[58rem]"
          >
            <label className="academic-field">
              <span className="sr-only">Asignatura</span>
              <select
                className="academic-control h-9"
                defaultValue={selectedSubject?.id ?? ''}
                name="subject"
                required
              >
                <option value="">Selecciona una asignatura</option>
                {activeSubjects.map((subject) => (
                  <option key={subject.id} value={subject.id}>
                    {subject.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="relative">
              <span className="sr-only">Buscar objetivos</span>
              <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
              <Input
                className="pl-9"
                defaultValue={search}
                name="q"
                placeholder="Código o enunciado"
              />
            </label>
            <label className="academic-field">
              <span className="sr-only">Nivel cognitivo</span>
              <select
                className="academic-control h-9"
                defaultValue={cognitiveLevel}
                name="level"
              >
                <option value="">Todos los niveles</option>
                {Object.entries(cognitiveLabels).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="academic-field">
              <span className="sr-only">Estado</span>
              <select
                className="academic-control h-9"
                defaultValue={status}
                name="status"
              >
                <option value="active">Activos</option>
                <option value="archived">Archivados</option>
              </select>
            </label>
            <Button size="sm" type="submit" variant="outline">
              <Filter /> Aplicar
            </Button>
          </form>
        </div>
      </section>

      {!selectedSubject ? (
        <section className="mt-4 rounded-xl border border-dashed p-8 text-center">
          <Target className="mx-auto size-7 text-primary" />
          <h2 className="mt-3 font-semibold">Elige la asignatura de trabajo</h2>
          <p className="mx-auto mt-1 max-w-xl text-sm text-muted-foreground">
            Esta vista no mezcla objetivos institucionales por defecto. El
            contexto seleccionado se mantiene en la URL y puede compartirse.
          </p>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {activeSubjects.map((subject) => (
              <Button asChild key={subject.id} size="sm" variant="outline">
                <Link href={`?subject=${subject.id}`}>
                  <BookOpen /> {subject.name}
                </Link>
              </Button>
            ))}
          </div>
        </section>
      ) : (
        <section className="mt-4">
          <div className="flex items-end justify-between gap-3">
            <div>
              <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
                {selectedSubject.name}
              </p>
              <h2 className="mt-1 text-lg font-semibold tracking-tight">
                Objetivos de la asignatura
              </h2>
            </div>
            <span className="text-xs text-muted-foreground">
              {total} {total === 1 ? 'objetivo' : 'objetivos'}
            </span>
          </div>
          <ul className="mt-3 grid gap-3">
            {objectives.length ? (
              objectives.map((objective) => (
                <li
                  className="rounded-xl border bg-background p-4 shadow-xs"
                  key={objective.id}
                >
                  <div className="flex flex-col gap-3 lg:flex-row lg:items-start">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-md bg-primary/10 px-2 py-1 font-mono text-xs font-semibold text-primary">
                          {objective.code}
                        </span>
                        {objective.cognitive_level ? (
                          <span className="rounded-full border px-2 py-0.5 text-xs text-muted-foreground">
                            {cognitiveLabels[objective.cognitive_level] ??
                              objective.cognitive_level}
                          </span>
                        ) : null}
                      </div>
                      <p className="mt-2 font-medium leading-6">
                        {objective.statement}
                      </p>
                      {objective.description ? (
                        <p className="mt-1 line-clamp-2 text-sm leading-6 text-muted-foreground">
                          {objective.description}
                        </p>
                      ) : null}
                    </div>
                    {canManage ? (
                      <ObjectiveActions objective={objective} slug={slug} />
                    ) : null}
                  </div>
                  {canManage ? (
                    <ConceptAssociationEditor
                      concepts={selectedConcepts}
                      entity="objective"
                      entityId={objective.id}
                      initialIds={conceptIdsByObjective.get(objective.id) ?? []}
                      slug={slug}
                    />
                  ) : null}
                </li>
              ))
            ) : (
              <li className="rounded-xl border border-dashed py-12 text-center">
                <Target className="mx-auto size-6 text-muted-foreground" />
                <p className="mt-3 text-sm font-medium">Sin resultados</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  No hay objetivos con los filtros seleccionados.
                </p>
              </li>
            )}
          </ul>
          <ObjectivePagination
            cognitiveLevel={cognitiveLevel}
            offset={offset}
            search={search}
            slug={slug}
            status={status}
            subjectId={selectedSubject.id}
            total={total}
          />
        </section>
      )}
    </main>
  );
}

function ObjectivePagination({
  cognitiveLevel,
  offset,
  search,
  slug,
  status,
  subjectId,
  total,
}: Readonly<{
  cognitiveLevel: string;
  offset: number;
  search: string;
  slug: string;
  status: string;
  subjectId: string;
  total: number;
}>) {
  if (total <= PAGE_SIZE) return null;
  const href = (nextOffset: number) => {
    const query = new URLSearchParams({ status, subject: subjectId });
    if (search) query.set('q', search);
    if (cognitiveLevel) query.set('level', cognitiveLevel);
    query.set('offset', String(nextOffset));
    return `/organizaciones/${slug}/curriculo/objetivos?${query.toString()}`;
  };
  return (
    <nav
      aria-label="Paginación de objetivos"
      className="mt-4 flex items-center justify-between rounded-lg border px-3 py-2"
    >
      <Button
        asChild={offset > 0}
        disabled={offset === 0}
        size="sm"
        variant="outline"
      >
        {offset > 0 ? (
          <Link href={href(Math.max(0, offset - PAGE_SIZE))}>Anterior</Link>
        ) : (
          <span>Anterior</span>
        )}
      </Button>
      <span className="text-xs text-muted-foreground">
        Página {Math.floor(offset / PAGE_SIZE) + 1} de{' '}
        {Math.ceil(total / PAGE_SIZE)}
      </span>
      <Button
        asChild={offset + PAGE_SIZE < total}
        disabled={offset + PAGE_SIZE >= total}
        size="sm"
        variant="outline"
      >
        {offset + PAGE_SIZE < total ? (
          <Link href={href(offset + PAGE_SIZE)}>Siguiente</Link>
        ) : (
          <span>Siguiente</span>
        )}
      </Button>
    </nav>
  );
}

function safeOffset(value: string) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : 0;
}

function chunks<T>(values: readonly T[], size: number): T[][] {
  return Array.from({ length: Math.ceil(values.length / size) }, (_, index) =>
    values.slice(index * size, (index + 1) * size),
  );
}

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '');
}
