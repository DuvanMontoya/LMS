import {
  ArrowRight,
  BookOpen,
  Clock3,
  Languages,
  Settings2,
} from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { formatDuration, languageLabel } from '@/lib/publishing/labels';
import { getLibrary } from '@/lib/publishing/server';

export default async function CoursesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getLibrary(slug);
  const canOpenAuthoring = data.access.capabilities.includes(
    'course.authoring.view',
  );

  return (
    <main className="academic-page">
      <PageHeader
        actions={
          canOpenAuthoring ? (
            <Button asChild size="sm" variant="outline">
              <Link href={`/organizaciones/${slug}/cursos/autoria`}>
                <Settings2 /> Gestionar autoría
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Cursos' },
        ]}
        description="Cursos publicados y disponibles en la institución."
        eyebrow="Aprendizaje"
        title="Cursos"
      />

      {data.courses.length ? (
        <ul className="course-catalog-grid">
          {data.courses.map((course) => (
            <li key={course.course_id}>
              <div className="course-catalog-card__mark">
                <BookOpen />
                <span>{course.unit_count}</span>
                <small>{course.unit_count === 1 ? 'unidad' : 'unidades'}</small>
              </div>
              <div className="course-catalog-card__body">
                <h2>{course.title}</h2>
                <p>{course.summary}</p>
                <dl>
                  <CourseFact
                    icon={<Clock3 />}
                    value={formatDuration(course.estimated_duration_minutes)}
                  />
                  <CourseFact
                    icon={<Languages />}
                    value={languageLabel(course.language_code)}
                  />
                </dl>
              </div>
              <Button
                asChild
                aria-label={`Abrir ${course.title}`}
                size="icon-sm"
                variant="ghost"
              >
                <Link
                  href={`/organizaciones/${slug}/cursos/publicados/${course.slug}`}
                >
                  <ArrowRight />
                </Link>
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <section className="platform-empty-state">
          <BookOpen className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">No hay cursos publicados</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Los cursos aparecerán aquí cuando exista un release activo.
          </p>
        </section>
      )}
    </main>
  );
}

function CourseFact({
  icon,
  value,
}: Readonly<{ icon: React.ReactNode; value: string }>) {
  return (
    <div>
      <dt className="sr-only">Detalle</dt>
      <dd>
        {icon}
        <span>{value}</span>
      </dd>
    </div>
  );
}
