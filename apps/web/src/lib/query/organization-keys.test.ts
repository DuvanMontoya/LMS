import { describe, expect, it } from 'vitest';

import { accessKeys, organizationKeys } from './organization-keys';

describe('organization query keys', () => {
  it('keeps access and tenant resources distinct', () => {
    expect(accessKeys.context()).toEqual(['access', 'context']);
    expect(organizationKeys.membersRoot('colegio')).toEqual([
      'organizations',
      'colegio',
      'members',
    ]);
    expect(organizationKeys.member('colegio', 'membership-id')).toEqual([
      'organizations',
      'colegio',
      'members',
      'membership-id',
    ]);
  });
});
