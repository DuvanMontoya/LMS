'use client';

import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ClipboardCheck,
  RotateCcw,
  Timer,
} from 'lucide-react';
import { useRouter } from 'next/navigation';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { MutationError } from '@/components/assessments/authoring-forms';
import {
  startAssessmentAttempt,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { LearnerDelivery } from '@/lib/assessments/server';

export function LearnerDeliveryList({
  deliveries,
  slug,
}: Readonly<{ deliveries: LearnerDelivery[]; slug: string }>) {
  if (!deliveries.length) {
    return (
      <section className="assessment-learner-empty">
        <ClipboardCheck className="mx-auto size-7 text-muted-foreground" />
        <h2 className="mt-3 font-semibold">
          No tienes evaluaciones disponibles
        </h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Las entregas aparecerán cuando un instructor las active y asigne a tu
          release vigente.
        </p>
      </section>
    );
  }
  return (
    <ul className="assessment-learner-grid">
      {deliveries.map((assignment) => (
        <DeliveryCard assignment={assignment} key={assignment.id} slug={slug} />
      ))}
    </ul>
  );
}

function DeliveryCard({
  assignment,
  slug,
}: Readonly<{ assignment: LearnerDelivery; slug: string }>) {
  const router = useRouter();
  const start = useAssessmentMutation(() =>
    startAssessmentAttempt(slug, assignment.id),
  );
  const delivery = assignment.delivery;
  const remaining = Math.max(
    0,
    assignment.attempt_limit - assignment.attempts_used,
  );
  return (
    <li className="assessment-learner-card">
      <div className="assessment-learner-card__header">
        <div>
          <p className="assessment-rail-kicker">
            {assignment.attempts_used
              ? 'Actividad en curso'
              : 'Nueva evaluación asignada'}
          </p>
          <h2>{delivery.assessment_title}</h2>
          <p>{delivery.name}</p>
        </div>
        <Badge
          className="assessment-status"
          data-status={assignment.status}
          variant="outline"
        >
          {assignment.status === 'active' ? 'Disponible' : assignment.status}
        </Badge>
      </div>
      <dl className="assessment-learner-card__facts">
        <div>
          <RotateCcw />
          <dt>Intentos restantes</dt>
          <dd>{remaining}</dd>
        </div>
        <div>
          <CalendarClock />
          <dt>Fecha de cierre</dt>
          <dd>
            {delivery.closes_at
              ? new Intl.DateTimeFormat('es-CO', {
                  dateStyle: 'short',
                  timeStyle: 'short',
                }).format(new Date(delivery.closes_at))
              : 'Sin límite'}
          </dd>
        </div>
      </dl>
      <div className="assessment-learner-card__progress">
        <div>
          <span
            style={{
              width: `${
                assignment.attempt_limit
                  ? Math.min(
                      100,
                      (assignment.attempts_used / assignment.attempt_limit) *
                        100,
                    )
                  : 0
              }%`,
            }}
          />
        </div>
        <p>
          {assignment.in_progress_attempt_id ? (
            <>
              <Timer /> Hay un intento en curso listo para continuar.
            </>
          ) : assignment.attempts_used ? (
            <>
              <CheckCircle2 /> Intento anterior registrado.
            </>
          ) : (
            <>
              <ClipboardCheck /> Aún no has iniciado esta evaluación.
            </>
          )}
        </p>
      </div>
      <Button
        className="mt-5 h-10 justify-between"
        disabled={
          assignment.status !== 'active' ||
          (!remaining && !assignment.in_progress_attempt_id) ||
          start.isPending
        }
        onClick={async () => {
          try {
            const attempt = await start.mutateAsync(undefined);
            router.push(
              `/organizaciones/${slug}/evaluaciones/intentos/${attempt.id}`,
            );
          } catch {
            // React Query presenta el error debajo de la acción.
          }
        }}
        type="button"
      >
        {remaining
          ? assignment.attempts_used
            ? 'Continuar o iniciar intento'
            : 'Comenzar'
          : assignment.in_progress_attempt_id
            ? 'Continuar intento en curso'
            : 'Sin intentos disponibles'}
        <ArrowRight data-icon="inline-end" />
      </Button>
      <MutationError error={start.error} />
    </li>
  );
}
