import { describe, expect, it } from 'vitest';

import { sanitizeReturnPath } from './return-path';

describe('sanitizeReturnPath', () => {
  it('preserves an internal path, query and fragment', () => {
    expect(sanitizeReturnPath('/estudiar?unit=1#section')).toBe(
      '/estudiar?unit=1#section',
    );
  });

  it.each([
    'https://evil.example',
    '//evil.example',
    '/%2F%2Fevil.example',
    'javascript:alert(1)',
    '/\\evil.example',
    '/auth/iniciar-sesion',
  ])('rejects unsafe return paths', (value) => {
    expect(sanitizeReturnPath(value)).toBe('/estudiar');
  });
});
