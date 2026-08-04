'use client';

import {
  ArrowDown,
  ArrowUp,
  CheckCircle2,
  Flag,
  PanelRightClose,
  PanelRightOpen,
  Save,
  Send,
  Timer,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';

import { AcademicDocument } from '@/components/content/academic-document';
import { AcademicAsset } from '@/components/content/academic-asset';
import { MathJaxFormula } from '@/components/content/mathjax-formula';
import { LatexText } from '@/components/content/latex-text';
import { MutationError } from '@/components/assessments/authoring-forms';
import {
  MathExpressionField,
  type MathExpressionValidationState,
  type MathExpressionValue,
} from '@/components/assessments/math-expression-field';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  saveAssessmentResponse,
  submitAssessmentAttempt,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { AssessmentAttempt } from '@/lib/assessments/server';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';
import type { AssetAccessDescriptor } from '@/lib/assets/api';

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
  allowed_functions?: string[];
  allowed_symbols?: string[];
  false_label?: string;
  left?: Option[];
  options?: Option[];
  prompt: LMSUnitAcademicDocumentVersion2;
  response_placeholder?: string;
  right?: Option[];
  schema_version: 1;
  true_label?: string;
  type: string;
  unit?: string;
};
type Answer =
  | boolean
  | null
  | string
  | string[]
  | Record<string, string>
  | MathExpressionValue;

export function AssessmentAttemptTimer({
  expiresAt,
}: Readonly<{ expiresAt: string | null }>) {
  const seconds = useRemainingSeconds(expiresAt);
  return (
    <div
      aria-atomic="true"
      aria-live={
        seconds !== null && seconds !== undefined && seconds < 300
          ? 'assertive'
          : 'polite'
      }
      className="assessment-header-timer"
      role="timer"
    >
      <Timer />
      <span>Tiempo</span>
      <strong>
        {seconds === undefined
          ? 'Calculando…'
          : seconds === null
            ? 'Sin límite'
            : formatDuration(seconds)}
      </strong>
    </div>
  );
}

export function AttemptRunner({
  initialAttempt,
  returnHref,
  slug,
}: Readonly<{
  initialAttempt: AssessmentAttempt;
  returnHref?: string | undefined;
  slug: string;
}>) {
  const router = useRouter();
  const [attempt, setAttempt] = useState(initialAttempt);
  const [activeIndex, setActiveIndex] = useState(0);
  const [answers, setAnswers] = useState<Record<string, Answer>>(() =>
    Object.fromEntries(
      initialAttempt.items.map((item) => [
        item.id,
        answerFrom(item.public_snapshot as PublicQuestion, item.response),
      ]),
    ),
  );
  const [saved, setSaved] = useState<Record<string, boolean>>({});
  const [marked, setMarked] = useState<Record<string, boolean>>({});
  const [navigatorCollapsed, setNavigatorCollapsed] = useState(false);
  useEffect(() => {
    const compactViewport = window.matchMedia('(max-width: 1023px)');
    const synchronize = () => setNavigatorCollapsed(compactViewport.matches);
    synchronize();
    compactViewport.addEventListener('change', synchronize);
    return () => compactViewport.removeEventListener('change', synchronize);
  }, []);
  const [confirming, setConfirming] = useState(false);
  const save = useAssessmentMutation(
    ({ itemId, response }: { itemId: string; response: unknown }) =>
      saveAssessmentResponse(slug, attempt.id, itemId, {
        expected_version: attempt.lock_version,
        response,
      }),
  );
  const submit = useAssessmentMutation(() =>
    submitAssessmentAttempt(slug, attempt.id, attempt.lock_version),
  );
  const submitRef = useRef(submit);
  const active = attempt.items[activeIndex];
  const answeredCount = attempt.items.filter(
    (item) => saved[item.id] || item.response,
  ).length;
  const resultHref =
    returnHref ??
    `/organizaciones/${slug}/evaluaciones/intentos/${attempt.id}/resultado`;

  useEffect(() => {
    submitRef.current = submit;
  }, [submit]);

  useEffect(() => {
    if (attempt.status !== 'in_progress' || !attempt.expires_at) return;
    const remaining = new Date(attempt.expires_at).getTime() - Date.now();
    const timer = window.setTimeout(
      () => {
        void submitRef.current
          .mutateAsync(undefined)
          .then(() => {
            router.replace(resultHref);
            router.refresh();
          })
          .catch(() => undefined);
      },
      Math.max(0, Math.min(remaining, 2_147_483_647)),
    );
    return () => window.clearTimeout(timer);
  }, [attempt.expires_at, attempt.status, resultHref, router]);

  async function saveItem(itemId: string, question: PublicQuestion) {
    try {
      const updated = await save.mutateAsync({
        itemId,
        response: {
          schema_version: 1,
          type: question.type,
          value: answers[itemId] ?? null,
        },
      });
      setAttempt(updated as AssessmentAttempt);
      setSaved((current) => ({ ...current, [itemId]: true }));
    } catch {
      // React Query presenta el error y conserva la respuesta local.
    }
  }

  if (attempt.status !== 'in_progress') {
    router.replace(
      `/organizaciones/${slug}/evaluaciones/intentos/${attempt.id}/resultado`,
    );
    return null;
  }

  return (
    <div
      className="assessment-attempt-workspace"
      data-navigator-collapsed={navigatorCollapsed}
    >
      {active ? (
        <QuestionPanel
          answer={answers[active.id]}
          assets={attempt.assets ?? []}
          attemptId={attempt.id}
          index={activeIndex}
          item={active}
          key={active.id}
          marked={Boolean(marked[active.id])}
          onAnswer={(answer) => {
            setAnswers((current) => ({ ...current, [active.id]: answer }));
            setSaved((current) => ({ ...current, [active.id]: false }));
          }}
          onNext={() =>
            setActiveIndex((current) =>
              Math.min(attempt.items.length - 1, current + 1),
            )
          }
          onPrevious={() =>
            setActiveIndex((current) => Math.max(0, current - 1))
          }
          onSave={() =>
            saveItem(active.id, active.public_snapshot as PublicQuestion)
          }
          onToggleMarked={() =>
            setMarked((current) => ({
              ...current,
              [active.id]: !current[active.id],
            }))
          }
          savePending={save.isPending}
          saved={Boolean(saved[active.id] || active.response)}
          slug={slug}
          total={attempt.items.length}
        />
      ) : null}
      <aside className="assessment-attempt-sidebar">
        <header>
          <div>
            <span>Navegador</span>
            <strong>
              {answeredCount} de {attempt.items.length} guardadas
            </strong>
          </div>
          <Button
            aria-label={
              navigatorCollapsed
                ? 'Expandir navegador de preguntas'
                : 'Compactar navegador de preguntas'
            }
            onClick={() => setNavigatorCollapsed((current) => !current)}
            size="icon-sm"
            type="button"
            variant="ghost"
          >
            {navigatorCollapsed ? <PanelRightOpen /> : <PanelRightClose />}
          </Button>
        </header>
        <nav
          aria-label="Navegador de preguntas"
          className="assessment-attempt-navigator"
        >
          <ol>
            {attempt.items.map((item, index) => (
              <li key={item.id}>
                <button
                  aria-current={index === activeIndex ? 'step' : undefined}
                  aria-label={`Pregunta ${index + 1}${saved[item.id] || item.response ? ', respondida' : ', pendiente'}${marked[item.id] ? ', marcada para revisar' : ''}`}
                  data-current={index === activeIndex}
                  data-marked={Boolean(marked[item.id])}
                  data-status={
                    saved[item.id] || item.response ? 'answered' : 'pending'
                  }
                  onClick={() => setActiveIndex(index)}
                  type="button"
                >
                  <span>{index + 1}</span>
                  <strong>Pregunta {index + 1}</strong>
                  {marked[item.id] ? <Flag /> : null}
                </button>
              </li>
            ))}
          </ol>
        </nav>
        <Button
          aria-label={
            confirming ? 'Confirmar envío definitivo' : 'Enviar intento'
          }
          className="assessment-attempt-sidebar__submit"
          disabled={submit.isPending || save.isPending}
          onClick={async () => {
            if (!confirming) {
              setConfirming(true);
              return;
            }
            try {
              await submit.mutateAsync(undefined);
              router.push(resultHref);
              router.refresh();
            } catch {
              // React Query presenta el error sin abandonar el intento.
            }
          }}
          type="button"
          variant={confirming ? 'destructive' : 'outline'}
        >
          <Send />
          <span>
            {confirming ? 'Confirmar envío definitivo' : 'Enviar intento'}
          </span>
        </Button>
        {confirming ? (
          <Button
            className="assessment-attempt-sidebar__continue"
            onClick={() => setConfirming(false)}
            type="button"
            variant="ghost"
          >
            Continuar revisando
          </Button>
        ) : null}
        <div className="mt-3">
          <MutationError error={save.error ?? submit.error} />
        </div>
      </aside>
    </div>
  );
}

function QuestionPanel({
  answer,
  assets,
  attemptId,
  index,
  item,
  marked,
  onAnswer,
  onNext,
  onPrevious,
  onSave,
  onToggleMarked,
  savePending,
  saved,
  slug,
  total,
}: Readonly<{
  answer: Answer | undefined;
  assets: readonly AssetAccessDescriptor[];
  attemptId: string;
  index: number;
  item: AssessmentAttempt['items'][number];
  marked: boolean;
  onAnswer: (answer: Answer) => void;
  onNext: () => void;
  onPrevious: () => void;
  onSave: () => Promise<void>;
  onToggleMarked: () => void;
  savePending: boolean;
  saved: boolean;
  slug: string;
  total: number;
}>) {
  const question = item.public_snapshot as PublicQuestion;
  const [mathValidationState, setMathValidationState] =
    useState<MathExpressionValidationState>(
      question.type === 'mathematical_expression' && answer ? 'valid' : 'idle',
    );

  const mathResponseBlocked =
    question.type === 'mathematical_expression' &&
    (mathValidationState === 'validating' || mathValidationState === 'invalid');

  return (
    <section
      aria-labelledby={`question-title-${item.id}`}
      className="assessment-question-panel"
    >
      <header className="assessment-question-panel__header">
        <div>
          <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
            Pregunta {index + 1} de {total}
          </p>
          <h1 className="mt-1 font-semibold" id={`question-title-${item.id}`}>
            {item.required ? 'Respuesta obligatoria' : 'Respuesta opcional'}
          </h1>
        </div>
        <div className="assessment-question-panel__status">
          <Button
            aria-pressed={marked}
            onClick={onToggleMarked}
            size="sm"
            type="button"
            variant={marked ? 'secondary' : 'ghost'}
          >
            <Flag /> {marked ? 'Marcada para revisar' : 'Marcar para revisar'}
          </Button>
          <Badge variant="outline">{item.points} puntos</Badge>
          {saved ? (
            <Badge variant="secondary">
              <CheckCircle2 className="size-3" /> Guardada
            </Badge>
          ) : null}
        </div>
      </header>
      <div className="assessment-question-panel__prompt">
        <AcademicDocument
          assessmentRefreshContext={{ attemptId, slug }}
          assets={assets}
          document={question.prompt}
        />
      </div>
      <ResponseControl
        answer={answer}
        assets={assets}
        attemptId={attemptId}
        itemId={item.id}
        onAnswer={onAnswer}
        onMathValidationStateChange={setMathValidationState}
        question={question}
        slug={slug}
      />
      <footer className="assessment-question-panel__footer">
        <Button
          disabled={index === 0}
          onClick={onPrevious}
          type="button"
          variant="outline"
        >
          Anterior
        </Button>
        <Button
          disabled={index === total - 1}
          onClick={onNext}
          type="button"
          variant="outline"
        >
          Siguiente
        </Button>
        <Button
          className="ml-auto"
          disabled={savePending || mathResponseBlocked}
          onClick={onSave}
          type="button"
        >
          <Save data-icon="inline-start" />
          Guardar respuesta
        </Button>
      </footer>
    </section>
  );
}

function ResponseControl({
  answer,
  assets,
  attemptId,
  itemId,
  onAnswer,
  onMathValidationStateChange,
  question,
  slug,
}: Readonly<{
  answer: Answer | undefined;
  assets: readonly AssetAccessDescriptor[];
  attemptId: string;
  itemId: string;
  onAnswer: (answer: Answer) => void;
  onMathValidationStateChange: (state: MathExpressionValidationState) => void;
  question: PublicQuestion;
  slug: string;
}>) {
  const legend = `Respuesta a la pregunta`;
  if (question.type === 'single_choice') {
    return (
      <fieldset className="mt-6 grid gap-3">
        <legend className="font-semibold">{legend}</legend>
        {question.options?.map((option) => (
          <label
            className="assessment-response-option"
            data-selected={answer === option.id}
            key={option.id}
          >
            <input
              checked={answer === option.id}
              name={`answer-${itemId}`}
              onChange={() => onAnswer(option.id)}
              type="radio"
            />
            <span className="min-w-0 flex-1">
              <LatexText value={option.label} />
              {option.math_latex ? (
                <MathJaxFormula display latex={option.math_latex} />
              ) : null}
              <ChoiceMedia
                assets={assets}
                attemptId={attemptId}
                {...(option.media ? { media: option.media } : {})}
                slug={slug}
              />
            </span>
          </label>
        ))}
      </fieldset>
    );
  }
  if (question.type === 'multiple_choice') {
    const selected = Array.isArray(answer) ? answer : [];
    return (
      <fieldset className="mt-6 grid gap-3">
        <legend className="font-semibold">{legend}</legend>
        {question.options?.map((option) => (
          <label
            className="assessment-response-option"
            data-selected={selected.includes(option.id)}
            key={option.id}
          >
            <input
              checked={selected.includes(option.id)}
              onChange={(event) =>
                onAnswer(
                  event.target.checked
                    ? [...selected, option.id]
                    : selected.filter((id) => id !== option.id),
                )
              }
              type="checkbox"
            />
            <span className="min-w-0 flex-1">
              <LatexText value={option.label} />
              {option.math_latex ? (
                <MathJaxFormula display latex={option.math_latex} />
              ) : null}
              <ChoiceMedia
                assets={assets}
                attemptId={attemptId}
                {...(option.media ? { media: option.media } : {})}
                slug={slug}
              />
            </span>
          </label>
        ))}
      </fieldset>
    );
  }
  if (question.type === 'true_false') {
    return (
      <fieldset className="mt-6 flex gap-3">
        <legend className="mb-3 font-semibold">{legend}</legend>
        {[true, false].map((value) => (
          <label
            className="assessment-response-option"
            data-selected={answer === value}
            key={String(value)}
          >
            <input
              checked={answer === value}
              name={`answer-${itemId}`}
              onChange={() => onAnswer(value)}
              type="radio"
            />
            {value
              ? question.true_label || 'Verdadero'
              : question.false_label || 'Falso'}
          </label>
        ))}
      </fieldset>
    );
  }
  if (question.type === 'ordering') {
    const current =
      Array.isArray(answer) && answer.length
        ? answer
        : (question.options?.map((option) => option.id) ?? []);
    return (
      <fieldset className="mt-6">
        <legend className="font-semibold">{legend}</legend>
        <ol className="mt-3 grid gap-2">
          {current.map((id, index) => {
            const option = question.options?.find((entry) => entry.id === id);
            return (
              <li className="flex items-center gap-2 border p-3" key={id}>
                <span className="w-6 text-center font-semibold">
                  {index + 1}
                </span>
                <span className="min-w-0 flex-1">
                  <LatexText value={option?.label ?? id} />
                  {option?.math_latex ? (
                    <MathJaxFormula display latex={option.math_latex} />
                  ) : null}
                </span>
                <ChoiceMedia
                  assets={assets}
                  attemptId={attemptId}
                  {...(option?.media ? { media: option.media } : {})}
                  slug={slug}
                />
                <Button
                  aria-label={`Subir ${option?.label ?? id}`}
                  disabled={index === 0}
                  onClick={() => onAnswer(move(current, index, index - 1))}
                  size="icon-sm"
                  type="button"
                  variant="outline"
                >
                  <ArrowUp />
                </Button>
                <Button
                  aria-label={`Bajar ${option?.label ?? id}`}
                  disabled={index === current.length - 1}
                  onClick={() => onAnswer(move(current, index, index + 1))}
                  size="icon-sm"
                  type="button"
                  variant="outline"
                >
                  <ArrowDown />
                </Button>
              </li>
            );
          })}
        </ol>
      </fieldset>
    );
  }
  if (question.type === 'matching') {
    const pairs: Record<string, string> =
      answer &&
      typeof answer === 'object' &&
      !Array.isArray(answer) &&
      !('latex' in answer) &&
      Object.values(answer).every((value) => typeof value === 'string')
        ? answer
        : {};
    return (
      <fieldset className="mt-6 grid gap-3">
        <legend className="font-semibold">{legend}</legend>
        {question.left?.map((left) => {
          return (
            <fieldset
              className="grid gap-3 rounded-lg border p-3"
              key={left.id}
            >
              <legend className="px-1 font-medium">
                <LatexText value={left.label} />
                {left.math_latex ? (
                  <MathJaxFormula display latex={left.math_latex} />
                ) : null}
                <ChoiceMedia
                  assets={assets}
                  attemptId={attemptId}
                  {...(left.media ? { media: left.media } : {})}
                  slug={slug}
                />
              </legend>
              <div className="grid gap-2 sm:grid-cols-2">
                {question.right?.map((right) => (
                  <label
                    className="assessment-response-option"
                    data-selected={pairs[left.id] === right.id}
                    key={right.id}
                  >
                    <input
                      checked={pairs[left.id] === right.id}
                      name={`match-${itemId}-${left.id}`}
                      onChange={() =>
                        onAnswer({ ...pairs, [left.id]: right.id })
                      }
                      type="radio"
                    />
                    <span className="min-w-0 flex-1">
                      <LatexText value={right.label} />
                      {right.math_latex ? (
                        <MathJaxFormula display latex={right.math_latex} />
                      ) : null}
                      <ChoiceMedia
                        assets={assets}
                        attemptId={attemptId}
                        {...(right.media ? { media: right.media } : {})}
                        slug={slug}
                      />
                    </span>
                  </label>
                ))}
              </div>
            </fieldset>
          );
        })}
      </fieldset>
    );
  }
  if (question.type === 'long_text') {
    return (
      <div className="mt-6">
        <Label htmlFor={`answer-${itemId}`}>{legend}</Label>
        <Textarea
          className="mt-2 min-h-48"
          id={`answer-${itemId}`}
          onChange={(event) => onAnswer(event.target.value)}
          placeholder={question.response_placeholder}
          value={typeof answer === 'string' ? answer : ''}
        />
      </div>
    );
  }
  if (question.type === 'mathematical_expression') {
    const expression =
      answer &&
      typeof answer === 'object' &&
      !Array.isArray(answer) &&
      'latex' in answer &&
      'mathjson' in answer
        ? (answer as MathExpressionValue)
        : null;
    return (
      <div className="mt-6">
        <MathExpressionField
          allowedFunctions={question.allowed_functions ?? []}
          allowedSymbols={question.allowed_symbols ?? []}
          label={legend}
          onChange={onAnswer}
          onValidationStateChange={onMathValidationStateChange}
          value={expression}
        />
        <p className="mt-2 text-sm text-muted-foreground">
          La validación del navegador ayuda a escribir la expresión; la
          calificación se realiza de forma segura en el servidor.
        </p>
      </div>
    );
  }
  return (
    <div className="mt-6">
      <Label htmlFor={`answer-${itemId}`}>{legend}</Label>
      <div className="mt-2 flex items-center gap-2">
        <Input
          id={`answer-${itemId}`}
          inputMode={question.type === 'numeric' ? 'decimal' : 'text'}
          onChange={(event) => onAnswer(event.target.value)}
          placeholder={question.response_placeholder}
          value={typeof answer === 'string' ? answer : ''}
        />
        {question.unit ? (
          <span className="text-sm">{question.unit}</span>
        ) : null}
      </div>
    </div>
  );
}

function ChoiceMedia({
  assets,
  attemptId,
  media,
  slug,
}: Readonly<{
  assets: readonly AssetAccessDescriptor[];
  attemptId: string;
  media?: OptionMedia;
  slug: string;
}>) {
  if (!media) return null;
  const descriptor = assets.find(
    (entry) => entry.asset_version_id === media.asset_version_id,
  );
  return (
    <div className="mt-3 overflow-hidden rounded-lg border bg-background">
      <AcademicAsset
        assessmentRefreshContext={{ attemptId, slug }}
        attrs={{
          altText: media.alt_text,
          assetVersionId: media.asset_version_id,
          caption: media.caption ?? '',
          decorative: false,
        }}
        {...(descriptor ? { descriptor } : {})}
        kind="image"
      />
      {media.long_description ? (
        <p className="border-t px-4 py-3 text-sm leading-6 text-muted-foreground">
          {media.long_description}
        </p>
      ) : null}
    </div>
  );
}

function answerFrom(question: PublicQuestion, response: unknown): Answer {
  if (response && typeof response === 'object' && 'value' in response) {
    const value = (response as { value: unknown }).value;
    if (
      value === null ||
      typeof value === 'string' ||
      typeof value === 'boolean' ||
      (Array.isArray(value) &&
        value.every((item) => typeof item === 'string')) ||
      (typeof value === 'object' &&
        value !== null &&
        !Array.isArray(value) &&
        (('latex' in value &&
          typeof value.latex === 'string' &&
          'mathjson' in value) ||
          Object.values(value).every((item) => typeof item === 'string')))
    )
      return value as Answer;
  }
  if (question.type === 'ordering')
    return question.options?.map((item) => item.id) ?? [];
  return question.type === 'multiple_choice' || question.type === 'matching'
    ? question.type === 'matching'
      ? {}
      : []
    : null;
}

function move(values: string[], from: number, to: number) {
  const next = [...values];
  const [item] = next.splice(from, 1);
  if (item !== undefined) next.splice(to, 0, item);
  return next;
}

function useRemainingSeconds(expiresAt: string | null) {
  const [seconds, setSeconds] = useState<number | null | undefined>(
    expiresAt ? undefined : null,
  );
  useEffect(() => {
    if (!expiresAt) return;
    const update = () =>
      setSeconds(
        Math.max(
          0,
          Math.floor((new Date(expiresAt).getTime() - Date.now()) / 1000),
        ),
      );
    const initial = window.setTimeout(update, 0);
    const timer = window.setInterval(update, 1000);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [expiresAt]);
  return seconds;
}

function formatDuration(totalSeconds: number) {
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;
  return [hours, minutes, seconds]
    .map((value) => String(value).padStart(2, '0'))
    .join(':');
}
