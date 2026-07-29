import { expect, test } from '@playwright/test';

test('shows the operational scaffolding page', async ({ page }) => {
  await page.goto('/');

  await expect(
    page.getByRole('heading', { name: 'Plataforma académica' }),
  ).toBeVisible();
});
