import { describe, expect, it } from 'vitest';

import { resolvePostLoginDestination } from './post-login-destination';

const administratorContext = {
  is_platform_operator: false,
  organizations: [
    {
      capabilities: [
        'catalog.view',
        'catalog.manage',
        'course.approved.view',
        'learning.cohort.view',
      ],
      roles: ['administrator'] as const,
      slug: 'demo',
    },
  ],
};

const ownerContext = {
  is_platform_operator: false,
  organizations: [
    {
      capabilities: ['membership.view'],
      roles: ['owner'] as const,
      slug: 'demo',
    },
  ],
};

describe('resolvePostLoginDestination', () => {
  it('keeps an administrator on the curriculum route it can operate', () => {
    expect(
      resolvePostLoginDestination(
        '/organizaciones/demo/curriculo',
        administratorContext,
      ),
    ).toBe('/organizaciones/demo/curriculo');
  });

  it('sends a valid owner session away from a curricular route it cannot open', () => {
    expect(
      resolvePostLoginDestination(
        '/organizaciones/demo/curriculo',
        ownerContext,
      ),
    ).toBe('/organizaciones/demo/miembros');
  });

  it('does not turn a non-operator into a platform administrator', () => {
    expect(
      resolvePostLoginDestination(
        '/administracion/organizaciones',
        ownerContext,
      ),
    ).toBe('/estudiar');
  });

  it('keeps safe public return paths unchanged', () => {
    expect(resolvePostLoginDestination('/estudiar', ownerContext)).toBe(
      '/estudiar',
    );
  });
});
