import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { LearningProgress } from './learning-progress';

describe('LearningProgress', () => {
  it('exposes exact completion through the native progress element', () => {
    render(
      <LearningProgress
        progress={{
          attendance: {
            basis_points: null,
            minimum_basis_points: null,
            satisfied: true,
          },
          blockers: [],
          completed_at: null,
          completed_required_activities: 0,
          completed_units: 3,
          completion: {
            completed_required: 3,
            satisfied: false,
            total_required: 4,
          },
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
          percent: '75.00',
          percent_basis_points: 7500,
          progress_version: 4,
          started_at: '2026-07-30T00:00:00Z',
          status: 'in_progress',
          total_required_activities: 4,
          total_units: 4,
        }}
      />,
    );
    const progress = screen.getByRole('progressbar', {
      name: '3 de 4 unidades completadas, 75 %',
    });
    expect(progress).toHaveAttribute('max', '4');
    expect(progress).toHaveAttribute('value', '3');
    expect(screen.getByText('En progreso')).toBeInTheDocument();
  });
});
