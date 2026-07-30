import AxeBuilder from '@axe-core/playwright';
import { expect, test, type BrowserContext, type Page } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

type CourseFixture = {
  contentPaths: string[];
  coursePath: string;
  revisionId: string;
  revisionVersion: number;
  unitIds: string[];
};

async function login(
  page: Page,
  email: string,
  next = '/organizaciones/organizacion-a/cursos',
) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password!);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL(next);
}

async function logout(page: Page) {
  await page.goto('/estudiar');
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL('/auth/iniciar-sesion');
}

function rejectExternalRequests(context: BrowserContext, external: string[]) {
  context.on('request', (request) => {
    const url = new URL(request.url());
    if (
      !['127.0.0.1', 'localhost'].includes(url.hostname) &&
      !['data:', 'blob:'].includes(url.protocol)
    )
      external.push(request.url());
  });
}

async function expectNoAxeViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

async function createCourseFixture(page: Page): Promise<CourseFixture> {
  return page.evaluate(async () => {
    const csrf = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1];
    async function api<T>(url: string, init: RequestInit = {}): Promise<T> {
      const response = await fetch(url, {
        ...init,
        headers: {
          'Content-Type': 'application/json',
          ...(csrf ? { 'X-CSRFToken': csrf } : {}),
          ...init.headers,
        },
      });
      if (!response.ok)
        throw new Error(`${init.method ?? 'GET'} ${url}: ${response.status}`);
      return response.json() as Promise<T>;
    }

    const subjects = await api<Array<{ id: string }>>(
      '/api/v1/organizations/organizacion-a/catalog/subjects/',
    );
    const objectives = await api<Array<{ id: string }>>(
      '/api/v1/organizations/organizacion-a/catalog/learning-objectives/',
    );
    const primary = subjects[0]!;
    const objective = objectives[0]!;
    const revision = await api<{ id: string; lock_version: number }>(
      '/api/v1/organizations/organizacion-a/courses/',
      {
        body: JSON.stringify({
          learning_objective_ids: [objective.id],
          primary_subject_id: primary.id,
          slug: 'contenido-semantico-e2e',
          summary: 'Curso aislado para verificar contenido semántico.',
          title: 'Contenido semántico E2E',
        }),
        method: 'POST',
      },
    );
    const courseBase =
      `/api/v1/organizations/organizacion-a/courses/contenido-semantico-e2e` +
      `/revisions/${revision.id}`;
    const courseModule = await api<{ id: string; lock_version: number }>(
      `${courseBase}/modules/`,
      {
        body: JSON.stringify({
          expected_version: revision.lock_version,
          title: 'Fundamentos semánticos',
        }),
        method: 'POST',
      },
    );
    let lockVersion = courseModule.lock_version;
    const unitIds: string[] = [];
    for (const title of ['Funciones', 'Límites']) {
      const unit = await api<{ id: string; lock_version: number }>(
        `${courseBase}/modules/${courseModule.id}/units/`,
        {
          body: JSON.stringify({
            expected_version: lockVersion,
            title,
          }),
          method: 'POST',
        },
      );
      unitIds.push(unit.id);
      lockVersion = unit.lock_version;
      const aligned = await api<{ lock_version: number }>(
        `${courseBase}/units/${unit.id}/learning-objectives/`,
        {
          body: JSON.stringify({
            expected_version: lockVersion,
            learning_objective_ids: [objective.id],
          }),
          method: 'PUT',
        },
      );
      lockVersion = aligned.lock_version;
    }
    return {
      contentPaths: unitIds.map(
        (unitId) => `${courseBase}/units/${unitId}/content/`,
      ),
      coursePath:
        '/organizaciones/organizacion-a/cursos/contenido-semantico-e2e',
      revisionId: revision.id,
      revisionVersion: lockVersion,
      unitIds,
    };
  });
}

async function saveSimpleDocument(
  page: Page,
  path: string,
  text: string,
  expectedVersion = 0,
) {
  return page.evaluate(
    async ({ expected, message, url }) => {
      const csrf = document.cookie
        .split('; ')
        .find((cookie) => cookie.startsWith('csrftoken='))
        ?.split('=')[1];
      const response = await fetch(url, {
        body: JSON.stringify({
          content: {
            content: [
              {
                attrs: { nodeId: crypto.randomUUID() },
                content: [{ text: message, type: 'text' }],
                type: 'paragraph',
              },
            ],
            type: 'doc',
          },
          expected_document_version: expected,
          schema_version: 1,
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(csrf ? { 'X-CSRFToken': csrf } : {}),
        },
        method: 'PUT',
      });
      return { body: await response.json(), status: response.status };
    },
    { expected: expectedVersion, message: text, url: path },
  );
}

test('semantic content authoring, versioning, conflict, readiness, roles, security and axe work end to end', async ({
  browser,
  context,
  page,
}) => {
  test.setTimeout(180_000);
  const externalRequests: string[] = [];
  rejectExternalRequests(context, externalRequests);
  await login(page, 'author@organizations.e2e.test');
  const fixture = await createCourseFixture(page);
  const primaryContentPath = fixture.contentPaths[0]!;
  const secondaryContentPath = fixture.contentPaths[1]!;
  const editorPath = `${fixture.coursePath}/unidades/${fixture.unitIds[0]}/contenido`;
  await page.goto(editorPath);
  await expect(page.getByRole('heading', { name: 'Funciones' })).toBeVisible();
  await expect(
    page.getByText('Editor de contenido académico semántico'),
  ).toBeVisible();
  await expectNoAxeViolations(page);

  const editor = page.getByRole('textbox', {
    name: 'Contenido académico de la unidad',
  });
  await editor.click();
  await page.keyboard.type(
    'Una función relaciona cada entrada con una salida.',
  );
  await page.keyboard.press('Enter');
  await page.getByRole('button', { name: 'Título nivel 2' }).click();
  const insertedHeading = editor.locator('h2').last();
  await expect(insertedHeading).toBeVisible();
  await insertedHeading.click();
  await page.keyboard.type('Representaciones de funciones');
  await page.getByRole('button', { name: 'Bloque pedagógico' }).click();
  await page.getByLabel('Título opcional').fill('Definición');
  await page.getByRole('button', { name: 'Insertar bloque' }).click();

  await page.getByRole('button', { name: 'Matemática inline' }).click();
  await page.locator('math-field').evaluate((element) => {
    const field = element as HTMLElement & { value: string };
    field.value = 'f(x)=x^2';
    field.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await page.getByRole('button', { name: 'Aplicar matemática' }).click();
  await page.getByRole('button', { name: 'Matemática display' }).click();
  await page.locator('math-field').evaluate((element) => {
    const field = element as HTMLElement & { value: string };
    field.value = '\\lim_{x\\to 0}\\frac{\\sin x}{x}=1';
    field.dispatchEvent(new Event('input', { bubbles: true }));
  });
  await page.getByLabel('Etiqueta opcional').fill('limite-seno');
  await page.getByRole('button', { name: 'Aplicar matemática' }).click();

  await page.getByRole('button', { name: 'Bloque de código' }).click();
  await page.getByLabel('Lenguaje').selectOption('python');
  await page
    .getByLabel('Descripción opcional')
    .fill('Evaluación de la función');
  await page.getByRole('button', { name: 'Insertar bloque de código' }).click();
  const codeEditor = page.locator('.cm-content').last();
  await codeEditor.click();
  await page.keyboard.type('def f(x):\\n    return x ** 2');
  await page.keyboard.press('Tab');
  await expect(page.getByText('Tab sale del editor de código.')).toBeVisible();

  await page.getByRole('button', { name: 'Tabla', exact: true }).click();
  await page.getByLabel('Descripción', { exact: true }).fill('Valores de f');
  await page.getByRole('button', { name: 'Insertar tabla' }).click();
  await expect(
    page.getByText('Cambios sin guardar', { exact: true }),
  ).toBeVisible();
  await page.getByRole('button', { name: 'Guardar contenido' }).click();
  await expect(
    page.getByText('Contenido guardado como versión 1.'),
  ).toBeVisible();
  const storedNodes = await page.evaluate(async (path) => {
    const current = await fetch(path).then((response) => response.json());
    const nodes: Array<{ attrs?: { code?: string }; type: string }> = [];
    function walk(node: {
      attrs?: { code?: string };
      content?: Array<Parameters<typeof walk>[0]>;
      type: string;
    }) {
      nodes.push(node);
      node.content?.forEach(walk);
    }
    walk(current.content);
    return nodes;
  }, primaryContentPath);
  expect(storedNodes.map((node) => node.type)).toEqual(
    expect.arrayContaining([
      'heading',
      'pedagogicalBlock',
      'inlineMath',
      'displayMath',
      'codeBlock',
      'table',
    ]),
  );
  expect(
    storedNodes.find((node) => node.type === 'codeBlock')?.attrs?.code,
  ).toContain('def f(x)');
  await page.reload();
  await expect(editor).toContainText('Una función relaciona');
  await page.getByRole('button', { name: 'Vista previa' }).click();
  await expect(page.getByText('Representaciones de funciones')).toBeVisible();
  await expect(page.locator('pre code')).toContainText('def f(x)');
  await expectNoAxeViolations(page);

  const contextB = await browser.newContext({
    baseURL: 'http://127.0.0.1:3000',
  });
  rejectExternalRequests(contextB, externalRequests);
  const pageB = await contextB.newPage();
  await login(pageB, 'author@organizations.e2e.test');
  await pageB.goto(editorPath);
  const winner = await saveSimpleDocument(
    page,
    primaryContentPath,
    'Versión ganadora del contexto A.',
    1,
  );
  expect(winner.status).toBe(200);
  const editorB = pageB.getByRole('textbox', {
    name: 'Contenido académico de la unidad',
  });
  await editorB.locator('p').first().click();
  await pageB.keyboard.press('End');
  await pageB.keyboard.type(' Cambio local B preservado.');
  await pageB.getByRole('button', { name: 'Guardar contenido' }).click();
  await expect(pageB.getByText(/Otra persona guardó/)).toBeVisible();
  await expect(editorB).toContainText('Cambio local B preservado');
  const serverCurrent = await page.evaluate(async (path) => {
    const response = await fetch(path);
    return response.json();
  }, primaryContentPath);
  expect(JSON.stringify(serverCurrent)).toContain('Versión ganadora');
  expect(JSON.stringify(serverCurrent)).not.toContain('Cambio local B');
  await contextB.close();

  await page.goto(editorPath);
  await editor.locator('p').first().click();
  await page.keyboard.press('End');
  await page.keyboard.type(' Segunda edición versionada.');
  await page.keyboard.press('Control+s');
  await expect(
    page.getByText('Contenido guardado como versión 3.'),
  ).toBeVisible();
  await page.getByText(/Historial de versiones/).click();
  const versionOne = page.getByRole('listitem').filter({
    hasText: 'Versión 1',
  });
  await versionOne.getByRole('button', { name: 'Ver' }).click();
  await expect(page.getByText('Vista de la versión 1')).toBeVisible();
  page.once('dialog', (dialog) => dialog.accept());
  await versionOne.getByRole('button', { name: 'Restaurar' }).click();
  await expect(
    page.getByText('Versión restaurada como versión 4.'),
  ).toBeVisible();

  const unsafeStatuses = await page.evaluate(
    async ({ path }) => {
      const csrf = document.cookie
        .split('; ')
        .find((cookie) => cookie.startsWith('csrftoken='))
        ?.split('=')[1];
      const current = await fetch(path).then((response) => response.json());
      const put = (content: unknown) =>
        fetch(path, {
          body: JSON.stringify({
            content,
            expected_document_version: current.document_version,
            schema_version: 1,
          }),
          headers: {
            'Content-Type': 'application/json',
            ...(csrf ? { 'X-CSRFToken': csrf } : {}),
          },
          method: 'PUT',
        }).then((response) => response.status);
      const linkStatus = await put({
        content: [
          {
            attrs: { nodeId: crypto.randomUUID() },
            content: [
              {
                marks: [
                  { attrs: { href: 'javascript:alert(1)' }, type: 'link' },
                ],
                text: 'malicioso',
                type: 'text',
              },
            ],
            type: 'paragraph',
          },
        ],
        type: 'doc',
      });
      const mathStatus = await put({
        content: [
          {
            attrs: {
              latex: '\\require{texhtml}\\href{javascript:alert(1)}{X}',
              nodeId: crypto.randomUUID(),
            },
            type: 'displayMath',
          },
        ],
        type: 'doc',
      });
      return { linkStatus, mathStatus };
    },
    { path: primaryContentPath },
  );
  expect(unsafeStatuses).toEqual({ linkStatus: 400, mathStatus: 400 });

  const missingReadiness = await page.evaluate(async ({ revisionId }) => {
    const response = await fetch(
      `/api/v1/organizations/organizacion-a/courses/contenido-semantico-e2e/revisions/${revisionId}/readiness/`,
    );
    return response.json();
  }, fixture);
  expect(missingReadiness.ready).toBe(false);
  expect(JSON.stringify(missingReadiness)).toContain('unit_content_missing');
  const secondSave = await saveSimpleDocument(
    page,
    secondaryContentPath,
    'Los límites describen el comportamiento local de una función.',
  );
  expect(secondSave.status).toBe(200);
  const submitted = await page.evaluate(
    async ({ revisionId, revisionVersion }) => {
      const csrf = document.cookie
        .split('; ')
        .find((cookie) => cookie.startsWith('csrftoken='))
        ?.split('=')[1];
      const response = await fetch(
        `/api/v1/organizations/organizacion-a/courses/contenido-semantico-e2e/revisions/${revisionId}/submit-review/`,
        {
          body: JSON.stringify({ expected_version: revisionVersion }),
          headers: {
            'Content-Type': 'application/json',
            ...(csrf ? { 'X-CSRFToken': csrf } : {}),
          },
          method: 'POST',
        },
      );
      return { body: await response.json(), status: response.status };
    },
    fixture,
  );
  expect(submitted.status).toBe(200);
  await page.goto(editorPath);
  await expect(
    page.getByRole('toolbar', { name: 'Herramientas de formato' }),
  ).toHaveCount(0);
  await expect(page.getByText(/modo de solo lectura/)).toBeVisible();

  await logout(page);
  await login(page, 'reviewer@organizations.e2e.test', editorPath);
  await expect(page.getByText('Representaciones de funciones')).toBeVisible();
  await expect(page.getByText(/modo de solo lectura/)).toBeVisible();
  const reviewerPut = await saveSimpleDocument(
    page,
    primaryContentPath,
    'Intento de reviewer.',
    4,
  );
  expect(reviewerPut.status).toBe(403);
  await expectNoAxeViolations(page);

  await logout(page);
  await login(page, 'owner@organizations.e2e.test', fixture.coursePath);
  const approved = await page.evaluate(async ({ revisionId }) => {
    const csrf = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1];
    const revision = await fetch(
      `/api/v1/organizations/organizacion-a/courses/contenido-semantico-e2e/revisions/${revisionId}/`,
    ).then((response) => response.json());
    return fetch(
      `/api/v1/organizations/organizacion-a/courses/contenido-semantico-e2e/revisions/${revisionId}/approve/`,
      {
        body: JSON.stringify({ expected_version: revision.lock_version }),
        headers: {
          'Content-Type': 'application/json',
          ...(csrf ? { 'X-CSRFToken': csrf } : {}),
        },
        method: 'POST',
      },
    ).then((response) => response.status);
  }, fixture);
  expect(approved).toBe(200);

  await logout(page);
  await login(page, 'instructor@organizations.e2e.test', editorPath);
  await expect(page.getByText(/modo de solo lectura/)).toBeVisible();
  await expect(
    page.getByRole('toolbar', { name: 'Herramientas de formato' }),
  ).toHaveCount(0);

  await logout(page);
  await login(page, 'learner@organizations.e2e.test', editorPath);
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
  await logout(page);
  await login(page, 'external@organizations.e2e.test', '/organizaciones');
  await page.goto(editorPath);
  await expect(page.getByRole('heading', { name: '404' })).toBeVisible();
  const idorStatus = await page.evaluate(
    (path) => fetch(path).then((response) => response.status),
    primaryContentPath,
  );
  expect(idorStatus).toBe(404);

  expect(externalRequests).toEqual([]);
});
