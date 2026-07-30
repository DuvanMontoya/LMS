import Link from 'next/link';

import { ContentWorkspace } from '@/components/content/content-workspace';
import { getUnitContentWorkspace } from '@/lib/content/server';

export default async function UnitContentPage({
  params,
}: Readonly<{
  params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
}>) {
  const { courseSlug, slug, unitId } = await params;
  const data = await getUnitContentWorkspace(slug, courseSlug, unitId);

  return (
    <main className="mx-auto min-h-screen max-w-7xl px-4 py-8 sm:px-6">
      <nav aria-label="Migas de pan" className="text-sm text-slate-600">
        <Link href={`/organizaciones/${slug}/cursos`}>Cursos</Link>
        {' / '}
        <Link href={`/organizaciones/${slug}/cursos/${courseSlug}`}>
          {data.revision.title}
        </Link>
        {' / '}
        <Link href={`/organizaciones/${slug}/cursos/${courseSlug}/estructura`}>
          Estructura
        </Link>
        {' / Contenido'}
      </nav>
      <header className="mt-5">
        <p className="text-sm font-medium text-sky-700">
          {data.courseModule.title}
        </p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">
          {data.unit.title}
        </h1>
        <p className="mt-2 text-slate-700">
          Editor de contenido académico semántico
        </p>
      </header>
      <ContentWorkspace
        courseSlug={courseSlug}
        current={data.current}
        organizationSlug={slug}
        revisionId={data.revision.id}
        revisionStatus={data.revision.authoring_status}
        unitId={unitId}
        versions={data.versions}
      />
    </main>
  );
}
