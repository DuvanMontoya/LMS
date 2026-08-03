import { notFound } from 'next/navigation';

import { QuestionStudio } from '@/components/assessments/question-studio';
import { PageHeader } from '@/components/platform/page-header';
import { getQuestionBank } from '@/lib/assessments/server';

export default async function NewQuestionPage({
  params,
}: Readonly<{ params: Promise<{ bankId: string; slug: string }> }>) {
  const { bankId, slug } = await params;
  const data = await getQuestionBank(slug, bankId);
  if (!data.access.capabilities.includes('assessment.question.manage')) {
    notFound();
  }
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/evaluaciones/bancos`,
            label: 'Bancos',
          },
          {
            href: `/organizaciones/${slug}/evaluaciones/bancos/${bankId}`,
            label: data.bank.name,
          },
          { label: 'Nueva pregunta' },
        ]}
        description="Redacta el enunciado, define la respuesta y documenta la solución."
        eyebrow="Autoría"
        title="Nueva pregunta"
      />
      <QuestionStudio bankId={bankId} slug={slug} />
    </main>
  );
}
