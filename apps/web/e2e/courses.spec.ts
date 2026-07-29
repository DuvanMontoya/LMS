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
  await expect(page).toHaveURL(next);
}

async function logout(page: import('@playwright/test').Page) {
  await page.goto('/estudiar');
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL('/auth/iniciar-sesion');
}

async function expectNoAxeViolations(page: import('@playwright/test').Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

test('course authoring, conflict, review, approval, roles and axe work end to end', async ({
  browser,
  page,
}) => {
  test.setTimeout(120_000);
  await login(page, 'author@organizations.e2e.test');
  await expectNoAxeViolations(page);
  await page.getByRole('link', { name: 'Crear curso' }).click();
  await expectNoAxeViolations(page);
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
  await expect(page).toHaveURL(coursePath);
  await expect(
    page.getByRole('heading', { name: 'Curso de estructura E2E' }),
  ).toBeVisible();

  await expectNoAxeViolations(page);
  const contextB = await browser.newContext({
    baseURL: 'http://127.0.0.1:3000',
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
  await page.getByLabel('Título del nuevo módulo').fill('Fundamentos');
  await page.getByRole('button', { name: 'Añadir módulo' }).click();
  await expect(
    page.getByRole('heading', { name: 'Fundamentos' }),
  ).toBeVisible();
  await page
    .getByLabel('Nueva unidad en «Fundamentos»')
    .fill('Funciones y representaciones');
  await page.getByRole('button', { name: 'Añadir unidad' }).click();
  await expect(
    page.getByRole('heading', { name: /Funciones y representaciones/ }),
  ).toBeVisible();
  await page
    .getByText('Gestionar alineación de «Funciones y representaciones»')
    .click();
  await page.getByRole('checkbox', { name: 'Funciones', exact: true }).check();
  await page
    .getByRole('button', {
      name: 'Guardar temas de Funciones y representaciones',
    })
    .click();
  await expect(
    page.getByText('Temas de la unidad actualizados.'),
  ).toBeVisible();
  await page.getByRole('checkbox', { name: /OBJ-COURSE-001/ }).check();
  await page
    .getByRole('button', {
      name: 'Guardar objetivos de Funciones y representaciones',
    })
    .click();
  await expect(
    page.getByText('Objetivos de la unidad actualizados.'),
  ).toBeVisible();

  await page.getByLabel('Título del nuevo módulo').fill('Aplicaciones');
  await page.getByRole('button', { name: 'Añadir módulo' }).click();
  await expect(
    page.getByRole('heading', { name: 'Aplicaciones' }),
  ).toBeVisible();
  const applicationUnitForm = page
    .getByLabel('Nueva unidad en «Aplicaciones»')
    .locator('xpath=ancestor::form[1]');
  await applicationUnitForm
    .getByLabel('Nueva unidad en «Aplicaciones»')
    .fill('Modelación contextual');
  await applicationUnitForm
    .getByRole('button', { name: 'Añadir unidad' })
    .click();
  await page
    .getByText('Gestionar alineación de «Modelación contextual»')
    .click();
  await page.getByRole('checkbox', { name: /OBJ-COURSE-001/ }).check();
  await page
    .getByRole('button', { name: 'Guardar objetivos de Modelación contextual' })
    .click();
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

  let applications = page
    .getByRole('heading', { name: 'Aplicaciones' })
    .locator('xpath=ancestor::li[1]');
  await applications
    .getByRole('button', { name: 'Archivar unidad' })
    .press('Enter');
  await expect(page.getByText('Elemento archivado.')).toBeVisible();
  applications = page
    .getByRole('heading', { name: 'Aplicaciones' })
    .locator('xpath=ancestor::li[1]');
  await applications
    .getByRole('button', { name: 'Restaurar unidad' })
    .press('Enter');
  await expect(page.getByText('Elemento restaurado al final.')).toBeVisible();
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

  await page.goto(`${coursePath}/revision`);
  await expectNoAxeViolations(page);
  await expect(page.getByText('Lista para revisión')).toBeVisible();
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Enviar a revisión' }).click();
  await expect(page.getByText('Estado actual: in_review')).toBeVisible();
  await page.goto(coursePath);
  await expect(
    page.getByRole('button', { name: 'Guardar información básica' }),
  ).toHaveCount(0);

  await logout(page);
  await login(page, 'reviewer@organizations.e2e.test', coursePath);
  await expect(
    page.getByRole('button', { name: 'Aprobar estructura' }),
  ).toHaveCount(0);
  const reviewNote = page.getByLabel('Nota para solicitar cambios');
  await page.getByRole('button', { name: 'Solicitar cambios' }).click();
  await expect(reviewNote).toBeFocused();
  await reviewNote.fill('Aclara la secuencia pedagógica.');
  await page.getByRole('button', { name: 'Solicitar cambios' }).press('Enter');
  await expect(
    page.getByText('Estado actual: changes_requested'),
  ).toBeVisible();

  await logout(page);
  await login(page, 'author@organizations.e2e.test', coursePath);
  await expect(
    page.getByRole('button', { name: 'Aprobar estructura' }),
  ).toHaveCount(0);
  await page.goto(`${coursePath}/estructura`);
  await page.getByText('Editar unidad «Modelación contextual»').click();
  await page
    .getByLabel('Nuevo título de unidad «Modelación contextual»')
    .fill('Modelación contextual corregida');
  await page
    .getByRole('button', { name: 'Guardar unidad «Modelación contextual»' })
    .click();
  await expect(page.getByText('Unidad actualizada.')).toBeVisible();
  await page.goto(coursePath);
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Enviar a revisión' }).click();
  await expect(page.getByText('Estado actual: in_review')).toBeVisible();

  await logout(page);
  await login(page, 'owner@organizations.e2e.test', coursePath);
  await page.getByRole('button', { name: 'Aprobar estructura' }).click();
  await expect(
    page.getByText(
      'La estructura fue aprobada. La publicación y el contenido se implementarán en fases posteriores.',
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
  await login(page, 'instructor@organizations.e2e.test');
  await expect(
    page.getByRole('heading', { name: 'Curso autor actualizado' }),
  ).toBeVisible();
  await logout(page);
  await login(page, 'learner@organizations.e2e.test', coursePath);
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
  await expect(page.getByText('Problemas por resolver')).toBeVisible();
  page.once('dialog', (dialog) => dialog.accept());
  await page.getByRole('button', { name: 'Enviar a revisión' }).click();
  await expect(
    page.getByText('Resuelve los problemas de integridad antes de enviar.'),
  ).toBeVisible();
  await expect(page.locator('#readiness-issues')).toBeFocused();
  await expect(page.getByText('Estado actual: draft')).toBeVisible();
});

test('foreign organization course URL is hidden with 404', async ({ page }) => {
  await login(page, 'owner@organizations.e2e.test');
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
  await expect(page).toHaveURL(idorPath);
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
  await login(page, 'external@organizations.e2e.test', '/organizaciones');
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
