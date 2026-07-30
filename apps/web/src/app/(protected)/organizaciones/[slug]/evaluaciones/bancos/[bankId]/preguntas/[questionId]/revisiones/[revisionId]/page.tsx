import { QuestionRevisionEditor } from '@/components/assessments/authoring-forms';
import { PageHeader } from '@/components/platform/page-header';
import { getQuestionRevision } from '@/lib/assessments/server';

export default async function QuestionRevisionPage({
  params,
}: Readonly<{
  params: Promise<{
    bankId: string;
    questionId: string;
    revisionId: string;
    slug: string;
  }>;
}>) {
  const { bankId, questionId, revisionId, slug } = await params;
  const data = await getQuestionRevision(slug, bankId, questionId, revisionId);
  const capabilities = data.access.capabilities;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/bancos/${bankId}`,
            label: 'Banco',
          },
          { label: `Revisión ${data.revision.number}` },
        ]}
        description="Inspecciona la experiencia pública, valida el contrato semántico y gobierna la revisión antes de crear una versión."
        eyebrow="Pregunta versionada"
        title={`Revisión ${data.revision.number}`}
      />
      <QuestionRevisionEditor
        bankId={bankId}
        canApprove={capabilities.includes('assessment.question.approve')}
        canManage={capabilities.includes('assessment.question.manage')}
        canReview={capabilities.includes('assessment.question.review')}
        canSubmit={capabilities.includes('assessment.question.submit')}
        questionId={questionId}
        revision={data.revision}
        slug={slug}
      />
    </main>
  );
}
