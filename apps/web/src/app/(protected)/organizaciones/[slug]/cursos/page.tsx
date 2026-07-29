import Link from 'next/link';

import { getCoursesForPage } from '@/lib/courses/server';

function statusLabel(value: string) {
  return (
    {
      active: 'Activo',
      approved: 'Aprobada',
      archived: 'Archivado',
      changes_requested: 'Cambios solicitados',
      draft: 'Borrador',
      in_review: 'En revisión',
    }[value] ?? value
  );
}

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
  const query = new URLSearchParams(
    Object.entries(filters).filter((entry): entry is [string, string] =>
      Boolean(entry[1]),
    ),
  );
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <nav aria-label="Migas de pan" className="text-sm text-slate-600">
        <Link href="/organizaciones">Organizaciones</Link>
        {' / '}
        <Link href={`/organizaciones/${slug}`}>{organization.name}</Link>
        {' / Cursos'}
      </nav>
      <div className="mt-5 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-600">
            {organization.name}
          </p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-950">Cursos</h1>
          <p className="mt-2 text-slate-700">
            Estructuras académicas versionadas y su flujo de revisión.
          </p>
        </div>
        {canManage ? (
          <Link
            className="rounded-lg bg-slate-950 px-4 py-2 font-medium text-white"
            href={`/organizaciones/${slug}/cursos/nuevo`}
          >
            Crear curso
          </Link>
        ) : null}
      </div>
      <form
        className="mt-7 grid gap-4 rounded-xl border border-slate-200 bg-white p-5 md:grid-cols-4"
        method="get"
      >
        <label className="font-medium md:col-span-2">
          Buscar
          <input
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            defaultValue={filters.search}
            name="search"
            placeholder="Título, resumen o slug"
          />
        </label>
        <label className="font-medium">
          Estado del curso
          <select
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            defaultValue={filters.status ?? ''}
            name="status"
          >
            <option value="">Todos</option>
            <option value="active">Activo</option>
            <option value="archived">Archivado</option>
          </select>
        </label>
        <label className="font-medium">
          Estado de autoría
          <select
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            defaultValue={filters.authoring_status ?? ''}
            name="authoring_status"
          >
            <option value="">Todos</option>
            <option value="draft">Borrador</option>
            <option value="in_review">En revisión</option>
            <option value="changes_requested">Cambios solicitados</option>
            <option value="approved">Aprobada</option>
          </select>
        </label>
        <label className="font-medium">
          Orden
          <select
            className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
            defaultValue={filters.ordering ?? '-updated_at'}
            name="ordering"
          >
            <option value="-updated_at">Actualización reciente</option>
            <option value="title">Título A–Z</option>
            <option value="-created_at">Creación reciente</option>
          </select>
        </label>
        <button
          className="self-end rounded-lg border border-slate-900 px-4 py-2 font-medium"
          type="submit"
        >
          Aplicar filtros
        </button>
      </form>
      {courses.results.length ? (
        <ul className="mt-7 grid gap-4 md:grid-cols-2">
          {courses.results.map((course) => (
            <li
              className="rounded-xl border border-slate-200 bg-white p-5"
              key={course.id}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="text-xl font-semibold">{course.title}</h2>
                  <p className="mt-1 text-sm text-slate-600">/{course.slug}</p>
                </div>
                <span className="rounded-full bg-slate-100 px-3 py-1 text-sm">
                  {statusLabel(course.authoring_status)}
                </span>
              </div>
              <p className="mt-3 line-clamp-3 text-slate-700">
                {course.summary}
              </p>
              <dl className="mt-4 grid grid-cols-2 gap-2 text-sm">
                <div>
                  <dt className="text-slate-500">Curso</dt>
                  <dd>{statusLabel(course.status)}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Asignatura principal</dt>
                  <dd>{course.primary_subject?.name ?? 'Sin asignar'}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-slate-500">Actualización</dt>
                  <dd>
                    {course.updated_at
                      ? new Intl.DateTimeFormat('es-CO', {
                          dateStyle: 'medium',
                        }).format(new Date(course.updated_at))
                      : 'Sin fecha'}
                  </dd>
                </div>
              </dl>
              <Link
                className="mt-5 inline-block font-semibold text-slate-950 underline"
                href={`/organizaciones/${slug}/cursos/${course.slug}`}
              >
                Abrir workspace
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <section className="mt-7 rounded-xl border border-dashed border-slate-300 p-8 text-center">
          <h2 className="text-xl font-semibold">No hay cursos para mostrar</h2>
          <p className="mt-2 text-slate-600">
            Ajusta los filtros o crea la primera estructura de curso.
          </p>
        </section>
      )}
      <nav aria-label="Paginación de cursos" className="mt-7 flex gap-3">
        {courses.previous ? (
          <Link
            className="rounded-lg border px-4 py-2"
            href={`?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page - 1) })}`}
          >
            Página anterior
          </Link>
        ) : null}
        {courses.next ? (
          <Link
            className="rounded-lg border px-4 py-2"
            href={`?${new URLSearchParams({ ...Object.fromEntries(query), page: String(page + 1) })}`}
          >
            Página siguiente
          </Link>
        ) : null}
      </nav>
    </main>
  );
}
