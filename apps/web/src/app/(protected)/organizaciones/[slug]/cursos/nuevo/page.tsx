import { CourseCreateForm } from '@/components/courses/course-create-form';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { getCourseCreationContext } from '@/lib/courses/server';
import Link from 'next/link';

export default async function NewCoursePage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { objectives, organization, subjects } =
    await getCourseCreationContext(slug);
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          { label: 'Nuevo curso' },
        ]}
        description="Define la identidad y su alineación curricular. La estructura se construye después en el espacio de autoría."
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
        <section className="mt-7 border-y border-amber-300 bg-amber-50/70 px-5 py-6">
          <h2 className="font-semibold">Falta una asignatura activa</h2>
          <p className="mt-2">
            Se necesita al menos una asignatura activa para crear un curso.
          </p>
          <Button asChild className="mt-4">
            <Link href={`/organizaciones/${slug}/curriculo`}>
              Abrir currículo
            </Link>
          </Button>
        </section>
      )}
    </main>
  );
}
