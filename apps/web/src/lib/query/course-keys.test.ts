import { describe, expect, it } from 'vitest';

import { courseKeys } from './course-keys';

describe('courseKeys', () => {
  it('keeps organization, course and revision scope in every outline key', () => {
    expect(courseKeys.outline('institucion', 'algebra', 'revision-1')).toEqual([
      'organizations',
      'institucion',
      'courses',
      'algebra',
      'revision-1',
      'outline',
    ]);
  });
});
