import { BankList } from '@/components/assessments/authoring-forms';
import { QuestionBankCreateDialog } from '@/components/assessments/question-bank-create-dialog';
import { PageHeader } from '@/components/platform/page-header';
import { getQuestionBanks } from '@/lib/assessments/server';

export default async function QuestionBanksPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getQuestionBanks(slug);
  const canManage = data.access.capabilities.includes('assessment.bank.manage');
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={canManage ? <QuestionBankCreateDialog slug={slug} /> : null}
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: 'Bancos' },
        ]}
        description="Organiza y reutiliza preguntas aprobadas en distintas evaluaciones."
        eyebrow="Evaluaciones"
        title="Bancos de preguntas"
      />
      <BankList banks={data.banks} slug={slug} />
    </main>
  );
}
