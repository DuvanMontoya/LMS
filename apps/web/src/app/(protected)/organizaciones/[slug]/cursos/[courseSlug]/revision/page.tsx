import { ReviewPanel } from '@/components/courses/review-panel';
import { PageHeader } from '@/components/platform/page-header';
import { getCourseWorkspace } from '@/lib/courses/server';
import { notFound } from 'next/navigation';

export default async function CourseReviewPage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  const capabilities = data.access.capabilities;
  if (!capabilities.includes('course.authoring.view')) notFound();
  if (!data.readiness) notFound();
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}/cursos/autoria`, label: 'Autoría' },
          {
            href: `/organizaciones/${slug}/cursos/${courseSlug}`,
            label: data.revision.title,
          },
          { label: 'Revisión' },
        ]}
        description="Verifica la integridad académica, resuelve bloqueos y registra una decisión."
        eyebrow="Control académico"
        title="Revisión de estructura"
      />
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
