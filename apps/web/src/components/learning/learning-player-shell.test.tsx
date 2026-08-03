import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { components } from '@/lib/api/generated/platform';
import { TooltipProvider } from '@/components/ui/tooltip';

import { LearningPlayerShell } from './learning-player-shell';

type LearningOutline = components['schemas']['LearningOutline'];

const outline = {
  cohort: null,
  course: { id: 'course-one', slug: 'calculo', title: 'Cálculo integral' },
  modules: [],
  progress: {
    attendance: {
      basis_points: null,
      minimum_basis_points: null,
      satisfied: true,
    },
    blockers: [],
    completed_at: null,
    completed_required_activities: 0,
    completed_units: 0,
    completion: { completed_required: 0, satisfied: false, total_required: 2 },
    grade: {
      basis_points: null,
      minimum_basis_points: null,
      satisfied: true,
    },
    is_complete: false,
    last_activity_at: null,
    mastery: {
      evidenced_count: 0,
      evidenced_objective_ids: [],
      total_objectives: 0,
    },
    percent: '0.00',
    percent_basis_points: 0,
    progress_version: 1,
    started_at: null,
    status: 'not_started',
    total_required_activities: 2,
    total_units: 0,
  },
  release_number: 1,
  resume: {
    activity_instance_id: null,
    href: null,
    node_id: null,
    unit_id: null,
  },
} satisfies LearningOutline;

describe('LearningPlayerShell focus mode', () => {
  it('starts compact for activities and lets the learner expand the syllabus', () => {
    const { container } = render(
      <TooltipProvider>
        <LearningPlayerShell
          courseTitle="Cálculo integral"
          outline={outline}
          outlineHref="/curso"
          positionLabel="Actividad 1 de 2"
          releaseNumber={1}
          stageMode="briefing"
          title="Evaluación diagnóstica"
        >
          <p>Contenido principal</p>
        </LearningPlayerShell>
      </TooltipProvider>,
    );

    expect(container.querySelector('main')).toHaveAttribute(
      'data-sidebar-collapsed',
      'true',
    );
    fireEvent.click(
      screen.getByRole('button', { name: 'Expandir temario del curso' }),
    );
    expect(container.querySelector('main')).toHaveAttribute(
      'data-sidebar-collapsed',
      'false',
    );
    expect(
      screen.getByRole('button', { name: 'Compactar temario del curso' }),
    ).toHaveAttribute('aria-expanded', 'true');
  });

  it('keeps the syllabus expanded by default for a document lesson', () => {
    render(
      <TooltipProvider>
        <LearningPlayerShell
          courseTitle="Cálculo integral"
          outline={outline}
          outlineHref="/curso"
          positionLabel="Unidad 1 de 2"
          releaseNumber={1}
          title="Guía de integración"
        >
          <p>Lección</p>
        </LearningPlayerShell>
      </TooltipProvider>,
    );

    expect(
      screen.getByRole('button', { name: 'Compactar temario del curso' }),
    ).toHaveAttribute('aria-expanded', 'true');
  });
});
