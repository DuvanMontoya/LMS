import { describe, expect, it } from 'vitest';

import { capabilityLabel, hasCapability, roleLabel, sortRoles } from './labels';

describe('organization labels', () => {
  it('translates and stably orders roles', () => {
    expect(roleLabel('owner')).toBe('Propietario');
    expect(sortRoles(['learner', 'administrator'])).toEqual([
      'administrator',
      'learner',
    ]);
  });

  it('uses readable capability labels without turning unknown values into UI codes', () => {
    expect(capabilityLabel('membership.add')).toBe('Añadir miembros');
    expect(capabilityLabel('future.capability')).toBe('Permiso institucional');
    expect(hasCapability(['membership.add'], 'membership.add')).toBe(true);
  });
});
