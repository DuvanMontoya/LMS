'use client';

import {
  BookOpenText,
  ChevronDown,
  Eye,
  ListTree,
  LogOut,
  PanelLeftClose,
  PanelLeftOpen,
} from 'lucide-react';
import Link from 'next/link';
import { useState, type ReactNode } from 'react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import type { components } from '@/lib/api/generated/platform';

type PublishedModule = components['schemas']['PublishedOutlineModule'];

export function CoursePreviewPlayer({
  children,
  courseHref,
  courseTitle,
  currentUnitId,
  modules,
  positionLabel,
  releaseNumber,
  title,
}: Readonly<{
  children: ReactNode;
  courseHref: string;
  courseTitle: string;
  currentUnitId: string;
  modules: readonly PublishedModule[];
  positionLabel: string;
  releaseNumber: number;
  title: string;
}>) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <main
      className="learning-player learning-player--preview"
      data-release-number={releaseNumber}
      data-sidebar-collapsed={sidebarCollapsed}
      id="contenido-principal"
    >
      <aside className="learning-player__sidebar">
        <header>
          <Link
            aria-label={`Volver a ${courseTitle}`}
            className="learning-player__course"
            href={courseHref}
          >
            <span>
              <BookOpenText />
            </span>
            <span>
              <small>Curso</small>
              <strong>{courseTitle}</strong>
            </span>
          </Link>
          <div className="learning-player__preview-status">
            <Eye />
            <span>
              <strong>Vista previa del estudiante</strong>
              <small>Release {releaseNumber} · sin guardar progreso</small>
            </span>
          </div>
        </header>
        <div className="learning-player__curriculum-scroll">
          <PublishedOutline
            compact={sidebarCollapsed}
            courseHref={courseHref}
            currentUnitId={currentUnitId}
            modules={modules}
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
          <Badge className="learning-player__preview-badge" variant="outline">
            <Eye />
            Vista previa
          </Badge>
          <div className="learning-player__header-actions">
            <Button
              asChild
              className="learning-player__exit"
              size="sm"
              variant="ghost"
            >
              <Link
                aria-label={`Salir de la vista previa y volver a ${courseTitle}`}
                href={courseHref}
              >
                <LogOut />
                <span className="hidden sm:inline">Salir</span>
              </Link>
            </Button>
          </div>
        </header>

        <details className="learning-player__mobile-outline">
          <summary>
            <ListTree />
            Contenido del curso
            <span>{modules.length} módulos</span>
          </summary>
          <div>
            <div className="learning-player__preview-status">
              <Eye />
              <span>
                <strong>Vista previa</strong>
                <small>El progreso no se guarda</small>
              </span>
            </div>
            <PublishedOutline
              courseHref={courseHref}
              currentUnitId={currentUnitId}
              modules={modules}
            />
          </div>
        </details>

        <div className="learning-player__stage">{children}</div>
      </div>
    </main>
  );
}

function PublishedOutline({
  compact = false,
  courseHref,
  currentUnitId,
  modules,
}: Readonly<{
  compact?: boolean;
  courseHref: string;
  currentUnitId: string;
  modules: readonly PublishedModule[];
}>) {
  return (
    <ol
      aria-label="Contenido publicado del curso"
      className="course-preview-outline"
      data-compact={compact}
    >
      {modules.map((module) => {
        const currentModule = module.units.some(
          (unit) => unit.id === currentUnitId,
        );
        return (
          <li key={module.id}>
            <details open={currentModule}>
              <summary>
                <span className="course-preview-outline__number">
                  {String(module.position).padStart(2, '0')}
                </span>
                <span className="course-preview-outline__title">
                  {module.title}
                </span>
                <small>{module.units.length}</small>
                <ChevronDown />
              </summary>
              <ol>
                {module.units.map((unit) => {
                  const current = unit.id === currentUnitId;
                  return (
                    <li key={unit.id}>
                      <Link
                        aria-current={current ? 'step' : undefined}
                        data-current={current ? 'true' : undefined}
                        href={`${courseHref}/unidades/${unit.id}`}
                      >
                        <span>
                          {module.position}.{unit.position}
                        </span>
                        <strong>{unit.title}</strong>
                      </Link>
                    </li>
                  );
                })}
              </ol>
            </details>
          </li>
        );
      })}
    </ol>
  );
}
