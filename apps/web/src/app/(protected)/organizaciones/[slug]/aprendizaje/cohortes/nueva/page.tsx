import { CohortCreateForm } from '@/components/learning/learning-admin-forms';
import { PageHeader } from '@/components/platform/page-header';
import { getLearningAdminOptions } from '@/lib/learning/server';
import { notFound } from 'next/navigation';

export default async function NewCohortPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getLearningAdminOptions(slug);
  if (!data.access.capabilities.includes('learning.cohort.manage')) notFound();
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/aprendizaje/cohortes`,
            label: 'Secciones',
          },
          { label: 'Nueva' },
        ]}
        description="Selecciona curso, release, grupo académico y equipo docente antes de sincronizar el padrón."
        eyebrow="Aprendizaje"
        title="Nueva sección"
      />
      <CohortCreateForm
        academicGroups={data.options.academicGroups}
        academicPeriods={data.options.academicPeriods}
        courses={data.options.courses}
        slug={slug}
      />
    </main>
  );
}
