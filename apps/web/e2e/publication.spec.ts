import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

const slug = 'organizacion-a';
const courseSlug = 'publicacion-inmutable-e2e';
const publicationPath = `/organizaciones/${slug}/cursos/${courseSlug}/publicacion`;
const libraryPath = `/organizaciones/${slug}/biblioteca`;

async function login(page: Page, email: string, next: string) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password!);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(next, { timeout: 20_000 });
}

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

test('immutable publication, authenticated library, withdrawal and axe work end to end', async ({
  browser,
  page,
}) => {
  test.setTimeout(240_000);
  await login(page, 'owner@organizations.e2e.test', publicationPath);
  await expect(
    page.getByRole('heading', { name: 'Publicación del curso' }),
  ).toBeVisible();
  await expect(
    page.getByRole('link', { name: 'Biblioteca', exact: true }),
  ).toBeVisible();
  await expect(
    page
      .locator('[data-sidebar="sidebar"]')
      .getByRole('link', { name: 'Publicación', exact: true }),
  ).toBeVisible();
  await expect(page.getByText('Sin publicar', { exact: true })).toBeVisible();
  await expectAccessible(page);

  await page
    .getByRole('button', { name: 'Publicar revisión aprobada' })
    .click();
  await expect(
    page.getByText(
      'Se creará una versión inmutable del curso. Los cambios futuros requerirán una revisión nueva y otro release.',
    ),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Confirmar publicación' }).click();
  await expect(
    page.getByText('Release 1', { exact: true }).first(),
  ).toBeVisible({ timeout: 20_000 });
  await expect(page.getByText('Verificada', { exact: true })).toBeVisible({
    timeout: 20_000,
  });
  await expectAccessible(page);

  await page.getByRole('link', { name: 'Inspeccionar' }).click();
  await expect(page).toHaveURL(
    `/organizaciones/${slug}/cursos/${courseSlug}/publicaciones/1`,
    { timeout: 20_000 },
  );
  await expect(
    page.getByRole('heading', {
      name: 'Funciones para lectura institucional',
    }),
  ).toBeVisible();
  await expect(page.getByText('Registro histórico inmutable')).toBeVisible();
  await expectAccessible(page);

  const readerContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const readerPage = await readerContext.newPage();
  await login(readerPage, 'instructor@organizations.e2e.test', libraryPath);
  await expect(
    readerPage.getByRole('heading', { name: 'Biblioteca' }),
  ).toBeVisible();
  const readerSidebar = readerPage.locator('[data-sidebar="sidebar"]');
  await expect(
    readerSidebar.getByRole('link', { name: 'Biblioteca', exact: true }),
  ).toBeVisible();
  await expect(
    readerSidebar.getByRole('link', { name: 'Miembros', exact: true }),
  ).toHaveCount(0);
  await readerPage
    .getByRole('link', {
      name: /Abrir curso/,
    })
    .click();
  await expect(
    readerPage.getByRole('heading', {
      name: 'Funciones para lectura institucional',
    }),
  ).toBeVisible();
  await expect(readerPage.getByText('esta fase no guarda avance')).toBeVisible({
    timeout: 20_000,
  });
  await expectAccessible(readerPage);
  await readerPage
    .getByRole('link', { name: 'Comenzar lectura' })
    .press('Enter');
  await expect(
    readerPage.getByRole('heading', {
      name: 'Concepto de función',
      level: 1,
    }),
  ).toBeVisible({ timeout: 20_000 });
  await expect(readerPage.getByText('Una función asigna')).toBeVisible({
    timeout: 20_000,
  });
  const next = readerPage.getByRole('link', {
    name: /Siguiente.*Dominio y rango/,
  });
  await next.focus();
  await expect(next).toBeFocused();
  await next.press('Enter');
  await expect(
    readerPage.getByRole('heading', { name: 'Dominio y rango', level: 1 }),
  ).toBeVisible({ timeout: 20_000 });

  await readerPage.setViewportSize({ width: 390, height: 844 });
  await readerPage
    .getByRole('button', { name: 'Mostrar u ocultar navegación' })
    .click();
  const mobileNavigation = readerPage.getByRole('dialog', {
    name: 'Navegación principal',
  });
  await expect(
    mobileNavigation.getByRole('link', { name: 'Biblioteca', exact: true }),
  ).toBeVisible();
  await readerPage.keyboard.press('Escape');
  await expect(mobileNavigation).toBeHidden();
  expect(
    await readerPage.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectAccessible(readerPage);
  const historical = await readerPage.goto(
    `/organizaciones/${slug}/cursos/${courseSlug}/publicaciones/1`,
  );
  expect(historical?.status()).toBe(404);

  await page
    .getByRole('button', { name: 'Crear revisión desde este release' })
    .click();
  await expect(
    page.getByText('El release histórico no cambiará.'),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Crear revisión' }).click();
  await expect(page).toHaveURL(`/organizaciones/${slug}/cursos/${courseSlug}`, {
    timeout: 20_000,
  });
  await page.getByRole('button', { name: 'Enviar a revisión' }).click();
  await page.getByRole('button', { name: 'Enviar revisión' }).click();
  await expect(
    page.getByRole('button', { name: 'Aprobar estructura' }),
  ).toBeVisible({ timeout: 20_000 });
  await page.getByRole('button', { name: 'Aprobar estructura' }).click();
  await expect(page.getByText('La estructura fue aprobada.')).toBeVisible({
    timeout: 20_000,
  });
  await page.goto(publicationPath);
  await page
    .getByRole('button', { name: 'Publicar revisión aprobada' })
    .click();
  await page.getByRole('button', { name: 'Confirmar publicación' }).click();
  await expect(
    page.getByText('Release 2', { exact: true }).first(),
  ).toBeVisible({ timeout: 20_000 });
  await readerPage.goto(`${libraryPath}/${courseSlug}`);
  await expect(
    readerPage.getByText('Orden estable del release 2.'),
  ).toBeVisible({ timeout: 20_000 });
  await expect(readerPage.getByText('Concepto de función')).toBeVisible();

  await page.goto(publicationPath);
  await page.getByRole('button', { name: 'Retirar de la biblioteca' }).click();
  await page
    .getByLabel('Justificación obligatoria')
    .fill('Corrección académica verificada por E2E.');
  await page.getByRole('button', { name: 'Confirmar retiro' }).click();
  await expect(page.getByText('Retirada', { exact: true })).toBeVisible();
  await expect(page.getByText('Corrección académica verificada')).toBeVisible();

  await readerPage.goto(libraryPath);
  await expect(readerPage.getByText('No hay cursos activos')).toBeVisible();
  const hiddenCourse = await readerPage.goto(`${libraryPath}/${courseSlug}`);
  expect(hiddenCourse?.status()).toBe(404);
  await readerContext.close();
});
