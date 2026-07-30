import {
  BankList,
  QuestionBankCreateForm,
} from '@/components/assessments/authoring-forms';
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
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones`,
            label: 'Evaluaciones',
          },
          { label: 'Bancos' },
        ]}
        description="Preguntas con código estable, revisión editorial y versiones inmutables."
        eyebrow="Banco institucional"
        title="Bancos de preguntas"
      />
      {canManage ? <QuestionBankCreateForm slug={slug} /> : null}
      <BankList banks={data.banks} slug={slug} />
    </main>
  );
}
