import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { LearnerDelivery } from '@/lib/assessments/server';

import { CourseAssessmentBriefing } from './course-assessment-briefing';

const mutateAsync = vi.fn();

vi.mock('@/lib/assessments/hooks', () => ({
  startAssessmentAttempt: vi.fn(),
  useAssessmentMutation: () => ({
    error: null,
    isPending: false,
    mutateAsync,
  }),
}));

const assignment: LearnerDelivery = {
  assigned_at: '2026-08-01T12:00:00Z',
  attempt_limit: 2,
  attempts_used: 0,
  delivery: {
    assessment_title: 'Quiz de sistemas lineales',
    assessment_version_id: '00000000-0000-0000-0000-000000000002',
    assessment_version_number: 1,
    closes_at: '2026-08-10T18:00:00Z',
    course_group_activity_id: '00000000-0000-0000-0000-000000000003',
    course_release_id: '00000000-0000-0000-0000-000000000004',
    course_release_number: 1,
    course_release_title: 'Ecuaciones diferenciales',
    created_at: '2026-08-01T12:00:00Z',
    id: '00000000-0000-0000-0000-000000000005',
    lock_version: 1,
    migration_review_required: false,
    name: 'Quiz 1',
    opens_at: '2026-08-01T12:00:00Z',
    status: 'active',
    unit_id: null,
    updated_at: '2026-08-01T12:00:00Z',
    withdrawal_note: '',
    withdrawn_at: null,
  },
  description: 'Comprueba el análisis de sistemas lineales.',
  feedback_mode: 'full_after_grading',
  id: '00000000-0000-0000-0000-000000000006',
  in_progress_attempt_id: null,
  item_count: 12,
  latest_attempt_id: null,
  latest_attempt_status: null,
  maximum_score: '100.000',
  pass_basis_points: 7000,
  status: 'active',
  time_limit_minutes: 45,
};

describe('CourseAssessmentBriefing', () => {
  it('explains the attempt before starting it', () => {
    render(
      <CourseAssessmentBriefing
        assignment={assignment}
        returnHref="/curso/actividad"
        slug="institucion"
      />,
    );

    expect(screen.getByText('45 min')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(screen.getByText('2 de 2')).toBeInTheDocument();
    expect(screen.getByText('70 %')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /iniciar evaluación/i }),
    ).toBeEnabled();
  });

  it('does not start while the assignment is unavailable', async () => {
    render(
      <CourseAssessmentBriefing
        assignment={{ ...assignment, status: 'revoked' }}
        returnHref="/curso/actividad"
        slug="institucion"
      />,
    );

    const button = screen.getByRole('button', {
      name: /iniciar evaluación/i,
    });
    expect(button).toBeDisabled();
    fireEvent.click(button);
    await waitFor(() => expect(mutateAsync).not.toHaveBeenCalled());
  });
});
