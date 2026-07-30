import { describe, expect, it } from 'vitest';

import {
  validateAssessmentResponse,
  validateQuestionPublic,
} from './validator';

const prompt = {
  content: [
    {
      attrs: { nodeId: '30000000-0000-4000-8000-000000000001' },
      content: [{ text: 'Selecciona.', type: 'text' }],
      type: 'paragraph',
    },
  ],
  type: 'doc',
};

describe('assessment browser schemas', () => {
  it('validates a public question without accepting grading keys', () => {
    const valid = validateQuestionPublic({
      options: [
        { id: 'a', label: 'A' },
        { id: 'b', label: 'B' },
      ],
      prompt,
      schema_version: 1,
      type: 'single_choice',
    });
    expect(valid.valid).toBe(true);
    const leaked = validateQuestionPublic({
      grading: { correct_option_ids: ['a'] },
      options: [
        { id: 'a', label: 'A' },
        { id: 'b', label: 'B' },
      ],
      prompt,
      schema_version: 1,
      type: 'single_choice',
    });
    expect(leaked.valid).toBe(false);
  });

  it('validates typed responses and rejects mass assignment', () => {
    expect(
      validateAssessmentResponse({
        schema_version: 1,
        type: 'numeric',
        value: '12.5',
      }).valid,
    ).toBe(true);
    expect(
      validateAssessmentResponse({
        score: '10',
        schema_version: 1,
        type: 'numeric',
        value: '12.5',
      }).valid,
    ).toBe(false);
  });
});
