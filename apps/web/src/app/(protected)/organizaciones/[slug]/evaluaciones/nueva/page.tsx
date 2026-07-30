import { AssessmentCreateForm } from '@/components/assessments/authoring-forms';
import { PageHeader } from '@/components/platform/page-header';
import { getAssessmentCreationContext } from '@/lib/assessments/server';

export default async function NewAssessmentPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAssessmentCreationContext(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: 'Nueva' },
        ]}
        description="Crea la identidad y primera revisión editable del instrumento."
        eyebrow="Assessment authoring"
        title="Nueva evaluación"
      />
      <AssessmentCreateForm slug={slug} />
    </main>
  );
}
