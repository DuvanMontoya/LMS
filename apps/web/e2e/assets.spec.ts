import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

async function login(page: Page, next: string) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page
    .getByLabel('Correo electrónico')
    .fill('owner@organizations.e2e.test');
  await page.getByLabel('Contraseña').fill(password!);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(next, { timeout: 20_000 });
}

async function expectAccessible(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(result.violations).toEqual([]);
}

test('academic assets library and upload surface are private, keyboard usable and accessible', async ({
  page,
}) => {
  const library = '/organizaciones/organizacion-a/recursos';
  await login(page, library);
  const main = page.locator('main');
  await expect(
    main.getByRole('heading', { name: 'Recursos', exact: true }),
  ).toBeVisible();
  const uploadLink = main.getByRole('link', {
    name: 'Cargar recurso',
    exact: true,
  });
  await expect(uploadLink).toBeVisible();
  await expectAccessible(page);

  await uploadLink.focus();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(`${library}/nuevo`, { timeout: 20_000 });
  await expect(
    page.getByRole('heading', { name: 'Cargar recurso', exact: true }),
  ).toBeVisible();
  await expect(page.getByLabel('Archivo')).toHaveAttribute('type', 'file');
  await expect(page.getByLabel('Tipo de recurso')).toHaveValue('image');
  await expectAccessible(page);
});

test('asset visual surfaces remain usable at 390 px without horizontal overflow', async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  const upload = '/organizaciones/organizacion-a/recursos/nuevo';
  await login(page, upload);
  const metrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(metrics.scrollWidth).toBeLessThanOrEqual(metrics.clientWidth);
  await expect(page.getByLabel('Archivo')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Iniciar carga' }),
  ).toBeVisible();
  await expectAccessible(page);
});
