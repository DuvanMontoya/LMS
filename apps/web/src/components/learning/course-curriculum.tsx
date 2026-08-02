import {
  CalendarClock,
  CheckCircle2,
  Circle,
  CircleDot,
  ClipboardCheck,
  Clock3,
  LockKeyhole,
  PlayCircle,
  Video,
} from 'lucide-react';
import Link from 'next/link';

import type { components } from '@/lib/api/generated/platform';

type LearningModule = components['schemas']['ModuleOutline'];

export function CourseCurriculum({
  currentActivityId,
  currentUnitId,
  modules,
  variant = 'course',
}: Readonly<{
  currentUnitId?: string;
  currentActivityId?: string;
  modules: readonly LearningModule[];
  variant?: 'course' | 'player';
}>) {
  return (
    <ol
      className="course-curriculum"
      data-variant={variant}
      aria-label="Contenido del curso"
    >
      {modules.map((module) => (
        <li className="course-curriculum__module" key={module.id}>
          <header>
            <span>Módulo {module.position}</span>
            <h3>{module.title}</h3>
            {variant === 'course' && module.description ? (
              <p>{module.description}</p>
            ) : null}
            <small>{activityCountLabel(module.activities.length)}</small>
          </header>
          <ol>
            {module.activities.map((activity) => {
              const current =
                activity.id === currentActivityId ||
                activity.source_activity_id === currentUnitId ||
                activity.is_current;
              const blocked = activity.status === 'locked';
              const content = (
                <>
                  <ActivityState status={activity.status} />
                  <span>
                    <strong>
                      {module.position}.{activity.position} {activity.title}
                    </strong>
                    {variant === 'course' && activity.summary ? (
                      <small>{activity.summary}</small>
                    ) : null}
                    <small className="course-curriculum__kind">
                      <ActivityKind type={activity.type} />
                      {activityTypeLabel(activity.type)}
                      {activity.required ? ' · Obligatoria' : ' · Opcional'}
                    </small>
                    {blocked && activity.blocked_reason ? (
                      <small>{activity.blocked_reason}</small>
                    ) : null}
                  </span>
                  {activity.estimated_duration_minutes ? (
                    <small className="course-curriculum__duration">
                      <Clock3 />
                      {activity.estimated_duration_minutes} min
                    </small>
                  ) : current ? (
                    <PlayCircle
                      aria-hidden="true"
                      className="course-curriculum__play"
                    />
                  ) : null}
                </>
              );
              return (
                <li key={activity.id}>
                  {blocked ? (
                    <span aria-disabled="true" data-current="false">
                      {content}
                    </span>
                  ) : (
                    <Link
                      aria-current={current ? 'step' : undefined}
                      data-current={current ? 'true' : undefined}
                      href={activity.href}
                    >
                      {content}
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        </li>
      ))}
    </ol>
  );
}

function ActivityState({ status }: Readonly<{ status: string }>) {
  if (['completed', 'passed', 'waived'].includes(status)) {
    return (
      <CheckCircle2
        aria-label="Completada"
        className="course-curriculum__state"
        data-status="completed"
      />
    );
  }
  if (status === 'locked') {
    return (
      <LockKeyhole
        aria-label="Bloqueada"
        className="course-curriculum__state"
        data-status="locked"
      />
    );
  }
  if (status === 'in_progress') {
    return (
      <CircleDot
        aria-label="En progreso"
        className="course-curriculum__state"
        data-status="in_progress"
      />
    );
  }
  return (
    <Circle
      aria-label="No iniciada"
      className="course-curriculum__state"
      data-status="not_started"
    />
  );
}

function ActivityKind({ type }: Readonly<{ type: string }>) {
  if (type === 'live_class') return <Video aria-hidden="true" />;
  if (type === 'assessment') return <ClipboardCheck aria-hidden="true" />;
  return <CalendarClock aria-hidden="true" />;
}

function activityTypeLabel(type: string) {
  if (type === 'live_class') return 'Clase en vivo';
  if (type === 'assessment') return 'Evaluación';
  return 'Lección';
}

function activityCountLabel(count: number) {
  return `${count} ${count === 1 ? 'actividad' : 'actividades'}`;
}
