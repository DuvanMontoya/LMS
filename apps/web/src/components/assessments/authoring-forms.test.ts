import { describe, expect, it } from 'vitest';

import { QUESTION_TYPES } from './authoring-forms';

describe('assessment authoring contracts', () => {
  it('exposes exactly the eight approved question types', () => {
    expect(QUESTION_TYPES.map(([value]) => value)).toEqual([
      'single_choice',
      'multiple_choice',
      'true_false',
      'numeric',
      'short_text',
      'long_text',
      'ordering',
      'matching',
    ]);
  });
});
