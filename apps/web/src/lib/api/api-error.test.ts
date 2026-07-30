import { describe, expect, it } from 'vitest';

import { apiErrorCode, apiErrorMessage } from './api-error';

describe('API error extraction', () => {
  it('uses structured response bodies already parsed by openapi-fetch', () => {
    const error = {
      code: 'member_could_not_be_added',
      detail: 'No fue posible agregar a la persona indicada.',
    };
    expect(apiErrorMessage(error, 'Error neutral')).toBe(error.detail);
    expect(apiErrorCode(error)).toBe(error.code);
  });

  it('uses field and nested error messages without reading a consumed body', () => {
    expect(
      apiErrorMessage(
        { email: ['Escribe un correo electrónico válido.'] },
        'Error neutral',
      ),
    ).toBe('Escribe un correo electrónico válido.');
    expect(apiErrorMessage(undefined, 'Error neutral')).toBe('Error neutral');
  });
});
