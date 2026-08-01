import { describe, expect, it } from 'vitest';

import {
  ageFromBirthDate,
  educationInstitutionApplies,
  suggestedDocument,
} from './member-profile-options';

describe('Colombian member profile helpers', () => {
  const today = new Date('2026-08-01T12:00:00-05:00');

  it('calculates age without advancing before the birthday', () => {
    expect(ageFromBirthDate('2008-08-02', today)).toBe(17);
    expect(ageFromBirthDate('2008-08-01', today)).toBe(18);
  });

  it('suggests the ordinary Colombian identity document by age', () => {
    expect(suggestedDocument(6)).toBe('RC');
    expect(suggestedDocument(7)).toBe('TI');
    expect(suggestedDocument(17)).toBe('TI');
    expect(suggestedDocument(18)).toBe('CC');
  });

  it('asks for an institution only when the education stage uses one', () => {
    expect(educationInstitutionApplies('school')).toBe(true);
    expect(educationInstitutionApplies('university')).toBe(true);
    expect(educationInstitutionApplies('not_studying')).toBe(false);
  });
});
