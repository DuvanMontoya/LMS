import { FileSearch, Search } from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import type { SearchResponse } from '@/lib/discovery/server';

const sourceLabels: Record<string, string> = {
  course_release: 'Curso',
  course_unit: 'Unidad',
  catalog_subject: 'Asignatura',
  catalog_topic: 'Tema',
  catalog_concept: 'Concepto',
  learning_objective: 'Objetivo',
  asset_version: 'Recurso',
  question_version: 'Pregunta',
  assessment_version: 'Evaluación',
};

export function SearchResults({
  data,
  organizationSlug,
  query,
  types,
}: Readonly<{
  data: SearchResponse;
  organizationSlug: string;
  query: string;
  types?: string | undefined;
}>) {
  if (!data.results.length) {
    return (
      <section className="platform-empty-state" aria-live="polite">
        <FileSearch className="mx-auto size-7 text-muted-foreground" />
        <h2 className="mt-3 font-semibold">Sin resultados autorizados</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Prueba otros términos o ajusta los tipos de contenido.
        </p>
      </section>
    );
  }
  return (
    <section aria-labelledby="search-results-heading" aria-live="polite">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="search-results-heading" className="font-semibold">
          Resultados
        </h2>
        <p className="text-sm text-muted-foreground">
          {data.pagination.total} coincidencias
        </p>
      </div>
      <ul className="grid gap-3">
        {data.results.map((result) => (
          <li
            className="rounded-xl border bg-card p-4 shadow-xs"
            key={`${result.source_type}-${result.source_id}`}
          >
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline">
                {sourceLabels[result.source_type] ?? result.source_type}
              </Badge>
              <span className="sr-only">Relevancia {result.rank_bucket}</span>
            </div>
            <h3 className="mt-2 text-base font-semibold">
              <Link
                className="underline-offset-4 hover:text-primary hover:underline"
                href={result.url_path}
              >
                {result.title}
              </Link>
            </h3>
            {result.subtitle ? (
              <p className="mt-1 text-sm text-muted-foreground">
                {result.subtitle}
              </p>
            ) : null}
            <p className="mt-2 text-sm leading-6">
              {result.snippet_segments.map((segment, index) =>
                segment.highlighted ? (
                  <mark
                    className="rounded-sm bg-amber-100 px-0.5 text-inherit"
                    key={index}
                  >
                    {segment.text}
                  </mark>
                ) : (
                  <span key={index}>{segment.text}</span>
                ),
              )}
            </p>
          </li>
        ))}
      </ul>
      {data.pagination.total > data.pagination.page_size ? (
        <nav
          aria-label="Paginación de resultados"
          className="mt-5 flex items-center justify-between gap-3"
        >
          <PaginationLink
            disabled={data.pagination.page <= 1}
            label="Anterior"
            organizationSlug={organizationSlug}
            page={Math.max(1, data.pagination.page - 1)}
            query={query}
            types={types}
          />
          <span className="text-sm text-muted-foreground">
            Página {data.pagination.page}
          </span>
          <PaginationLink
            disabled={
              data.pagination.page * data.pagination.page_size >=
              data.pagination.total
            }
            label="Siguiente"
            organizationSlug={organizationSlug}
            page={data.pagination.page + 1}
            query={query}
            types={types}
          />
        </nav>
      ) : null}
    </section>
  );
}

function PaginationLink({
  disabled,
  label,
  organizationSlug,
  page,
  query,
  types,
}: Readonly<{
  disabled: boolean;
  label: string;
  organizationSlug: string;
  page: number;
  query: string;
  types?: string | undefined;
}>) {
  const params = new URLSearchParams({ page: String(page), q: query });
  if (types) params.set('types', types);
  return (
    <Link
      aria-disabled={disabled}
      className={`inline-flex h-9 items-center rounded-md border px-4 text-sm font-medium ${disabled ? 'pointer-events-none opacity-50' : 'hover:bg-muted'}`}
      href={`/organizaciones/${organizationSlug}/buscar?${params.toString()}`}
    >
      {label}
    </Link>
  );
}

export function SearchPrompt() {
  return (
    <section className="platform-empty-state">
      <Search className="mx-auto size-7 text-muted-foreground" />
      <h2 className="mt-3 font-semibold">Busca en tu espacio académico</h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Los resultados se limitan a contenido que puedes consultar.
      </p>
    </section>
  );
}
