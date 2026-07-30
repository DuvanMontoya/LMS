import { describe, expect, it } from 'vitest';

import { completeContentFixture } from '../test-fixtures';
import {
  contentSafetyError,
  safeContentHref,
  validateContentDocument,
} from './validator';

describe('canonical content schema', () => {
  it('accepts the complete semantic fixture through Ajv 2020-12', () => {
    const result = validateContentDocument(completeContentFixture());
    if (!result.valid) throw new Error(result.message);
    expect(result.valid).toBe(true);
  });

  it('rejects unknown nodes, extra attributes, and unsafe shapes', () => {
    const unknown = structuredClone(completeContentFixture()) as unknown as {
      content: Array<Record<string, unknown>>;
    };
    unknown.content[0] = { type: 'script' };
    const result = validateContentDocument(unknown);
    expect(result.valid).toBe(false);
    if (!result.valid) expect(result.message).toContain('type');
  });

  it('rejects unsafe links and dangerous MathJax capabilities before save', () => {
    expect(safeContentHref('https://example.test/resource')).toBe(true);
    expect(safeContentHref('/recursos/1')).toBe(true);
    expect(safeContentHref('javascript:alert(1)')).toBe(false);
    const malicious = structuredClone(completeContentFixture());
    const displayMath = malicious.content[3];
    if (!displayMath || displayMath.type !== 'displayMath')
      throw new Error('Fixture math node missing.');
    displayMath.attrs.latex = String.raw`\require{texhtml}`;
    expect(contentSafetyError(malicious)).toMatch(/fórmula/i);
  });
});
