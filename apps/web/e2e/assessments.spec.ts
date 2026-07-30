import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

const slug = 'organizacion-a';

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

async function csrfRequest(
  page: Page,
  path: string,
  method: 'POST' | 'PUT',
  body?: unknown,
) {
  return page.evaluate(
    async ({ body, method, path }) => {
      const token = document.cookie
        .split(';')
        .map((part) => part.trim())
        .find((part) => part.startsWith('csrftoken='))
        ?.slice('csrftoken='.length);
      const response = await fetch(path, {
        ...(body === undefined ? {} : { body: JSON.stringify(body) }),
        credentials: 'same-origin',
        headers: {
          ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
          ...(token ? { 'X-CSRFToken': decodeURIComponent(token) } : {}),
        },
        method,
      });
      return { status: response.status };
    },
    { body, method, path },
  );
}

async function saveAndNext(page: Page) {
  await page.getByRole('button', { name: 'Guardar respuesta' }).click();
  await expect(page.getByText('Guardada', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Siguiente' }).click();
}

test('assessment phase 13: authoring, delivery, attempt, conflict, manual grading, security and responsive access work', async ({
  browser,
  page,
}) => {
  test.setTimeout(420_000);
  const authoringPath = `/organizaciones/${slug}/evaluaciones`;
  await login(page, 'owner@organizations.e2e.test', authoringPath);
  await expect(
    page.getByRole('heading', { name: 'Evaluaciones', exact: true }),
  ).toBeVisible();
  await expect(page.getByText('Diagnóstico integral E2E')).toBeVisible();
  await expectAccessible(page);

  await page.goto(`/organizaciones/${slug}/evaluaciones/bancos`);
  await expect(page.getByText('Banco E2E de assessments')).toBeVisible();
  await page
    .getByRole('heading', { name: 'Banco E2E de assessments' })
    .locator('..')
    .locator('..')
    .getByRole('link', { name: 'Abrir espacio de autoría' })
    .click();
  await expect(page.getByText('ASSESS-E2E-001')).toBeVisible();
  await expect(page.getByText('ASSESS-E2E-008')).toBeVisible();

  await page.goto(`/organizaciones/${slug}/evaluaciones/bancos`);
  const browserBankName = 'Banco creado por navegador E2E';
  await page.getByLabel('Nombre del banco').fill(browserBankName);
  await page.getByLabel('Slug').fill('banco-creado-navegador-e2e');
  await page
    .getByLabel('Descripción')
    .fill('Valida creación, errores inline y navegación editorial real.');
  await page.getByRole('button', { name: 'Crear banco' }).click();
  await expect(
    page.getByRole('heading', { name: browserBankName }),
  ).toBeVisible();
  await page
    .getByRole('heading', { name: browserBankName })
    .locator('..')
    .locator('..')
    .getByRole('link', { name: 'Abrir espacio de autoría' })
    .click();

  await page
    .getByRole('button', { name: 'Crear borrador de pregunta' })
    .click();
  await expect(page.getByRole('alert')).toContainText([
    'Asigna un código estable.',
    'Escribe el enunciado.',
  ]);
  await expect(page.getByText('Runtime Error')).toHaveCount(0);
  await page.getByLabel('Código estable').fill('BROWSER-E2E-001');
  await page
    .getByLabel('Enunciado')
    .fill('¿Qué porcentaje representa 30 de un total de 120?');
  await page.getByLabel('Opciones de respuesta').fill('20 %\n25 %\n30 %\n40 %');
  await page.getByRole('radio', { name: 'Marcar 25 % como correcta' }).check();
  await expect(
    page.locator('.assessment-question-preview li').filter({ hasText: '25 %' }),
  ).toBeVisible();
  await page
    .getByRole('button', { name: 'Crear borrador de pregunta' })
    .click();
  await expect(page.getByText('BROWSER-E2E-001')).toBeVisible();
  await expect(page.getByText('Runtime Error')).toHaveCount(0);

  await page.goto(`/organizaciones/${slug}/evaluaciones/nueva`);
  await page
    .getByLabel('Título de la evaluación')
    .fill('Evaluación creada por navegador E2E');
  await page.getByLabel('Slug').fill('evaluacion-creada-navegador-e2e');
  await page
    .getByLabel('Propósito y alcance')
    .fill('Comprueba la creación real del instrumento y su compositor.');
  await page.getByRole('button', { name: 'Crear y abrir compositor' }).click();
  await expect(page).toHaveURL(
    `/organizaciones/${slug}/evaluaciones/evaluacion-creada-navegador-e2e`,
    { timeout: 20_000 },
  );
  await expect(
    page.getByRole('heading', {
      name: 'Evaluación creada por navegador E2E',
    }),
  ).toBeVisible();
  await expect(page.getByText('Arquitectura del instrumento')).toBeVisible();
  await expect(page.getByText('Runtime Error')).toHaveCount(0);

  await page.goto(`/organizaciones/${slug}/evaluaciones/entregas`);
  await expect(page.getByText('Entrega E2E activa')).toBeVisible();
  await expectAccessible(page);

  const studentContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
    viewport: { height: 844, width: 390 },
  });
  const student = await studentContext.newPage();
  const assignedPath = `/organizaciones/${slug}/evaluaciones/asignadas`;
  await login(student, 'learner@organizations.e2e.test', assignedPath);
  await expect(
    student.getByRole('heading', { name: 'Mis evaluaciones' }),
  ).toBeVisible();
  const accessResponse = await student.request.get('/api/v1/access/context/');
  expect(accessResponse.ok()).toBe(true);
  const accessContext = (await accessResponse.json()) as {
    organizations: { capabilities: string[]; slug: string }[];
  };
  const learnerOrganization = accessContext.organizations.find(
    (organization) => organization.slug === slug,
  );
  expect(learnerOrganization?.capabilities.slice().sort()).toEqual([
    'assessment.attempt',
    'organization.view',
  ]);
  await expect(
    student.locator(`a[href="/organizaciones/${slug}/curriculo"]`),
  ).toHaveCount(0);
  await expect(
    student.locator(`a[href="/organizaciones/${slug}/evaluaciones"]`),
  ).toHaveCount(0);
  await expect(
    student.locator(`a[href="/organizaciones/${slug}/miembros"]`),
  ).toHaveCount(0);
  await expect(
    student.locator(`a[href="/organizaciones/${slug}/evaluaciones/entregas"]`),
  ).toHaveCount(0);
  await expect(student.getByText('Diagnóstico integral E2E')).toBeVisible();
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectAccessible(student);

  const assignmentsResponse = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/my-deliveries/`,
  );
  expect(assignmentsResponse.ok()).toBe(true);
  const assignments = (await assignmentsResponse.json()) as { id: string }[];
  await student.getByRole('button', { name: 'Comenzar' }).click();
  await expect(student).toHaveURL(/\/evaluaciones\/intentos\/[0-9a-f-]+$/, {
    timeout: 20_000,
  });
  await expect(student.getByRole('timer')).toContainText('Tiempo restante');
  const attemptId = student.url().split('/').at(-1)!;
  const attemptResponse = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/attempts/${attemptId}/`,
  );
  expect(attemptResponse.ok()).toBe(true);
  const attempt = (await attemptResponse.json()) as {
    id: string;
    items: { id: string }[];
    lock_version: number;
  };
  const firstSave = await csrfRequest(
    student,
    `/api/v1/organizations/${slug}/assessments/attempts/${attempt.id}/responses/${attempt.items[0]!.id}/`,
    'PUT',
    {
      expected_version: attempt.lock_version,
      response: {
        schema_version: 1,
        type: 'single_choice',
        value: 'b',
      },
    },
  );
  expect(firstSave.status).toBe(200);
  const staleSave = await csrfRequest(
    student,
    `/api/v1/organizations/${slug}/assessments/attempts/${attempt.id}/responses/${attempt.items[0]!.id}/`,
    'PUT',
    {
      expected_version: attempt.lock_version,
      response: {
        schema_version: 1,
        type: 'single_choice',
        value: 'a',
      },
    },
  );
  expect(staleSave.status).toBe(409);

  await student.reload();
  const html = await student.content();
  expect(html).not.toMatch(
    /correct_option_ids|correct_pairs|grading_snapshot|seed/i,
  );
  await expect(student.getByText('Pregunta demo 1')).toBeVisible();
  await student.getByRole('button', { name: 'Siguiente' }).click();

  await student
    .getByRole('checkbox', { name: 'Primera opción', exact: true })
    .check();
  await student
    .getByRole('checkbox', { name: 'Tercera opción', exact: true })
    .check();
  await saveAndNext(student);

  await student.getByRole('radio', { name: 'Verdadero', exact: true }).check();
  await saveAndNext(student);

  await student.getByLabel('Respuesta a la pregunta').fill('12.5');
  await saveAndNext(student);

  await student.getByLabel('Respuesta a la pregunta').fill('  DERIVADA  ');
  await saveAndNext(student);

  await student
    .getByLabel('Respuesta a la pregunta')
    .fill('La derivada representa una tasa de cambio.');
  await saveAndNext(student);

  await student.getByRole('button', { name: 'Subir Tercera opción' }).click();
  await student.getByRole('button', { name: 'Subir Tercera opción' }).click();
  await saveAndNext(student);

  await student.getByLabel('Derivada').selectOption('r1');
  await student.getByLabel('Integral').selectOption('r2');
  await student.getByRole('button', { name: 'Guardar respuesta' }).click();
  await expect(student.getByText('Guardada', { exact: true })).toBeVisible();
  await student.getByRole('button', { name: 'Enviar intento' }).click();
  await student
    .getByRole('button', { name: 'Confirmar envío definitivo' })
    .click();
  await expect(
    student.getByRole('heading', { name: 'Calificación manual pendiente' }),
  ).toBeVisible({ timeout: 20_000 });
  await expectAccessible(student);

  await page.goto(`/organizaciones/${slug}/evaluaciones/calificacion-manual`);
  await expect(page.getByText('La derivada representa')).toBeVisible();
  await page.getByLabel(/Puntaje/).fill('1.000');
  await page.getByLabel('Feedback').fill('Argumento claro y suficiente.');
  await page.getByRole('button', { name: 'Registrar decisión' }).click();
  await expect(
    page.getByRole('button', { name: 'Registrar corrección' }),
  ).toBeVisible({ timeout: 20_000 });
  await expect(
    page.locator('.assessment-grade-history li').filter({
      hasText: '#1',
    }),
  ).toContainText('1.000 puntos');
  await page
    .getByLabel('Feedback')
    .fill('Corrección confirmada con evidencia suficiente.');
  await page.getByRole('button', { name: 'Registrar corrección' }).click();
  await expect(
    page.locator('.assessment-grade-history li').filter({
      hasText: '#2',
    }),
  ).toContainText('1.000 puntos', { timeout: 20_000 });

  await student.reload();
  await expect(
    student.getByRole('heading', { name: 'Intento calificado' }),
  ).toBeVisible();
  await expect(student.getByText('8.000 / 8.000')).toBeVisible();

  const secondStart = await csrfRequest(
    student,
    `/api/v1/organizations/${slug}/assessments/my-deliveries/${assignments[0]!.id}/attempts/start/`,
    'POST',
  );
  expect(secondStart.status).toBe(201);
  const secondAttemptResponse = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/my-deliveries/${assignments[0]!.id}/attempts/start/`,
  );
  expect(secondAttemptResponse.status()).toBe(405);
  const deliveriesAfterFirst = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/my-deliveries/`,
  );
  expect(deliveriesAfterFirst.ok()).toBe(true);
  const activeAttemptResponse = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/attempts/00000000-0000-0000-0000-000000000000/`,
  );
  expect(activeAttemptResponse.status()).toBe(404);
  await student.goto(assignedPath);
  await student.getByRole('button', { name: /Continuar intento/ }).click();
  await expect(student).toHaveURL(/\/evaluaciones\/intentos\/[0-9a-f-]+$/, {
    timeout: 20_000,
  });
  const secondAttemptId = student.url().split('/').at(-1)!;
  const secondAttemptGet = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/attempts/${secondAttemptId}/`,
  );
  const secondAttempt = (await secondAttemptGet.json()) as {
    id: string;
    lock_version: number;
  };
  const secondSubmit = await csrfRequest(
    student,
    `/api/v1/organizations/${slug}/assessments/attempts/${secondAttempt.id}/submit/`,
    'POST',
    { expected_version: secondAttempt.lock_version },
  );
  expect(secondSubmit.status).toBe(200);
  const thirdStart = await csrfRequest(
    student,
    `/api/v1/organizations/${slug}/assessments/my-deliveries/${assignments[0]!.id}/attempts/start/`,
    'POST',
  );
  expect(thirdStart.status).toBe(409);

  const foreign = await student.goto(
    '/organizaciones/organizacion-b/evaluaciones/asignadas',
  );
  expect(foreign?.status()).toBe(404);
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await studentContext.close();
});
