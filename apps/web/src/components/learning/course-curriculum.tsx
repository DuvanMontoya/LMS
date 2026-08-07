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
  Video,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef } from 'react';

import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { components } from '@/lib/api/generated/platform';

type LearningModule = components['schemas']['ModuleOutline'];

export function CourseCurriculum({
  accordionName,
  compact = false,
  currentActivityId,
  currentUnitId,
  modules,
  variant = 'course',
}: Readonly<{
  accordionName?: string;
  compact?: boolean;
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
      data-compact={compact}
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
              const unavailable = !activity.href;
              const blocked = activity.status === 'locked' || unavailable;
              const accessibleTitle = `${module.position}.${activity.position} ${activity.title}`;
              const content = (
                <>
                  {variant === 'player' ? (
                    <span className="course-curriculum__item-title">
                      <ActivityKind type={activity.type} />
                      <span className="sr-only">
                        {activityTypeLabel(activity.type)}:{' '}
                      </span>
                      <strong title={accessibleTitle}>
                        {module.position}.{activity.position} {activity.title}
                      </strong>
                      <ActivityState status={activity.status} />
                    </span>
                  ) : (
                    <>
                      <ActivityState status={activity.status} />
                      <span>
                        <strong>
                          {module.position}.{activity.position} {activity.title}
                        </strong>
                        {activity.summary ? (
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
                    </>
                  )}
                  {variant === 'course' &&
                  activity.estimated_duration_minutes ? (
                    <small className="course-curriculum__duration">
                      <Clock3 />
                      {activity.estimated_duration_minutes} min
                    </small>
                  ) : null}
                </>
              );
              const item =
                blocked || !activity.href ? (
                  <span
                    aria-label={`${activityTypeLabel(activity.type)}: ${accessibleTitle}. ${unavailable ? 'No disponible para esta matrícula' : activityStatusLabel(activity.status)}`}
                    aria-disabled="true"
                    data-current="false"
                    data-status={activity.status}
                  >
                    {content}
                  </span>
                ) : (
                  <Link
                    aria-current={current ? 'step' : undefined}
                    aria-label={`${activityTypeLabel(activity.type)}: ${accessibleTitle}. ${activityStatusLabel(activity.status)}`}
                    data-current={current ? 'true' : undefined}
                    data-status={activity.status}
                    href={activity.href}
                    ref={current ? activeItemRef : undefined}
                  >
                    {content}
                  </Link>
                );
              return (
                <li key={activity.id}>
                  {variant === 'player' && compact ? (
                    <Tooltip>
                      <TooltipTrigger asChild>{item}</TooltipTrigger>
                      <TooltipContent
                        className="course-curriculum__tooltip"
                        side="right"
                        sideOffset={8}
                      >
                        <span>{activityTypeLabel(activity.type)}</span>
                        <strong>{accessibleTitle}</strong>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    item
                  )}
                </li>
              );
            })}
          </ol>
        );
        const moduleNumber = (
          <span
            className="course-curriculum__module-number"
            data-module-position={module.position}
          >
            Módulo {module.position}
          </span>
        );

        return (
          <li className="course-curriculum__module" key={module.id}>
            {variant === 'player' ? (
              <details name={accordionName} open={moduleCurrent}>
                <summary
                  aria-label={`Módulo ${module.position}: ${module.title}`}
                >
                  {compact ? (
                    <Tooltip>
                      <TooltipTrigger asChild>{moduleNumber}</TooltipTrigger>
                      <TooltipContent
                        className="course-curriculum__tooltip"
                        side="right"
                        sideOffset={8}
                      >
                        <span>Módulo {module.position}</span>
                        <strong>{module.title}</strong>
                      </TooltipContent>
                    </Tooltip>
                  ) : (
                    moduleNumber
                  )}
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
  if (status === 'unavailable') {
    return (
      <LockKeyhole
        aria-label="No disponible"
        className="course-curriculum__state"
        data-status="unavailable"
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

function activityStatusLabel(status: string) {
  if (['completed', 'passed', 'waived'].includes(status)) return 'Completada';
  if (status === 'locked') return 'Bloqueada';
  if (status === 'unavailable') return 'No disponible';
  if (status === 'in_progress') return 'En progreso';
  return 'No iniciada';
}

function activityCountLabel(count: number) {
  return `${count} ${count === 1 ? 'actividad' : 'actividades'}`;
}
