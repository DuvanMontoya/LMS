import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

const slug = 'organizacion-a';

async function login(page: Page, next: string) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page
    .getByLabel('Correo electrónico')
    .fill('owner@organizations.e2e.test');
  await page.getByLabel('Contraseña').fill(password!);
  const [response] = await Promise.all([
    page.waitForResponse(
      (candidate) =>
        candidate.url().includes('/_allauth/browser/v1/auth/login') &&
        candidate.request().method() === 'POST',
    ),
    page.getByRole('button', { name: 'Iniciar sesión' }).click(),
  ]);
  expect(response.ok()).toBe(true);
  await page.goto(next);
}

test('academic scheduling: calendar, occurrence detail and live lobby work without issuing a token', async ({
  page,
}) => {
  test.setTimeout(180_000);
  const calendarPath = `/organizaciones/${slug}/calendario`;
  await login(page, calendarPath);
  await expect(
    page.getByRole('heading', { name: 'Calendario', level: 1 }),
  ).toBeVisible();
  await expect(page.getByRole('grid', { name: /2026/ })).toBeVisible();

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  await expect(
    page.getByRole('tab', { name: 'Vista del agenda', selected: true }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 1280, height: 900 });
  await page.reload();

  await page.getByRole('button', { name: 'Nuevo evento' }).click();
  await page.getByLabel('Título').fill('Clase E2E de agenda académica');
  await page.getByRole('button', { name: 'Crear evento' }).click();
  await expect(
    page.getByText('Clase E2E de agenda académica').first(),
  ).toBeVisible({ timeout: 20_000 });
  await page.getByText('Clase E2E de agenda académica').first().click();
  const openClass = page.getByRole('link', { name: /Abrir clase/ });
  await expect(openClass).toBeVisible();

  const sessionPath = await openClass.getAttribute('href');
  expect(sessionPath).toMatch(/^\/organizaciones\/organizacion-a\/clases\//);
  await openClass.click();
  await expect(
    page.getByRole('heading', {
      name: 'Clase E2E de agenda académica',
      level: 1,
    }),
  ).toBeVisible({ timeout: 30_000 });
  await expect(
    page.getByRole('button', { name: /(?:Iniciar|Entrar a) clase/ }),
  ).toBeVisible();
  expect(
    await page.evaluate(() =>
      Object.keys(window.localStorage).some((key) =>
        /token|livekit|room/i.test(key),
      ),
    ),
  ).toBe(false);
  const headers = await page.request.get(sessionPath!);
  expect(headers.headers()['permissions-policy']).toContain('camera=(self)');

  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  expect(accessibility.violations).toEqual([]);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
});
