import { Search, X } from 'lucide-react';
import Link from 'next/link';

import {
  SearchPrompt,
  SearchResults,
} from '@/components/discovery/search-results';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  searchOrganization,
  suggestOrganization,
} from '@/lib/discovery/server';

export default async function SearchPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string; q?: string; types?: string }>;
}>) {
  const { slug } = await params;
  const filters = await searchParams;
  const query = (filters.q ?? '').trim();
  const data = query
    ? await searchOrganization(slug, {
        q: query,
        page: Number(filters.page ?? '1'),
        page_size: 20,
        ...(filters.types ? { types: filters.types } : {}),
      })
    : undefined;
  const suggestions =
    data && data.results.length === 0
      ? await suggestOrganization(slug, query)
      : [];
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: 'Organización' },
          { label: 'Buscar' },
        ]}
        description="Encuentra cursos, unidades y recursos respetando tu acceso vigente."
        eyebrow="Descubrimiento académico"
        title="Buscar"
      />
      <form
        className="mt-5 rounded-xl border bg-card p-4"
        method="get"
        role="search"
      >
        <fieldset className="grid gap-3 md:grid-cols-[1fr_14rem_auto_auto]">
          <legend className="sr-only">Consulta y filtros académicos</legend>
          <div className="space-y-1.5">
            <Label htmlFor="academic-search">Términos de búsqueda</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                defaultValue={query}
                id="academic-search"
                maxLength={200}
                minLength={2}
                name="q"
                placeholder="Ej. funciones cuadráticas"
                required
                className="pl-9"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="search-types">Tipo</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
              defaultValue={filters.types ?? ''}
              id="search-types"
              name="types"
            >
              <option value="">Todos los permitidos</option>
              <option value="course_release,course_unit">
                Cursos y unidades
              </option>
              <option value="catalog_subject,catalog_topic,catalog_concept,learning_objective">
                Currículo
              </option>
              <option value="asset_version">Recursos</option>
              <option value="question_version,assessment_version">
                Evaluaciones
              </option>
            </select>
          </div>
          <Button className="self-end" type="submit">
            Buscar
          </Button>
          {query ? (
            <Button asChild className="self-end" variant="outline">
              <Link href={`/organizaciones/${slug}/buscar`}>
                <X /> Limpiar
              </Link>
            </Button>
          ) : null}
        </fieldset>
      </form>
      <div className="mt-6">
        {suggestions.length ? (
          <aside
            aria-labelledby="search-suggestions-heading"
            className="mb-4 rounded-xl border bg-card p-4"
          >
            <h2 className="font-semibold" id="search-suggestions-heading">
              Quizás buscabas
            </h2>
            <ul className="mt-2 flex flex-wrap gap-2">
              {suggestions.map((suggestion) => (
                <li key={`${suggestion.source_type}:${suggestion.url_path}`}>
                  <Button asChild size="sm" variant="outline">
                    <Link href={suggestion.url_path}>{suggestion.title}</Link>
                  </Button>
                </li>
              ))}
            </ul>
          </aside>
        ) : null}
        {data ? (
          <SearchResults
            data={data}
            organizationSlug={slug}
            query={query}
            types={filters.types}
          />
        ) : (
          <SearchPrompt />
        )}
      </div>
    </main>
  );
}
