import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  retries: 0,
  outputDir: '.local/e2e-results',
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      name: 'django-e2e',
      command: 'node scripts/e2e-django-server.mjs',
      url: 'http://127.0.0.1:8000/health/live/',
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      name: 'next-e2e',
      command: 'node scripts/e2e-next-server.mjs',
      url: 'http://127.0.0.1:3000/',
      reuseExistingServer: false,
      timeout: 45_000,
    },
  ],
});
