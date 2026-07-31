import Link from 'next/link';

import { CreateGradebookForm } from '@/components/assessments/advanced-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getGradebooks } from '@/lib/assessments/server';

export default async function GradebooksPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getGradebooks(slug);
  const releases = [
    ...new Map(
      data.deliveries
        .filter((delivery) => delivery.course_release_id)
        .filter(
          (delivery) =>
            !data.gradebooks.some(
              (gradebook) =>
                gradebook.course_release_id === delivery.course_release_id,
            ),
        )
        .map((delivery) => [
          delivery.course_release_id!,
          {
            id: delivery.course_release_id!,
            label: `${delivery.course_release_title ?? 'Curso'} · release ${delivery.course_release_number ?? '—'}`,
          },
        ]),
    ).values(),
  ];
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: 'Libros de calificaciones' },
        ]}
        description="Resumen ponderado por release, separado del progreso del curso y del aprobado de cada evaluación."
        eyebrow="Consolidación institucional"
        title="Libros de calificaciones"
      />
      {data.canManage && releases.length ? (
        <section className="assessment-builder-section">
          <header className="assessment-builder-section__header">
            <div>
              <h2>Crear libro para un release</h2>
              <p>
                Sólo aparecen releases vinculados a entregas de evaluación de
                esta organización.
              </p>
            </div>
          </header>
          <CreateGradebookForm releaseOptions={releases} slug={slug} />
        </section>
      ) : data.canManage ? (
        <section className="assessment-builder-section">
          <header className="assessment-builder-section__header">
            <div>
              <h2>Cobertura completa</h2>
              <p>
                Cada release disponible ya tiene un libro de calificaciones.
                Abre uno de los libros para consultar su consolidación.
              </p>
            </div>
            <Badge variant="outline">Al día</Badge>
          </header>
        </section>
      ) : null}
      <section className="assessment-collection">
        <header className="assessment-collection__header">
          <div>
            <p className="assessment-rail-kicker">Registro institucional</p>
            <h2>Libros disponibles</h2>
          </div>
          <span>
            {data.gradebooks.length}{' '}
            {data.gradebooks.length === 1 ? 'libro' : 'libros'}
          </span>
        </header>
        <ul className="assessment-question-list">
          {data.gradebooks.map((gradebook) => (
            <li key={gradebook.id}>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3>
                    {gradebook.course_title} · release{' '}
                    {gradebook.release_number}
                  </h3>
                  <Badge variant="outline">
                    {gradebook.status === 'active' ? 'Activo' : 'Borrador'}
                  </Badge>
                </div>
                <p>
                  {gradebook.columns.length}{' '}
                  {gradebook.columns.length === 1 ? 'columna' : 'columnas'} ·
                  versión de bloqueo {gradebook.lock_version}
                </p>
              </div>
              <Button asChild variant="outline">
                <Link
                  href={`/organizaciones/${slug}/evaluaciones/gradebooks/${gradebook.id}`}
                >
                  Abrir libro
                </Link>
              </Button>
            </li>
          ))}
          {!data.gradebooks.length ? (
            <li>
              <div>
                <h3>Aún no hay libros configurados</h3>
                <p>Crea uno a partir de un release con entregas vinculadas.</p>
              </div>
            </li>
          ) : null}
        </ul>
      </section>
    </main>
  );
}
