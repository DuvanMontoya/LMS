import Link from 'next/link';

import { StructureEditor } from '@/components/courses/structure-editor';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseStructurePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <nav aria-label="Migas de pan" className="text-sm text-slate-600">
        <Link href={`/organizaciones/${slug}/cursos`}>Cursos</Link>
        {' / '}
        <Link href={`/organizaciones/${slug}/cursos/${courseSlug}`}>
          {data.revision.title}
        </Link>
        {' / Estructura'}
      </nav>
      <h1 className="mt-5 text-3xl font-semibold">Editor de estructura</h1>
      <p className="mt-2 text-slate-700">
        Lista jerárquica de módulos y unidades. El contenido académico vendrá en
        una fase posterior.
      </p>
      <div className="mt-8">
        <StructureEditor
          canManage={data.access.capabilities.includes(
            'course.authoring.manage',
          )}
          courseSlug={courseSlug}
          key={data.outline.revision.lock_version}
          objectives={data.objectives}
          outline={data.outline}
          slug={slug}
          topics={data.topics}
        />
      </div>
    </main>
  );
}
