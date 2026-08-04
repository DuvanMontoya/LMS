import { describe, expect, it } from 'vitest';

import { distributeBasisPoints } from './grading-scheme-card';

describe('distributeBasisPoints', () => {
  it.each([
    [1, [10_000]],
    [2, [5_000, 5_000]],
    [3, [3_334, 3_333, 3_333]],
  ])('distributes 100 percent across %i activities', (count, expected) => {
    const weights = distributeBasisPoints(count);

    expect(weights).toEqual(expected);
    expect(weights.reduce((sum, weight) => sum + weight, 0)).toBe(10_000);
  });

  it('returns no weights when there are no activities', () => {
    expect(distributeBasisPoints(0)).toEqual([]);
  });
});
