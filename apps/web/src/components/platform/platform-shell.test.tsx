import { cleanup, render, within } from '@testing-library/react';
import { vi } from 'vitest';

import { TooltipProvider } from '@/components/ui/tooltip';

let pathname = '/organizaciones/academia';

vi.mock('next/navigation', () => ({
  usePathname: () => pathname,
  useRouter: () => ({ push: vi.fn(), refresh: vi.fn(), replace: vi.fn() }),
}));

vi.mock('@/hooks/use-mobile', () => ({
  useIsMobile: () => false,
}));

vi.mock('@/components/notifications/notification-badge', () => ({
  NotificationBadge: () => null,
}));

vi.mock('@/components/auth/logout-button', () => ({
  LogoutButton: () => <button type="button">Cerrar sesión</button>,
}));

import {
  courseWorkspaceBase,
  isNavigationItemActive,
  PlatformShell,
} from './platform-shell';

type Role =
  'owner' | 'administrator' | 'author' | 'reviewer' | 'instructor' | 'learner';

function renderNavigation(role: Role, capabilities: readonly string[]) {
  pathname = '/organizaciones/academia';
  const { container } = render(
    <TooltipProvider>
      <PlatformShell
        displayName={`Cuenta ${role}`}
        isPlatformOperator={false}
        organizations={[
          {
            capabilities,
            id: 'organization-id',
            membership_id: 'membership-id',
            name: 'Academia',
            roles: [role],
            slug: 'academia',
          },
        ]}
      >
        <main>Contenido</main>
      </PlatformShell>
    </TooltipProvider>,
  );
  const sidebar = container.querySelector('[data-sidebar="sidebar"]');
  if (!sidebar) throw new Error('Sidebar was not rendered.');
  return within(sidebar as HTMLElement);
}

describe('PlatformShell role navigation', () => {
  it('keeps global utilities and redundant landing links out of every role sidebar', () => {
    for (const role of [
      'owner',
      'administrator',
      'author',
      'reviewer',
      'instructor',
      'learner',
    ] as const) {
      const navigation = renderNavigation(role, []);
      for (const redundant of [
        'Inicio',
        'Mi perfil',
        'Buscar',
        'Resumen institucional',
      ]) {
        expect(
          navigation.queryByRole('link', { name: redundant }),
        ).not.toBeInTheDocument();
      }
      cleanup();
    }
  });

  it('keeps authors and reviewers out of teaching operations', () => {
    for (const role of ['author', 'reviewer'] as const) {
      const navigation = renderNavigation(role, [
        'catalog.view',
        'course.authoring.view',
        'course.approved.view',
        'course.published.view',
        'asset.library.view',
        'assessment.authoring.view',
        'assessment.bank.view',
      ]);

      expect(navigation.getByText('Autoría y contenido')).toBeInTheDocument();
      expect(navigation.getByRole('link', { name: 'Currículo' })).toBeVisible();
      expect(
        navigation.getByRole('link', { name: 'Autoría de evaluaciones' }),
      ).toBeVisible();
      expect(
        navigation.queryByRole('link', { name: 'Mis grupos' }),
      ).not.toBeInTheDocument();
      expect(
        navigation.queryByRole('link', { name: 'Clases en vivo' }),
      ).not.toBeInTheDocument();
      expect(
        navigation.queryByRole('link', { name: 'Evaluación y calificación' }),
      ).not.toBeInTheDocument();
      expect(
        navigation.queryByRole('link', { name: 'Personas' }),
      ).not.toBeInTheDocument();
      cleanup();
    }
  });

  it('gives instructors a scoped teaching workspace without authoring routes', () => {
    const navigation = renderNavigation('instructor', [
      'catalog.teaching_responsibility.view',
      'course.approved.view',
      'course.published.view',
      'learning.cohort.view',
      'learning.enrollment.view',
      'learning.progress.view',
      'scheduling.view',
      'assessment.delivery.view',
      'assessment.results.view',
      'assessment.grading.manage',
      'asset.library.view',
    ]);

    expect(navigation.getByText('Docencia')).toBeInTheDocument();
    expect(
      navigation.getByRole('link', { name: 'Mis asignaturas' }),
    ).toBeVisible();
    expect(navigation.getByRole('link', { name: 'Mis grupos' })).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Evaluación y calificación' }),
    ).toBeVisible();
    expect(
      navigation.queryByRole('link', { name: 'Currículo' }),
    ).not.toBeInTheDocument();
    expect(
      navigation.queryByRole('link', { name: 'Autoría de evaluaciones' }),
    ).not.toBeInTheDocument();
    expect(
      navigation.queryByRole('link', { name: 'Personas' }),
    ).not.toBeInTheDocument();
  });

  it('keeps learners inside their personal learning surface', () => {
    const navigation = renderNavigation('learner', [
      'assessment.attempt',
      'scheduling.view',
    ]);

    expect(navigation.getAllByText('Mi aprendizaje')).toHaveLength(2);
    expect(
      navigation.getByRole('link', { name: 'Mi aprendizaje' }),
    ).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Mi calendario' }),
    ).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Mis clases en vivo' }),
    ).toBeVisible();
    expect(
      navigation.queryByRole('link', { name: 'Resumen institucional' }),
    ).not.toBeInTheDocument();
    expect(
      navigation.queryByRole('link', { name: 'Cursos' }),
    ).not.toBeInTheDocument();
    expect(
      navigation.queryByRole('link', { name: 'Personas' }),
    ).not.toBeInTheDocument();
  });

  it('limits owners to institutional governance', () => {
    const navigation = renderNavigation('owner', [
      'membership.view',
      'membership.settings.view',
    ]);

    expect(navigation.getByRole('link', { name: 'Personas' })).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Configuración institucional' }),
    ).toBeVisible();
    for (const forbidden of [
      'Currículo',
      'Cursos',
      'Calendario',
      'Clases en vivo',
      'Autoría de evaluaciones',
      'Evaluación y calificación',
      'Grupos y matrículas',
    ]) {
      expect(
        navigation.queryByRole('link', { name: forbidden }),
      ).not.toBeInTheDocument();
    }
  });

  it('gives administrators operations without authoring or grading powers', () => {
    const navigation = renderNavigation('administrator', [
      'catalog.view',
      'course.approved.view',
      'course.published.view',
      'learning.cohort.view',
      'learning.enrollment.view',
      'scheduling.view',
      'assessment.delivery.view',
      'assessment.results.view',
      'assessment.gradebook.view',
      'asset.library.view',
      'membership.view',
      'membership.settings.view',
    ]);

    expect(navigation.getByText('Operación académica')).toBeInTheDocument();
    expect(navigation.getByRole('link', { name: 'Currículo' })).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Entregas y resultados' }),
    ).toBeVisible();
    expect(
      navigation.queryByRole('link', { name: 'Autoría de evaluaciones' }),
    ).not.toBeInTheDocument();
    expect(
      navigation.queryByRole('link', { name: 'Calificación manual' }),
    ).not.toBeInTheDocument();
  });
});

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
