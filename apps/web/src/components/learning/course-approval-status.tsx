import {
  CircleCheck,
  CircleDashed,
  CircleX,
  ClipboardCheck,
  GraduationCap,
  UsersRound,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import type { components } from '@/lib/api/generated/platform';
import { percentLabel } from '@/lib/learning/labels';

type ApprovalState = 'approved' | 'in_progress' | 'not_approved' | 'pending';

const statePresentation: Record<
  ApprovalState,
  { label: string; description: string; className: string }
> = {
  approved: {
    className:
      'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/45 dark:text-emerald-200',
    description: 'Cumpliste todos los criterios institucionales.',
    label: 'Aprobado',
  },
  in_progress: {
    className:
      'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-900 dark:bg-blue-950/45 dark:text-blue-200',
    description: 'Tu aprobación se actualiza con cada actividad.',
    label: 'En progreso',
  },
  not_approved: {
    className:
      'border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950/45 dark:text-red-200',
    description: 'El acceso terminó sin completar todos los criterios.',
    label: 'No aprobado',
  },
  pending: {
    className:
      'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900 dark:bg-amber-950/45 dark:text-amber-200',
    description: 'Aún no hay actividad suficiente para decidir.',
    label: 'Pendiente',
  },
};

export function courseApprovalState(
  progress: components['schemas']['Progress'],
  accessState: string,
): ApprovalState {
  if (progress.is_complete) return 'approved';
  if (accessState === 'ended') return 'not_approved';
  if (progress.status === 'in_progress' || progress.started_at) {
    return 'in_progress';
  }
  return 'pending';
}

export function CourseApprovalStatus({
  accessState,
  progress,
}: Readonly<{
  accessState: string;
  progress: components['schemas']['Progress'];
}>) {
  const state = courseApprovalState(progress, accessState);
  const presentation = statePresentation[state];
  const primaryBlocker = progress.blockers.at(0);

  return (
    <section
      aria-label="Estado de aprobación del curso"
      className="course-approval-status"
    >
      <header>
        <div>
          <p className="academic-kicker">Resultado del curso</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <h3 className="text-sm font-semibold">Estado de aprobación</h3>
            <CourseApprovalBadge
              accessState={accessState}
              progress={progress}
            />
          </div>
          <p className="mt-1 text-xs leading-5 text-muted-foreground">
            {presentation.description}
          </p>
        </div>
      </header>
      <dl>
        <Criterion
          current={`${progress.completion.completed_required}/${progress.completion.total_required}`}
          icon={ClipboardCheck}
          label="Actividades"
          satisfied={progress.completion.satisfied}
          target="obligatorias"
        />
        <Criterion
          current={thresholdCurrent(
            progress.grade.basis_points,
            progress.grade.minimum_basis_points,
          )}
          icon={GraduationCap}
          label="Calificación"
          satisfied={progress.grade.satisfied}
          target={thresholdTarget(progress.grade.minimum_basis_points)}
        />
        <Criterion
          current={thresholdCurrent(
            progress.attendance.basis_points,
            progress.attendance.minimum_basis_points,
          )}
          icon={UsersRound}
          label="Asistencia"
          satisfied={progress.attendance.satisfied}
          target={thresholdTarget(progress.attendance.minimum_basis_points)}
        />
      </dl>
      {primaryBlocker ? (
        <p className="course-approval-status__blocker">
          <span className="sr-only">Criterio pendiente: </span>
          {primaryBlocker.message.replace(/[.!?]+$/, '')}
          {progress.blockers.length > 1
            ? `; además, ${progress.blockers.length - 1} criterio${progress.blockers.length > 2 ? 's' : ''} más.`
            : '.'}
        </p>
      ) : null}
    </section>
  );
}

export function CourseApprovalBadge({
  accessState,
  progress,
}: Readonly<{
  accessState: string;
  progress: components['schemas']['Progress'];
}>) {
  const state = courseApprovalState(progress, accessState);
  const presentation = statePresentation[state];
  return (
    <Badge className={presentation.className} variant="outline">
      {state === 'approved' ? (
        <CircleCheck data-icon="inline-start" />
      ) : state === 'not_approved' ? (
        <CircleX data-icon="inline-start" />
      ) : (
        <CircleDashed data-icon="inline-start" />
      )}
      {presentation.label}
    </Badge>
  );
}

function Criterion({
  current,
  icon: Icon,
  label,
  satisfied,
  target,
}: Readonly<{
  current: string;
  icon: typeof ClipboardCheck;
  label: string;
  satisfied: boolean;
  target: string;
}>) {
  return (
    <div data-satisfied={satisfied}>
      <dt>
        <Icon />
        {label}
      </dt>
      <dd>{current}</dd>
      <p>{target}</p>
    </div>
  );
}

function thresholdCurrent(
  value: number | null,
  minimum: number | null,
): string {
  if (minimum === null) return 'No exigida';
  return value === null ? 'Pendiente' : `${percentLabel(value)} %`;
}

function thresholdTarget(value: number | null): string {
  return value === null ? 'Sin mínimo' : `mínimo ${percentLabel(value)} %`;
}
