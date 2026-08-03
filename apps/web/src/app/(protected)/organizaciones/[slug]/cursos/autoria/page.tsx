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

export default async function CourseAuthoringPage({
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
  const query = {
    ...(filters.authoring_status
      ? { authoring_status: filters.authoring_status }
      : {}),
    ordering: filters.ordering || '-updated_at',
    page,
    ...(filters.search ? { search: filters.search } : {}),
    ...(filters.status ? { status: filters.status } : {}),
  };
  const { access, courses, organization } = await getCoursesForPage(
    slug,
    query,
  );
  const canManage = access.capabilities.includes('course.authoring.manage');
  const hasFilters = Boolean(
    filters.authoring_status || filters.search || filters.status,
  );
  const retained = new URLSearchParams(
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
                <Plus /> Crear curso
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          { label: 'Autoría' },
        ]}
        description="Borradores, revisiones y versiones aprobadas del equipo académico."
        eyebrow="Gestión editorial"
        title="Autoría de cursos"
      />

      <form className="course-authoring-filters" method="get">
        <label className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <span className="sr-only">Buscar curso</span>
          <Input
            className="pl-9"
            defaultValue={filters.search}
            name="search"
            placeholder="Buscar por título o resumen"
          />
        </label>
        <div>
          <Label className="sr-only" htmlFor="course-status">
            Estado del curso
          </Label>
          <select
            className="academic-control"
            defaultValue={filters.status ?? ''}
            id="course-status"
            name="status"
          >
            <option value="">Todos los cursos</option>
            <option value="active">Activos</option>
            <option value="archived">Archivados</option>
          </select>
        </div>
        <div>
          <Label className="sr-only" htmlFor="authoring-status">
            Estado de autoría
          </Label>
          <select
            className="academic-control"
            defaultValue={filters.authoring_status ?? ''}
            id="authoring-status"
            name="authoring_status"
          >
            <option value="">Todas las revisiones</option>
            <option value="draft">Borrador</option>
            <option value="in_review">En revisión</option>
            <option value="changes_requested">Cambios solicitados</option>
            <option value="approved">Aprobada</option>
          </select>
        </div>
        <div>
          <Label className="sr-only" htmlFor="course-ordering">
            Orden
          </Label>
          <select
            className="academic-control"
            defaultValue={filters.ordering ?? '-updated_at'}
            id="course-ordering"
            name="ordering"
          >
            <option value="-updated_at">Actualización reciente</option>
            <option value="title">Título A–Z</option>
            <option value="-created_at">Creación reciente</option>
          </select>
        </div>
        <Button type="submit" variant="outline">
          Aplicar
        </Button>
      </form>

      {courses.results.length ? (
        <ul className="course-authoring-list">
          {courses.results.map((course) => (
            <li key={course.id}>
              <span className="course-authoring-list__icon">
                <BookOpenCheck />
              </span>
              <div className="course-authoring-list__body">
                <Link href={`/organizaciones/${slug}/cursos/${course.slug}`}>
                  {course.title}
                </Link>
                <p>{course.summary || 'Sin resumen.'}</p>
              </div>
              <span className="course-authoring-list__subject">
                {course.primary_subject?.name ?? 'Sin asignatura'}
              </span>
              <Badge variant="secondary">
                {courseStatusLabel(course.authoring_status)}
              </Badge>
              <time dateTime={course.updated_at ?? undefined}>
                {course.updated_at
                  ? new Intl.DateTimeFormat('es-CO', {
                      day: '2-digit',
                      month: 'short',
                      year: 'numeric',
                    }).format(new Date(course.updated_at))
                  : 'Sin fecha'}
              </time>
              <Button
                asChild
                aria-label={`Abrir ${course.title}`}
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
      ) : (
        <section className="platform-empty-state">
          <BookOpenCheck className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">
            {hasFilters ? 'Sin resultados' : 'Aún no hay cursos'}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {hasFilters
              ? 'Ajusta los filtros de búsqueda.'
              : 'Crea el primer curso para iniciar su autoría.'}
          </p>
        </section>
      )}

      <nav aria-label="Paginación de cursos" className="mt-5 flex gap-3">
        {courses.previous ? (
          <Button asChild variant="outline">
            <Link
              href={`?${new URLSearchParams({ ...Object.fromEntries(retained), page: String(page - 1) })}`}
            >
              <ArrowLeft /> Página anterior
            </Link>
          </Button>
        ) : null}
        {courses.next ? (
          <Button asChild variant="outline">
            <Link
              href={`?${new URLSearchParams({ ...Object.fromEntries(retained), page: String(page + 1) })}`}
            >
              Página siguiente <ArrowRight />
            </Link>
          </Button>
        ) : null}
      </nav>
    </main>
  );
}
