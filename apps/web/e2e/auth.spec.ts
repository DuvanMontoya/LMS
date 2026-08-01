import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

import { waitForMailCode } from './mail';

const mailDirectory = process.env.E2E_MAIL_PATH;
if (!mailDirectory)
  throw new Error('E2E_MAIL_PATH is required for browser tests.');
const requiredMailDirectory: string = mailDirectory;

const password = 'CorrectHorseBatteryStaple42!';
const newPassword = 'NewCorrectHorseBatteryStaple42!';

function e2eEmail() {
  return `student-${randomUUID()}@example.test`;
}

async function registerAndVerify(
  page: import('@playwright/test').Page,
  email: string,
) {
  await page.goto('/auth/registro');
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña nueva').fill(password);
  await page.getByLabel('Confirmar contraseña').fill(password);
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  await expect(page).toHaveURL('/auth/verificar-correo');
  const code = await waitForMailCode(
    requiredMailDirectory,
    'Usa este código para verificar tu correo electrónico',
  );
  await page.getByLabel('Código de verificación').fill(code);
  await page.getByRole('button', { name: 'Verificar correo' }).click();
  await expect(page).toHaveURL('/estudiar');
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL('/auth/iniciar-sesion');
}

async function login(
  page: import('@playwright/test').Page,
  email: string,
  secret = password,
) {
  await page.goto('/auth/iniciar-sesion?next=/estudiar');
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(secret);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('/estudiar');
}

test.describe.serial('browser session authentication', () => {
  test('registers, verifies, logs in, reaches the study workspace and logs out', async ({
    page,
  }) => {
    const email = e2eEmail();
    await registerAndVerify(page, email);
    await login(page, email);
    await expect(
      page.getByRole('heading', { name: 'Espacio de trabajo' }),
    ).toBeVisible();
    await expect(
      page.getByRole('heading', { name: 'Sin organización asignada' }),
    ).toBeVisible();
    await expect(page.getByText(email)).toBeVisible();
    await page.getByRole('button', { name: 'Cerrar sesión' }).click();
    await expect(page).toHaveURL('/auth/iniciar-sesion');
    await page.goBack();
    await expect(page).toHaveURL(/\/auth\/iniciar-sesion/);
  });

  test('resets a password without authenticating and accepts only the new password', async ({
    page,
  }) => {
    const email = e2eEmail();
    await registerAndVerify(page, email);
    await page.goto('/auth/recuperar-contrasena');
    await page.getByLabel('Correo electrónico').fill(email);
    await page.getByRole('button', { name: 'Solicitar código' }).click();
    await expect(page).toHaveURL('/auth/restablecer-contrasena?sent=1');
    const code = await waitForMailCode(
      requiredMailDirectory,
      'Usa este código para restablecer tu contraseña',
    );
    await page.getByLabel('Código recibido').fill(code);
    await page.getByLabel('Nueva contraseña').fill(newPassword);
    await page.getByLabel('Confirmar contraseña').fill(newPassword);
    await page.getByRole('button', { name: 'Restablecer contraseña' }).click();
    await expect(
      page.getByText(
        'Tu contraseña fue actualizada. Ya puedes iniciar sesión.',
      ),
    ).toBeVisible();
    await page.goto('/auth/iniciar-sesion');
    await page.getByLabel('Correo electrónico').fill(email);
    await page.getByLabel('Contraseña').fill(password);
    await page.getByRole('button', { name: 'Iniciar sesión' }).click();
    await expect(
      page.getByRole('region', { name: 'Aula Académica' }).getByRole('alert'),
    ).toContainText('El correo o la contraseña no son correctos.');
    await login(page, email, newPassword);
  });

  test('enforces protected routes, blocks open redirects and preserves CSRF', async ({
    page,
    request,
  }) => {
    await page.goto('/estudiar');
    await expect(page).toHaveURL(
      /\/auth\/iniciar-sesion\?next=(?:%2F|\/)estudiar/,
    );
    await page.context().addCookies([
      {
        name: 'sessionid',
        value: 'forged-session-cookie',
        domain: '127.0.0.1',
        path: '/',
      },
    ]);
    await page.goto('/estudiar');
    await expect(page).toHaveURL(
      /\/auth\/iniciar-sesion\?next=(?:%2F|\/)estudiar/,
    );
    await page.context().clearCookies();

    for (const next of [
      'https://example.invalid',
      '//example.invalid',
      '/%2F%2Fexample.invalid',
      'javascript:alert(1)',
      '/\\example.invalid',
    ]) {
      await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
      await page.getByLabel('Correo electrónico').fill('missing@example.test');
      await page.getByLabel('Contraseña').fill(password);
      await page.getByRole('button', { name: 'Iniciar sesión' }).click();
      await expect(page).toHaveURL(/\/auth\/iniciar-sesion/);
    }
    const response = await request.post('/_allauth/browser/v1/auth/signup', {
      data: { email: e2eEmail(), password },
    });
    expect(response.status()).toBe(403);
  });

  test('@a11y has no automatic A/AA violations on public auth pages', async ({
    page,
  }) => {
    await page.goto('/auth/iniciar-sesion');
    await page.getByLabel('Correo electrónico').focus();
    await page.keyboard.press('Tab');
    await expect(page.getByLabel('Contraseña')).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(page.getByRole('button', { name: 'Mostrar' })).toBeFocused();
    await page.keyboard.press('Tab');
    await expect(
      page.getByRole('button', { name: 'Iniciar sesión' }),
    ).toBeFocused();

    for (const path of [
      '/auth/iniciar-sesion',
      '/auth/registro',
      '/auth/verificar-correo',
      '/auth/recuperar-contrasena',
      '/auth/restablecer-contrasena',
    ]) {
      await page.goto(path);
      const results = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze();
      expect(results.violations).toEqual([]);
    }
  });
});
