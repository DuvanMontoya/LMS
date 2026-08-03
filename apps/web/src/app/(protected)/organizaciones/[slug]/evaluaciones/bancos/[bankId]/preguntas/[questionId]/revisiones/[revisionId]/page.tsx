import { QuestionRevisionWorkflow } from '@/components/assessments/authoring-forms';
import { QuestionRevisionPreview } from '@/components/assessments/question-preview-dialog';
import { QuestionStudio } from '@/components/assessments/question-studio';
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
  const editable =
    capabilities.includes('assessment.question.manage') &&
    ['draft', 'changes_requested'].includes(data.revision.status);
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
      {editable ? (
        <>
          <QuestionStudio
            bankId={bankId}
            initialRevision={{
              code: data.question.code,
              definition: data.revision.definition,
              id: data.revision.id,
              lockVersion: data.revision.lock_version,
              questionId,
              status: data.revision.status,
              type: data.revision.type,
            }}
            slug={slug}
          />
          <QuestionRevisionWorkflow
            bankId={bankId}
            canApprove={capabilities.includes('assessment.question.approve')}
            canReview={capabilities.includes('assessment.question.review')}
            canSubmit={capabilities.includes('assessment.question.submit')}
            questionId={questionId}
            revision={data.revision}
            slug={slug}
          />
        </>
      ) : (
        <>
          <QuestionRevisionPreview
            bankId={bankId}
            code={data.question.code}
            questionId={questionId}
            slug={slug}
          />
          <QuestionRevisionWorkflow
            bankId={bankId}
            canApprove={capabilities.includes('assessment.question.approve')}
            canReview={capabilities.includes('assessment.question.review')}
            canSubmit={capabilities.includes('assessment.question.submit')}
            questionId={questionId}
            revision={data.revision}
            slug={slug}
          />
        </>
      )}
    </main>
  );
}
