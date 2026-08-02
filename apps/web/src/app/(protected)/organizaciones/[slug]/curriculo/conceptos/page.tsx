import { BookOpenText, Filter, Search } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { ConceptForm } from '@/components/catalog/concept-form';
import { ConceptList } from '@/components/catalog/concept-list';
import { CurriculumWorkspaceNav } from '@/components/catalog/curriculum-workspace-nav';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

const PAGE_SIZE = 24;

type SearchParams = Promise<Record<string, string | string[] | undefined>>;

export default async function ConceptsPage({
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
  const requestedSubject = single(query.subject);
  const subject = activeSubjects.find((item) => item.id === requestedSubject);
  const search = single(query.q).trim();
  const status = single(query.status) === 'archived' ? 'archived' : 'active';
  const offset = safeOffset(single(query.offset));
  const conceptRequest = await client.GET(
    '/api/v1/organizations/{slug}/catalog/concepts/',
    {
      params: {
        path: { slug },
        query: {
          limit: PAGE_SIZE,
          offset,
          ordering: 'name',
          status,
          ...(search ? { search } : {}),
          ...(subject ? { subject: subject.id } : {}),
        },
      },
    },
  );
  const concepts = conceptRequest.data ?? [];
  const total = Number(conceptRequest.response.headers.get('X-Total-Count'));
  const resultTotal = Number.isFinite(total) ? total : concepts.length;
  const canManage = access.capabilities.includes('catalog.manage');

  return (
    <main className="academic-page">
      <PageHeader
        actions={canManage ? <ConceptForm slug={slug} /> : undefined}
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/curriculo`, label: 'Currículo' },
          { label: 'Conceptos' },
        ]}
        description="Diccionario institucional reutilizable en temas y objetivos, con contexto y búsqueda por asignatura."
        eyebrow="Currículo"
        title="Conceptos"
      />
      <CurriculumWorkspaceNav current="conceptos" slug={slug} />

      <section className="mt-4 rounded-xl border bg-muted/15 p-4 sm:p-5">
        <div className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
            <BookOpenText className="size-4" />
          </span>
          <div>
            <h2 className="text-sm font-semibold">Diccionario, no temario</h2>
            <p className="mt-1 max-w-4xl text-sm leading-6 text-muted-foreground">
              Un concepto puede reutilizarse en varias asignaturas. El filtro de
              asignatura muestra sólo los que ya están relacionados con sus
              temas u objetivos; la estructura temática se administra dentro de
              cada asignatura.
            </p>
          </div>
        </div>
      </section>

      <form
        key={`${subject?.id ?? 'all'}-${status}`}
        className="mt-4 grid gap-3 rounded-xl border bg-background p-3 shadow-xs lg:grid-cols-[minmax(16rem,1fr)_minmax(14rem,0.65fr)_10rem_auto]"
      >
        <label className="relative">
          <span className="sr-only">Buscar conceptos</span>
          <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
          <Input
            className="pl-9"
            defaultValue={search}
            name="q"
            placeholder="Buscar por nombre o definición"
          />
        </label>
        <label className="academic-field">
          <span className="sr-only">Filtrar por asignatura</span>
          <select
            className="academic-control h-9"
            defaultValue={subject?.id ?? ''}
            name="subject"
          >
            <option value="">Todas las asignaturas</option>
            {activeSubjects.map((item) => (
              <option key={item.id} value={item.id}>
                {item.name}
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

      <div className="mt-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h2 className="text-sm font-semibold">
            {subject
              ? `Conceptos usados en ${subject.name}`
              : 'Diccionario institucional'}
          </h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            {resultTotal} {resultTotal === 1 ? 'resultado' : 'resultados'}
          </p>
        </div>
        {subject ? (
          <Button asChild size="sm" variant="ghost">
            <Link href={`/organizaciones/${slug}/curriculo/conceptos`}>
              Quitar filtro de asignatura
            </Link>
          </Button>
        ) : null}
      </div>
      <ConceptList canManage={canManage} concepts={concepts} slug={slug} />
      <DirectoryPagination
        basePath={`/organizaciones/${slug}/curriculo/conceptos`}
        offset={offset}
        pageSize={PAGE_SIZE}
        query={{ q: search, status, subject: subject?.id ?? '' }}
        total={resultTotal}
      />
    </main>
  );
}

function DirectoryPagination({
  basePath,
  offset,
  pageSize,
  query,
  total,
}: Readonly<{
  basePath: string;
  offset: number;
  pageSize: number;
  query: Record<string, string>;
  total: number;
}>) {
  if (total <= pageSize) return null;
  const page = Math.floor(offset / pageSize) + 1;
  const pages = Math.ceil(total / pageSize);
  const href = (nextOffset: number) => {
    const params = new URLSearchParams(
      Object.entries(query).filter((entry) => Boolean(entry[1])),
    );
    params.set('offset', String(nextOffset));
    return `${basePath}?${params.toString()}`;
  };
  return (
    <nav
      aria-label="Paginación de conceptos"
      className="mt-4 flex items-center justify-between rounded-lg border px-3 py-2"
    >
      <Button
        asChild={offset > 0}
        disabled={offset === 0}
        size="sm"
        variant="outline"
      >
        {offset > 0 ? (
          <Link href={href(Math.max(0, offset - pageSize))}>Anterior</Link>
        ) : (
          <span>Anterior</span>
        )}
      </Button>
      <span className="text-xs text-muted-foreground">
        Página {page} de {pages}
      </span>
      <Button
        asChild={offset + pageSize < total}
        disabled={offset + pageSize >= total}
        size="sm"
        variant="outline"
      >
        {offset + pageSize < total ? (
          <Link href={href(offset + pageSize)}>Siguiente</Link>
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

function single(value: string | string[] | undefined) {
  return Array.isArray(value) ? (value[0] ?? '') : (value ?? '');
}
