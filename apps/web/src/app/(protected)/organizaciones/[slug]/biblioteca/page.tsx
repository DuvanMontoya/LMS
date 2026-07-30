import { BookOpen, Clock3, Languages, LibraryBig } from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { formatDuration, languageLabel } from '@/lib/publishing/labels';
import { getLibrary } from '@/lib/publishing/server';

export default async function LibraryPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getLibrary(slug);
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Biblioteca' },
        ]}
        description="Cursos que la institución mantiene activos para lectura."
        eyebrow="Colección institucional"
        title="Biblioteca"
      />
      {data.courses.length ? (
        <ul className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {data.courses.map((course) => (
            <li
              className="flex min-w-0 flex-col border p-5"
              key={course.course_id}
            >
              <div className="flex items-start gap-3">
                <span className="grid size-10 shrink-0 place-items-center border bg-muted/30">
                  <LibraryBig className="size-5 text-primary" />
                </span>
                <div className="min-w-0">
                  <h2 className="font-semibold">{course.title}</h2>
                  <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                    {course.summary}
                  </p>
                </div>
              </div>
              <dl className="mt-5 grid grid-cols-3 gap-2 border-y py-3 text-xs">
                <CourseFact
                  icon={<Clock3 />}
                  label="Duración"
                  value={formatDuration(course.estimated_duration_minutes)}
                />
                <CourseFact
                  icon={<BookOpen />}
                  label="Unidades"
                  value={`${course.unit_count} unidades`}
                />
                <CourseFact
                  icon={<Languages />}
                  label="Idioma"
                  value={languageLabel(course.language_code)}
                />
              </dl>
              <Button asChild className="mt-4" size="sm" variant="outline">
                <Link
                  href={`/organizaciones/${slug}/biblioteca/${course.slug}`}
                >
                  Abrir curso
                </Link>
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <section className="mt-6 border border-dashed px-6 py-12 text-center">
          <LibraryBig className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">No hay cursos activos</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Los cursos aparecerán aquí cuando se publique un release.
          </p>
        </section>
      )}
    </main>
  );
}

function CourseFact({
  icon,
  label,
  value,
}: Readonly<{ icon: React.ReactNode; label: string; value: string }>) {
  return (
    <div>
      <dt className="sr-only">{label}</dt>
      <dd className="flex min-w-0 items-center gap-1.5 text-muted-foreground [&_svg]:size-3.5">
        {icon}
        <span className="truncate">{value}</span>
      </dd>
    </div>
  );
}
