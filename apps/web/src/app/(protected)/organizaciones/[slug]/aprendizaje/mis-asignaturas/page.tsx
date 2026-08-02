import { CourseTeachingExceptionsPanel } from '@/components/catalog/course-teaching-exceptions-panel';
import { TeachingResponsibilitiesPanel } from '@/components/catalog/teaching-responsibilities-panel';
import { PageHeader } from '@/components/platform/page-header';
import { getTeachingResponsibilities } from '@/lib/catalog/server';

export default async function MySubjectsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getTeachingResponsibilities(slug);
  const canManage = data.access.capabilities.includes('catalog.manage');
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Mis asignaturas' },
        ]}
        description="Una responsabilidad vincula a una persona con una asignatura del currículo; no es un curso ni concede acceso automático a grupos. Los cursos se asignan por separado."
        eyebrow="Responsabilidad docente"
        title={canManage ? 'Responsabilidades docentes' : 'Mis asignaturas'}
      />
      <TeachingResponsibilitiesPanel
        canManage={canManage}
        responsibilities={data.responsibilities}
        slug={slug}
        subjects={data.subjects}
      />
      <CourseTeachingExceptionsPanel
        canManage={canManage}
        courses={data.courses}
        exceptions={data.courseExceptions}
        slug={slug}
      />
    </main>
  );
}
