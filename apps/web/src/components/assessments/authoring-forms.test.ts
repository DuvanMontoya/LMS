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
      promptMath: '',
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

  it('pins rich prompt resources and informative images to individual choices', () => {
    const definition = buildQuestionDefinition(
      {
        accepted: 'o1',
        allowedFunctions: '',
        allowedSymbols: 'x',
        code: 'MEDIA-001',
        feedbackCorrect: 'Correcta.',
        feedbackGeneral: '',
        feedbackIncorrect: 'Revisa.',
        mathAssumptions: 'x:real',
        mathLatex: '',
        mathStrategy: 'structural',
        options: 'Parábola A\nParábola B',
        prompt: 'Selecciona la gráfica correcta.',
        promptMath: 'y=x^2',
        tolerance: '0',
        type: 'single_choice',
      },
      {
        optionMath: { o1: 'y=x^2' },
        optionMedia: {
          o1: {
            alt_text: 'Parábola abierta hacia arriba.',
            asset_version_id: '50000000-0000-4000-8000-000000000001',
            kind: 'image',
            long_description: 'El vértice está en el origen.',
          },
        },
        promptNodes: [
          {
            attrs: {
              altText: 'Plano cartesiano.',
              assetVersionId: '50000000-0000-4000-8000-000000000002',
              decorative: false,
              displaySize: 'large',
              nodeId: '50000000-0000-4000-8000-000000000003',
            },
            type: 'imageAsset',
          },
        ],
      },
    );

    expect(
      (
        definition.public.options as Array<{
          id: string;
          media?: { asset_version_id: string };
        }>
      )[0],
    ).toMatchObject({
      id: 'o1',
      math_latex: 'y=x^2',
      media: {
        asset_version_id: '50000000-0000-4000-8000-000000000001',
      },
    });
    expect(
      (definition.public.prompt as { content: unknown[] }).content,
    ).toHaveLength(3);
    expect(JSON.stringify(definition.public)).not.toContain(
      'correct_option_ids',
    );
  });
});
