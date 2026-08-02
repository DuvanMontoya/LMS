import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

async function loginAsAuthor(page: import('@playwright/test').Page) {
  await page.goto(
    '/auth/iniciar-sesion?next=%2Forganizaciones%2Forganizacion-a%2Fcurriculo%2Fobjetivos',
  );
  await page
    .getByLabel('Correo electrónico')
    .fill('author@organizations.e2e.test');
  await page.getByLabel('Contraseña').fill(password!);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await page.waitForURL(/\/organizaciones\/organizacion-a\//);
}

async function expectAccessibleAndContained(
  page: import('@playwright/test').Page,
) {
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

test('curriculum workspaces keep explicit scope and scale at 390 px', async ({
  page,
}) => {
  test.setTimeout(60_000);
  await loginAsAuthor(page);
  await page.setViewportSize({ height: 844, width: 390 });

  await page.goto('/organizaciones/organizacion-a/curriculo/objetivos');
  await expect(
    page.getByRole('heading', { name: 'Objetivos de aprendizaje' }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(
    page.getByRole('heading', { name: 'Elige la asignatura de trabajo' }),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText('OBJ-COURSE-001')).toHaveCount(0);
  await page.getByRole('link', { name: 'Precálculo', exact: true }).click();
  await expect(page).toHaveURL(/subject=/, { timeout: 15_000 });
  await expect(page.getByLabel('Asignatura')).toHaveValue(/.+/, {
    timeout: 15_000,
  });
  await expect(page.getByText('OBJ-COURSE-001')).toBeVisible({
    timeout: 15_000,
  });
  await expect(
    page.getByText(
      'Interpretar funciones mediante distintas representaciones.',
    ),
  ).toBeVisible();
  await expectAccessibleAndContained(page);

  await page
    .getByRole('navigation', { name: 'Secciones del currículo' })
    .getByRole('link', { name: 'Conceptos' })
    .click();
  await expect(page).toHaveURL(/\/curriculo\/conceptos$/, { timeout: 15_000 });
  await expect(page.getByText('Diccionario, no temario')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByLabel('Buscar conceptos')).toBeVisible();
  await expect(page.getByLabel('Filtrar por asignatura')).toBeVisible();
  await expectAccessibleAndContained(page);

  await page
    .getByRole('navigation', { name: 'Secciones del currículo' })
    .getByRole('link', { name: 'Prerrequisitos' })
    .click();
  await expect(page).toHaveURL(/\/curriculo\/prerrequisitos$/, {
    timeout: 15_000,
  });
  await expect(page.getByText('Ruta entre asignaturas')).toBeVisible({
    timeout: 15_000,
  });
  const graphNavigation = page.getByRole('navigation', {
    name: 'Tipo de grafo',
  });
  await expect(
    graphNavigation.getByRole('link', { name: 'Asignaturas' }),
  ).toHaveAttribute('aria-current', 'page');
  await expect(page.getByText('Dependencias entre conceptos')).toHaveCount(0);
  await expectAccessibleAndContained(page);

  await graphNavigation
    .getByRole('link', { name: 'Conceptos', exact: true })
    .click();
  await expect(page).toHaveURL(/graph=concepts/, { timeout: 15_000 });
  await expect(page.getByText('Dependencias entre conceptos')).toBeVisible({
    timeout: 15_000,
  });
  await expect(page.getByText('Ruta entre asignaturas')).toHaveCount(0);
  await expectAccessibleAndContained(page);
});
