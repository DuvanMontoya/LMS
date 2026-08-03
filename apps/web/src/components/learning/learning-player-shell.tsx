'use client';

import {
  BookOpenText,
  ChevronLeft,
  ChevronRight,
  ListTree,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import Link from 'next/link';
import { useState, type ReactNode } from 'react';

import { CourseCurriculum } from '@/components/learning/course-curriculum';
import { LearningProgress } from '@/components/learning/learning-progress';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
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
  headerAccessory,
  headerActions,
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
  headerAccessory?: ReactNode;
  headerActions?: ReactNode;
  outline: LearningOutline;
  outlineHref: string;
  positionLabel: string;
  releaseNumber: number;
  stageMode?: 'active' | 'briefing' | 'document';
  title: string;
}>) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    stageMode !== 'document',
  );
  const completedActivities = outline.progress.completion.completed_required;
  const totalActivities = outline.progress.completion.total_required;

  return (
    <main
      className="learning-player"
      data-release-number={releaseNumber}
      data-sidebar-collapsed={sidebarCollapsed}
      id="contenido-principal"
    >
      <aside className="learning-player__sidebar">
        <header>
          <Link
            aria-label={`Volver a ${courseTitle}`}
            className="learning-player__course"
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
          <div className="learning-player__sidebar-progress">
            <LearningProgress progress={outline.progress} />
          </div>
        </header>
        <div className="learning-player__curriculum-scroll">
          <CourseCurriculum
            accordionName="course-modules-desktop"
            compact={sidebarCollapsed}
            currentActivityId={currentActivityId}
            currentUnitId={currentUnitId}
            modules={outline.modules}
            variant="player"
          />
        </div>
      </aside>

      <div className="learning-player__workspace">
        <header className="learning-player__topbar">
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                aria-expanded={!sidebarCollapsed}
                aria-label={
                  sidebarCollapsed
                    ? 'Expandir temario del curso'
                    : 'Compactar temario del curso'
                }
                className="learning-player__sidebar-toggle"
                onClick={() => setSidebarCollapsed((current) => !current)}
                size="icon"
                type="button"
                variant="ghost"
              >
                {sidebarCollapsed ? <PanelLeftOpen /> : <PanelLeftClose />}
              </Button>
            </TooltipTrigger>
            <TooltipContent side="bottom">
              {sidebarCollapsed ? 'Expandir temario' : 'Modo enfoque'}
            </TooltipContent>
          </Tooltip>
          <div className="learning-player__position">
            <span>{positionLabel}</span>
            <p>{title}</p>
          </div>
          <Badge className="learning-player__release" variant="outline">
            Release {releaseNumber}
          </Badge>
          {headerAccessory ? (
            <div className="learning-player__header-accessory">
              {headerAccessory}
            </div>
          ) : null}
          <div className="learning-player__header-actions">
            <div id="learning-player-live-controls" />
            <Button
              asChild
              className="learning-player__exit"
              size="sm"
              variant="ghost"
            >
              <Link
                aria-label={`Salir del aula y volver a ${courseTitle}`}
                href={outlineHref}
              >
                <LogOut />
                <span className="hidden sm:inline">Salir</span>
              </Link>
            </Button>
            {headerActions}
          </div>
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
              accordionName="course-modules-mobile"
              currentActivityId={currentActivityId}
              currentUnitId={currentUnitId}
              modules={outline.modules}
              variant="player"
            />
          </div>
        </details>

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
        <Button asChild size="icon" variant="outline">
          <Link aria-label={`Anterior: ${previous.title}`} href={previous.href}>
            <ChevronLeft />
            <span className="sr-only">Anterior</span>
          </Link>
        </Button>
      ) : null}
      {next ? (
        <Button asChild size="icon" variant="outline">
          <Link aria-label={`Siguiente: ${next.title}`} href={next.href}>
            <ChevronRight />
            <span className="sr-only">Siguiente</span>
          </Link>
        </Button>
      ) : null}
    </nav>
  );
}
