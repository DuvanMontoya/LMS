import { PageHeader } from '@/components/platform/page-header';
import { StructureEditor } from '@/components/courses/structure-editor';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseStructurePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
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
        description="Organiza módulos y unidades, y accede al contenido académico semántico de cada unidad."
        eyebrow="Autoría estructural"
        title="Estructura del curso"
      />
      <div className="mt-6">
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
