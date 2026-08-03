import { Plus } from 'lucide-react';
import Link from 'next/link';

import {
  QuestionBankSettingsForm,
  QuestionList,
} from '@/components/assessments/authoring-forms';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
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
        actions={
          canManage ? (
            <Button asChild size="sm">
              <Link
                href={`/organizaciones/${slug}/evaluaciones/bancos/${bankId}/preguntas/nueva`}
              >
                <Plus data-icon="inline-start" /> Nueva pregunta
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/bancos`,
            label: 'Bancos',
          },
          { label: data.bank.name },
        ]}
        description={
          data.bank.description ||
          'Colección institucional de preguntas versionadas y reutilizables.'
        }
        eyebrow="Banco de preguntas"
        title={data.bank.name}
      />
      <QuestionList bankId={bankId} questions={data.questions} slug={slug} />
      {canManage ? (
        <QuestionBankSettingsForm bank={data.bank} slug={slug} />
      ) : null}
    </main>
  );
}
