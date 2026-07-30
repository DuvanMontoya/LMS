import { LearnerDeliveryList } from '@/components/assessments/learner-deliveries';
import { PageHeader } from '@/components/platform/page-header';
import { getMyAssessmentDeliveries } from '@/lib/assessments/server';

export default async function AssignedAssessmentsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getMyAssessmentDeliveries(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Mis evaluaciones' },
        ]}
        description="Intentos disponibles para tu matrícula y release actualmente asignado."
        eyebrow="Experiencia del estudiante"
        title="Mis evaluaciones"
      />
      <LearnerDeliveryList deliveries={data.deliveries} slug={slug} />
    </main>
  );
}
