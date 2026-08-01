import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Page } from '@playwright/test';
import { readdir, readFile } from 'node:fs/promises';

const password = process.env.E2E_ORGANIZATIONS_PASSWORD;
const mailPath = process.env.E2E_MAIL_PATH;
if (!password || !mailPath)
  throw new Error('E2E credentials and isolated mail path are required.');

const slug = 'organizacion-a';

async function login(page: Page, email: string, next: string) {
  const configuration = await page.request.get('/_allauth/browser/v1/config');
  expect(configuration.ok()).toBe(true);
  const csrf = (await page.context().cookies()).find(
    (cookie) => cookie.name === 'csrftoken',
  )?.value;
  expect(csrf).toBeTruthy();
  const authenticated = await page.request.post(
    '/_allauth/browser/v1/auth/login',
    {
      data: { email, password },
      headers: { 'X-CSRFToken': csrf! },
    },
  );
  expect(authenticated.ok()).toBe(true);
  await page.goto(next, { timeout: 75_000, waitUntil: 'domcontentloaded' });
  await expect(page).toHaveURL(next);
}

async function expectAccessible(page: Page) {
  const result = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze();
  expect(result.violations).toEqual([]);
}

test('platform operations: authorized learner and author search, typo, notification, email and privacy', async ({
  browser,
}) => {
  test.setTimeout(240_000);
  const learnerContext = await browser.newContext();
  const learner = await learnerContext.newPage();
  const searchPath = `/organizaciones/${slug}/buscar?q=funci%C3%B3n`;
  await login(learner, 'learner@organizations.e2e.test', searchPath);
  await expect(
    learner.getByRole('heading', { name: 'Resultados' }),
  ).toBeVisible();
  await expect(
    learner.getByText(/Concepto de función|Funciones para/).first(),
  ).toBeVisible();
  await expect(learner.locator('mark').first()).toBeVisible();
  await expectAccessible(learner);

  await learner.goto(`/organizaciones/${slug}/buscar?q=funcions`);
  await expect(
    learner.getByRole('heading', { name: 'Resultados' }),
  ).toBeVisible();
  const crossOrganization = await learner.request.get(
    '/api/v1/organizations/organizacion-b/search/?q=funcion',
  );
  expect(crossOrganization.ok()).toBe(true);
  expect((await crossOrganization.json()).results).toEqual([]);

  await learner.goto(`/organizaciones/${slug}/notificaciones`);
  await expect(
    learner.getByRole('heading', { name: 'Notificaciones', exact: true }),
  ).toBeVisible();
  await expect(learner.getByText('Matrícula creada').first()).toBeVisible();
  await expect(
    learner.getByLabel('Notificaciones', { exact: true }),
  ).toBeVisible();
  await learner
    .getByRole('button', { name: 'Marcar todas como leídas' })
    .click();
  const notificationsBeforeReplay = await learner.request.get(
    '/api/v1/notifications/',
  );
  expect(notificationsBeforeReplay.ok()).toBe(true);
  const notificationTotalBeforeReplay = (
    (await notificationsBeforeReplay.json()) as {
      pagination: { total: number };
    }
  ).pagination.total;
  await learner.getByRole('link', { name: 'Preferencias' }).click();
  await expect(learner.getByLabel('Aprendizaje por correo')).toBeVisible({
    timeout: 30_000,
  });
  await expectAccessible(learner);
  await learnerContext.close();

  const authorContext = await browser.newContext();
  const author = await authorContext.newPage();
  await login(
    author,
    'author@organizations.e2e.test',
    `/organizaciones/${slug}/buscar?q=Diagn%C3%B3stico`,
  );
  const response = await author.request.get(
    `/api/v1/organizations/${slug}/search/?q=Diagn%C3%B3stico`,
  );
  expect(response.ok()).toBe(true);
  const serialized = JSON.stringify(await response.json());
  expect(serialized).toContain('Diagnóstico integral E2E');
  expect(serialized).not.toMatch(/grading|expected_mathjson|answer.key/i);
  await authorContext.close();

  const mailCountBeforeReplay = (await readdir(mailPath!)).length;
  const ownerContext = await browser.newContext();
  const owner = await ownerContext.newPage();
  await login(
    owner,
    'owner@organizations.e2e.test',
    `/organizaciones/${slug}/buscar`,
  );
  const eventsResponse = await owner.request.get('/api/v1/platform/events/');
  expect(eventsResponse.ok()).toBe(true);
  const enrollmentEvent = (
    (await eventsResponse.json()) as Array<{ id: string; event_type: string }>
  ).find((event) => event.event_type === 'learning.enrollment.created.v1');
  expect(enrollmentEvent).toBeDefined();
  const deliveriesBeforeReplay = await owner.request.get(
    `/api/v1/platform/events/${enrollmentEvent!.id}/deliveries/`,
  );
  expect(deliveriesBeforeReplay.ok()).toBe(true);
  expect(
    (
      (await deliveriesBeforeReplay.json()) as Array<{
        consumer_name: string;
        status: string;
      }>
    ).find(
      (delivery) =>
        delivery.consumer_name === 'notifications.domain_event_router.v1',
    )?.status,
  ).toBe('dead');
  const replayResponse = await owner.request.post(
    '/api/v1/platform/events/replays/',
    {
      headers: {
        'X-CSRFToken': (await owner.context().cookies()).find(
          (cookie) => cookie.name === 'csrftoken',
        )!.value,
      },
      data: {
        consumer_name: 'notifications.domain_event_router.v1',
        organization_slug: slug,
        event_type: 'learning.enrollment.created.v1',
        from_event_id: enrollmentEvent!.id,
        to_event_id: enrollmentEvent!.id,
        reason: 'Verificación E2E controlada de replay idempotente.',
      },
    },
  );
  expect(replayResponse.status()).toBe(202);
  const replay = (await replayResponse.json()) as { id: string };
  await expect
    .poll(
      async () => {
        const response = await owner.request.get(
          `/api/v1/platform/events/replays/${replay.id}/`,
        );
        return ((await response.json()) as { status: string }).status;
      },
      { timeout: 30_000 },
    )
    .toBe('completed');
  await expect
    .poll(
      async () => {
        const response = await owner.request.get(
          `/api/v1/platform/events/${enrollmentEvent!.id}/deliveries/`,
        );
        const deliveries = (await response.json()) as Array<{
          consumer_name: string;
          status: string;
        }>;
        return deliveries.find(
          (delivery) =>
            delivery.consumer_name === 'notifications.domain_event_router.v1',
        )?.status;
      },
      { timeout: 30_000 },
    )
    .toBe('completed');
  await ownerContext.close();

  const replayLearnerContext = await browser.newContext();
  const replayLearner = await replayLearnerContext.newPage();
  await login(
    replayLearner,
    'learner@organizations.e2e.test',
    `/organizaciones/${slug}/notificaciones`,
  );
  const notificationsAfterReplay = await replayLearner.request.get(
    '/api/v1/notifications/',
  );
  expect(notificationsAfterReplay.ok()).toBe(true);
  expect(
    (
      (await notificationsAfterReplay.json()) as {
        pagination: { total: number };
      }
    ).pagination.total,
  ).toBe(notificationTotalBeforeReplay);
  await replayLearnerContext.close();

  const mailFiles = await readdir(mailPath!);
  expect(mailFiles).toHaveLength(mailCountBeforeReplay);
  const messages = await Promise.all(
    mailFiles.map((name) => readFile(`${mailPath}/${name}`, 'utf8')),
  );
  expect(messages.some((message) => message.includes('Matr'))).toBe(true);
  expect(messages.join('\n')).not.toMatch(
    /grading|expected_mathjson|answer.key/i,
  );
});

test('platform operations visual: search and notification surfaces pass desktop, 390 px, keyboard and axe', async ({
  page,
}) => {
  test.setTimeout(90_000);
  await page.setViewportSize({ width: 1440, height: 900 });
  const path = `/organizaciones/${slug}/buscar?q=funci%C3%B3n`;
  await login(page, 'learner@organizations.e2e.test', path);
  await expect(page.locator('mark').first()).toBeVisible();
  await page.getByRole('link', { name: 'Limpiar' }).focus();
  await expect(page.getByRole('link', { name: 'Limpiar' })).toBeFocused();
  await expectAccessible(page);

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  const searchMetrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(searchMetrics.scrollWidth).toBeLessThanOrEqual(
    searchMetrics.clientWidth,
  );
  await expectAccessible(page);

  await page.goto(`/organizaciones/${slug}/notificaciones`);
  const notificationMetrics = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }));
  expect(notificationMetrics.scrollWidth).toBeLessThanOrEqual(
    notificationMetrics.clientWidth,
  );
  await expectAccessible(page);
});
