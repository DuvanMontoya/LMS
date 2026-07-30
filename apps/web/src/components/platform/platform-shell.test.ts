import { courseWorkspaceBase } from './platform-shell';

describe('courseWorkspaceBase', () => {
  const organizationBase = '/organizaciones/academia';

  it('keeps the current course context across its nested routes', () => {
    expect(
      courseWorkspaceBase(
        '/organizaciones/academia/cursos/calculo/estructura',
        organizationBase,
      ),
    ).toBe('/organizaciones/academia/cursos/calculo');
    expect(
      courseWorkspaceBase(
        '/organizaciones/academia/cursos/calculo/unidades/unit-1/contenido',
        organizationBase,
      ),
    ).toBe('/organizaciones/academia/cursos/calculo');
  });

  it('does not mistake the course list or creation form for a workspace', () => {
    expect(
      courseWorkspaceBase('/organizaciones/academia/cursos', organizationBase),
    ).toBeUndefined();
    expect(
      courseWorkspaceBase(
        '/organizaciones/academia/cursos/nuevo',
        organizationBase,
      ),
    ).toBeUndefined();
  });

  it('does not leak context across organizations', () => {
    expect(
      courseWorkspaceBase(
        '/organizaciones/otra/cursos/calculo',
        organizationBase,
      ),
    ).toBeUndefined();
  });
});
