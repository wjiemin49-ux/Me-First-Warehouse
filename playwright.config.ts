import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.E2E_BASE_URL ?? 'http://127.0.0.1:4173';
const webPort = Number(new URL(baseURL).port || '4173');

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  timeout: 60_000,
  expect: {
    timeout: 10_000
  },
  retries: process.env.CI ? 2 : 0,
  forbidOnly: Boolean(process.env.CI),
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL,
    headless: true,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure'
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ],
  webServer: [
    {
      command: "pnpm --filter @focusflow/server e2e:server",
      url: "http://127.0.0.1:3001/health",
      timeout: 120_000,
      reuseExistingServer: false
    },
    {
      command: `pnpm --filter @focusflow/web dev --host 127.0.0.1 --port ${webPort}`,
      url: baseURL,
      timeout: 120_000,
      reuseExistingServer: false
    }
  ]
});
