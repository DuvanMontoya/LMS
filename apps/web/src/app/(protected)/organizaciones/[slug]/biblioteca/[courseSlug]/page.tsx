import { ArrowRight, BookOpen, Clock3, Languages, Target } from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDuration, languageLabel } from '@/lib/publishing/labels';
import { getLibraryCourse } from '@/lib/publishing/server';

export default async function LibraryCoursePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getLibraryCourse(slug, courseSlug);
  const firstUnit = data.course.outline[0]?.units[0];
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          firstUnit ? (
            <Button asChild size="sm">
              <Link
                href={`/organizaciones/${slug}/biblioteca/${courseSlug}/unidades/${firstUnit.id}`}
              >
                Comenzar lectura
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { href: `/organizaciones/${slug}/biblioteca`, label: 'Biblioteca' },
          { label: data.course.title },
        ]}
        description={data.course.summary}
        eyebrow="Curso publicado"
        title={data.course.title}
      />
      <p className="mt-4 max-w-4xl text-sm leading-6 text-foreground/80">
        {data.course.description}
      </p>
      <dl className="mt-5 grid border sm:grid-cols-2 lg:grid-cols-4">
        <CourseFact
          icon={<Clock3 />}
          label="Duración"
          value={formatDuration(data.course.estimated_duration_minutes)}
        />
        <CourseFact
          icon={<BookOpen />}
          label="Estructura"
          value={`${data.course.module_count} módulos · ${data.course.unit_count} unidades`}
        />
        <CourseFact
          icon={<Languages />}
          label="Idioma"
          value={languageLabel(data.course.language_code)}
        />
        <CourseFact
          icon={<Target />}
          label="Objetivos"
          value={`${data.objectives.length} declarados`}
        />
      </dl>
      <div className="mt-7 grid gap-6 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <section className="border">
          <header className="border-b px-5 py-4">
            <h2 className="font-semibold">Tabla de contenidos</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Orden estable del release {data.course.release_number}.
            </p>
          </header>
          <ol className="divide-y">
            {data.course.outline.map((module) => (
              <li
                className="grid lg:grid-cols-[16rem_minmax(0,1fr)]"
                key={module.id}
              >
                <div className="border-b bg-muted/15 px-5 py-4 lg:border-r lg:border-b-0">
                  <span className="text-xs text-muted-foreground">
                    Módulo {module.position}
                  </span>
                  <h3 className="mt-1 text-sm font-semibold">{module.title}</h3>
                  {module.description ? (
                    <p className="mt-2 text-xs text-muted-foreground">
                      {module.description}
                    </p>
                  ) : null}
                </div>
                <ol className="divide-y">
                  {module.units.map((unit) => (
                    <li key={unit.id}>
                      <Link
                        className="flex min-h-12 items-center gap-3 px-5 py-3 text-sm hover:bg-muted/30 focus-visible:outline-2 focus-visible:outline-offset-[-2px]"
                        href={`/organizaciones/${slug}/biblioteca/${courseSlug}/unidades/${unit.id}`}
                      >
                        <span className="text-muted-foreground">
                          {module.position}.{unit.position}
                        </span>
                        <span className="min-w-0 flex-1 font-medium">
                          {unit.title}
                        </span>
                        <ArrowRight className="size-4" aria-hidden="true" />
                      </Link>
                    </li>
                  ))}
                </ol>
              </li>
            ))}
          </ol>
        </section>
        <aside className="grid content-start gap-5">
          <section className="border p-5">
            <h2 className="font-semibold">Asignaturas</h2>
            <div className="mt-3 flex flex-wrap gap-2">
              {data.subjects.map((subject) => (
                <Badge key={subject.id} variant="outline">
                  {subject.name}
                </Badge>
              ))}
            </div>
          </section>
          <section className="border p-5">
            <h2 className="font-semibold">Objetivos de aprendizaje</h2>
            <ol className="mt-3 space-y-3 text-sm">
              {data.objectives.map((objective) => (
                <li
                  className="border-l-2 border-primary pl-3"
                  key={objective.id}
                >
                  <span className="text-xs font-semibold text-muted-foreground">
                    {objective.code}
                  </span>
                  <p>{objective.statement}</p>
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </div>
      <p className="mt-5 text-xs text-muted-foreground">
        “Comenzar lectura” abre la primera unidad; esta fase no guarda avance.
      </p>
    </main>
  );
}

function CourseFact({
  icon,
  label,
  value,
}: Readonly<{ icon: React.ReactNode; label: string; value: string }>) {
  return (
    <div className="border-b px-5 py-4 lg:border-r lg:border-b-0">
      <dt className="flex items-center gap-2 text-xs text-muted-foreground">
        <span className="text-primary [&_svg]:size-4">{icon}</span>
        {label}
      </dt>
      <dd className="mt-1 text-sm font-medium">{value}</dd>
    </div>
  );
}
