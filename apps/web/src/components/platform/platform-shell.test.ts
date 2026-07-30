import { courseWorkspaceBase, isNavigationItemActive } from './platform-shell';

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

describe('isNavigationItemActive', () => {
  it('keeps the student learning entry separate from administration routes', () => {
    const item = {
      activePrefixes: ['/organizaciones/academia/aprender/'],
      exact: true,
      href: '/organizaciones/academia/aprendizaje',
    };

    expect(
      isNavigationItemActive(item, '/organizaciones/academia/aprendizaje'),
    ).toBe(true);
    expect(
      isNavigationItemActive(item, '/organizaciones/academia/aprender/calculo'),
    ).toBe(true);
    expect(
      isNavigationItemActive(
        item,
        '/organizaciones/academia/aprendizaje/cohortes',
      ),
    ).toBe(false);
  });

  it('keeps learning delivery active across cohort and enrollment routes', () => {
    const item = {
      activePrefixes: ['/organizaciones/academia/aprendizaje/matriculas'],
      href: '/organizaciones/academia/aprendizaje/cohortes',
    };

    expect(
      isNavigationItemActive(
        item,
        '/organizaciones/academia/aprendizaje/cohortes/cohort-1',
      ),
    ).toBe(true);
    expect(
      isNavigationItemActive(
        item,
        '/organizaciones/academia/aprendizaje/matriculas/enrollment-1',
      ),
    ).toBe(true);
  });
});
