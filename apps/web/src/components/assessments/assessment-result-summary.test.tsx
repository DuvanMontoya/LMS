import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import type { AssessmentResult } from '@/lib/assessments/server';

import { AssessmentResultSummary } from './assessment-result-summary';

vi.mock('@/components/content/mathjax-formula', () => ({
  MathJaxFormula: ({ latex }: { latex: string }) => (
    <span data-testid="rendered-math">{latex}</span>
  ),
}));

const result: AssessmentResult = {
  attempt_number: 1,
  auto_score: '1.000',
  basis_points: 10000,
  feedback: [
    {
      attempt_item_id: '00000000-0000-0000-0000-000000000001',
      manual_feedback: 'Comprueba $m=(y_2-y_1)/(x_2-x_1)$.',
      maximum: '1.000',
      message: 'Introduce $u=3x$.',
      score: '1.000',
    },
  ],
  graded_at: '2026-08-04T18:00:00Z',
  id: '00000000-0000-0000-0000-000000000002',
  manual_score: '0.000',
  maximum_score: '1.000',
  passed: true,
  status: 'graded',
  submitted_at: '2026-08-04T17:59:00Z',
  total_score: '1.000',
};

describe('AssessmentResultSummary', () => {
  it('renders inline mathematics in automatic and manual feedback', () => {
    render(
      <AssessmentResultSummary
        attemptId={result.id}
        result={result}
        slug="institucion"
      />,
    );

    expect(screen.getAllByTestId('rendered-math')).toHaveLength(2);
    expect(screen.getByText('u=3x')).toBeInTheDocument();
    expect(screen.getByText('m=(y_2-y_1)/(x_2-x_1)')).toBeInTheDocument();
  });
});
