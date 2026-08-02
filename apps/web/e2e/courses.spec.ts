import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

const coursePath = '/organizaciones/organizacion-a/cursos/curso-estructura-e2e';

async function login(
  page: import('@playwright/test').Page,
  email = 'owner@organizations.e2e.test',
  next = '/organizaciones/organizacion-a/cursos',
) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password!);
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

async function expectNoAxeViolations(page: import('@playwright/test').Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

async function submitForReview(page: import('@playwright/test').Page) {
  await page.getByRole('button', { name: 'Enviar a revisión' }).click();
  await page.getByRole('button', { name: 'Enviar revisión' }).click();
}

test('course authoring, conflict, review, approval, roles and axe work end to end', async ({
  browser,
  page,
}) => {
  test.setTimeout(300_000);
  await login(page, 'author@organizations.e2e.test');
  await expectNoAxeViolations(page);
  await page.getByRole('link', { name: 'Crear curso' }).click();
  await expectNoAxeViolations(page);
  await expect(page.getByRole('radio')).toHaveCount(1, { timeout: 15_000 });
  await expect(
    page.getByRole('radio', { name: 'Principal: Precálculo' }),
  ).toBeChecked({ timeout: 15_000 });
  await expect(
    page.getByText(
      'No tienes responsabilidad académica sobre todas las asignaturas.',
    ),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByText('Resumen de creación')).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.setViewportSize({ width: 1280, height: 720 });
  await page.getByLabel('Slug').fill('curso-estructura-e2e');
  await page
    .getByRole('textbox', { name: 'Título', exact: true })
    .fill('Curso de estructura E2E');
  await page
    .getByLabel('Resumen')
    .fill('Curso neutral para verificar el flujo estructural completo.');
  await page.getByLabel('Principal: Precálculo').check();
  await page
    .getByRole('checkbox', {
      name: /OBJ-COURSE-001.*Interpretar funciones/,
    })
    .check();
  await page.getByRole('button', { name: 'Crear curso' }).click();
  await expect(page).toHaveURL(coursePath, { timeout: 15_000 });
  await expect(
    page.getByRole('heading', { name: 'Curso de estructura E2E' }),
  ).toBeVisible();

  await expectNoAxeViolations(page);
  const contextB = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const pageB = await contextB.newPage();
  await login(
    pageB,
    'author@organizations.e2e.test',
    '/organizaciones/organizacion-a/cursos',
  );
  await pageB.goto(coursePath);
  const revision = await page.evaluate(async () => {
    const rows = (await fetch(
      '/api/v1/organizations/organizacion-a/courses/curso-estructura-e2e/revisions/',
    ).then((response) => response.json())) as Array<{
      id: string;
      lock_version: number;
    }>;
    return rows[0];
  });
  expect(revision).toBeTruthy();
  const updateFrom = async (
    target: import('@playwright/test').Page,
    summary: string,
  ) =>
    target.evaluate(
      async ({ current, value }) => {
        const csrfToken = document.cookie
          .split('; ')
          .find((cookie) => cookie.startsWith('csrftoken='))
          ?.split('=')[1];
        return fetch(
          `/api/v1/organizations/organizacion-a/courses/curso-estructura-e2e/revisions/${current!.id}/`,
          {
            body: JSON.stringify({
              expected_version: current!.lock_version,
              summary: value,
            }),
            headers: {
              'Content-Type': 'application/json',
              ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
            },
            method: 'PATCH',
          },
        ).then((response) => response.status);
      },
      { current: revision, value: summary },
    );
  expect(await updateFrom(page, 'Cambio ganador desde el contexto A.')).toBe(
    200,
  );
  expect(await updateFrom(pageB, 'Valor obsoleto del contexto B.')).toBe(409);
  await contextB.close();

  const preservedSummary =
    'Valor preservado en el formulario tras el conflicto.';
  await page.getByLabel('Resumen').fill(preservedSummary);
  await page
    .getByRole('button', { name: 'Guardar información básica' })
    .click();
  await expect(page.getByText(/Tus valores se conservaron/)).toBeVisible();
  await expect(page.getByLabel('Resumen')).toHaveValue(preservedSummary);
  await page.reload();
  await page
    .getByLabel('Título', { exact: true })
    .fill('Curso autor actualizado');
  await page
    .getByLabel('Resumen')
    .fill('Curso corregido por Author antes de construir la estructura.');
  await page
    .getByRole('button', { name: 'Guardar información básica' })
    .click();
  await expect(page.getByText('Información básica actualizada.')).toBeVisible();

  await page.goto(`${coursePath}/estructura`);
  await expectNoAxeViolations(page);
  await page.getByLabel('Nombre del módulo').fill('Fundamentos');
  await page.getByRole('button', { name: 'Crear módulo' }).click();
  await expect(
    page.getByRole('heading', { name: 'Fundamentos' }),
  ).toBeVisible();
  let fundamentals = page
    .getByRole('heading', { name: 'Fundamentos' })
    .locator('xpath=ancestor::li[1]');
  await fundamentals.getByText('Añadir lección', { exact: true }).click();
  await fundamentals
    .getByLabel('Título de la lección')
    .fill('Funciones y representaciones');
  await fundamentals.getByRole('button', { name: 'Crear lección' }).click();
  await expect(
    page.getByText(/^\d+\. Funciones y representaciones$/),
  ).toBeVisible();
  fundamentals = page
    .getByRole('heading', { name: 'Fundamentos' })
    .locator('xpath=ancestor::li[1]');
  let lesson = fundamentals
    .getByText(/^\d+\. Funciones y representaciones$/)
    .locator('xpath=ancestor::li[1]');
  await lesson
    .getByLabel('Configurar lección «Funciones y representaciones»')
    .click();
  await lesson
    .getByRole('checkbox', { name: 'Funciones', exact: true })
    .check();
  await lesson.getByRole('button', { name: 'Guardar temas' }).click();
  await expect(
    page.getByText('Temas de la unidad actualizados.'),
  ).toBeVisible();
  await lesson.getByRole('checkbox', { name: /OBJ-COURSE-001/ }).check();
  await lesson.getByRole('button', { name: 'Guardar objetivos' }).click();
  await expect(
    page.getByText('Objetivos de la unidad actualizados.'),
  ).toBeVisible();

  await page.getByLabel('Nombre del módulo').fill('Aplicaciones');
  await page.getByRole('button', { name: 'Crear módulo' }).click();
  await expect(
    page.getByRole('heading', { name: 'Aplicaciones' }),
  ).toBeVisible();
  let applications = page
    .getByRole('heading', { name: 'Aplicaciones' })
    .locator('xpath=ancestor::li[1]');
  await applications.getByText('Añadir lección', { exact: true }).click();
  await applications
    .getByLabel('Título de la lección')
    .fill('Modelación contextual');
  await applications.getByRole('button', { name: 'Crear lección' }).click();
  applications = page
    .getByRole('heading', { name: 'Aplicaciones' })
    .locator('xpath=ancestor::li[1]');
  lesson = applications
    .getByText(/^\d+\. Modelación contextual$/)
    .locator('xpath=ancestor::li[1]');
  await lesson.getByLabel('Configurar lección «Modelación contextual»').click();
  await lesson.getByRole('checkbox', { name: /OBJ-COURSE-001/ }).check();
  await lesson.getByRole('button', { name: 'Guardar objetivos' }).click();
  await expect(
    page.getByText('Objetivos de la unidad actualizados.'),
  ).toBeVisible();

  await page
    .getByRole('button', {
      name: 'Mover «Aplicaciones» una posición arriba',
    })
    .press('Enter');
  await expect(
    page.getByText('«Aplicaciones» ahora está en la posición 1.'),
  ).toBeVisible();
  await page.reload();
  await expect(
    page
      .locator('section[aria-labelledby="course-structure"] > ol > li h3')
      .first(),
  ).toHaveText('Aplicaciones');

  applications = page
    .getByRole('heading', { name: 'Aplicaciones' })
    .locator('xpath=ancestor::li[1]');
  await applications
    .getByRole('button', { name: 'Archivar módulo' })
    .press('Enter');
  await expect(page.getByText('Elemento archivado.')).toBeVisible();
  await page.getByRole('button', { name: 'Restaurar módulo' }).press('Enter');
  await expect(page.getByText('Elemento restaurado al final.')).toBeVisible();
  await expectNoAxeViolations(page);

  const readinessSetupStatuses = await page.evaluate(async () => {
    const csrfToken = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1];
    const headers = {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
    };
    const courseBase =
      '/api/v1/organizations/organizacion-a/courses/curso-estructura-e2e';
    const revisions = (await fetch(`${courseBase}/revisions/`).then(
      (response) => response.json(),
    )) as Array<{ id: string; lock_version: number }>;
    const revision = revisions[0]!;
    const revisionBase = `${courseBase}/revisions/${revision.id}`;
    const outline = (await fetch(`${revisionBase}/outline/`).then((response) =>
      response.json(),
    )) as { modules: Array<{ units: Array<{ id: string }> }> };
    const contentStatuses = await Promise.all(
      outline.modules.flatMap((module) =>
        module.units.map((unit) =>
          fetch(`${revisionBase}/units/${unit.id}/content/`, {
            body: JSON.stringify({
              content: {
                content: [
                  {
                    attrs: { nodeId: crypto.randomUUID() },
                    content: [
                      {
                        text: 'Contenido académico verificable para la revisión.',
                        type: 'text',
                      },
                    ],
                    type: 'paragraph',
                  },
                ],
                type: 'doc',
              },
              expected_document_version: 0,
              schema_version: 1,
            }),
            headers,
            method: 'PUT',
          }).then((response) => response.status),
        ),
      ),
    );
    const policyStatus = await fetch(`${revisionBase}/completion-policy/`, {
      body: JSON.stringify({
        expected_version: revision.lock_version,
        minimum_attendance_basis_points: null,
        minimum_grade_basis_points: null,
        require_required_activities: true,
      }),
      headers,
      method: 'PUT',
    }).then((response) => response.status);
    return [...contentStatuses, policyStatus];
  });
  expect(readinessSetupStatuses).toEqual([200, 200, 200]);

  await page.goto(`${coursePath}/revision`);
  await expectNoAxeViolations(page);
  await expect(page.getByText('Lista para revisión')).toBeVisible();
  await submitForReview(page);
  await expect(page.getByText('Estado actual: En revisión')).toBeVisible({
    timeout: 15_000,
  });
  await page.goto(coursePath);
  await expect(
    page.getByRole('button', { name: 'Guardar información básica' }),
  ).toHaveCount(0);

  await logout(page);
  await login(page, 'reviewer@organizations.e2e.test', coursePath);
  await expect(
    page.getByRole('button', { name: 'Aprobar estructura' }),
  ).toBeVisible();
  const reviewNote = page.getByLabel('Nota para solicitar cambios');
  await page.getByRole('button', { name: 'Solicitar cambios' }).click();
  await expect(reviewNote).toBeFocused();
  await reviewNote.fill('Aclara la secuencia pedagógica.');
  await page.getByRole('button', { name: 'Solicitar cambios' }).press('Enter');
  await expect(
    page.getByText('Estado actual: Cambios solicitados'),
  ).toBeVisible({ timeout: 15_000 });

  await logout(page);
  await login(page, 'author@organizations.e2e.test', coursePath);
  await expect(
    page.getByRole('button', { name: 'Aprobar estructura' }),
  ).toHaveCount(0);
  await page.goto(`${coursePath}/estructura`);
  applications = page
    .getByRole('heading', { name: 'Aplicaciones' })
    .locator('xpath=ancestor::li[1]');
  lesson = applications
    .getByText(/^\d+\. Modelación contextual$/)
    .locator('xpath=ancestor::li[1]');
  await lesson.getByLabel('Configurar lección «Modelación contextual»').click();
  await lesson
    .getByRole('textbox', { name: 'Título', exact: true })
    .fill('Modelación contextual corregida');
  await lesson.getByRole('button', { name: 'Guardar información' }).click();
  await expect(page.getByText('Unidad actualizada.')).toBeVisible();
  await page.goto(coursePath);
  await submitForReview(page);
  await expect(page.getByText('Estado actual: En revisión')).toBeVisible({
    timeout: 15_000,
  });

  await logout(page);
  await login(page, 'reviewer@organizations.e2e.test', coursePath);
  await page.getByRole('button', { name: 'Aprobar estructura' }).click();
  await expect(
    page.getByText(
      'La estructura fue aprobada. La publicación y el contenido se mantienen separados: aprobar no publica el curso.',
    ),
  ).toBeVisible();

  await page.setViewportSize({ height: 844, width: 390 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectNoAxeViolations(page);

  await logout(page);
  await login(page, 'author@organizations.e2e.test', coursePath);
  await expect(
    page.getByRole('button', { name: 'Guardar información básica' }),
  ).toHaveCount(0);
  await logout(page);
  await login(page, 'instructor@organizations.e2e.test', coursePath);
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
  await logout(page);
  await login(
    page,
    'learner@organizations.e2e.test',
    '/organizaciones/organizacion-a/aprendizaje',
  );
  await page.goto(coursePath);
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
});

test('incomplete course cannot enter review and focuses its readiness issues', async ({
  page,
}) => {
  await login(page, 'author@organizations.e2e.test');
  await page.getByRole('link', { name: 'Crear curso' }).click();
  await page.getByLabel('Slug').fill('curso-incompleto-e2e');
  await page
    .getByRole('textbox', { name: 'Título', exact: true })
    .fill('Curso incompleto E2E');
  await page
    .getByLabel('Resumen')
    .fill('Curso creado para probar la validación antes de revisión.');
  await page.getByLabel('Principal: Precálculo').check();
  await page.getByRole('button', { name: 'Crear curso' }).click();
  await expect(page).toHaveURL(
    '/organizaciones/organizacion-a/cursos/curso-incompleto-e2e',
    { timeout: 15_000 },
  );
  await expect(page.getByText('Problemas por resolver')).toBeVisible();
  await submitForReview(page);
  await expect(
    page.getByText('Resuelve los problemas de integridad antes de enviar.'),
  ).toBeVisible();
  await expect(page.locator('#readiness-issues')).toBeFocused();
  await expect(page.getByText('Estado actual: Borrador')).toBeVisible();
});

test('foreign organization course URL is hidden with 404', async ({ page }) => {
  await login(page, 'author@organizations.e2e.test');
  await page.getByRole('link', { name: 'Crear curso' }).click();
  await page.getByLabel('Slug').fill('curso-idor-e2e');
  await page
    .getByRole('textbox', { name: 'Título', exact: true })
    .fill('Curso para IDOR');
  await page
    .getByLabel('Resumen')
    .fill('Curso temporal para probar aislamiento en todos los niveles.');
  await page.getByLabel('Principal: Precálculo').check();
  await page.getByRole('button', { name: 'Crear curso' }).click();
  const idorPath = '/organizaciones/organizacion-a/cursos/curso-idor-e2e';
  await expect(page).toHaveURL(idorPath, { timeout: 15_000 });
  const ids = await page.evaluate(async () => {
    const csrfToken = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1];
    const revisions = (await fetch(
      '/api/v1/organizations/organizacion-a/courses/curso-idor-e2e/revisions/',
    ).then((response) => response.json())) as Array<{
      id: string;
      lock_version: number;
    }>;
    const revision = revisions[0]!;
    const headers = {
      'Content-Type': 'application/json',
      ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
    };
    const courseBase = `/api/v1/organizations/organizacion-a/courses/curso-idor-e2e/revisions/${revision.id}`;
    const courseModule = (await fetch(`${courseBase}/modules/`, {
      body: JSON.stringify({
        expected_version: revision.lock_version,
        title: 'Módulo ajeno',
      }),
      headers,
      method: 'POST',
    }).then((response) => response.json())) as {
      id: string;
      lock_version: number;
    };
    const unit = (await fetch(
      `${courseBase}/modules/${courseModule.id}/units/`,
      {
        body: JSON.stringify({
          expected_version: courseModule.lock_version,
          title: 'Unidad ajena',
        }),
        headers,
        method: 'POST',
      },
    ).then((response) => response.json())) as { id: string };
    return {
      moduleId: courseModule.id,
      revisionId: revision.id,
      unitId: unit.id,
    };
  });
  await logout(page);
  await login(
    page,
    'external@organizations.e2e.test',
    '/organizaciones/organizacion-b/miembros',
  );
  await page.goto(idorPath);
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
  const statuses = await page.evaluate(async (foreignIds) => {
    const base = '/api/v1/organizations/organizacion-a/courses/curso-idor-e2e';
    return Promise.all(
      [
        `${base}/`,
        `${base}/revisions/${foreignIds.revisionId}/`,
        `${base}/revisions/${foreignIds.revisionId}/modules/${foreignIds.moduleId}/`,
        `${base}/revisions/${foreignIds.revisionId}/units/${foreignIds.unitId}/`,
      ].map((url) => fetch(url).then((response) => response.status)),
    );
  }, ids);
  expect(statuses).toEqual([404, 404, 404, 404]);
});
