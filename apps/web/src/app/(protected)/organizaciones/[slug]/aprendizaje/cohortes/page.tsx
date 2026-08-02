import { Search, UsersRound } from 'lucide-react';
import Link from 'next/link';

import { LearningPagination } from '@/components/learning/learning-pagination';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { accessWindowLabel, cohortStatusLabel } from '@/lib/learning/labels';
import { getCohorts } from '@/lib/learning/server';

const PAGE_SIZE = 20;

export default async function CohortsPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    page?: string;
    search?: string;
    status?: string;
  }>;
}>) {
  const { slug } = await params;
  const requested = await searchParams;
  const page = positivePage(requested.page);
  const search = requested.search?.trim() ?? '';
  const status =
    requested.status === 'active' || requested.status === 'archived'
      ? requested.status
      : '';
  const data = await getCohorts(slug, {
    ordering: 'name',
    page,
    page_size: PAGE_SIZE,
    ...(search ? { search } : {}),
    ...(status ? { status } : {}),
  });
  const canManage = data.access.capabilities.includes('learning.cohort.manage');
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          canManage ? (
            <Button asChild>
              <Link href={`/organizaciones/${slug}/aprendizaje/cohortes/nueva`}>
                Nueva sección
              </Link>
            </Button>
          ) : undefined
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Secciones' },
        ]}
        description="Secciones vinculadas a un curso, su release inmutable y un período académico."
        eyebrow="Aprendizaje"
        title="Secciones"
      />
      <form
        className="academic-panel mt-6 grid gap-3 p-4 sm:grid-cols-[minmax(14rem,1fr)_12rem_auto_auto] sm:items-end"
        method="get"
      >
        <label className="grid gap-1.5 text-sm font-medium">
          Buscar
          <Input
            defaultValue={search}
            name="search"
            placeholder="Nombre, curso o slug"
          />
        </label>
        <label className="grid gap-1.5 text-sm font-medium">
          Estado
          <select
            className="academic-control"
            defaultValue={status}
            name="status"
          >
            <option value="">Todos</option>
            <option value="active">Activas</option>
            <option value="archived">Archivadas</option>
          </select>
        </label>
        <Button type="submit" variant="outline">
          <Search />
          Filtrar
        </Button>
        {search || status ? (
          <Button asChild variant="ghost">
            <Link href={`/organizaciones/${slug}/aprendizaje/cohortes`}>
              Limpiar
            </Link>
          </Button>
        ) : null}
      </form>
      <div className="academic-panel mt-5 overflow-x-auto">
        <table className="w-full min-w-3xl text-left text-sm">
          <caption className="sr-only">
            Secciones de {data.organization.name}
          </caption>
          <thead className="border-b bg-muted/30">
            <tr>
              <th className="p-3">Nombre</th>
              <th className="p-3">Curso</th>
              <th className="p-3">Release</th>
              <th className="p-3">Estado</th>
              <th className="p-3">Ventana</th>
              <th className="p-3">Matrículas</th>
            </tr>
          </thead>
          <tbody>
            {data.cohorts.results.map((cohort) => (
              <tr
                className="border-b transition-colors last:border-0 hover:bg-muted/20"
                key={cohort.id}
              >
                <td className="p-3 font-medium">
                  <Link
                    className="underline-offset-4 hover:underline"
                    href={`/organizaciones/${slug}/aprendizaje/cohortes/${cohort.id}`}
                  >
                    {cohort.name}
                  </Link>
                </td>
                <td className="p-3">{cohort.course_title}</td>
                <td className="p-3">R{cohort.release_number}</td>
                <td className="p-3">
                  <Badge
                    variant={
                      cohort.status === 'active' ? 'secondary' : 'outline'
                    }
                  >
                    {cohortStatusLabel(cohort.status ?? 'active')}
                  </Badge>
                </td>
                <td className="p-3">
                  {accessWindowLabel(
                    cohort.access_starts_at,
                    cohort.access_ends_at,
                  )}
                </td>
                <td className="p-3">{cohort.enrollment_count ?? 0}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!data.cohorts.results.length ? (
        <section className="academic-panel mt-5 border-dashed px-6 py-12 text-center">
          <UsersRound className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">No encontramos secciones</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {search || status
              ? 'Ajusta los filtros para ampliar los resultados.'
              : 'Crea la primera sección para organizar una entrega.'}
          </p>
        </section>
      ) : null}
      <LearningPagination
        baseHref={`/organizaciones/${slug}/aprendizaje/cohortes`}
        page={page}
        pageSize={PAGE_SIZE}
        params={{ search, status }}
        total={data.cohorts.count}
      />
    </main>
  );
}

function positivePage(value?: string) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}
