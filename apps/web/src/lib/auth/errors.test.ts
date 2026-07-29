import { describe, expect, it } from 'vitest';

import { mapAllauthErrorToSpanish, toAuthApiError } from './errors';

describe('allauth error mapping', () => {
  it('maps structured field errors without exposing backend detail', () => {
    const error = toAuthApiError(400, {
      errors: [{ code: 'incorrect_code', param: 'key' }],
    });
    expect(error.fieldErrors.key).toBe('incorrect_code');
    expect(error.message).toBe('El código no es válido o ya expiró.');
  });

  it('uses a safe generic message for unexpected failures', () => {
    expect(mapAllauthErrorToSpanish('unknown', null)).toBe(
      'No fue posible completar la solicitud. Inténtalo nuevamente.',
    );
  });
});
