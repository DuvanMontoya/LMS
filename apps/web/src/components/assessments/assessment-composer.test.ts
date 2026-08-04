import { describe, expect, it } from 'vitest';

import {
  publicQuestionExcerpt,
  questionContentFeatures,
} from './assessment-composer';

describe('questionContentFeatures', () => {
  it('detects mathematical, image and code content from the public snapshot', () => {
    expect(
      questionContentFeatures({
        prompt: {
          content: [
            { attrs: { latex: 'x^2' }, type: 'math_inline' },
            { attrs: { assetVersionId: 'asset-id' }, type: 'image' },
            { attrs: { language: 'python' }, type: 'codeBlock' },
          ],
        },
      }),
    ).toEqual({ hasCode: true, hasImage: true, hasMath: true });
  });

  it('does not label plain text with unsupported features', () => {
    expect(
      questionContentFeatures({
        prompt: { content: [{ text: 'Texto sencillo', type: 'text' }] },
      }),
    ).toEqual({ hasCode: false, hasImage: false, hasMath: false });
  });
});

describe('publicQuestionExcerpt', () => {
  it('preserves inline and display math delimiters for the visual preview', () => {
    expect(
      publicQuestionExcerpt({
        prompt: {
          content: [
            { text: 'Resuelve', type: 'text' },
            { attrs: { latex: 'x^2=9' }, type: 'math_inline' },
            { attrs: { latex: '\\int_0^1 x\\,dx' }, type: 'math_block' },
          ],
        },
      }),
    ).toBe('Resuelve $x^2=9$ $$\\int_0^1 x\\,dx$$');
  });
});
