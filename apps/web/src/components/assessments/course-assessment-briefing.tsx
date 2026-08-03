'use client';

import {
  ArrowRight,
  CalendarClock,
  ClipboardCheck,
  ListChecks,
  Loader2,
  RotateCcw,
  ShieldCheck,
  Timer,
  Trophy,
} from 'lucide-react';
import type { ReactNode } from 'react';

import { MutationError } from '@/components/assessments/authoring-forms';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  startAssessmentAttempt,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { LearnerDelivery } from '@/lib/assessments/server';

export function CourseAssessmentBriefing({
  assignment,
  returnHref,
  slug,
}: Readonly<{
  assignment: LearnerDelivery | null;
  returnHref: string;
  slug: string;
}>) {
  if (!assignment) {
    return (
      <Alert>
        <ClipboardCheck />
        <AlertTitle>Evaluación aún no habilitada</AlertTitle>
        <AlertDescription>
          La actividad forma parte del curso, pero todavía no existe una entrega
          activa para tu matrícula y este release.
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <AssessmentBriefingContent
      assignment={assignment}
      returnHref={returnHref}
      slug={slug}
    />
  );
}

function AssessmentBriefingContent({
  assignment,
  returnHref,
  slug,
}: Readonly<{
  assignment: LearnerDelivery;
  returnHref: string;
  slug: string;
}>) {
  const start = useAssessmentMutation(() =>
    startAssessmentAttempt(slug, assignment.id),
  );
  const remaining = Math.max(
    0,
    assignment.attempt_limit - assignment.attempts_used,
  );
  const available =
    assignment.status === 'active' &&
    (remaining > 0 || Boolean(assignment.in_progress_attempt_id));

  return (
    <section className="assessment-briefing" aria-labelledby="assessment-ready">
      <div className="assessment-briefing__hero">
        <div className="assessment-briefing__icon">
          <ClipboardCheck />
        </div>
        <div>
          <p className="assessment-briefing__eyebrow">Antes de comenzar</p>
          <h2 id="assessment-ready">{assignment.delivery.assessment_title}</h2>
          <p>
            {assignment.description ||
              'Revisa las condiciones del intento y lee cada pregunta con atención. Tus respuestas se guardan dentro del intento activo.'}
          </p>
        </div>
        <Badge
          className="assessment-status"
          data-status={assignment.status}
          variant="outline"
        >
          {assignment.status === 'active' ? 'Disponible' : assignment.status}
        </Badge>
      </div>

      <dl className="assessment-briefing__facts">
        <Fact
          icon={<Timer />}
          label="Tiempo del intento"
          value={durationLabel(assignment.time_limit_minutes)}
        />
        <Fact
          icon={<ListChecks />}
          label="Preguntas"
          value={`${assignment.item_count}`}
        />
        <Fact
          icon={<RotateCcw />}
          label="Intentos restantes"
          value={`${remaining} de ${assignment.attempt_limit}`}
        />
        <Fact
          icon={<Trophy />}
          label="Puntaje para aprobar"
          value={`${(assignment.pass_basis_points / 100).toLocaleString('es-CO')} %`}
        />
        <Fact
          icon={<ShieldCheck />}
          label="Puntaje máximo"
          value={Number(assignment.maximum_score).toLocaleString('es-CO')}
        />
        <Fact
          icon={<CalendarClock />}
          label="Cierre"
          value={dateTimeLabel(assignment.delivery.closes_at)}
        />
      </dl>

      <div className="assessment-briefing__notice">
        <ShieldCheck />
        <div>
          <strong>Tu intento es individual y queda registrado</strong>
          <p>
            El cronómetro empieza al pulsar el botón. Si sales, podrás continuar
            el mismo intento mientras siga vigente y no lo hayas enviado.
          </p>
        </div>
      </div>

      <div className="assessment-briefing__action">
        <div>
          <strong>
            {assignment.in_progress_attempt_id
              ? 'Tienes un intento en curso'
              : 'Todo listo para comenzar'}
          </strong>
          <span>
            {available
              ? 'Al entrar, la evaluación ocupará todo el espacio de trabajo.'
              : 'La evaluación no admite un nuevo intento en este momento.'}
          </span>
        </div>
        <Button
          disabled={!available || start.isPending}
          onClick={async () => {
            try {
              const attempt = await start.mutateAsync(undefined);
              window.location.assign(`${returnHref}?attempt=${attempt.id}`);
            } catch {
              // React Query presenta el error junto a la acción.
            }
          }}
          size="lg"
          type="button"
        >
          {start.isPending ? <Loader2 className="animate-spin" /> : null}
          {assignment.in_progress_attempt_id
            ? 'Continuar intento'
            : 'Iniciar evaluación'}
          <ArrowRight data-icon="inline-end" />
        </Button>
      </div>
      <MutationError error={start.error} />
    </section>
  );
}

function Fact({
  icon,
  label,
  value,
}: Readonly<{ icon: ReactNode; label: string; value: string }>) {
  return (
    <div>
      {icon}
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function durationLabel(minutes: number | null) {
  if (!minutes) return 'Sin límite';
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes ? `${hours} h ${remainingMinutes} min` : `${hours} h`;
}

function dateTimeLabel(value: string | null) {
  if (!value) return 'Sin fecha límite';
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}
