import { describe, expect, it } from 'vitest';

import {
  normalizeMathJsonNumbers,
  validateClientMathJson,
} from './math-expression-field';

describe('safe mathematical expression payloads', () => {
  it('accepts only the configured symbols and functions', () => {
    expect(() =>
      validateClientMathJson(
        ['Add', ['Sin', 'x'], 1],
        new Set(['x']),
        new Set(['Sin']),
      ),
    ).not.toThrow();
    for (const value of [
      ['Assign', 'x', 1],
      ['Sin', 'x'],
      ['Add', 'secret', 1],
      ['Power', 'x', 21],
      { fn: 'Add', args: ['x', 1] },
    ]) {
      expect(() =>
        validateClientMathJson(value, new Set(['x']), new Set()),
      ).toThrow();
    }
  });

  it('normalizes decimal numbers as bounded decimal strings', () => {
    expect(normalizeMathJsonNumbers(['Add', 'x', 0.5])).toEqual([
      'Add',
      'x',
      '0.5',
    ]);
    expect(() => normalizeMathJsonNumbers(Number.POSITIVE_INFINITY)).toThrow();
    expect(() => normalizeMathJsonNumbers(1e-30)).toThrow();
  });
});
