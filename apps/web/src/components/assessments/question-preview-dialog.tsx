'use client';

import { useQuery } from '@tanstack/react-query';
import { Eye, LoaderCircle } from 'lucide-react';
import { useState } from 'react';

import { AcademicAsset } from '@/components/content/academic-asset';
import { AcademicDocument } from '@/components/content/academic-document';
import { LatexText } from '@/components/content/latex-text';
import { MathJaxFormula } from '@/components/content/mathjax-formula';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { apiErrorMessage } from '@/lib/api/api-error';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { AssetAccessDescriptor } from '@/lib/assets/api';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';

type QuestionPreview = components['schemas']['QuestionPreview'];
type OptionMedia = {
  alt_text: string;
  asset_version_id: string;
  caption?: string;
  kind: 'image';
  long_description?: string;
};
type Option = {
  id: string;
  label: string;
  math_latex?: string;
  media?: OptionMedia;
};
type PublicQuestion = {
  false_label?: string;
  left?: Option[];
  options?: Option[];
  prompt: LMSUnitAcademicDocumentVersion2;
  response_placeholder?: string;
  right?: Option[];
  true_label?: string;
  type: string;
  unit?: string;
};

async function getPreview(
  slug: string,
  bankId: string,
  questionId: string,
): Promise<QuestionPreview> {
  const { data, error, response } = await platformBrowserClient.GET(
    '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/preview/',
    { params: { path: { bank_id: bankId, question_id: questionId, slug } } },
  );
  if (!response.ok || !data) {
    throw new Error(
      apiErrorMessage(error, 'No fue posible previsualizar la pregunta.'),
    );
  }
  return data;
}

export function QuestionPreviewDialog({
  bankId,
  code,
  questionId,
  slug,
}: Readonly<{
  bankId: string;
  code: string;
  questionId: string;
  slug: string;
}>) {
  const [open, setOpen] = useState(false);
  const query = useQuery({
    enabled: open,
    queryFn: () => getPreview(slug, bankId, questionId),
    queryKey: ['assessment-question-preview', slug, bankId, questionId],
    staleTime: 30_000,
  });
  const publicQuestion = query.data?.public as PublicQuestion | undefined;
  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button
          aria-label={`Previsualizar ${code}`}
          size="icon-sm"
          type="button"
          variant="ghost"
        >
          <Eye />
        </Button>
      </DialogTrigger>
      <DialogContent className="assessment-question-preview-dialog max-h-[92vh] overflow-y-auto sm:max-w-5xl">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <DialogTitle>{query.data?.code ?? code}</DialogTitle>
            {query.data ? (
              <Badge variant="outline">
                {questionTypeLabel(query.data.type)}
              </Badge>
            ) : null}
          </div>
          <DialogDescription>
            Vista fiel del contenido público que recibe el estudiante; no
            incluye claves ni rúbricas privadas.
          </DialogDescription>
        </DialogHeader>
        {query.isPending ? (
          <div className="assessment-question-preview-dialog__loading">
            <LoaderCircle className="animate-spin" /> Preparando pregunta…
          </div>
        ) : null}
        {query.error ? (
          <p className="assessment-error" role="alert">
            {query.error.message}
          </p>
        ) : null}
        {publicQuestion ? (
          <div className="assessment-question-preview-dialog__surface">
            <div className="assessment-question-preview-dialog__prompt">
              <AcademicDocument
                assets={(query.data?.assets ?? []) as AssetAccessDescriptor[]}
                document={publicQuestion.prompt}
              />
            </div>
            <ResponsePreview
              assets={(query.data?.assets ?? []) as AssetAccessDescriptor[]}
              question={publicQuestion}
            />
          </div>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

export function QuestionRevisionPreview({
  bankId,
  code,
  questionId,
  slug,
}: Readonly<{
  bankId: string;
  code: string;
  questionId: string;
  slug: string;
}>) {
  const query = useQuery({
    queryFn: () => getPreview(slug, bankId, questionId),
    queryKey: ['assessment-question-preview', slug, bankId, questionId],
    staleTime: 30_000,
  });
  const publicQuestion = query.data?.public as PublicQuestion | undefined;
  return (
    <section className="assessment-question-review">
      <header>
        <div>
          <p>Vista pública</p>
          <h2>{query.data?.code ?? code}</h2>
        </div>
        {query.data ? (
          <Badge variant="outline">{questionTypeLabel(query.data.type)}</Badge>
        ) : null}
      </header>
      {query.isPending ? (
        <div className="assessment-question-preview-dialog__loading">
          <LoaderCircle className="animate-spin" /> Preparando pregunta…
        </div>
      ) : null}
      {query.error ? (
        <p className="assessment-error" role="alert">
          {query.error.message}
        </p>
      ) : null}
      {publicQuestion ? (
        <div className="assessment-question-preview-dialog__surface">
          <div className="assessment-question-preview-dialog__prompt">
            <AcademicDocument
              assets={(query.data?.assets ?? []) as AssetAccessDescriptor[]}
              document={publicQuestion.prompt}
            />
          </div>
          <ResponsePreview
            assets={(query.data?.assets ?? []) as AssetAccessDescriptor[]}
            question={publicQuestion}
          />
        </div>
      ) : null}
    </section>
  );
}

function ResponsePreview({
  assets,
  question,
}: Readonly<{
  assets: readonly AssetAccessDescriptor[];
  question: PublicQuestion;
}>) {
  if (
    ['single_choice', 'multiple_choice', 'ordering'].includes(question.type)
  ) {
    return (
      <ol className="assessment-question-preview-dialog__options">
        {question.options?.map((option, index) => (
          <li key={option.id}>
            <span>{String.fromCharCode(65 + index)}</span>
            <div>
              <LatexText value={option.label} />
              {option.math_latex ? (
                <MathJaxFormula latex={option.math_latex} />
              ) : null}
              <OptionMedia
                assets={assets}
                {...(option.media ? { media: option.media } : {})}
              />
            </div>
          </li>
        ))}
      </ol>
    );
  }
  if (question.type === 'true_false') {
    return (
      <div className="assessment-question-preview-dialog__binary">
        <span>{question.true_label ?? 'Verdadero'}</span>
        <span>{question.false_label ?? 'Falso'}</span>
      </div>
    );
  }
  if (question.type === 'matching') {
    return (
      <div className="assessment-question-preview-dialog__matching">
        <div>
          {question.left?.map((item) => (
            <div key={item.id}>
              <LatexText value={item.label} />
              {item.math_latex ? (
                <MathJaxFormula latex={item.math_latex} />
              ) : null}
              <OptionMedia
                assets={assets}
                {...(item.media ? { media: item.media } : {})}
              />
            </div>
          ))}
        </div>
        <div>
          {question.right?.map((item) => (
            <div key={item.id}>
              <LatexText value={item.label} />
              {item.math_latex ? (
                <MathJaxFormula latex={item.math_latex} />
              ) : null}
              <OptionMedia
                assets={assets}
                {...(item.media ? { media: item.media } : {})}
              />
            </div>
          ))}
        </div>
      </div>
    );
  }
  return (
    <div className="assessment-question-preview-dialog__answer">
      {question.response_placeholder ??
        (question.type === 'mathematical_expression'
          ? 'El estudiante escribe una expresión matemática.'
          : 'El estudiante escribe su respuesta.')}
      {question.unit ? <span>Unidad esperada: {question.unit}</span> : null}
    </div>
  );
}

function OptionMedia({
  assets,
  media,
}: Readonly<{
  assets: readonly AssetAccessDescriptor[];
  media?: OptionMedia;
}>) {
  if (!media) return null;
  const descriptor = assets.find(
    (item) => item.asset_version_id === media.asset_version_id,
  );
  return (
    <div className="assessment-question-preview-dialog__media">
      <AcademicAsset
        attrs={{
          altText: media.alt_text,
          assetVersionId: media.asset_version_id,
          caption: media.caption ?? '',
          decorative: false,
        }}
        {...(descriptor ? { descriptor } : {})}
        kind="image"
      />
      {media.long_description ? <p>{media.long_description}</p> : null}
    </div>
  );
}

function questionTypeLabel(type: string) {
  return (
    {
      matching: 'Correspondencia',
      long_text: 'Respuesta abierta',
      mathematical_expression: 'Expresión matemática',
      multiple_choice: 'Selección múltiple',
      numeric: 'Respuesta numérica',
      ordering: 'Ordenamiento',
      single_choice: 'Selección única',
      short_text: 'Respuesta corta',
      true_false: 'Verdadero o falso',
    }[type] ?? type
  );
}
