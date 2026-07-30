'use client';

import { ArrowDown, ArrowUp, CheckCircle2, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { AcademicDocument } from '@/components/content/academic-document';
import { MutationError } from '@/components/assessments/authoring-forms';
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
import type { LMSUnitAcademicDocumentVersion1 } from '@/lib/content/generated/unit-document-v1';

type Option = { id: string; label: string };
type PublicQuestion = {
  false_label?: string;
  left?: Option[];
  options?: Option[];
  prompt: LMSUnitAcademicDocumentVersion1;
  response_placeholder?: string;
  right?: Option[];
  schema_version: 1;
  true_label?: string;
  type: string;
  unit?: string;
};
type Answer = boolean | null | string | string[] | Record<string, string>;

export function AttemptRunner({
  initialAttempt,
  slug,
}: Readonly<{ initialAttempt: AssessmentAttempt; slug: string }>) {
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
  const active = attempt.items[activeIndex];
  const seconds = useRemainingSeconds(attempt.expires_at);

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
    <div className="assessment-attempt-workspace">
      <aside className="assessment-attempt-sidebar">
        <div
          aria-atomic="true"
          aria-live={
            seconds !== null && seconds !== undefined && seconds < 300
              ? 'assertive'
              : 'polite'
          }
          className="assessment-attempt-timer"
          role="timer"
        >
          <span className="text-xs text-muted-foreground">Tiempo restante</span>
          <strong className="mt-1 block tabular-nums">
            {seconds === undefined
              ? 'Calculando…'
              : seconds === null
                ? 'Sin límite'
                : formatDuration(seconds)}
          </strong>
        </div>
        <nav
          aria-label="Navegador de preguntas"
          className="assessment-attempt-navigator"
        >
          <ol className="grid grid-cols-4 gap-2 lg:grid-cols-3">
            {attempt.items.map((item, index) => (
              <li key={item.id}>
                <Button
                  aria-current={index === activeIndex ? 'step' : undefined}
                  aria-label={`Pregunta ${index + 1}${saved[item.id] || item.response ? ', guardada' : ''}`}
                  className="w-full"
                  onClick={() => setActiveIndex(index)}
                  size="sm"
                  type="button"
                  variant={index === activeIndex ? 'default' : 'outline'}
                >
                  {index + 1}
                </Button>
              </li>
            ))}
          </ol>
        </nav>
        <Button
          className="mt-5 w-full"
          disabled={submit.isPending || save.isPending}
          onClick={async () => {
            if (!confirming) {
              setConfirming(true);
              return;
            }
            try {
              await submit.mutateAsync(undefined);
              router.push(
                `/organizaciones/${slug}/evaluaciones/intentos/${attempt.id}/resultado`,
              );
              router.refresh();
            } catch {
              // React Query presenta el error sin abandonar el intento.
            }
          }}
          type="button"
          variant={confirming ? 'destructive' : 'outline'}
        >
          {confirming ? 'Confirmar envío definitivo' : 'Enviar intento'}
        </Button>
        {confirming ? (
          <Button
            className="mt-2 w-full"
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
      {active ? (
        <QuestionPanel
          answer={answers[active.id]}
          index={activeIndex}
          item={active}
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
          savePending={save.isPending}
          saved={Boolean(saved[active.id] || active.response)}
          total={attempt.items.length}
        />
      ) : null}
    </div>
  );
}

function QuestionPanel({
  answer,
  index,
  item,
  onAnswer,
  onNext,
  onPrevious,
  onSave,
  savePending,
  saved,
  total,
}: Readonly<{
  answer: Answer | undefined;
  index: number;
  item: AssessmentAttempt['items'][number];
  onAnswer: (answer: Answer) => void;
  onNext: () => void;
  onPrevious: () => void;
  onSave: () => Promise<void>;
  savePending: boolean;
  saved: boolean;
  total: number;
}>) {
  const question = item.public_snapshot as PublicQuestion;
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
        <div className="flex items-center gap-2">
          <Badge variant="outline">{item.points} puntos</Badge>
          {saved ? (
            <Badge variant="secondary">
              <CheckCircle2 className="size-3" /> Guardada
            </Badge>
          ) : null}
        </div>
      </header>
      <div className="assessment-question-panel__prompt">
        <AcademicDocument document={question.prompt} />
      </div>
      <ResponseControl
        answer={answer}
        itemId={item.id}
        onAnswer={onAnswer}
        question={question}
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
          disabled={savePending}
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
  itemId,
  onAnswer,
  question,
}: Readonly<{
  answer: Answer | undefined;
  itemId: string;
  onAnswer: (answer: Answer) => void;
  question: PublicQuestion;
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
            <span>{option.label}</span>
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
            <span>{option.label}</span>
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
                <span className="min-w-0 flex-1">{option?.label ?? id}</span>
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
    const pairs =
      answer && typeof answer === 'object' && !Array.isArray(answer)
        ? answer
        : {};
    return (
      <fieldset className="mt-6 grid gap-3">
        <legend className="font-semibold">{legend}</legend>
        {question.left?.map((left) => {
          return (
            <div
              className="grid gap-2 border p-3 sm:grid-cols-2 sm:items-center"
              key={left.id}
            >
              <Label htmlFor={`match-${itemId}-${left.id}`}>{left.label}</Label>
              <select
                className="h-9 border bg-background px-3 text-sm"
                id={`match-${itemId}-${left.id}`}
                onChange={(event) =>
                  onAnswer(
                    Object.fromEntries(
                      Object.entries({
                        ...pairs,
                        [left.id]: event.target.value,
                      }).filter(([, value]) => value),
                    ),
                  )
                }
                value={pairs[left.id] ?? ''}
              >
                <option value="">Selecciona la correspondencia</option>
                {question.right?.map((right) => (
                  <option key={right.id} value={right.id}>
                    {right.label}
                  </option>
                ))}
              </select>
            </div>
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
        Object.values(value).every((item) => typeof item === 'string'))
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
