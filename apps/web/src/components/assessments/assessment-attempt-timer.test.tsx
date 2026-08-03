import { act, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { AssessmentAttemptTimer } from './attempt-runner';

describe('AssessmentAttemptTimer', () => {
  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  it('keeps the remaining time in the player header', () => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-08-03T12:00:00Z'));
    render(<AssessmentAttemptTimer expiresAt="2026-08-03T12:30:00Z" />);
    act(() => vi.advanceTimersByTime(0));

    expect(screen.getByRole('timer')).toHaveTextContent('00:30:00');
  });
});
