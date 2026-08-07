import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { components } from '@/lib/api/generated/platform';

import { CourseCurriculum } from './course-curriculum';

type Module = components['schemas']['ModuleOutline'];

const modules = [
  {
    activities: [
      {
        availability_rules: [],
        binding: {},
        blocked_reason: null,
        completion_policy: {},
        estimated_duration_minutes: 30,
        href: '/actividad-anterior',
        id: 'activity-one',
        is_current: true,
        position: 1,
        required: true,
        source_activity_id: 'unit-one',
        status: 'in_progress',
        summary: '',
        title: 'Actividad anterior',
        type: 'lesson',
      },
    ],
    description: '',
    id: 'module-one',
    position: 1,
    title: 'Primer módulo',
    units: [],
  },
  {
    activities: [
      {
        availability_rules: [],
        binding: {},
        blocked_reason: null,
        completion_policy: {},
        estimated_duration_minutes: 45,
        href: '/actividad-actual',
        id: 'activity-two',
        is_current: false,
        position: 1,
        required: true,
        source_activity_id: '',
        status: 'available',
        summary: '',
        title: 'Actividad realmente abierta',
        type: 'assessment',
      },
    ],
    description: '',
    id: 'module-two',
    position: 2,
    title: 'Segundo módulo',
    units: [],
  },
] satisfies Module[];

describe('CourseCurriculum player', () => {
  it('prioritizes the explicit route and opens only its module', () => {
    const { container } = render(
      <CourseCurriculum
        accordionName="test-course-modules"
        currentActivityId="activity-two"
        modules={modules}
        variant="player"
      />,
    );

    expect(
      screen.getByRole('link', { name: /actividad realmente abierta/i }),
    ).toHaveAttribute('aria-current', 'step');
    expect(
      screen.getByRole('link', { name: /actividad anterior/i }),
    ).not.toHaveAttribute('aria-current');
    const details = container.querySelectorAll('details');
    expect(details).toHaveLength(2);
    expect(details[0]).not.toHaveAttribute('open');
    expect(details[1]).toHaveAttribute('open');
    expect(details[0]).toHaveAttribute('name', 'test-course-modules');
    expect(screen.queryByText('45 min')).not.toBeInTheDocument();
  });

  it('does not turn an unavailable activity into a broken link', () => {
    const baseModule = modules[0];
    const baseActivity = baseModule?.activities[0];
    if (!baseModule || !baseActivity) throw new Error('Missing test activity.');
    const unavailableActivity: Module['activities'][number] = {
      ...baseActivity,
      href: null,
      id: 'unavailable-activity',
      status: 'unavailable',
      title: 'Evaluación sin cohorte',
      type: 'assessment',
    };
    render(
      <CourseCurriculum
        modules={[
          {
            ...baseModule,
            activities: [unavailableActivity],
          },
        ]}
        variant="player"
      />,
    );

    expect(
      screen.queryByRole('link', { name: /evaluación sin cohorte/i }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByText(/Evaluación sin cohorte/).closest('[aria-disabled]'),
    ).toHaveAttribute('aria-disabled', 'true');
  });
});
