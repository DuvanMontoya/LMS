import {
  ArrowLeft,
  ArrowRight,
  BookOpenText,
  ChevronLeft,
  ListTree,
  PanelLeftClose,
} from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';

import { CourseCurriculum } from '@/components/learning/course-curriculum';
import { LearningProgress } from '@/components/learning/learning-progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';

type LearningOutline = components['schemas']['LearningOutline'];

export type LearningPlayerNavigationItem = {
  href: string;
  title: string;
};

export function LearningPlayerShell({
  children,
  courseTitle,
  currentActivityId,
  currentUnitId,
  outline,
  outlineHref,
  positionLabel,
  releaseNumber,
  stageMode = 'document',
  title,
}: Readonly<{
  children: ReactNode;
  courseTitle: string;
  currentActivityId?: string;
  currentUnitId?: string;
  outline: LearningOutline;
  outlineHref: string;
  positionLabel: string;
  releaseNumber: number;
  stageMode?: 'active' | 'briefing' | 'document';
  title: string;
}>) {
  const completedActivities = outline.progress.completion.completed_required;
  const totalActivities = outline.progress.completion.total_required;

  return (
    <main
      className="learning-player"
      data-release-number={releaseNumber}
      id="contenido-principal"
    >
      <header className="learning-player__topbar">
        <Link
          aria-label={`Volver a ${courseTitle}`}
          className="learning-player__brand"
          href={outlineHref}
        >
          <span>
            <BookOpenText />
          </span>
          <span>
            <small>Curso</small>
            <strong>{courseTitle}</strong>
          </span>
        </Link>
        <div className="learning-player__position">
          <span>{positionLabel}</span>
          <p>{title}</p>
        </div>
        <Badge className="learning-player__release" variant="outline">
          Release {releaseNumber}
        </Badge>
        <Button asChild size="sm" variant="ghost">
          <Link
            aria-label={`Salir del aula y volver a ${courseTitle}`}
            href={outlineHref}
          >
            <PanelLeftClose />
            <span className="hidden sm:inline">Salir del aula</span>
          </Link>
        </Button>
      </header>

      <details className="learning-player__mobile-outline">
        <summary>
          <ListTree />
          Contenido del curso
          <progress
            aria-label={`${completedActivities} de ${totalActivities} actividades completadas`}
            max={Math.max(1, totalActivities)}
            value={completedActivities}
          />
          <span>
            {completedActivities}/{totalActivities}
          </span>
        </summary>
        <div>
          <LearningProgress progress={outline.progress} />
          <CourseCurriculum
            currentActivityId={currentActivityId}
            currentUnitId={currentUnitId}
            modules={outline.modules}
            variant="player"
          />
        </div>
      </details>

      <div className="learning-player__layout">
        <aside className="learning-player__sidebar">
          <header>
            <div>
              <span>Contenido del curso</span>
              <small>
                {completedActivities}/{totalActivities} completadas
              </small>
            </div>
            <LearningProgress progress={outline.progress} />
          </header>
          <div className="learning-player__curriculum-scroll">
            <CourseCurriculum
              currentActivityId={currentActivityId}
              currentUnitId={currentUnitId}
              modules={outline.modules}
              variant="player"
            />
          </div>
          <footer>
            <Button asChild size="sm" variant="ghost">
              <Link href={outlineHref}>
                <ChevronLeft />
                Vista general del curso
              </Link>
            </Button>
          </footer>
        </aside>

        <div className="learning-player__stage" data-mode={stageMode}>
          {children}
        </div>
      </div>
    </main>
  );
}

export function LearningPlayerNavigation({
  label,
  next,
  previous,
}: Readonly<{
  label: string;
  next: LearningPlayerNavigationItem | null;
  previous: LearningPlayerNavigationItem | null;
}>) {
  return (
    <nav aria-label={label} className="learning-player__navigation">
      {previous ? (
        <Button asChild className="h-auto justify-start py-3" variant="outline">
          <Link href={previous.href}>
            <ArrowLeft data-icon="inline-start" />
            <span>
              <small>Anterior</small>
              {previous.title}
            </span>
          </Link>
        </Button>
      ) : (
        <span />
      )}
      {next ? (
        <Button asChild className="h-auto justify-end py-3">
          <Link href={next.href}>
            <span>
              <small>Siguiente</small>
              {next.title}
            </span>
            <ArrowRight data-icon="inline-end" />
          </Link>
        </Button>
      ) : null}
    </nav>
  );
}
