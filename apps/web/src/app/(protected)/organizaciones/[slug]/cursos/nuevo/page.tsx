import Link from 'next/link';

import { CourseCreateForm } from '@/components/courses/course-create-form';
import { getCourseCreationContext } from '@/lib/courses/server';

export default async function NewCoursePage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { objectives, organization, subjects } =
    await getCourseCreationContext(slug);
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
      <nav aria-label="Migas de pan" className="text-sm text-slate-600">
        <Link href={`/organizaciones/${slug}`}>{organization.name}</Link>
        {' / '}
        <Link href={`/organizaciones/${slug}/cursos`}>Cursos</Link>
        {' / Nuevo'}
      </nav>
      <h1 className="mt-5 text-3xl font-semibold">Crear curso</h1>
      <p className="mt-2 text-slate-700">
        Define la identidad y alineación inicial. La estructura se añade
        después.
      </p>
      {subjects.length ? (
        <CourseCreateForm
          objectives={objectives}
          slug={slug}
          subjects={subjects}
        />
      ) : (
        <section className="mt-8 rounded-xl border border-amber-300 bg-amber-50 p-6">
          <h2 className="font-semibold">Primero configura el currículo</h2>
          <p className="mt-2">
            Se necesita al menos una asignatura activa para crear un curso.
          </p>
          <Link
            className="mt-4 inline-block font-semibold underline"
            href={`/organizaciones/${slug}/curriculo`}
          >
            Abrir currículo
          </Link>
        </section>
      )}
    </main>
  );
}
