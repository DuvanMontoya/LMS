import { describe, expect, it } from 'vitest';

import { buildQuestionDefinition, QUESTION_TYPES } from './authoring-forms';

describe('assessment authoring contracts', () => {
  it('exposes exactly the nine approved question types', () => {
    expect(QUESTION_TYPES.map(([value]) => value)).toEqual([
      'single_choice',
      'multiple_choice',
      'true_false',
      'numeric',
      'short_text',
      'long_text',
      'ordering',
      'matching',
      'mathematical_expression',
    ]);
  });

  it('builds a mathematical expression without leaking its key publicly', () => {
    const definition = buildQuestionDefinition({
      accepted: '["Add","x",1]',
      allowedFunctions: 'Sin',
      allowedSymbols: 'x',
      code: 'MATH-001',
      feedbackCorrect: 'Correcta.',
      feedbackGeneral: '',
      feedbackIncorrect: 'Revisa.',
      mathAssumptions: 'x:real',
      mathLatex: 'x+1',
      mathStrategy: 'structural',
      options: '',
      prompt: 'Simplifica la expresión.',
      tolerance: '0',
      type: 'mathematical_expression',
    });

    expect(definition.public).toMatchObject({
      allowed_functions: ['Sin'],
      allowed_symbols: ['x'],
      type: 'mathematical_expression',
    });
    expect(definition.public).not.toHaveProperty('expected_mathjson');
    expect(definition.grading).toMatchObject({
      equivalence_strategy: 'structural',
      expected_mathjson: ['Add', 'x', 1],
      symbol_assumptions: { x: ['real'] },
    });
  });
});
