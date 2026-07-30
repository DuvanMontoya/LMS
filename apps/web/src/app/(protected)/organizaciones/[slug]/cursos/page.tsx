import {
  ArrowLeft,
  ArrowRight,
  BookOpenCheck,
  Plus,
  Search,
} from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { courseStatusLabel } from '@/lib/courses/labels';
import { getCoursesForPage } from '@/lib/courses/server';

export default async function CoursesPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    authoring_status?: string;
    ordering?: string;
    page?: string;
    search?: string;
    status?: string;
  }>;
}>) {
  const { slug } = await params;
  const filters = await searchParams;
  const page = Math.max(1, Number(filters.page ?? '1') || 1);
  const courseQuery: {
    authoring_status?: string;
    ordering?: string;
    page?: number;
    search?: string;
    status?: string;
  } = { ordering: filters.ordering || '-updated_at', page };
  if (filters.authoring_status)
    courseQuery.authoring_status = filters.authoring_status;
  if (filters.search) courseQuery.search = filters.search;
  if (filters.status) courseQuery.status = filters.status;
  const { access, courses, organization } = await getCoursesForPage(
    slug,
    courseQuery,
  );
  const canManage = access.capabilities.includes('course.authoring.manage');
  const hasActiveFilters = Boolean(
    filters.authoring_status || filters.search || filters.status,
  );
  const query = new URLSearchParams(
    Object.entries(filters).filter((entry): entry is [string, string] =>
      Boolean(entry[1]),
    ),
  );
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          canManage ? (
            <Button asChild>
              <Link href={`/organizaciones/${slug}/cursos/nuevo`}>
                <Plus data-icon="inline-start" />
                Crear curso
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { label: 'Cursos' },
        ]}
        description="Estructuras académicas versionadas y su flujo de revisión."
        eyebrow="Autoría académica"
        title="Cursos"
      />
      {courses.results.length || hasActiveFilters ? (
        <form
          className="mt-5 grid gap-3 border-b pb-4 md:grid-cols-2 xl:grid-cols-[1.4fr_0.8fr_0.8fr_0.8fr_auto]"
          method="get"
        >
          <div className="space-y-1.5">
            <Label htmlFor="course-search">Buscar</Label>
            <div className="relative">
              <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                defaultValue={filters.search}
                id="course-search"
                name="search"
                placeholder="Título, resumen o slug"
              />
            </div>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="course-status">Estado del curso</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
              defaultValue={filters.status ?? ''}
              id="course-status"
              name="status"
            >
              <option value="">Todos</option>
              <option value="active">Activo</option>
              <option value="archived">Archivado</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="authoring-status">Estado de autoría</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
              defaultValue={filters.authoring_status ?? ''}
              id="authoring-status"
              name="authoring_status"
            >
              <option value="">Todos</option>
              <option value="draft">Borrador</option>
              <option value="in_review">En revisión</option>
              <option value="changes_requested">Cambios solicitados</option>
              <option value="approved">Aprobada</option>
            </select>
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="course-ordering">Orden</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
              defaultValue={filters.ordering ?? '-updated_at'}
              id="course-ordering"
              name="ordering"
            >
              <option value="-updated_at">Actualización reciente</option>
              <option value="title">Título A–Z</option>
              <option value="-created_at">Creación reciente</option>
            </select>
          </div>
          <Button className="self-end" type="submit" variant="outline">
            Aplicar filtros
          </Button>
        </form>
      ) : null}
      {courses.results.length ? (
        <section
          aria-label="Catálogo de cursos"
          className="mt-6 overflow-hidden rounded-lg border bg-card"
        >
          <div className="hidden grid-cols-[minmax(18rem,1.6fr)_minmax(12rem,0.8fr)_9rem_9rem_3rem] gap-4 border-b bg-muted/30 px-5 py-2.5 text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase lg:grid">
            <span>Curso</span>
            <span>Asignatura principal</span>
            <span>Autoría</span>
            <span>Actualización</span>
            <span className="sr-only">Abrir</span>
          </div>
          <ul className="divide-y">
            {courses.results.map((course) => (
              <li
                className="group grid gap-4 px-5 py-4 transition-colors hover:bg-muted/20 lg:grid-cols-[minmax(18rem,1.6fr)_minmax(12rem,0.8fr)_9rem_9rem_3rem] lg:items-center"
                key={course.id}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      aria-hidden="true"
                      className="size-1.5 shrink-0 rounded-full bg-primary"
                    />
                    <Link
                      className="truncate font-semibold underline-offset-4 hover:text-primary hover:underline"
                      href={`/organizaciones/${slug}/cursos/${course.slug}`}
                    >
                      {course.title}
                    </Link>
                  </div>
                  <p className="mt-1 truncate pl-3.5 text-sm text-muted-foreground">
                    {course.summary}
                  </p>
                  <p className="mt-1 truncate pl-3.5 font-mono text-[0.6875rem] text-muted-foreground">
                    /{course.slug}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground lg:hidden">
                    Asignatura principal
                  </span>
                  <p className="mt-0.5 truncate text-sm font-medium">
                    {course.primary_subject?.name ?? 'Sin asignar'}
                  </p>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground lg:hidden">
                    Estado de autoría
                  </span>
                  <Badge className="mt-0.5 rounded" variant="secondary">
                    {courseStatusLabel(course.authoring_status)}
                  </Badge>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground lg:hidden">
                    Actualización
                  </span>
                  <p className="mt-0.5 text-sm">
                    {course.updated_at
                      ? new Intl.DateTimeFormat('es-CO', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric',
                        }).format(new Date(course.updated_at))
                      : 'Sin fecha'}
                  </p>
                </div>
                <Button
                  asChild
                  aria-label={`Abrir ${course.title}`}
                  className="justify-self-start lg:justify-self-end"
                  size="icon-sm"
                  variant="ghost"
                >
                  <Link href={`/organizaciones/${slug}/cursos/${course.slug}`}>
                    <ArrowRight />
                  </Link>
                </Button>
              </li>
            ))}
          </ul>
        </section>
      ) : (
        <section className="mt-6 rounded-md border border-dashed border-border px-6 py-12 text-center">
          <span className="mx-auto grid size-10 place-items-center rounded-md bg-primary/8 text-primary">
            <BookOpenCheck className="size-5" />
          </span>
          <h2 className="mt-4 text-base font-semibold">
            {hasActiveFilters ? 'Sin resultados' : 'Aún no hay cursos'}
          </h2>
          <p className="mx-auto mt-1.5 max-w-md text-sm text-muted-foreground">
            {hasActiveFilters
              ? 'No encontramos cursos con los filtros seleccionados.'
              : 'Crea la primera estructura académica para iniciar su autoría.'}
          </p>
          {hasActiveFilters ? (
            <Button asChild className="mt-4" size="sm" variant="outline">
              <Link href={`/organizaciones/${slug}/cursos`}>
                Limpiar filtros
              </Link>
            </Button>
          ) : null}
        </section>
      )}
      <nav aria-label="Paginación de cursos" className="mt-7 flex gap-3">
        {courses.previous ? (
          <Button asChild variant="outline">
            <Link
              href={`?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page - 1) })}`}
            >
              <ArrowLeft data-icon="inline-start" />
              Página anterior
            </Link>
          </Button>
        ) : null}
        {courses.next ? (
          <Button asChild variant="outline">
            <Link
              href={`?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page + 1) })}`}
            >
              Página siguiente
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        ) : null}
      </nav>
    </main>
  );
}
