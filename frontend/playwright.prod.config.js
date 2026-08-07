import { defineConfig, devices } from '@playwright/test';

/** E2E smoke tests contre la stack prod (Nginx :8080). */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  retries: 1,
  reporter: 'list',
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8080',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'prod-chrome',
      testMatch: /prod\.smoke\.spec\.js/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
