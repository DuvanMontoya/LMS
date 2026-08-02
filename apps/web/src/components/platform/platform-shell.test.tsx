import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from '@testing-library/react';
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

import { isNavigationItemActive, PlatformShell } from './platform-shell';

type Role =
  'owner' | 'administrator' | 'author' | 'reviewer' | 'instructor' | 'learner';

function renderNavigation(
  role: Role,
  capabilities: readonly string[],
  currentPath = '/organizaciones/academia',
) {
  pathname = currentPath;
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

  it('places the contextual help immediately before sign out in the account menu', async () => {
    renderNavigation('administrator', []);
    fireEvent.pointerDown(
      screen.getByRole('button', {
        name: 'Abrir menú de cuenta de Cuenta administrator',
      }),
    );
    const help = await screen.findByRole('menuitem', {
      name: 'Ayuda y guía de uso',
    });
    const signOut = screen.getByRole('button', { name: 'Cerrar sesión' });

    expect(help).toHaveAttribute('href', '/organizaciones/academia/ayuda');
    expect(
      help.compareDocumentPosition(signOut) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
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
        navigation.getByRole('link', { name: 'Panel de evaluaciones' }),
      ).toBeVisible();
      expect(
        navigation.queryByRole('link', { name: 'Mis grupos' }),
      ).not.toBeInTheDocument();
      expect(
        navigation.queryByRole('link', { name: 'Clases en vivo' }),
      ).not.toBeInTheDocument();
      expect(
        navigation.queryByRole('link', { name: 'Entregas' }),
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
    expect(navigation.getByRole('link', { name: 'Entregas' })).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Calificación manual' }),
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
      navigation.queryByRole('link', { name: 'Configuración' }),
    ).not.toBeInTheDocument();
    for (const forbidden of [
      'Currículo',
      'Cursos',
      'Calendario',
      'Clases en vivo',
      'Panel de evaluaciones',
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
      'catalog.teaching_responsibility.manage',
      'course.approved.view',
      'course.published.view',
      'learning.cohort.view',
      'learning.enrollment.view',
      'scheduling.view',
      'assessment.delivery.view',
      'assessment.results.view',
      'assessment.gradebook.view',
      'assessment.analytics.view',
      'asset.library.view',
      'membership.view',
      'membership.settings.view',
    ]);

    expect(navigation.getByText('Institución')).toBeInTheDocument();
    expect(navigation.getByText('Diseño académico')).toBeInTheDocument();
    expect(navigation.getByText('Operación académica')).toBeInTheDocument();
    expect(navigation.getByText('Herramientas académicas')).toBeInTheDocument();
    expect(navigation.getByRole('link', { name: 'Currículo' })).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Responsabilidades docentes' }),
    ).toBeVisible();
    expect(navigation.getByRole('link', { name: 'Grupos' })).toBeVisible();
    expect(navigation.getByRole('link', { name: 'Entregas' })).toBeVisible();
    expect(
      navigation.getByRole('link', { name: 'Analítica de ítems' }),
    ).toBeVisible();
    expect(
      navigation.queryByRole('link', { name: 'Panel de evaluaciones' }),
    ).not.toBeInTheDocument();
    expect(
      navigation.queryByRole('link', { name: 'Calificación manual' }),
    ).not.toBeInTheDocument();

    const curriculum = navigation.getByRole('link', { name: 'Currículo' });
    const responsibilities = navigation.getByRole('link', {
      name: 'Responsabilidades docentes',
    });
    const courses = navigation.getByRole('link', { name: 'Cursos' });
    const courseGroup = navigation.getByRole('link', {
      name: 'Secciones',
    });
    expect(
      curriculum.compareDocumentPosition(responsibilities) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      responsibilities.compareDocumentPosition(courses) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      courses.compareDocumentPosition(courseGroup) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  it('keeps routes stable and never reveals a contextual sidebar section', () => {
    const capabilities = [
      'assessment.delivery.view',
      'assessment.results.view',
      'assessment.gradebook.view',
      'assessment.analytics.view',
    ];
    const baseNavigation = renderNavigation('administrator', capabilities);
    expect(
      baseNavigation.getByRole('link', { name: 'Entregas' }),
    ).toBeVisible();
    expect(
      baseNavigation.queryByRole('link', { name: 'Calificación manual' }),
    ).not.toBeInTheDocument();
    cleanup();

    const evaluationNavigation = renderNavigation(
      'administrator',
      capabilities,
      '/organizaciones/academia/evaluaciones/entregas',
    );
    expect(
      evaluationNavigation.getByRole('link', { name: 'Entregas' }),
    ).toBeVisible();
    expect(
      evaluationNavigation.getByRole('link', { name: 'Resultados' }),
    ).toBeVisible();
    expect(
      evaluationNavigation.getByRole('link', {
        name: 'Libros de calificaciones',
      }),
    ).toBeVisible();
    expect(
      evaluationNavigation.getByRole('link', { name: 'Analítica de ítems' }),
    ).toBeVisible();
    for (const forbidden of [
      'Nueva evaluación',
      'Calificación manual',
      'Recalificación',
      'Curso actual',
    ]) {
      expect(
        evaluationNavigation.queryByRole('link', { name: forbidden }),
      ).not.toBeInTheDocument();
    }
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
