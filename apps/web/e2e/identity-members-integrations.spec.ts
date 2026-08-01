import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';
import { randomUUID } from 'node:crypto';

import { waitForInvitationLink, waitForMailCode } from './mail';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
const mailDirectory = process.env.E2E_MAIL_PATH;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');
if (!mailDirectory) throw new Error('E2E_MAIL_PATH is required.');

const requiredPassword: string = password;
const requiredMailDirectory: string = mailDirectory;
const organizationSlug = 'organizacion-a';
const activatedPassword = 'ActivatedStudentPassword42!';
const registrationPassword = 'PublicJoinPassword42!';

function e2eEmail(prefix: string) {
  return `${prefix}-${randomUUID()}@example.test`;
}

async function login(
  page: import('@playwright/test').Page,
  email: string,
  next = '/organizaciones',
  secret = requiredPassword,
  destination = next,
) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(secret);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(destination, { timeout: 45_000 });
}

test.describe
  .serial('identity, member management and governed integrations', () => {
  test('platform registration policy governs the actual public registration page', async ({
    browser,
    page,
  }) => {
    await login(
      page,
      'platform-admin@organizations.e2e.test',
      '/administracion/configuracion',
    );
    await page.getByRole('radio', { name: 'Sólo invitación' }).check();
    await page.getByRole('button', { name: 'Guardar política' }).click();
    await expect(page.getByText('Política actualizada')).toBeVisible();

    const publicContext = await browser.newContext();
    const publicPage = await publicContext.newPage();
    const closedRegistration = await publicPage.goto('/auth/registro');
    expect(closedRegistration?.status()).toBe(404);
    await expect(publicPage.getByLabel('Correo electrónico')).toHaveCount(0);

    await page.getByRole('radio', { name: 'Abierto' }).check();
    await page.getByRole('button', { name: 'Guardar política' }).click();
    await expect(page.getByText('Política actualizada')).toBeVisible();
    await publicPage.reload();
    await expect(publicPage.getByLabel('Correo electrónico')).toBeVisible();
    await publicContext.close();
  });

  test('owner creates, corrects and activates a managed student, then accepts an existing-user invitation', async ({
    browser,
    page,
  }) => {
    test.setTimeout(240_000);
    await login(
      page,
      'owner@organizations.e2e.test',
      `/organizaciones/${organizationSlug}/miembros/nuevo?rol=learner`,
    );
    const initialEmail = e2eEmail('managed-wrong');
    const correctedEmail = e2eEmail('managed-student');
    await page.getByLabel('Correo institucional o personal').fill(initialEmail);
    await page.getByLabel('Primer nombre').fill('Ana');
    await page.getByLabel('Primer apellido').fill('Díaz');
    await page.getByLabel('Tipo de miembro').selectOption('learner');
    const managedCreation = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response
          .url()
          .includes(`/organizations/${organizationSlug}/managed-accounts/`),
    );
    await page
      .getByRole('button', { name: 'Crear cuenta y activación' })
      .click();
    expect((await managedCreation).status()).toBe(201);

    await page.goto(
      `/organizaciones/${organizationSlug}/miembros/invitaciones?status=pending`,
    );
    await page
      .getByLabel('Corregir correo antes de activar')
      .fill(correctedEmail);
    await page.getByRole('button', { name: 'Guardar y reenviar' }).click();
    await expect(page.getByText(correctedEmail)).toBeVisible();

    const activationLink = await waitForInvitationLink(
      requiredMailDirectory,
      correctedEmail,
    );
    const studentContext = await browser.newContext();
    const studentPage = await studentContext.newPage();
    await studentPage.goto(activationLink);
    await expect(
      studentPage.getByText('Activar cuenta institucional', { exact: true }),
    ).toBeVisible({ timeout: 45_000 });
    await studentPage
      .getByLabel('Define tu contraseña')
      .fill(activatedPassword);
    await studentPage.getByRole('button', { name: 'Activar cuenta' }).click();
    await expect(studentPage).toHaveURL('/auth/iniciar-sesion', {
      timeout: 45_000,
    });
    await login(
      studentPage,
      correctedEmail,
      `/organizaciones/${organizationSlug}/aprendizaje`,
      activatedPassword,
    );
    await expect(
      studentPage.getByText('Organización A', { exact: true }).first(),
    ).toBeVisible();

    const existingEmail = 'candidate@organizations.e2e.test';
    await page.goto(`/organizaciones/${organizationSlug}/miembros/nuevo`);
    await page.getByLabel('Invitar a una cuenta').check();
    await page
      .getByLabel('Correo institucional o personal')
      .fill(existingEmail);
    const invitationCreation = page.waitForResponse(
      (response) =>
        response.request().method() === 'POST' &&
        response
          .url()
          .includes(`/organizations/${organizationSlug}/invitations/`),
    );
    await page.getByRole('button', { name: 'Enviar invitación' }).click();
    expect((await invitationCreation).status()).toBe(201);
    const invitationLink = await waitForInvitationLink(
      requiredMailDirectory,
      existingEmail,
    );
    const existingContext = await browser.newContext();
    const existingPage = await existingContext.newPage();
    await existingPage.goto(invitationLink);
    await expect(existingPage.getByText('Invitación validada')).toBeVisible();
    await existingPage
      .getByRole('link', { name: 'Iniciar sesión y aceptar' })
      .click();
    await login(
      existingPage,
      existingEmail,
      '/invitaciones/aceptar',
      requiredPassword,
      `/organizaciones/${organizationSlug}/aprendizaje`,
    );
    await expect(
      existingPage.getByText('Organización A', { exact: true }).first(),
    ).toBeVisible();

    await existingContext.close();
    await studentContext.close();
  });

  test('the platform operator provisions institutions without inheriting access to existing ones', async ({
    page,
  }) => {
    await login(
      page,
      'platform-admin@organizations.e2e.test',
      '/administracion/organizaciones',
    );
    await expect(
      page.getByRole('heading', { name: 'Instituciones' }),
    ).toBeVisible();
    const foreignOrganization = await page.goto(
      `/organizaciones/${organizationSlug}`,
    );
    expect(foreignOrganization?.status()).toBe(404);

    await page.goto('/administracion/organizaciones');
    const institutionName = `Institución E2E ${randomUUID().slice(0, 8)}`;
    await page.getByLabel('Nombre de la institución').fill(institutionName);
    await page.getByRole('button', { name: 'Crear institución' }).click();
    await expect(page.getByText('Institución creada')).toBeVisible();
    const createdInstitution = page.getByRole('link', {
      name: 'Abrir la institución',
    });
    await expect(createdInstitution).toBeVisible();
    await createdInstitution.click();
    await expect(page).toHaveURL(/\/organizaciones\/[a-z0-9-]+$/, {
      timeout: 45_000,
    });
  });

  test('a verified public request is reviewed before it becomes a member', async ({
    browser,
    page,
  }) => {
    test.setTimeout(240_000);
    await login(
      page,
      'owner@organizations.e2e.test',
      `/organizaciones/${organizationSlug}/configuracion`,
    );
    const publicJoin = page.getByLabel('Permitir solicitudes de membresía');
    if (!(await publicJoin.isChecked())) await publicJoin.check();
    const approval = page.getByLabel('Requerir aprobación');
    if (!(await approval.isChecked())) await approval.check();
    await page
      .getByRole('button', { name: 'Guardar reglas de incorporación' })
      .click();
    await expect(page.getByText('Configuración actualizada')).toBeVisible();
    await expect(
      page.getByRole('link', { name: 'Abrir enlace público de ingreso' }),
    ).toBeVisible();

    const applicantEmail = e2eEmail('public-join');
    const applicantContext = await browser.newContext();
    const applicantPage = await applicantContext.newPage();
    await applicantPage.goto(`/unirse/${organizationSlug}`);
    await applicantPage
      .getByRole('button', { name: 'Solicitar acceso' })
      .click();
    await applicantPage
      .getByRole('link', { name: 'Crear y verificar cuenta' })
      .click();
    await applicantPage.getByLabel('Correo electrónico').fill(applicantEmail);
    await applicantPage
      .getByLabel('Contraseña nueva')
      .fill(registrationPassword);
    await applicantPage
      .getByLabel('Confirmar contraseña')
      .fill(registrationPassword);
    await applicantPage.getByRole('button', { name: 'Crear cuenta' }).click();
    await expect(applicantPage).toHaveURL('/auth/verificar-correo', {
      timeout: 45_000,
    });
    const code = await waitForMailCode(
      requiredMailDirectory,
      'Usa este código para verificar tu correo electrónico',
    );
    await applicantPage.getByLabel('Código de verificación').fill(code);
    await applicantPage
      .getByRole('button', { name: 'Verificar correo' })
      .click();
    await expect(applicantPage).toHaveURL('/estudiar', { timeout: 45_000 });

    await page.goto(`/organizaciones/${organizationSlug}/miembros/solicitudes`);
    await expect(page.getByText(applicantEmail).first()).toBeVisible();
    await page.getByRole('button', { name: 'Aprobar' }).click();
    await expect(page.getByText('Aprobada')).toBeVisible();
    await applicantPage.goto('/organizaciones');
    await expect(
      applicantPage.getByText('Organización A', { exact: true }).first(),
    ).toBeVisible();
    await applicantContext.close();
  });

  test('provider connections execute against isolated contracts, retain no API keys in the UI, and remain usable at 390px', async ({
    page,
  }) => {
    test.setTimeout(240_000);
    await login(
      page,
      'owner@organizations.e2e.test',
      `/organizaciones/${organizationSlug}/configuracion/integraciones`,
    );
    for (const apiKey of [
      'e2e-openai-key',
      'e2e-gemini-key',
      'e2e-deepseek-key',
    ]) {
      await page.getByLabel('API key').first().fill(apiKey);
      await page
        .getByRole('button', { name: 'Guardar y preparar prueba' })
        .first()
        .click();
    }
    await expect(page.getByText('Última prueba: Correcta')).toHaveCount(3, {
      timeout: 30_000,
    });
    await expect(page.locator('body')).not.toContainText('e2e-openai-key');
    await expect(page.locator('body')).not.toContainText('e2e-gemini-key');
    await expect(page.locator('body')).not.toContainText('e2e-deepseek-key');

    await page.getByLabel(/Google Meet/).check();
    await page
      .getByRole('button', { name: 'Autorizar Google Workspace' })
      .click();
    await expect(page).toHaveURL(
      `/organizaciones/${organizationSlug}/configuracion/integraciones?oauth=complete`,
      { timeout: 45_000 },
    );
    await expect(
      page.getByRole('button', { name: 'Crear reunión de prueba' }),
    ).toBeVisible();
    await page.getByRole('button', { name: 'Crear reunión de prueba' }).click();
    await expect(page.getByText('Reunión de prueba creada')).toBeVisible();

    for (const path of [
      `/organizaciones/${organizationSlug}/miembros/nuevo?rol=learner`,
      `/organizaciones/${organizationSlug}/configuracion`,
      `/organizaciones/${organizationSlug}/configuracion/integraciones`,
    ]) {
      await page.goto(path);
      const axe = await new AxeBuilder({ page })
        .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
        .analyze();
      expect(axe.violations).toEqual([]);
      await page.setViewportSize({ width: 390, height: 844 });
      await expect
        .poll(() =>
          page
            .locator('body')
            .evaluate((body) => body.scrollWidth <= body.clientWidth),
        )
        .toBe(true);
      await page.setViewportSize({ width: 1280, height: 900 });
    }
  });
});
