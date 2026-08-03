'use client';

import {
  CalendarClock,
  CheckCircle2,
  ChevronDown,
  Circle,
  CircleDot,
  ClipboardCheck,
  Clock3,
  LockKeyhole,
  PlayCircle,
  Video,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef } from 'react';

import type { components } from '@/lib/api/generated/platform';

type LearningModule = components['schemas']['ModuleOutline'];

export function CourseCurriculum({
  currentActivityId,
  currentUnitId,
  modules,
  variant = 'course',
}: Readonly<{
  currentUnitId?: string | undefined;
  currentActivityId?: string | undefined;
  modules: readonly LearningModule[];
  variant?: 'course' | 'player';
}>) {
  const activeItemRef = useRef<HTMLAnchorElement | null>(null);
  const hasExplicitCurrent = Boolean(currentActivityId || currentUnitId);

  useEffect(() => {
    const activeItem = activeItemRef.current;
    if (!activeItem || !activeItem.offsetParent) return;
    activeItem.scrollIntoView({ block: 'center' });
  }, [currentActivityId, currentUnitId]);

  return (
    <ol
      className="course-curriculum"
      data-variant={variant}
      aria-label="Contenido del curso"
    >
      {modules.map((module) => {
        const moduleCurrent = module.activities.some((activity) =>
          hasExplicitCurrent
            ? activity.id === currentActivityId ||
              activity.source_activity_id === currentUnitId
            : activity.is_current,
        );
        const completedCount = module.activities.filter((activity) =>
          ['completed', 'passed', 'waived'].includes(activity.status),
        ).length;
        const activityList = (
          <ol>
            {module.activities.map((activity) => {
              const current = hasExplicitCurrent
                ? activity.id === currentActivityId ||
                  activity.source_activity_id === currentUnitId
                : activity.is_current;
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
                      {variant === 'course'
                        ? activity.required
                          ? ' · Obligatoria'
                          : ' · Opcional'
                        : null}
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
                      ref={current ? activeItemRef : undefined}
                    >
                      {content}
                    </Link>
                  )}
                </li>
              );
            })}
          </ol>
        );

        return (
          <li className="course-curriculum__module" key={module.id}>
            {variant === 'player' ? (
              <details open={moduleCurrent}>
                <summary>
                  <span className="course-curriculum__module-number">
                    Módulo {module.position}
                  </span>
                  <span className="course-curriculum__module-title">
                    {module.title}
                  </span>
                  <small>
                    {completedCount}/{module.activities.length}
                  </small>
                  <ChevronDown aria-hidden="true" />
                </summary>
                {activityList}
              </details>
            ) : (
              <>
                <header>
                  <span>Módulo {module.position}</span>
                  <h3>{module.title}</h3>
                  {module.description ? <p>{module.description}</p> : null}
                  <small>{activityCountLabel(module.activities.length)}</small>
                </header>
                {activityList}
              </>
            )}
          </li>
        );
      })}
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
