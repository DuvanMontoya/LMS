import { PageHeader } from '@/components/platform/page-header';
import { StructureEditor } from '@/components/courses/structure-editor';
import { getApprovedAssessmentVersionOptions } from '@/lib/assessments/server';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseStructurePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  const assessmentVersions = data.access.capabilities.includes(
    'assessment.authoring.view',
  )
    ? await getApprovedAssessmentVersionOptions(slug)
    : [];
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          {
            href: `/organizaciones/${slug}/cursos/${courseSlug}`,
            label: data.revision.title,
          },
          { label: 'Estructura' },
        ]}
        description={
          data.canAuthor
            ? 'Ordena una sola secuencia de lecciones, clases en vivo y evaluaciones, con sus políticas académicas y bindings operativos.'
            : 'Consulta la secuencia aprobada de lecciones, clases en vivo y evaluaciones de este curso.'
        }
        eyebrow={data.canAuthor ? 'Autoría estructural' : 'Curso asignado'}
        title={data.canAuthor ? 'Estructura del curso' : 'Secuencia del curso'}
      />
      <div className="mt-6">
        <StructureEditor
          assessmentVersions={assessmentVersions}
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
