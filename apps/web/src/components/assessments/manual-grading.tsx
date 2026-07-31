'use client';

import { ClipboardCheck, History, Scale, ShieldCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { MutationError } from '@/components/assessments/authoring-forms';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  gradeAssessmentResponse,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { PendingManual } from '@/lib/assessments/server';

export function ManualGradingQueue({
  responses,
  slug,
}: Readonly<{ responses: PendingManual[]; slug: string }>) {
  if (!responses.length) {
    return (
      <section className="assessment-empty mt-6 rounded-xl border border-border bg-card shadow-[0_12px_35px_rgb(15_23_42_/_0.045)]">
        <ClipboardCheck aria-hidden="true" />
        <h2 className="mt-3 font-semibold">Cola al día</h2>
        <p>No hay respuestas abiertas pendientes de decisión manual.</p>
      </section>
    );
  }
  return (
    <ul className="assessment-grading-queue">
      {responses.map((response) => (
        <ManualGradeCard
          key={response.response_id}
          response={response}
          slug={slug}
        />
      ))}
    </ul>
  );
}

function ManualGradeCard({
  response,
  slug,
}: Readonly<{ response: PendingManual; slug: string }>) {
  const router = useRouter();
  const [score, setScore] = useState(response.current_score);
  const [feedback, setFeedback] = useState('');
  const mutation = useAssessmentMutation(() =>
    gradeAssessmentResponse(slug, response.response_id, { feedback, score }),
  );
  return (
    <li className="assessment-grading-card">
      <div className="assessment-grading-card__response">
        <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
          {response.learner}
        </p>
        <h2>
          <ClipboardCheck /> Respuesta abierta
        </h2>
        <blockquote>{response.answer || 'Sin texto'}</blockquote>
        <p className="assessment-grading-card__trace">
          <ShieldCheck />
          Intento {response.attempt_id} · ítem {response.attempt_item_id}
        </p>
        {response.decision_history.length ? (
          <section className="assessment-grade-history">
            <h3>
              <History /> Historial de decisiones
            </h3>
            <ol>
              {response.decision_history.map((decision) => (
                <li key={decision.id}>
                  <span>#{decision.sequence}</span>
                  <div>
                    <strong>{decision.score} puntos</strong>
                    <p>{decision.feedback || 'Sin comentario registrado.'}</p>
                  </div>
                </li>
              ))}
            </ol>
          </section>
        ) : null}
      </div>
      <fieldset className="assessment-grade-decision">
        <legend>
          <Scale /> Decisión de calificación
        </legend>
        <Label htmlFor={`score-${response.response_id}`}>
          Puntaje (máximo {response.points})
        </Label>
        <Input
          id={`score-${response.response_id}`}
          max={response.points}
          min="0"
          onChange={(event) => setScore(event.target.value)}
          step="0.001"
          type="number"
          value={score}
        />
        <Label htmlFor={`feedback-${response.response_id}`}>Feedback</Label>
        <Textarea
          id={`feedback-${response.response_id}`}
          onChange={(event) => setFeedback(event.target.value)}
          value={feedback}
        />
        <Button
          className="w-full"
          disabled={mutation.isPending}
          onClick={async () => {
            try {
              await mutation.mutateAsync(undefined);
              router.refresh();
            } catch {
              // React Query conserva el error en esta tarjeta.
            }
          }}
          type="button"
        >
          {response.response_status === 'manually_graded'
            ? 'Registrar corrección'
            : 'Registrar decisión'}
        </Button>
        <p className="text-xs text-muted-foreground">
          Cada corrección agrega una decisión append-only; el historial no se
          sobrescribe.
        </p>
        <MutationError error={mutation.error} />
      </fieldset>
    </li>
  );
}
