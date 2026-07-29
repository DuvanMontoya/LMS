import AxeBuilder from '@axe-core/playwright';
import { expect, test } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

async function login(
  page: import('@playwright/test').Page,
  password: string,
  email = 'owner@organizations.e2e.test',
) {
  await page.goto(
    '/auth/iniciar-sesion?next=%2Forganizaciones%2Forganizacion-a%2Fcurriculo',
  );
  await page.getByLabel('Correo electrónico').fill(email);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Iniciar sesión' }).click();
  await expect(page).toHaveURL('/organizaciones/organizacion-a/curriculo');
}

async function logout(page: import('@playwright/test').Page) {
  await page.goto('/estudiar');
  await page.getByRole('button', { name: 'Cerrar sesión' }).click();
  await expect(page).toHaveURL('/auth/iniciar-sesion');
}

test('owner sees the curriculum hierarchy in Chromium', async ({ page }) => {
  await login(page, password);
  await expect(page.getByRole('heading', { name: 'Currículo' })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Matemáticas Activo', exact: true }),
  ).toBeVisible();
  await page.setViewportSize({ height: 844, width: 390 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole('link', { name: 'Precálculo' }).click();
  await expect(page.getByRole('heading', { name: 'Precálculo' })).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Árbol de temas' }),
  ).toBeVisible();
  await expect(
    page.getByLabel('Temas de la asignatura').getByText('Funciones', {
      exact: true,
    }),
  ).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
});

test('owner has no automatic WCAG A/AA violations on every curriculum route', async ({
  page,
}) => {
  await login(page, password);
  const subjectRoute = await page
    .getByRole('link', { name: 'Precálculo' })
    .getAttribute('href');
  expect(subjectRoute).toBeTruthy();
  const curriculumRoutes = [
    '/organizaciones/organizacion-a/curriculo',
    subjectRoute!,
    '/organizaciones/organizacion-a/curriculo/conceptos',
    '/organizaciones/organizacion-a/curriculo/objetivos',
    '/organizaciones/organizacion-a/curriculo/prerrequisitos',
  ];
  for (const route of curriculumRoutes) {
    await page.goto(route);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    const results = await new AxeBuilder({ page })
      .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
      .analyze();
    expect(results.violations, route).toEqual([]);
  }
});

test('owner creates a discipline and subject through the visible hierarchy forms', async ({
  page,
}) => {
  await login(page, password);
  const areaForm = page
    .getByRole('heading', { name: 'Nueva área' })
    .locator('..');
  await areaForm.getByLabel('Nombre').fill('Ciencias');
  await areaForm.getByLabel('Slug').fill('ciencias');
  await areaForm.getByRole('button', { name: 'Crear área' }).click();
  await expect(
    page.getByRole('heading', { name: 'Ciencias Activo', exact: true }),
  ).toBeVisible();
  const disciplineForm = page
    .getByRole('heading', { name: 'Nueva disciplina' })
    .locator('..');
  await disciplineForm.getByLabel('Área').selectOption({ label: 'Ciencias' });
  await disciplineForm.getByLabel('Nombre').fill('Estadística');
  await disciplineForm.getByLabel('Slug').fill('estadistica');
  await disciplineForm.getByRole('button', { name: 'Crear' }).click();
  await expect(
    page
      .getByLabel('Área, disciplina y asignatura')
      .getByText('Estadística', { exact: false }),
  ).toBeVisible();
  const subjectForm = page
    .getByRole('heading', { name: 'Nueva asignatura' })
    .locator('..');
  await subjectForm
    .getByLabel('Disciplina')
    .selectOption({ label: 'Estadística' });
  await subjectForm.getByLabel('Nombre').fill('Probabilidad');
  await subjectForm.getByLabel('Slug').fill('probabilidad');
  await subjectForm.getByRole('button', { name: 'Crear' }).click();
  await expect(page.getByRole('link', { name: 'Probabilidad' })).toBeVisible();
  await page.goto('/organizaciones/organizacion-a/curriculo/prerrequisitos');
  const subjectEditor = page
    .getByRole('heading', { name: 'Prerrequisitos de asignaturas' })
    .locator('..');
  await subjectEditor.getByLabel('Asignatura').selectOption({
    label: 'Probabilidad',
  });
  await subjectEditor.getByRole('checkbox', { name: 'Precálculo' }).check();
  await subjectEditor
    .getByRole('button', { name: 'Guardar prerrequisitos' })
    .click();
  await expect(
    subjectEditor.getByText('Prerrequisitos guardados.'),
  ).toBeVisible();
  await subjectEditor.getByLabel('Asignatura').selectOption({
    label: 'Precálculo',
  });
  await subjectEditor.getByRole('checkbox', { name: 'Probabilidad' }).check();
  await subjectEditor
    .getByRole('button', { name: 'Guardar prerrequisitos' })
    .click();
  await expect(
    page.getByText('La relación produciría un ciclo de prerrequisitos.'),
  ).toBeVisible();
});

test('owner creates a topic and learning objective through visible forms', async ({
  page,
}) => {
  await login(page, password);
  await page.getByRole('link', { name: 'Precálculo' }).click();
  await page.getByLabel('Título').fill('Límites');
  await page.getByLabel('Slug').fill('limites');
  await page.getByRole('button', { name: 'Crear tema' }).click();
  await expect(
    page.locator('span.font-medium').filter({ hasText: 'Límites' }),
  ).toBeVisible();
  await page.getByLabel('Tema padre').selectOption({ label: 'Límites' });
  await page.getByLabel('Título').fill('Continuidad');
  await page.getByLabel('Slug').fill('continuidad');
  await page.getByRole('button', { name: 'Crear tema' }).click();
  await expect(
    page.locator('span.font-medium').filter({ hasText: 'Continuidad' }),
  ).toBeVisible();
  const topicTree = page
    .locator('ul[aria-label="Temas de la asignatura"]')
    .first();
  const continuity = page.locator('li[data-topic-title="Continuidad"]');
  await continuity.getByRole('button', { name: 'Reducir nivel' }).click();
  await expect(
    topicTree.locator(':scope > li[data-topic-title="Continuidad"]'),
  ).toBeVisible();
  const rootContinuity = topicTree.locator(
    ':scope > li[data-topic-title="Continuidad"]',
  );
  await rootContinuity
    .getByLabel('Mover bajo')
    .selectOption({ label: 'Límites' });
  await rootContinuity.getByRole('button', { name: 'Mover como hijo' }).click();
  await expect(
    topicTree.locator(':scope > li[data-topic-title="Continuidad"]'),
  ).not.toBeVisible();
  const limits = page.locator('li[data-topic-title="Límites"]');
  await expect(
    limits
      .getByLabel('Mover bajo')
      .getByRole('option', { name: 'Continuidad' }),
  ).toHaveCount(0);
  const descendantMoveStatus = await page.evaluate(async () => {
    const csrfToken = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1];
    const subjects = (await fetch(
      '/api/v1/organizations/organizacion-a/catalog/subjects/',
    ).then((response) => response.json())) as Array<{
      id: string;
      name: string;
    }>;
    const subject = subjects.find((item) => item.name === 'Precálculo');
    if (!subject) return -1;
    const topics = (await fetch(
      `/api/v1/organizations/organizacion-a/catalog/subjects/${subject.id}/topics/`,
    ).then((response) => response.json())) as Array<{
      children: Array<{ id: string; title: string }>;
      id: string;
      title: string;
    }>;
    const root = topics.find((item) => item.title === 'Límites');
    const child = root?.children.find((item) => item.title === 'Continuidad');
    if (!root || !child) return -1;
    const response = await fetch(
      `/api/v1/organizations/organizacion-a/catalog/topics/${root.id}/move/`,
      {
        body: JSON.stringify({ position: 'last-child', target_id: child.id }),
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
        },
        method: 'POST',
      },
    );
    return response.status;
  });
  expect(descendantMoveStatus).toBe(400);
  await page.goto('/organizaciones/organizacion-a/curriculo/objetivos');
  await page.getByLabel('Asignatura').selectOption({ label: 'Precálculo' });
  await page.getByLabel('Código').fill('OBJ-LIM-001');
  await page
    .getByLabel('Enunciado')
    .fill('Explicar el comportamiento de una función cerca de un punto.');
  await page.getByRole('button', { name: 'Crear objetivo' }).click();
  await expect(page.getByText('OBJ-LIM-001', { exact: true })).toBeVisible();
});

test('owner creates a concept through the visual curriculum form', async ({
  page,
}) => {
  await login(page, password);
  await page.getByRole('link', { name: 'Conceptos' }).click();
  await expect(page.getByRole('heading', { name: 'Conceptos' })).toBeVisible();
  await page.getByLabel('Nombre').fill('Transformación lineal');
  await page.getByLabel('Slug').fill('transformacion-lineal');
  await page
    .getByLabel('Definición')
    .fill('Una correspondencia que preserva las operaciones lineales.');
  await page.getByRole('button', { name: 'Crear concepto' }).click();
  await expect(page.getByText('Concepto creado.')).toBeVisible();
  await expect(
    page.getByRole('heading', { name: 'Transformación lineal' }),
  ).toBeVisible();
  const archive = page.getByRole('button', { name: 'Archivar', exact: true });
  expect(await archive.count()).toBe(1);
  await archive.click();
  await expect(page.getByText('Archivado')).toBeVisible();
  const restore = page.getByRole('button', { name: 'Restaurar', exact: true });
  expect(await restore.count()).toBe(1);
  await restore.click();
  await expect(page.getByText('Activo')).toBeVisible();
  await page.getByLabel('Nombre').fill('Espacio vectorial');
  await page.getByLabel('Slug').fill('espacio-vectorial');
  await page
    .getByLabel('Definición')
    .fill('Conjunto cerrado bajo suma y producto por escalar.');
  await page.getByRole('button', { name: 'Crear concepto' }).click();
  await page.goto('/organizaciones/organizacion-a/curriculo/prerrequisitos');
  const conceptEditor = page
    .getByRole('heading', { name: 'Prerrequisitos de conceptos' })
    .locator('..');
  await conceptEditor.getByLabel('Concepto').selectOption({
    label: 'Transformación lineal',
  });
  await conceptEditor
    .getByRole('checkbox', { name: 'Espacio vectorial' })
    .check();
  await conceptEditor
    .getByRole('button', { name: 'Guardar prerrequisitos' })
    .click();
  await expect(
    conceptEditor.getByText('Prerrequisitos guardados.'),
  ).toBeVisible();
  await conceptEditor.getByLabel('Concepto').selectOption({
    label: 'Espacio vectorial',
  });
  await conceptEditor
    .getByRole('checkbox', { name: 'Transformación lineal' })
    .check();
  await conceptEditor
    .getByRole('button', { name: 'Guardar prerrequisitos' })
    .click();
  await expect(
    conceptEditor.getByText(
      'La relación produciría un ciclo de prerrequisitos.',
    ),
  ).toBeVisible();
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
});

test('owner orders visible topic and objective concept associations', async ({
  page,
}) => {
  await login(page, password);
  await page.getByRole('link', { name: 'Precálculo' }).click();
  const topic = page.locator('li[data-topic-title="Límites"]');
  const topicEditor = topic.locator(
    ':scope > section[aria-label="Editor de conceptos del tema"]',
  );
  await topicEditor
    .getByRole('button', { name: 'Añadir Transformación lineal' })
    .click();
  await topicEditor.getByRole('button', { name: 'Guardar conceptos' }).click();
  await expect(topicEditor.getByText('Asociaciones guardadas.')).toBeVisible();
  await page.goto('/organizaciones/organizacion-a/curriculo/objetivos');
  const objective = page
    .getByRole('listitem')
    .filter({ hasText: 'OBJ-LIM-001' });
  await objective
    .getByRole('button', { name: 'Añadir Transformación lineal' })
    .click();
  await objective.getByRole('button', { name: 'Guardar conceptos' }).click();
  await expect(objective.getByText('Asociaciones guardadas.')).toBeVisible();
});

test('owner must remove active associations before archiving a concept', async ({
  page,
}) => {
  await login(page, password);
  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  const concept = page
    .getByRole('listitem')
    .filter({ hasText: 'Transformación lineal' });
  page.once('dialog', (dialog) => dialog.accept());
  await concept.getByRole('button', { name: 'Archivar' }).click();
  await expect(
    page.getByText('La operación curricular no es válida.'),
  ).toBeVisible();

  await page.getByRole('link', { name: 'Volver al currículo' }).click();
  await page.getByRole('link', { name: 'Precálculo' }).click();
  const topic = page.locator('li[data-topic-title="Límites"]');
  const topicEditor = topic.locator(
    ':scope > section[aria-label="Editor de conceptos del tema"]',
  );
  await topicEditor
    .getByRole('button', { name: 'Quitar Transformación lineal' })
    .click();
  await topicEditor.getByRole('button', { name: 'Guardar conceptos' }).click();
  await expect(topicEditor.getByText('Asociaciones guardadas.')).toBeVisible();

  await page.goto('/organizaciones/organizacion-a/curriculo/objetivos');
  const objective = page
    .getByRole('listitem')
    .filter({ hasText: 'OBJ-LIM-001' });
  await objective
    .getByRole('button', { name: 'Quitar Transformación lineal' })
    .click();
  await objective.getByRole('button', { name: 'Guardar conceptos' }).click();
  await expect(objective.getByText('Asociaciones guardadas.')).toBeVisible();

  await page.goto('/organizaciones/organizacion-a/curriculo/prerrequisitos');
  const conceptEditor = page
    .getByRole('heading', { name: 'Prerrequisitos de conceptos' })
    .locator('..');
  await conceptEditor.getByLabel('Concepto').selectOption({
    label: 'Transformación lineal',
  });
  await conceptEditor
    .getByRole('checkbox', { name: 'Espacio vectorial' })
    .uncheck();
  await conceptEditor
    .getByRole('button', { name: 'Guardar prerrequisitos' })
    .click();
  await expect(
    conceptEditor.getByText('Prerrequisitos guardados.'),
  ).toBeVisible();

  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  const archivableConcept = page
    .getByRole('listitem')
    .filter({ hasText: 'Transformación lineal' });
  page.once('dialog', (dialog) => dialog.accept());
  await archivableConcept.getByRole('button', { name: 'Archivar' }).click();
  await expect(archivableConcept.getByText('Archivado')).toBeVisible();
  await archivableConcept.getByRole('button', { name: 'Restaurar' }).click();
  await expect(archivableConcept.getByText('Activo')).toBeVisible();
});

test('owner edits each visible catalog level', async ({ page }) => {
  await login(page, password);
  const area = page
    .getByRole('heading', { name: 'Matemáticas Activo', exact: true })
    .locator('..');
  await area.getByRole('button', { name: 'Editar área' }).click();
  await area
    .getByLabel('Editar nombre de Matemáticas')
    .fill('Matemáticas aplicadas');
  await area.getByRole('button', { name: 'Guardar nombre' }).click();
  await expect(
    page.getByRole('heading', {
      name: 'Matemáticas aplicadas Activo',
      exact: true,
    }),
  ).toBeVisible();

  const discipline = page.getByLabel('Acciones de Estadística').locator('..');
  await discipline.getByRole('button', { name: 'Editar disciplina' }).click();
  await discipline
    .getByLabel('Editar nombre de Estadística')
    .fill('Estadística formal');
  await discipline.getByRole('button', { name: 'Guardar nombre' }).click();
  await expect(page.getByLabel('Acciones de Estadística formal')).toBeVisible();

  const subject = page.getByLabel('Acciones de Probabilidad').locator('..');
  await subject.getByRole('button', { name: 'Editar asignatura' }).click();
  await subject
    .getByLabel('Editar nombre de Probabilidad')
    .fill('Probabilidad aplicada');
  await subject.getByRole('button', { name: 'Guardar nombre' }).click();
  await expect(
    page.getByLabel('Acciones de Probabilidad aplicada'),
  ).toBeVisible();

  const precalculusLink = page.getByRole('link', { name: 'Precálculo' });
  await expect(precalculusLink).toHaveCount(1);
  await precalculusLink.click();
  await expect(page.getByRole('heading', { name: 'Precálculo' })).toBeVisible();
  const topic = page.locator('li[data-topic-title="Límites"]');
  const topicActions = topic.locator(':scope > fieldset');
  await topicActions.getByRole('button', { name: 'Editar tema' }).click();
  await topicActions
    .getByLabel('Editar título de Límites')
    .fill('Límites avanzados');
  await topicActions.getByRole('button', { name: 'Guardar tema' }).click();
  await expect(
    page.locator('span.font-medium').filter({ hasText: 'Límites avanzados' }),
  ).toBeVisible();
});

test('author can manage the curriculum while reviewer and learner remain read-only', async ({
  page,
}) => {
  await login(page, password, 'author@organizations.e2e.test');
  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  await page.getByLabel('Nombre').fill('Concepto del autor');
  await page.getByLabel('Slug').fill('concepto-del-autor');
  await page.getByLabel('Definición').fill('Creado por una persona autora.');
  await page.getByRole('button', { name: 'Crear concepto' }).click();
  await expect(page.getByText('Concepto creado.')).toBeVisible();
  const authorConcept = page
    .getByRole('listitem')
    .filter({ hasText: 'Concepto del autor' });
  await authorConcept.getByRole('button', { name: 'Editar concepto' }).click();
  await authorConcept
    .getByLabel('Editar definición de Concepto del autor')
    .fill('Editado por una persona autora.');
  await authorConcept.getByRole('button', { name: 'Guardar concepto' }).click();
  await expect(
    authorConcept.getByText('Editado por una persona autora.'),
  ).toBeVisible();

  await page.goto('/organizaciones/organizacion-a/curriculo/objetivos');
  const objective = page
    .getByRole('listitem')
    .filter({ hasText: 'OBJ-LIM-001' });
  await objective.getByRole('button', { name: 'Editar objetivo' }).click();
  await objective
    .getByLabel('Editar enunciado de OBJ-LIM-001')
    .fill('Explicar límites con lenguaje matemático preciso.');
  await objective.getByRole('button', { name: 'Guardar cambios' }).click();
  await expect(
    objective.getByText('Explicar límites con lenguaje matemático preciso.'),
  ).toBeVisible();
  await page.goto('/organizaciones/organizacion-a/curriculo/prerrequisitos');
  const subjectEditor = page
    .getByRole('heading', { name: 'Prerrequisitos de asignaturas' })
    .locator('..');
  await subjectEditor.getByLabel('Asignatura').selectOption({
    label: 'Probabilidad aplicada',
  });
  await subjectEditor
    .getByLabel('Justificación')
    .fill('Actualizado por una persona autora.');
  await subjectEditor
    .getByRole('button', { name: 'Guardar prerrequisitos' })
    .click();
  await expect(
    subjectEditor.getByText('Prerrequisitos guardados.'),
  ).toBeVisible();

  await logout(page);
  await login(page, password, 'reviewer@organizations.e2e.test');
  await expect(page.getByRole('heading', { name: 'Currículo' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Crear área' })).toHaveCount(0);
  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  await expect(
    page.getByRole('button', { name: 'Crear concepto' }),
  ).toHaveCount(0);
  await expect(
    page.getByRole('button', { name: 'Archivar', exact: true }),
  ).toHaveCount(0);
  const reviewerWriteStatus = await page.evaluate(async () => {
    const csrfToken = document.cookie
      .split('; ')
      .find((cookie) => cookie.startsWith('csrftoken='))
      ?.split('=')[1];
    const response = await fetch(
      '/api/v1/organizations/organizacion-a/catalog/concepts/',
      {
        body: JSON.stringify({
          definition: 'La escritura del revisor debe ser rechazada.',
          name: 'Intento del revisor',
          slug: 'intento-del-revisor',
        }),
        headers: {
          'Content-Type': 'application/json',
          ...(csrfToken ? { 'X-CSRFToken': csrfToken } : {}),
        },
        method: 'POST',
      },
    );
    return response.status;
  });
  expect(reviewerWriteStatus).toBe(403);
  await page.goto('/organizaciones/organizacion-a/curriculo/objetivos');
  await expect(
    page.getByRole('button', { name: 'Editar objetivo' }),
  ).toHaveCount(0);

  await logout(page);
  await login(page, password, 'learner@organizations.e2e.test');
  await expect(page.getByRole('heading', { name: 'Currículo' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Crear área' })).toHaveCount(0);
  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  await expect(page.getByText('Concepto del autor')).toBeVisible();
  await expect(
    page.getByRole('button', { name: 'Crear concepto' }),
  ).toHaveCount(0);

  await logout(page);
  await login(page, password, 'instructor@organizations.e2e.test');
  await expect(page.getByRole('heading', { name: 'Currículo' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Crear área' })).toHaveCount(0);
  await page.goto('/organizaciones/organizacion-a/curriculo/prerrequisitos');
  await expect(
    page.getByRole('button', { name: 'Guardar prerrequisitos' }),
  ).toHaveCount(0);
});

test('archived catalog content is hidden from learner in Chromium', async ({
  page,
}) => {
  await login(page, password);
  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  await page.getByLabel('Nombre').fill('Sólo para archivo');
  await page.getByLabel('Slug').fill('solo-para-archivo');
  await page
    .getByLabel('Definición')
    .fill('Este concepto no debe permanecer visible para estudiantes.');
  await page.getByRole('button', { name: 'Crear concepto' }).click();
  const archivedConcept = page
    .getByRole('listitem')
    .filter({ hasText: 'Sólo para archivo' });
  page.once('dialog', (dialog) => dialog.accept());
  await archivedConcept.getByRole('button', { name: 'Archivar' }).click();
  await expect(archivedConcept.getByText('Archivado')).toBeVisible();

  await logout(page);
  await login(page, password, 'learner@organizations.e2e.test');
  await page.goto('/organizaciones/organizacion-a/curriculo/conceptos');
  await expect(page.getByText('Sólo para archivo')).toHaveCount(0);
});

test('member cannot access another organization curriculum by URL', async ({
  page,
}) => {
  await login(page, password, 'learner@organizations.e2e.test');
  await page.goto('/organizaciones/organizacion-b/curriculo');
  await expect(page.getByText('404')).toBeVisible();
  await expect(page.getByText('Organización B')).toHaveCount(0);
  const scopedStatuses = await page.evaluate(async () => {
    const external = await fetch(
      '/api/v1/organizations/organizacion-b/catalog/areas/',
    );
    const unknown = await fetch(
      '/api/v1/organizations/organizacion-a/catalog/areas/00000000-0000-0000-0000-000000000000/',
    );
    return [external.status, unknown.status];
  });
  expect(scopedStatuses).toEqual([404, 404]);
});
