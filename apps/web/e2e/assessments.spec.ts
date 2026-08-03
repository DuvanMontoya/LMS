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
  await expect(page).toHaveURL(next, { timeout: 45_000 });
}

async function switchUser(page: Page, email: string, next: string) {
  await page.context().clearCookies();
  await login(page, email, next);
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

async function csrfJson(
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
      return {
        data: (await response.json()) as unknown,
        status: response.status,
      };
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
  await login(page, 'author@organizations.e2e.test', authoringPath);
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
    .getByRole('link', { name: 'Explorar banco' })
    .click();
  await expect(page.getByText('ASSESS-E2E-001')).toBeVisible();
  await expect(page.getByText('ASSESS-E2E-008')).toBeVisible();

  await page.goto(`/organizaciones/${slug}/evaluaciones/bancos/nuevo`);
  const browserBankName = 'Banco creado por navegador E2E';
  await page.getByLabel('Nombre del banco').fill(browserBankName);
  await page.getByLabel('Slug').fill('banco-creado-navegador-e2e');
  await page
    .getByLabel('Descripción')
    .fill('Valida creación, errores inline y navegación editorial real.');
  await page.getByRole('button', { name: 'Crear y abrir banco' }).click();
  await expect(
    page.getByRole('heading', { name: browserBankName }),
  ).toBeVisible();
  await page.getByRole('link', { name: 'Nueva pregunta' }).click();
  await page.getByRole('button', { name: 'Crear revisión' }).first().click();
  await expect(page.getByRole('alert')).toContainText(
    'Asigna un código estable.',
  );
  await expect(page.getByText('Runtime Error')).toHaveCount(0);
  await page.getByLabel('Código estable').fill('BROWSER-E2E-001');
  await page
    .getByRole('textbox', { name: 'Contexto y enunciado de la pregunta' })
    .fill('¿Qué porcentaje representa 30 de un total de 120?');
  for (const [index, value] of ['20 %', '25 %', '30 %', '40 %'].entries()) {
    await page.getByLabel(`Texto de la opción ${index + 1}`).fill(value);
  }
  await page
    .locator('.assessment-choice-list > li')
    .filter({ hasText: '25 %' })
    .getByRole('button', { name: 'Marcar como correcta' })
    .click();
  await expect(
    page.locator('.assessment-live-preview li').filter({ hasText: '25 %' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Crear revisión' }).first().click();
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

  await switchUser(
    page,
    'administrator@organizations.e2e.test',
    `/organizaciones/${slug}/evaluaciones/entregas`,
  );
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
  await expect(
    student.getByRole('link', { name: 'Calificaciones', exact: true }),
  ).toBeVisible();
  await expect(
    student.getByRole('heading', { name: 'Libros de calificaciones' }),
  ).toHaveCount(0);
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectAccessible(student);
  await student.setViewportSize({ height: 900, width: 1440 });
  expect(
    await student
      .locator('.assessment-learner-grid')
      .evaluate((grid) =>
        getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean),
      ),
  ).toHaveLength(4);
  await student.setViewportSize({ height: 844, width: 390 });

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

  await student
    .getByRole('group', { name: /Derivada/ })
    .getByRole('radio', { name: /Tasa de cambio/ })
    .check();
  await student
    .getByRole('group', { name: /Integral/ })
    .getByRole('radio', { name: /Acumulación/ })
    .check();
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

  await switchUser(
    page,
    'instructor@organizations.e2e.test',
    `/organizaciones/${slug}/evaluaciones/calificacion-manual`,
  );
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

test('assessment phase 14: safe math, pools, async grading, regrading, gradebook and analytics work end to end', async ({
  browser,
  page,
}) => {
  test.setTimeout(420_000);
  const assessmentPath = `/organizaciones/${slug}/evaluaciones/assessment-avanzado-e2e`;
  await login(page, 'author@organizations.e2e.test', assessmentPath);
  await expect(
    page.getByRole('heading', { name: 'Assessment avanzado E2E' }),
  ).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Pools aleatorios' }),
  ).toBeVisible();
  await expect(page.getByText('1 pool', { exact: true })).toBeVisible();
  await expect(page.getByText('Elige 5 de 20')).toBeVisible();
  await expectAccessible(page);

  await page.goto(`/organizaciones/${slug}/evaluaciones/bancos`);
  await page
    .getByRole('heading', { name: 'Banco E2E avanzado' })
    .locator('..')
    .locator('..')
    .getByRole('link', { name: 'Explorar banco' })
    .click();
  await expect(page).toHaveURL(/\/evaluaciones\/bancos\/[0-9a-f-]+$/, {
    timeout: 30_000,
  });
  // Next dev can expose the streamed form before React has hydrated it.
  // Let hydration own the controls before changing the dynamic question type.
  await page.waitForTimeout(1_500);
  await page.getByRole('link', { name: 'Nueva pregunta' }).click();
  await page.getByLabel('Código estable').fill('ADV-BROWSER-MATH-001');
  await page.getByRole('button', { name: /Expresión matemática/ }).click();
  await expect(page.getByLabel('Símbolos permitidos')).toBeVisible({
    timeout: 30_000,
  });
  await page
    .getByRole('textbox', { name: 'Contexto y enunciado de la pregunta' })
    .fill('Escribe una expresión equivalente a x más uno.');
  await page.getByLabel('Símbolos permitidos').fill('x');
  await page.getByLabel('Hipótesis sobre símbolos').fill('x:real');
  await page
    .getByLabel('Criterio de equivalencia')
    .selectOption('symbolic_common_domain');
  const authorMathField = page.locator('math-field:visible').first();
  await expect(authorMathField).toBeVisible();
  await authorMathField.evaluate((field) => {
    const mathField = field as HTMLElement & { value: string };
    mathField.value = 'x+1';
    mathField.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect(
    page
      .locator('.assessment-studio-quality > div[data-ready="true"]')
      .filter({ hasText: 'Clave o rúbrica definida' }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Crear revisión' }).first().click();
  await expect(page).toHaveURL(
    /\/evaluaciones\/bancos\/[0-9a-f-]+\/preguntas\/[0-9a-f-]+\/revisiones\/[0-9a-f-]+$/,
    { timeout: 30_000 },
  );
  await expect(page.getByRole('heading', { name: 'Revisión 1' })).toBeVisible({
    timeout: 30_000,
  });
  await page.waitForTimeout(1_500);
  await page.getByRole('button', { name: 'Enviar a revisión' }).click();
  const revisionPath = new URL(page.url()).pathname;
  await switchUser(page, 'reviewer@organizations.e2e.test', revisionPath);
  await expect(
    page.getByRole('button', { name: 'Aprobar y crear versión' }),
  ).toBeVisible({ timeout: 15_000 });
  await page.getByRole('button', { name: 'Aprobar y crear versión' }).click();
  await expect(page.getByText('Aprobada', { exact: true })).toBeVisible({
    timeout: 15_000,
  });

  await switchUser(
    page,
    'instructor@organizations.e2e.test',
    `/organizaciones/${slug}/evaluaciones/gradebooks`,
  );
  await page.getByLabel('Release del curso').selectOption({ index: 1 });
  await page.getByRole('button', { name: 'Crear libro' }).click();
  await expect(
    page.getByRole('heading', { name: 'Libro de calificaciones' }),
  ).toBeVisible({ timeout: 30_000 });
  await page.getByLabel('Evaluación entregada').selectOption({
    label: 'Assessment avanzado E2E · Entrega avanzada E2E',
  });
  await page.getByLabel('Título de columna').fill('Assessment avanzado');
  await page.getByLabel('Peso porcentual').fill('100');
  await page.getByLabel('Agregación de intentos').selectOption('highest');
  await page.getByRole('button', { name: 'Añadir columna' }).click();
  await expect(page.locator('input[name="title"]').first()).toHaveValue(
    'Assessment avanzado',
    { timeout: 15_000 },
  );
  await page.getByRole('button', { name: 'Activar libro' }).click();
  await expect(page.getByText('Activo', { exact: true })).toBeVisible({
    timeout: 15_000,
  });
  const gradebookId = page.url().split('/').at(-1)!;

  const studentContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
    viewport: { height: 844, width: 390 },
  });
  const student = await studentContext.newPage();
  const assignedPath = `/organizaciones/${slug}/evaluaciones/asignadas`;
  await login(student, 'learner@organizations.e2e.test', assignedPath);
  const advancedCard = student
    .locator('li.assessment-learner-card')
    .filter({ hasText: 'Assessment avanzado E2E' });
  await advancedCard.getByRole('button', { name: 'Comenzar' }).click();
  await expect(student).toHaveURL(/\/evaluaciones\/intentos\/[0-9a-f-]+$/, {
    timeout: 30_000,
  });
  const attemptId = student.url().split('/').at(-1)!;
  const attemptBefore = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/attempts/${attemptId}/`,
  );
  const initialAttempt = (await attemptBefore.json()) as {
    items: {
      id: string;
      public_snapshot: {
        prompt: { content: { content?: { text: string }[] }[] };
      };
    }[];
  };
  expect(initialAttempt.items).toHaveLength(10);
  expect(new Set(initialAttempt.items.map((item) => item.id)).size).toBe(10);
  const selectedPrompts = initialAttempt.items.map(
    (item) => item.public_snapshot.prompt.content[0]?.content?.[0]?.text,
  );
  expect(new Set(selectedPrompts).size).toBe(10);
  await student.reload();
  const attemptAfterReload = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/attempts/${attemptId}/`,
  );
  expect(
    (
      (await attemptAfterReload.json()) as { items: { id: string }[] }
    ).items.map((item) => item.id),
  ).toEqual(initialAttempt.items.map((item) => item.id));

  await student
    .getByRole('checkbox', { name: 'Primera opción', exact: true })
    .check();
  await saveAndNext(student);
  await student.getByLabel('Respuesta a la pregunta').fill('12.3');
  await saveAndNext(student);
  await student.getByRole('button', { name: 'Subir Tercera opción' }).click();
  await saveAndNext(student);
  await student
    .getByRole('group', { name: /Derivada/ })
    .getByRole('radio', { name: /Tasa de cambio/ })
    .check();
  await student
    .getByRole('group', { name: /Integral/ })
    .getByRole('radio', { name: /Tasa de cambio/ })
    .check();
  await saveAndNext(student);
  const learnerMathField = student.locator('math-field').first();
  await expect(learnerMathField).toBeVisible();
  await learnerMathField.evaluate((field) => {
    const mathField = field as HTMLElement & { value: string };
    mathField.value = '1+x';
    mathField.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await expect(
    student.getByText('Expresión lista para guardar.', { exact: true }),
  ).toBeVisible();
  await student.getByRole('button', { name: 'Guardar respuesta' }).click();
  await expect(student.getByText('Guardada', { exact: true })).toBeVisible();
  await student.getByRole('button', { name: 'Enviar intento' }).click();
  await student
    .getByRole('button', { name: 'Confirmar envío definitivo' })
    .click();
  await expect(
    student.getByRole('heading', { name: 'Intento calificado' }),
  ).toBeVisible({ timeout: 30_000 });
  const resultResponse = await student.request.get(
    `/api/v1/organizations/${slug}/assessments/attempts/${attemptId}/result/`,
  );
  const result = (await resultResponse.json()) as {
    basis_points: number;
    status: string;
    total_score: string;
  };
  expect(result).toMatchObject({
    basis_points: 2833,
    status: 'graded',
    total_score: '2.833',
  });
  await expectAccessible(student);

  const gradesPath = `/organizaciones/${slug}/evaluaciones/calificaciones`;
  await student.goto(gradesPath);
  await expect(
    student.getByRole('heading', { name: 'Mis calificaciones', level: 1 }),
  ).toBeVisible();
  await expect(
    student.getByRole('heading', { name: 'Libros de calificaciones' }),
  ).toBeVisible();
  await expect(
    student.getByText('Assessment avanzado', { exact: true }),
  ).toBeVisible();
  await expect(
    student.getByText('28.33 %', { exact: true }).first(),
  ).toBeVisible();
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectAccessible(student);
  await student
    .getByRole('link', { name: 'Evaluaciones', exact: true })
    .click();
  await expect(student).toHaveURL(assignedPath);
  await expect(
    student.getByRole('heading', { name: 'Libros de calificaciones' }),
  ).toHaveCount(0);

  const assessmentsResponse = await page.request.get(
    `/api/v1/organizations/${slug}/assessments/`,
  );
  const assessments = (await assessmentsResponse.json()) as {
    results: { slug: string }[];
  };
  expect(
    assessments.results.some(
      (assessment) => assessment.slug === 'assessment-avanzado-e2e',
    ),
  ).toBe(true);
  const versionsResponse = await page.request.get(
    `/api/v1/organizations/${slug}/assessments/assessment-avanzado-e2e/versions/`,
  );
  const versions = (await versionsResponse.json()) as { id: string }[];
  const assessmentVersionId = versions.at(-1)!.id;
  const scoringResponse = await page.request.get(
    `/api/v1/organizations/${slug}/assessments/scoring-policies/${assessmentVersionId}/`,
  );
  const scoring = (await scoringResponse.json()) as {
    current_revision: {
      grading_snapshot: {
        items: {
          grading_payload: Record<string, unknown>;
          scoring_policy: string;
          source_id: string;
        }[];
      };
      id: string;
    };
    lock_version: number;
  };
  const firstPolicyItem = scoring.current_revision.grading_snapshot.items[0]!;
  const correctionResponse = await csrfJson(
    page,
    `/api/v1/organizations/${slug}/assessments/scoring-policies/${assessmentVersionId}/corrections/`,
    'POST',
    {
      expected_version: scoring.lock_version,
      item_overrides: {
        [firstPolicyItem.source_id]: {
          grading_payload: firstPolicyItem.grading_payload,
          scoring_policy: firstPolicyItem.scoring_policy,
        },
      },
      reason: 'Corrección E2E auditada sin cambiar el resultado.',
    },
  );
  expect(correctionResponse.status).toBe(201);
  const correction = correctionResponse.data as { id: string };
  await page.goto(`/organizaciones/${slug}/evaluaciones/regrading`);
  await page
    .getByLabel('Versión de evaluación')
    .selectOption(assessmentVersionId);
  await page.getByLabel('Revisión de calificación').selectOption(correction.id);
  await page
    .getByLabel('Justificación auditable')
    .fill('Recalificación E2E con preservación manual e historial completo.');
  await page.getByLabel('Confirmo el alcance de esta recalificación').check();
  await page.getByRole('button', { name: 'Crear recalificación' }).click();
  await expect(page).toHaveURL(/\/evaluaciones\/regrading\/[0-9a-f-]+$/, {
    timeout: 30_000,
  });
  const regradeJobId = page.url().split('/').at(-1)!;
  await expect
    .poll(async () => {
      const response = await page.request.get(
        `/api/v1/organizations/${slug}/assessments/regrade-jobs/${regradeJobId}/`,
      );
      return ((await response.json()) as { status: string }).status;
    })
    .toBe('completed');
  await page.reload();
  await expect(
    page.getByRole('definition').filter({ hasText: '1' }).first(),
  ).toBeVisible();
  await expect(page.getByText('Sin error')).toBeVisible();

  await page.goto(
    `/organizaciones/${slug}/evaluaciones/analitica/${assessmentVersionId}`,
  );
  await expect(page.getByText('Aún no hay analítica agregada')).toBeVisible();
  await page.getByLabel('Revisión de calificación').selectOption(correction.id);
  await page.getByRole('button', { name: 'Actualizar snapshot' }).click();
  await expect(page.getByText('Snapshot actualizado.')).toBeVisible({
    timeout: 45_000,
  });
  await expect(page.getByText('Muestra pequeña')).toBeVisible({
    timeout: 15_000,
  });
  await expect(
    page.getByText('Facilidad, discriminación y omisiones'),
  ).toBeVisible();
  await expectAccessible(page);

  const gradebookResponse = await page.request.get(
    `/api/v1/organizations/${slug}/assessments/gradebooks/${gradebookId}/summaries/`,
  );
  const summaries = (await gradebookResponse.json()) as {
    weighted_percent_basis_points: number;
  }[];
  expect(summaries[0]?.weighted_percent_basis_points).toBe(2833);
  await studentContext.close();
});
