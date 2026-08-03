import { Send } from 'lucide-react';
import Link from 'next/link';

import { AssessmentComposer } from '@/components/assessments/assessment-composer';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { getAssessmentWorkspace } from '@/lib/assessments/server';

export default async function AssessmentWorkspacePage({
  params,
}: Readonly<{ params: Promise<{ assessmentSlug: string; slug: string }> }>) {
  const { assessmentSlug, slug } = await params;
  const data = await getAssessmentWorkspace(slug, assessmentSlug);
  const capabilities = data.access.capabilities;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          capabilities.includes('assessment.delivery.view') ? (
            <Button asChild size="sm" variant="outline">
              <Link href={`/organizaciones/${slug}/evaluaciones/entregas`}>
                <Send data-icon="inline-start" /> Ir a entregas
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: data.assessment.title },
        ]}
        description="Configura objetivos, secciones, preguntas fijadas y el workflow de aprobación."
        eyebrow="Compositor de evaluación"
        title={data.assessment.title}
      />
      <AssessmentComposer
        assessmentSlug={assessmentSlug}
        canApprove={capabilities.includes('assessment.authoring.approve')}
        canManage={capabilities.includes('assessment.authoring.manage')}
        canReview={capabilities.includes('assessment.authoring.review')}
        canSubmit={capabilities.includes('assessment.authoring.submit')}
        objectives={data.objectives}
        outline={data.outline}
        pools={data.pools}
        questions={data.questions}
        readiness={data.readiness}
        slug={slug}
        subjects={data.subjects}
      />
    </main>
  );
}
