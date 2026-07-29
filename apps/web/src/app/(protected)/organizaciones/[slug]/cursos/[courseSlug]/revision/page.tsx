import Link from 'next/link';

import { ReviewPanel } from '@/components/courses/review-panel';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseReviewPage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  const capabilities = data.access.capabilities;
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-10">
      <nav aria-label="Migas de pan" className="text-sm text-slate-600">
        <Link href={`/organizaciones/${slug}/cursos/${courseSlug}`}>
          {data.revision.title}
        </Link>
        {' / Revisión'}
      </nav>
      <h1 className="mt-5 text-3xl font-semibold">Revisión de estructura</h1>
      <p className="mt-2 text-slate-700">
        Verifica integridad, consulta problemas y registra decisiones.
      </p>
      <div className="mt-8">
        <ReviewPanel
          canApprove={capabilities.includes('course.authoring.approve')}
          canReview={capabilities.includes('course.authoring.review')}
          canSubmit={capabilities.includes('course.authoring.submit')}
          courseSlug={courseSlug}
          readiness={data.readiness}
          revision={data.revision}
          slug={slug}
        />
      </div>
    </main>
  );
}
