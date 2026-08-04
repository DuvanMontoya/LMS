import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { components } from '@/lib/api/generated/platform';

import {
  CourseApprovalStatus,
  courseApprovalState,
} from './course-approval-status';

const progress: components['schemas']['Progress'] = {
  attendance: {
    basis_points: 6250,
    minimum_basis_points: 8000,
    satisfied: false,
  },
  blockers: [
    { code: 'required_activities', message: 'Completa todas las actividades.' },
    { code: 'minimum_grade_not_met', message: 'Alcanza la nota mínima.' },
    { code: 'minimum_attendance_not_met', message: 'Cumple la asistencia.' },
  ],
  completed_at: null,
  completed_required_activities: 8,
  completed_units: 7,
  completion: {
    completed_required: 8,
    satisfied: false,
    total_required: 14,
  },
  grade: {
    basis_points: 6800,
    minimum_basis_points: 7000,
    satisfied: false,
  },
  is_complete: false,
  last_activity_at: '2026-08-04T12:00:00Z',
  mastery: {
    evidenced_count: 0,
    evidenced_objective_ids: [],
    total_objectives: 0,
  },
  percent: '57.14',
  percent_basis_points: 5714,
  progress_version: 5,
  started_at: '2026-08-04T11:00:00Z',
  status: 'in_progress',
  total_required_activities: 14,
  total_units: 12,
};

describe('CourseApprovalStatus', () => {
  it('shows the composed approval decision and every governing criterion', () => {
    render(
      <CourseApprovalStatus accessState="available" progress={progress} />,
    );

    expect(screen.getByText('En progreso')).toBeInTheDocument();
    expect(screen.getByText('8/14')).toBeInTheDocument();
    expect(screen.getByText('68 %')).toBeInTheDocument();
    expect(screen.getByText('mínimo 70 %')).toBeInTheDocument();
    expect(screen.getByText('62,5 %')).toBeInTheDocument();
    expect(screen.getByText('mínimo 80 %')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Completa todas las actividades; además, 2 criterios más.',
      ),
    ).toBeInTheDocument();
  });

  it('marks a completed projection as approved before considering access state', () => {
    expect(
      courseApprovalState(
        { ...progress, blockers: [], is_complete: true, status: 'completed' },
        'ended',
      ),
    ).toBe('approved');
  });

  it('distinguishes pending and terminal non-approval', () => {
    expect(
      courseApprovalState(
        {
          ...progress,
          last_activity_at: null,
          started_at: null,
          status: 'not_started',
        },
        'available',
      ),
    ).toBe('pending');
    expect(courseApprovalState(progress, 'ended')).toBe('not_approved');
  });
});
