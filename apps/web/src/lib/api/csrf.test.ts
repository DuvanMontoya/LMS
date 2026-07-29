import { describe, expect, it } from 'vitest';

import { readCookie } from './csrf';

describe('readCookie', () => {
  it('matches an exact cookie name and decodes its value', () => {
    expect(readCookie('other=value; csrftoken=uno%20dos', 'csrftoken')).toBe(
      'uno dos',
    );
  });

  it('does not return partial or malformed cookie values', () => {
    expect(readCookie('notcsrftoken=value; csrf=%', 'csrftoken')).toBeNull();
  });
});
