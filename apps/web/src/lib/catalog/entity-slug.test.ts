import { describe, expect, it } from 'vitest';

import { entitySlug } from './entity-slug';

describe('entitySlug', () => {
  it('derives a stable technical identifier from a Spanish display name', () => {
    expect(entitySlug('  Álgebra y Geometría 10°  ')).toBe(
      'algebra-y-geometria-10',
    );
  });
});
