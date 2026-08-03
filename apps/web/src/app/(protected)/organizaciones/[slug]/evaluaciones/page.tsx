import { LibraryBig, Plus } from 'lucide-react';
import Link from 'next/link';

import { AssessmentPortfolio } from '@/components/assessments/assessment-portfolio';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import { getAssessments } from '@/lib/assessments/server';

export default async function AssessmentsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAssessments(slug);
  const canManage = data.access.capabilities.includes(
    'assessment.authoring.manage',
  );
  const canViewBanks =
    data.access.capabilities.includes('assessment.bank.view') ||
    data.access.capabilities.includes('assessment.question.view');
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          <div className="flex gap-2">
            {canViewBanks ? (
              <Button asChild size="sm" variant="outline">
                <Link href={`/organizaciones/${slug}/evaluaciones/bancos`}>
                  <LibraryBig data-icon="inline-start" /> Bancos
                </Link>
              </Button>
            ) : null}
            {canManage ? (
              <Button asChild size="sm">
                <Link href={`/organizaciones/${slug}/evaluaciones/nueva`}>
                  <Plus data-icon="inline-start" /> Nueva evaluación
                </Link>
              </Button>
            ) : null}
          </div>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Evaluaciones' },
        ]}
        description="Diseña instrumentos trazables, gobierna su revisión editorial y fija versiones inmutables antes de entregarlas."
        eyebrow="Centro de evaluación"
        title="Evaluaciones"
      />
      <AssessmentPortfolio assessments={data.assessments.results} slug={slug} />
    </main>
  );
}
