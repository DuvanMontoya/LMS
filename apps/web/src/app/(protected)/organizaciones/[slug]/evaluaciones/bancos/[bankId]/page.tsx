import {
  QuestionCreateForm,
  QuestionBankSettingsForm,
  QuestionList,
} from '@/components/assessments/authoring-forms';
import { PageHeader } from '@/components/platform/page-header';
import { getQuestionBank } from '@/lib/assessments/server';

export default async function QuestionBankPage({
  params,
}: Readonly<{ params: Promise<{ bankId: string; slug: string }> }>) {
  const { bankId, slug } = await params;
  const data = await getQuestionBank(slug, bankId);
  const canManage = data.access.capabilities.includes(
    'assessment.question.manage',
  );
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/bancos`,
            label: 'Bancos',
          },
          { label: data.bank.name },
        ]}
        description={data.bank.description}
        eyebrow="Banco de preguntas"
        title={data.bank.name}
      />
      {canManage ? (
        <>
          <QuestionBankSettingsForm bank={data.bank} slug={slug} />
          <QuestionCreateForm bankId={bankId} slug={slug} />
        </>
      ) : null}
      <QuestionList bankId={bankId} questions={data.questions} slug={slug} />
    </main>
  );
}
