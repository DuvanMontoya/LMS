import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
if (!password) throw new Error('E2E_ORGANIZATIONS_PASSWORD is required.');

const slug = 'organizacion-a';
const courseSlug = 'publicacion-inmutable-e2e';

async function login(page: Page, email: string, next: string) {
  await page.goto(`/auth/iniciar-sesion?next=${encodeURIComponent(next)}`);
  await page.getByLabel('Correo electrónico').fill(email);
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
  await expect(page).toHaveURL(next, { timeout: 20_000 });
}

async function expectAccessible(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(results.violations).toEqual([]);
}

async function addPersonFromDirectory(
  page: Page,
  searchboxName: string,
  email: string,
) {
  await page.getByRole('searchbox', { name: searchboxName }).fill(email);
  const results = page.getByRole('list', { name: 'Resultados de personas' });
  await expect(results).toBeVisible();
  const add = results.getByRole('button', { name: 'Añadir' });
  await expect(add).toHaveCount(1);
  await add.click();
}

test('learning delivery: cohort, enrollment, progress, lifecycle and responsive access work', async ({
  browser,
  page,
}) => {
  test.setTimeout(600_000);
  const cohortsPath = `/organizaciones/${slug}/aprendizaje/cohortes`;
  await login(page, 'administrator@organizations.e2e.test', cohortsPath);
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expectAccessible(page);

  await page.goto(`${cohortsPath}/nueva`);
  await page.getByLabel('Nombre').fill('Cohorte E2E de funciones');
  await page.getByLabel('Slug (opcional)').fill('cohorte-e2e-funciones');
  await page.getByLabel('Curso').selectOption(courseSlug);
  await page.getByLabel('Release asignado').selectOption('1');
  await page.getByRole('button', { name: 'Crear sección' }).click();
  await expect(page).toHaveURL(cohortsPath, { timeout: 20_000 });
  await page.getByRole('link', { name: 'Cohorte E2E de funciones' }).click();
  await expect(
    page.getByRole('heading', { name: 'Cohorte E2E de funciones' }),
  ).toBeVisible({ timeout: 20_000 });
  const cohortHref = new URL(page.url()).pathname;
  await addPersonFromDirectory(
    page,
    'Buscar estudiante para la sección',
    'learner@organizations.e2e.test',
  );
  await page.getByRole('button', { name: 'Matricular selección' }).click();
  await expect(
    page.getByText('learner@organizations.e2e.test').last(),
  ).toBeVisible({ timeout: 20_000 });

  const enrollmentLink = page.getByRole('link', { name: 'Ver matrícula' });
  const enrollmentHref = await enrollmentLink.getAttribute('href');
  expect(enrollmentHref).toBeTruthy();
  await expectAccessible(page);

  const studentContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
    viewport: { height: 844, width: 390 },
  });
  const student = await studentContext.newPage();
  const learningPath = `/organizaciones/${slug}/aprendizaje`;
  await login(student, 'learner@organizations.e2e.test', learningPath);
  await expect(
    student.getByRole('heading', { name: 'Mi aprendizaje' }),
  ).toBeVisible();
  await expect(student.getByText('Release 1')).toBeVisible();
  await expect(
    student.getByRole('link', { name: 'Biblioteca', exact: true }),
  ).toHaveCount(0);
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectAccessible(student);

  const courseHomePath = `/organizaciones/${slug}/aprender/${courseSlug}`;
  await student.goto(courseHomePath);
  await expect(
    student.getByRole('heading', {
      name: 'Funciones para lectura institucional',
      level: 1,
    }),
  ).toBeVisible();
  await expect(
    student.getByRole('navigation', { name: 'Secciones del curso' }),
  ).toBeVisible();
  await student.getByRole('link', { name: 'Contenido', exact: true }).click();
  await expect(student).toHaveURL(`${courseHomePath}?tab=contenido`, {
    timeout: 20_000,
  });
  await expect(
    student.getByRole('heading', { name: 'Contenido del curso' }),
  ).toBeVisible({ timeout: 20_000 });
  await student.getByRole('link', { name: 'Evaluaciones' }).click();
  await expect(
    student.getByRole('heading', { name: 'Evaluaciones del curso' }),
  ).toBeVisible({ timeout: 20_000 });
  await student.getByRole('link', { name: 'Calificaciones' }).click();
  await expect(
    student.getByRole('heading', { name: 'Calificaciones', exact: true }),
  ).toBeVisible({ timeout: 20_000 });
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await expectAccessible(student);

  await student.goto(learningPath);
  await student.getByRole('link', { name: 'Comenzar' }).click();
  await expect(student).toHaveURL(/\/(?:actividades|unidades)\/[0-9a-f-]+$/, {
    timeout: 60_000,
  });
  await expect(student.getByRole('heading', { level: 1 })).toBeVisible({
    timeout: 60_000,
  });
  await expect(student.getByText('Una función asigna')).toBeVisible();
  await expect(
    student.getByRole('button', { name: 'Marcar unidad como completada' }),
  ).toBeVisible();
  await expect(
    student.getByRole('navigation', { name: 'Navegación entre lecciones' }),
  ).toBeVisible();
  await expect(
    student.getByRole('link', { name: 'Mi aprendizaje' }),
  ).toHaveCount(0);
  expect(
    await student.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await student
    .getByRole('button', { name: 'Marcar unidad como completada' })
    .click();
  await expect(student.getByText('La unidad quedó completada.')).toBeVisible({
    timeout: 20_000,
  });
  await student.getByRole('link', { name: /Dominio y rango/ }).click();
  await expect(
    student.getByRole('heading', { name: 'Dominio y rango', level: 1 }),
  ).toBeVisible();
  await student
    .getByRole('button', { name: 'Marcar unidad como completada' })
    .click();
  await expect(
    student.getByRole('progressbar', {
      name: /2 de 2 actividades completadas, 100/,
    }),
  ).toBeVisible({ timeout: 20_000 });
  await expectAccessible(student);

  await page.goto(enrollmentHref!);
  await page.getByRole('button', { name: 'Suspender' }).click();
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Suspender' })
    .click();
  await expect(page.getByText('Suspendida', { exact: true })).toBeVisible({
    timeout: 20_000,
  });
  await student.goto(learningPath);
  await expect(student.getByText('Matrícula suspendida')).toBeVisible();
  await expect(student.getByRole('link', { name: 'Continuar' })).toHaveCount(0);

  await page.getByRole('button', { name: 'Reactivar' }).click();
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Reactivar' })
    .click();
  await expect(page.getByText('Activa', { exact: true })).toBeVisible({
    timeout: 20_000,
  });
  await student.goto(learningPath);
  await expect(student.getByText('Disponible', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Revocar' }).click();
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Revocar' })
    .click();
  await expect(page.getByText('Revocada', { exact: true })).toBeVisible({
    timeout: 20_000,
  });
  await student.goto(learningPath);
  await expect(
    student.getByRole('heading', { name: 'Aún no tienes matrículas' }),
  ).toBeVisible();
  await page.goto(cohortHref);
  await addPersonFromDirectory(
    page,
    'Buscar estudiante para la sección',
    'learner@organizations.e2e.test',
  );
  await page.getByRole('button', { name: 'Matricular selección' }).click();
  await expect(
    page.getByText('learner@organizations.e2e.test').last(),
  ).toBeVisible({ timeout: 20_000 });
  await student.goto(learningPath);
  await expect(student.getByText('Release 1')).toBeVisible();

  const publicationPath = `/organizaciones/${slug}/cursos/${courseSlug}/publicacion`;
  const authorContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const author = await authorContext.newPage();
  await login(
    author,
    'author@organizations.e2e.test',
    `/organizaciones/${slug}/cursos/${courseSlug}/publicaciones/1`,
  );
  await author
    .getByRole('button', { name: 'Crear revisión desde este release' })
    .click();
  await author.getByRole('button', { name: 'Crear revisión' }).click();
  await author.getByRole('button', { name: 'Enviar a revisión' }).click();
  await author.getByRole('button', { name: 'Enviar revisión' }).click();
  const revisionPath = new URL(author.url()).pathname;
  await authorContext.close();

  const reviewerAuthoringContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const reviewerAuthoring = await reviewerAuthoringContext.newPage();
  await login(
    reviewerAuthoring,
    'reviewer@organizations.e2e.test',
    revisionPath,
  );
  await reviewerAuthoring
    .getByRole('button', { name: 'Aprobar estructura' })
    .click();
  await expect(
    reviewerAuthoring.getByText('La estructura fue aprobada.'),
  ).toBeVisible({
    timeout: 20_000,
  });
  await reviewerAuthoringContext.close();
  await page.goto(publicationPath);
  await page
    .getByRole('button', { name: 'Publicar revisión aprobada' })
    .click();
  await page.getByRole('button', { name: 'Confirmar publicación' }).click();
  await expect(
    page.getByText('Release 2', { exact: true }).first(),
  ).toBeVisible({ timeout: 20_000 });
  await student.goto(learningPath);
  await expect(student.getByText('Release 1')).toBeVisible();
  await expect(student.getByText('Release 2')).toHaveCount(0);

  const competingContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const competing = await competingContext.newPage();
  await login(competing, 'learner@organizations.e2e.test', learningPath);
  await Promise.all([
    student.getByRole('link', { name: 'Comenzar' }).click(),
    competing.getByRole('link', { name: 'Comenzar' }).click(),
  ]);
  await Promise.all([
    expect(
      student.getByRole('heading', { name: 'Concepto de función', level: 1 }),
    ).toBeVisible({ timeout: 20_000 }),
    expect(
      competing.getByRole('heading', {
        name: 'Concepto de función',
        level: 1,
      }),
    ).toBeVisible({ timeout: 20_000 }),
  ]);
  const completionResponses = await Promise.all([
    Promise.all([
      student.waitForResponse(
        (response) =>
          response.url().includes('/complete/') &&
          response.request().method() === 'POST',
      ),
      student
        .getByRole('button', { name: 'Marcar unidad como completada' })
        .click(),
    ]).then(([response]) => response.status()),
    Promise.all([
      competing.waitForResponse(
        (response) =>
          response.url().includes('/complete/') &&
          response.request().method() === 'POST',
      ),
      competing
        .getByRole('button', { name: 'Marcar unidad como completada' })
        .click(),
    ]).then(([response]) => response.status()),
  ]);
  expect(completionResponses.sort()).toEqual([200, 409]);
  await competingContext.close();
  await student.goto(learningPath);

  await page.goto(`/organizaciones/${slug}/aprendizaje/matriculas`);
  await page.getByText('Crear matrícula individual', { exact: true }).click();
  await addPersonFromDirectory(
    page,
    'Buscar estudiante para matrícula individual',
    'instructor@organizations.e2e.test',
  );
  await page.getByLabel('Curso').selectOption(courseSlug);
  await page.getByLabel('Release asignado').selectOption('1');
  await page.getByRole('button', { name: 'Crear matrícula' }).click();
  const instructorRow = page
    .locator('article')
    .filter({ hasText: 'instructor@organizations.e2e.test' });
  await expect(instructorRow).toBeVisible({ timeout: 20_000 });
  await instructorRow.getByRole('link', { name: 'Detalle' }).click();
  await page.getByLabel('Actualizar release asignado').selectOption('2');
  await page.getByRole('button', { name: 'Actualizar' }).click();
  await page
    .getByRole('alertdialog')
    .getByRole('button', { name: 'Actualizar' })
    .click();
  await expect(page.getByRole('alertdialog')).toBeHidden({
    timeout: 20_000,
  });
  await expect(page.getByText(/· release 2$/i)).toBeVisible({
    timeout: 20_000,
  });

  const instructorContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const instructor = await instructorContext.newPage();
  await login(instructor, 'instructor@organizations.e2e.test', learningPath);
  await expect(instructor.getByText('Release 2')).toBeVisible();
  await instructorContext.close();

  await page.goto(`/organizaciones/${slug}/aprendizaje/cohortes/nueva`);
  await page.getByLabel('Nombre').fill('Cohorte futura E2E');
  await page.getByLabel('Slug (opcional)').fill('cohorte-futura-e2e');
  await page.getByLabel('Curso').selectOption(courseSlug);
  await page.getByLabel('Release asignado').selectOption('2');
  const tomorrow = new Date(Date.now() + 86_400_000).toISOString().slice(0, 16);
  await page.getByLabel('Inicio de acceso').fill(tomorrow);
  await page.getByRole('button', { name: 'Crear sección' }).click();
  await page.getByRole('link', { name: 'Cohorte futura E2E' }).click();
  await addPersonFromDirectory(
    page,
    'Buscar estudiante para la sección',
    'reviewer@organizations.e2e.test',
  );
  await page.getByRole('button', { name: 'Matricular selección' }).click();
  const reviewerContext = await browser.newContext({
    baseURL: `http://127.0.0.1:${process.env.E2E_WEB_PORT ?? '3000'}`,
  });
  const reviewer = await reviewerContext.newPage();
  await login(reviewer, 'reviewer@organizations.e2e.test', learningPath);
  await expect(reviewer.getByText('Acceso no iniciado')).toBeVisible();
  await expect(reviewer.getByRole('link', { name: 'Comenzar' })).toHaveCount(0);
  await reviewerContext.close();

  const foreign = await student.goto(
    '/organizaciones/organizacion-b/aprendizaje',
  );
  expect(foreign?.status()).toBe(404);
  await student.goto(learningPath);

  await page.goto(publicationPath);
  await page.getByRole('button', { name: 'Retirar de la biblioteca' }).click();
  await page
    .getByLabel('Justificación obligatoria')
    .fill('Retiro temporal validado por learning E2E.');
  await page.getByRole('button', { name: 'Confirmar retiro' }).click();
  await student.goto(learningPath);
  await expect(student.getByText('Publicación retirada')).toBeVisible();
  await expect(student.getByRole('link', { name: 'Continuar' })).toHaveCount(0);

  await student
    .getByRole('button', { name: 'Mostrar u ocultar navegación' })
    .click();
  const mobileNavigation = student.getByRole('dialog', {
    name: 'Navegación principal',
  });
  await expect(
    mobileNavigation.getByRole('link', { name: 'Mi aprendizaje' }),
  ).toBeVisible();
  await student.keyboard.press('Escape');
  await expect(mobileNavigation).toBeHidden();
  await studentContext.close();
});
