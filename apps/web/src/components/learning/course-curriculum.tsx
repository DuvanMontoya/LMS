import {
  CheckCircle2,
  Circle,
  CircleDot,
  Clock3,
  PlayCircle,
} from 'lucide-react';
import Link from 'next/link';

import type { components } from '@/lib/api/generated/platform';

type LearningModule = components['schemas']['ModuleOutline'];

export function CourseCurriculum({
  currentUnitId,
  modules,
  variant = 'course',
}: Readonly<{
  currentUnitId?: string;
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
            <small>
              {module.units.length}{' '}
              {module.units.length === 1 ? 'lección' : 'lecciones'}
            </small>
          </header>
          <ol>
            {module.units.map((unit) => {
              const current = unit.id === currentUnitId || unit.is_current;
              return (
                <li key={unit.id}>
                  <Link
                    aria-current={current ? 'step' : undefined}
                    data-current={current ? 'true' : undefined}
                    href={unit.href}
                  >
                    <UnitState status={unit.status} />
                    <span>
                      <strong>
                        {module.position}.{unit.position} {unit.title}
                      </strong>
                      {variant === 'course' && unit.summary ? (
                        <small>{unit.summary}</small>
                      ) : null}
                    </span>
                    {unit.estimated_duration_minutes ? (
                      <small className="course-curriculum__duration">
                        <Clock3 />
                        {unit.estimated_duration_minutes} min
                      </small>
                    ) : current ? (
                      <PlayCircle
                        aria-hidden="true"
                        className="course-curriculum__play"
                      />
                    ) : null}
                  </Link>
                </li>
              );
            })}
          </ol>
        </li>
      ))}
    </ol>
  );
}

function UnitState({ status }: Readonly<{ status: string }>) {
  if (status === 'completed') {
    return (
      <CheckCircle2
        aria-label="Completada"
        className="course-curriculum__state"
        data-status="completed"
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
