import { ArrowLeft, BookOpenCheck, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

import { CourseCreateForm } from '@/components/courses/course-create-form';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { getCourseCreationContext } from '@/lib/courses/server';

export default async function NewCoursePage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { objectives, organization, subjects } =
    await getCourseCreationContext(slug);
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          <Button asChild size="sm" variant="outline">
            <Link href={`/organizaciones/${slug}/cursos`}>
              <ArrowLeft data-icon="inline-start" />
              Volver a cursos
            </Link>
          </Button>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          { label: 'Nuevo curso' },
        ]}
        description="Configura la identidad y la alineación curricular del curso. Al crearlo, abrirás su espacio de autoría para construir la estructura."
        eyebrow="Autoría"
        title="Crear curso"
      />
      {subjects.length ? (
        <CourseCreateForm
          objectives={objectives}
          slug={slug}
          subjects={subjects}
        />
      ) : (
        <section className="mt-6 max-w-3xl rounded-xl border bg-card p-6 shadow-sm sm:p-8">
          <div className="grid size-11 place-items-center rounded-lg border bg-muted/30 text-primary">
            <BookOpenCheck className="size-5" />
          </div>
          <h2 className="mt-4 text-lg font-semibold">
            No tienes asignaturas disponibles para autoría
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-muted-foreground">
            Para crear un curso necesitas al menos una responsabilidad docente
            vigente sobre una asignatura activa. La plataforma evita ofrecerte
            combinaciones que el servidor rechazaría.
          </p>
          <div className="mt-5 flex flex-wrap gap-2">
            <Button asChild>
              <Link
                href={`/organizaciones/${slug}/aprendizaje/mis-asignaturas`}
              >
                <ShieldCheck data-icon="inline-start" />
                Ver mis responsabilidades
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href={`/organizaciones/${slug}/curriculo`}>
                Abrir currículo
              </Link>
            </Button>
          </div>
        </section>
      )}
    </main>
  );
}
