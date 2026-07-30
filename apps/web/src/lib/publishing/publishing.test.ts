import { describe, expect, it } from 'vitest';

import { libraryKeys, publicationKeys } from '@/lib/query/publication-keys';
import { formatDuration, publicationStatusLabel, shortDigest } from './labels';
import { validateReleaseSnapshot } from './schema/validator';

describe('publishing frontend contracts', () => {
  it('builds stable organization-scoped query keys', () => {
    expect(publicationKeys.status('institucion', 'algebra')).toEqual([
      'organizations',
      'institucion',
      'courses',
      'algebra',
      'publication',
      'status',
    ]);
    expect(publicationKeys.verification('institucion', 'algebra', 2)).toEqual([
      'organizations',
      'institucion',
      'courses',
      'algebra',
      'publication',
      'releases',
      2,
      'verification',
    ]);
    expect(libraryKeys.unit('institucion', 'algebra', 'unit-1')).toEqual([
      'organizations',
      'institucion',
      'library',
      'courses',
      'algebra',
      'units',
      'unit-1',
    ]);
  });

  it('uses sober labels and digest presentation', () => {
    expect(publicationStatusLabel('active')).toBe('Activa');
    expect(publicationStatusLabel('withdrawn')).toBe('Retirada');
    expect(formatDuration(125)).toBe('2 h 5 min');
    expect(shortDigest('a'.repeat(64))).toBe('aaaaaaaaaaaa…aaaaaaaa');
  });

  it('rejects an unexpected release contract without correcting it', () => {
    const value = { schema_version: 1, unexpected: true };
    const result = validateReleaseSnapshot(value);
    expect(result.valid).toBe(false);
    expect(value).toEqual({ schema_version: 1, unexpected: true });
  });
});
