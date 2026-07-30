import { DeliveryManager } from '@/components/assessments/delivery-manager';
import { PageHeader } from '@/components/platform/page-header';
import { getAssessmentDeliveries } from '@/lib/assessments/server';

export default async function AssessmentDeliveriesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAssessmentDeliveries(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Entregas de evaluaciones' },
        ]}
        description="Fija una versión aprobada, define la ventana y asigna únicamente matrículas con release efectivo."
        eyebrow="Assessment delivery"
        title="Entregas de evaluaciones"
      />
      <DeliveryManager
        canManage={data.canManage}
        deliveries={data.deliveries}
        enrollments={data.enrollments}
        releaseOptions={data.releaseOptions}
        slug={slug}
        versions={data.versions}
      />
    </main>
  );
}
