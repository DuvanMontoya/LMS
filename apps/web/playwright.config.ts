import { defineConfig, devices } from '@playwright/test';

const webPort = Number(process.env.E2E_WEB_PORT ?? '3000');
const apiPort = Number(process.env.E2E_API_PORT ?? '8000');
const webOrigin = `http://127.0.0.1:${webPort}`;

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 45_000,
  retries: 0,
  outputDir: '.local/e2e-results',
  use: {
    baseURL: webOrigin,
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      name: 'django-e2e',
      command: 'node scripts/e2e-django-server.mjs',
      url: `http://127.0.0.1:${apiPort}/health/live/`,
      reuseExistingServer: false,
      timeout: 30_000,
    },
    {
      name: 'next-e2e',
      command: 'node scripts/e2e-next-server.mjs',
      url: `${webOrigin}/`,
      reuseExistingServer: false,
      timeout: 45_000,
    },
  ],
});
