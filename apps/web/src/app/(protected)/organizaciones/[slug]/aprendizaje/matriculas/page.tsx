import { Search, UserRoundSearch } from 'lucide-react';
import Link from 'next/link';

import { EnrollmentCreateForm } from '@/components/learning/learning-admin-forms';
import { LearningPagination } from '@/components/learning/learning-pagination';
import { LearningProgress } from '@/components/learning/learning-progress';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { accessStateLabel, enrollmentStatusLabel } from '@/lib/learning/labels';
import { getEnrollments } from '@/lib/learning/server';

const PAGE_SIZE = 20;

export default async function EnrollmentsPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{
    page?: string;
    progress?: string;
    search?: string;
    status?: string;
  }>;
}>) {
  const { slug } = await params;
  const requested = await searchParams;
  const page = positivePage(requested.page);
  const search = requested.search?.trim() ?? '';
  const status = ['active', 'revoked', 'suspended'].includes(
    requested.status ?? '',
  )
    ? requested.status
    : '';
  const progress = ['completed', 'in_progress', 'not_started'].includes(
    requested.progress ?? '',
  )
    ? requested.progress
    : '';
  const data = await getEnrollments(slug, {
    individual: true,
    ordering: '-created_at',
    page,
    page_size: PAGE_SIZE,
    ...(progress ? { progress_status: progress } : {}),
    ...(search ? { search } : {}),
    ...(status ? { status } : {}),
  });
  const canManage = data.access.capabilities.includes(
    'learning.enrollment.manage',
  );
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Matrículas individuales' },
        ]}
        description="Excepciones de acceso individual fijadas a releases publicados."
        eyebrow="Aprendizaje"
        title="Matrículas individuales"
      />
      {canManage ? (
        <details className="academic-panel group mt-6">
          <summary className="cursor-pointer rounded-md p-5 font-medium marker:text-primary hover:bg-muted/20">
            Crear matrícula individual
          </summary>
          <div className="border-t p-5 sm:p-6">
            <EnrollmentCreateForm courses={data.options.courses} slug={slug} />
          </div>
        </details>
      ) : null}
      <form
        className="academic-panel mt-5 grid gap-3 p-4 sm:grid-cols-2 xl:grid-cols-[minmax(14rem,1fr)_11rem_11rem_auto_auto] xl:items-end"
        method="get"
      >
        <label className="grid gap-1.5 text-sm font-medium">
          Buscar
          <Input
            defaultValue={search}
            name="search"
            placeholder="Correo, curso o cohorte"
          />
        </label>
        <label className="grid gap-1.5 text-sm font-medium">
          Matrícula
          <select
            className="academic-control"
            defaultValue={status}
            name="status"
          >
            <option value="">Todos los estados</option>
            <option value="active">Activas</option>
            <option value="suspended">Suspendidas</option>
            <option value="revoked">Revocadas</option>
          </select>
        </label>
        <label className="grid gap-1.5 text-sm font-medium">
          Progreso
          <select
            className="academic-control"
            defaultValue={progress}
            name="progress"
          >
            <option value="">Cualquier progreso</option>
            <option value="not_started">Sin iniciar</option>
            <option value="in_progress">En progreso</option>
            <option value="completed">Completado</option>
          </select>
        </label>
        <Button type="submit" variant="outline">
          <Search />
          Filtrar
        </Button>
        {search || status || progress ? (
          <Button asChild variant="ghost">
            <Link href={`/organizaciones/${slug}/aprendizaje/matriculas`}>
              Limpiar
            </Link>
          </Button>
        ) : null}
      </form>
      <div className="mt-5 grid gap-4">
        {data.enrollments.results.map((enrollment) => (
          <article
            className="academic-panel grid gap-4 p-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(9rem,0.7fr)_minmax(16rem,1fr)_auto] lg:items-center"
            key={enrollment.id}
          >
            <div>
              <p className="font-medium">{enrollment.student_email}</p>
              <p className="text-sm text-muted-foreground">
                {enrollment.course_title} · R{enrollment.release_number}
              </p>
              <p className="mt-1 text-sm">
                {enrollment.cohort_name ?? 'Matrícula individual'}
              </p>
            </div>
            <div>
              <Badge
                variant={
                  enrollment.status === 'active' ? 'secondary' : 'outline'
                }
              >
                {enrollmentStatusLabel(enrollment.status ?? 'active')}
              </Badge>
              <p className="mt-2 text-sm">
                {accessStateLabel(enrollment.access_state)}
              </p>
            </div>
            <LearningProgress progress={enrollment.progress} />
            <Button asChild variant="outline">
              <Link
                href={`/organizaciones/${slug}/aprendizaje/matriculas/${enrollment.id}`}
              >
                Detalle
              </Link>
            </Button>
          </article>
        ))}
      </div>
      {!data.enrollments.results.length ? (
        <section className="academic-panel mt-5 border-dashed px-6 py-12 text-center">
          <UserRoundSearch className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">No encontramos matrículas</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {search || status || progress
              ? 'Ajusta los filtros para ampliar los resultados.'
              : 'Las matrículas institucionales aparecerán aquí.'}
          </p>
        </section>
      ) : null}
      <LearningPagination
        baseHref={`/organizaciones/${slug}/aprendizaje/matriculas`}
        page={page}
        pageSize={PAGE_SIZE}
        params={{ progress, search, status }}
        total={data.enrollments.count}
      />
    </main>
  );
}

function positivePage(value?: string) {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : 1;
}
