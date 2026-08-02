import { CircleHelp } from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { StructureEditor } from '@/components/courses/structure-editor';
import { Button } from '@/components/ui/button';
import { getApprovedAssessmentVersionOptions } from '@/lib/assessments/server';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseStructurePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  const assessmentVersions = data.access.capabilities.includes(
    'assessment.authoring.manage',
  )
    ? await getApprovedAssessmentVersionOptions(slug)
    : [];
  return (
    <main className="academic-page">
      <PageHeader
        actions={
          <Button asChild variant="outline">
            <Link href={`/organizaciones/${slug}/ayuda`}>
              <CircleHelp />
              Ver guía de creación
            </Link>
          </Button>
        }
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
            ? 'Construye el recorrido real del estudiante: organiza módulos y ordena lecciones, clases en vivo y evaluaciones en una sola secuencia.'
            : 'Consulta el recorrido aprobado de lecciones, clases en vivo y evaluaciones de este curso.'
        }
        eyebrow={data.canAuthor ? 'Autoría estructural' : 'Curso asignado'}
        title={data.canAuthor ? 'Estructura del curso' : 'Secuencia del curso'}
      />
      <div className="mt-6">
        <StructureEditor
          assessmentVersions={assessmentVersions}
          canManageAssessments={data.access.capabilities.includes(
            'assessment.authoring.manage',
          )}
          canManage={data.access.capabilities.includes(
            'course.authoring.manage',
          )}
          courseSlug={courseSlug}
          key={data.outline.revision.lock_version}
          objectives={data.unitObjectives}
          outline={data.outline}
          slug={slug}
          topics={data.topics}
        />
      </div>
    </main>
  );
}
