import { describe, expect, it } from 'vitest';

import { primaryWorkspaceHref } from './workspace-route';

describe('primaryWorkspaceHref', () => {
  it.each([
    ['owner', '/organizaciones/academia/miembros'],
    ['administrator', '/organizaciones/academia/aprendizaje/cohortes'],
    ['instructor', '/organizaciones/academia/aprendizaje/mis-asignaturas'],
    ['author', '/organizaciones/academia/cursos/autoria'],
    ['reviewer', '/organizaciones/academia/cursos/autoria'],
    ['learner', '/organizaciones/academia/aprendizaje'],
  ] as const)(
    'routes %s to its primary existing workspace',
    (role, expected) => {
      expect(primaryWorkspaceHref('academia', [role])).toBe(expected);
    },
  );
});
