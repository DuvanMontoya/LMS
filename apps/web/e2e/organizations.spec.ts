import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');
const requiredPassword: string = password;

const organizationSlug = 'organizacion-a';

async function login(
  page: import('@playwright/test').Page,
  email: string,
  next = `/organizaciones/${organizationSlug}`,
) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(requiredPassword);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(next, { timeout: 15_000 });
}

async function logout(page: import('@playwright/test').Page) {
  await page.goto('/estudiar');
  const accountMenu = page.getByRole('button', {
    name: /Abrir menú de cuenta/,
  });
  await expect(accountMenu).toBeVisible({ timeout: 15_000 });
  await accountMenu.click();
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL('/auth/iniciar-sesion', { timeout: 15_000 });
}

test.describe.serial('institutional organization access', () => {
  test('each role reaches every route exposed in its sidebar without a 404', async ({
    page,
  }) => {
    // The matrix follows every distinct sidebar link across six isolated roles.
    test.setTimeout(10 * 60_000);
    const roleLandings: ReadonlyArray<readonly [string, string]> = [
      [
        'owner@organizations.e2e.test',
        `/organizaciones/${organizationSlug}/miembros`,
      ],
      [
        'administrator@organizations.e2e.test',
        `/organizaciones/${organizationSlug}/aprendizaje/cohortes`,
      ],
      [
        'author@organizations.e2e.test',
        `/organizaciones/${organizationSlug}/cursos`,
      ],
      [
        'reviewer@organizations.e2e.test',
        `/organizaciones/${organizationSlug}/cursos`,
      ],
      [
        'instructor@organizations.e2e.test',
        `/organizaciones/${organizationSlug}/aprendizaje/mis-asignaturas`,
      ],
      [
        'learner@organizations.e2e.test',
        `/organizaciones/${organizationSlug}/aprendizaje`,
      ],
    ];
    for (const [email, landingPath] of roleLandings) {
      await login(page, email, landingPath);
      const sidebar = page.locator('[data-sidebar="sidebar"]');
      const hrefs = await sidebar
        .locator('a[href]')
        .evaluateAll((links) => [
          ...new Set(
            links
              .map((link) => link.getAttribute('href'))
              .filter(
                (href): href is string =>
                  href?.startsWith('/organizaciones/organizacion-a') ?? false,
              ),
          ),
        ]);

      for (const href of hrefs) {
        const response = await page.goto(href);
        expect(response?.status(), `${email} → ${href}`).not.toBe(404);
      }
      await logout(page);
    }
  });

  test('administrator follows the compact workflow and sees the course-authoring handoff', async ({
    page,
  }) => {
    await login(
      page,
      'administrator@organizations.e2e.test',
      `/organizaciones/${organizationSlug}/cursos`,
    );

    const sidebar = page.locator('[data-sidebar="sidebar"]');
    await expect(
      sidebar.getByText('Institución', { exact: true }),
    ).toBeVisible();
    await expect(
      sidebar.getByText('Diseño académico', { exact: true }),
    ).toBeVisible();
    await expect(
      sidebar.getByText('Operación académica', { exact: true }),
    ).toBeVisible();
    await expect(
      sidebar.getByText('Herramientas académicas', { exact: true }),
    ).toBeVisible();
    await expect(
      sidebar.getByRole('link', { name: 'Configuración', exact: true }),
    ).toHaveCount(0);
    for (const label of [
      'Currículo',
      'Responsabilidades docentes',
      'Cursos',
      'Grupos',
      'Calendario',
      'Clases en vivo',
      'Recursos',
    ]) {
      await expect(
        sidebar.getByRole('link', { name: label, exact: true }),
      ).toBeVisible();
    }
    expect(
      await sidebar.evaluate(
        (element) => element.scrollHeight <= element.clientHeight,
      ),
    ).toBe(true);

    await page.getByRole('button', { name: /Abrir menú de cuenta/ }).click();
    await expect(
      page.getByRole('menuitem', { name: 'Configuración', exact: true }),
    ).toHaveAttribute(
      'href',
      `/organizaciones/${organizationSlug}/configuracion`,
    );
    await page.keyboard.press('Escape');

    await expect(
      page.getByRole('region', { name: 'Acceso a la creación de cursos' }),
    ).toContainText('no la autoría del curso');
    await expect(
      page.getByRole('region', { name: 'Acceso a la creación de cursos' }),
    ).toContainText('consultar cursos aprobados y operar sus releases');
    await expect(
      page.getByRole('link', { name: 'Gestionar roles' }),
    ).toHaveAttribute('href', `/organizaciones/${organizationSlug}/miembros`);
  });

  test('owner adds, suspends, reactivates, revokes and rejoins a verified member', async ({
    page,
  }) => {
    await login(page, 'owner@organizations.e2e.test');
    await page.getByRole('link', { name: 'Gestionar miembros' }).click();
    await expect(
      page.getByRole('heading', { name: 'Miembros de Organización A' }),
    ).toBeVisible();

    await page
      .getByLabel('Correo electrónico')
      .fill('candidate@organizations.e2e.test');
    await page.getByRole('button', { name: 'Añadir miembro' }).click();
    const candidateRow = page.getByRole('row', {
      name: /candidate@organizations.e2e.test/,
    });
    await expect(candidateRow).toContainText('Activa');
    await expect(candidateRow).toContainText('Estudiante');

    await candidateRow.getByRole('button', { name: 'Suspender' }).click();
    await candidateRow
      .getByRole('button', { name: 'Confirmar suspender' })
      .click();
    await expect(candidateRow).toContainText('Suspendida');
    await candidateRow.getByRole('button', { name: 'Reactivar' }).click();
    await candidateRow
      .getByRole('button', { name: 'Confirmar reactivar' })
      .click();
    await expect(candidateRow).toContainText('Activa');
    await candidateRow.getByRole('button', { name: 'Revocar' }).click();
    await candidateRow
      .getByRole('button', { name: 'Confirmar revocar' })
      .click();
    await expect(candidateRow).toContainText('Revocada');

    await page
      .getByLabel('Correo electrónico')
      .fill('candidate@organizations.e2e.test');
    await page.getByRole('button', { name: 'Añadir miembro' }).click();
    await expect(page.getByText('La membresía fue creada.')).toBeVisible();
    await logout(page);
  });

  test('administrator can add a learner but cannot manage the owner', async ({
    page,
  }) => {
    await login(
      page,
      'administrator@organizations.e2e.test',
      `/organizaciones/${organizationSlug}/miembros`,
    );
    const ownerRow = page.getByRole('row', {
      name: /owner@organizations.e2e.test/,
    });
    await expect(
      ownerRow.getByRole('button', { name: 'Suspender' }),
    ).toHaveCount(0);
    await expect(ownerRow.getByRole('button', { name: 'Revocar' })).toHaveCount(
      0,
    );
    await expect(page.getByLabel('Propietario')).toHaveCount(0);

    await page
      .getByLabel('Correo electrónico')
      .fill('rejoin@organizations.e2e.test');
    await page.getByRole('button', { name: 'Añadir miembro' }).click();
    await expect(
      page.getByRole('row', { name: /rejoin@organizations.e2e.test/ }),
    ).toContainText('Activa');
    await logout(page);
  });

  test('learner sees only their institution and external context returns 404', async ({
    page,
  }) => {
    await login(page, 'learner@organizations.e2e.test', '/organizaciones');
    await expect(
      page.getByRole('link', { name: 'Abrir contexto institucional' }),
    ).toHaveCount(1);
    const response = await page.goto('/organizaciones/organizacion-b');
    expect(response?.status()).toBe(404);
    await logout(page);
  });

  test('@a11y checks keyboard and WCAG rules on institutional routes', async ({
    page,
  }) => {
    await login(page, 'owner@organizations.e2e.test');
    await page.getByRole('link', { name: 'Gestionar miembros' }).focus();
    await expect(
      page.getByRole('link', { name: 'Gestionar miembros' }),
    ).toBeFocused();
    for (const path of [
      '/organizaciones',
      `/organizaciones/${organizationSlug}`,
      `/organizaciones/${organizationSlug}/miembros`,
    ]) {
      await page.goto(path);
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze();
      expect(results.violations).toEqual([]);
    }
  });
});
