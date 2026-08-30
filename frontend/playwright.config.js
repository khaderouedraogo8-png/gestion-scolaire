import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  globalSetup: './e2e/global-setup.js',
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: 1,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
  },
  ...(process.env.CI
    ? {}
    : {
        webServer: {
          command: 'npm run dev',
          url: 'http://localhost:5173',
          reuseExistingServer: true,
        },
      }),
  projects: [
    { name: 'setup', testMatch: /.*\.setup\.js/ },
    {
      name: 'modules',
      testMatch: /modules\.spec\.js/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'login',
      testMatch: /login\.spec\.js/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['modules'],
    },
    {
      name: 'pedagogie',
      testMatch: /pedagogie\.spec\.js/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'navigation',
      testMatch: /navigation\.spec\.js/,
      use: { ...devices['Desktop Chrome'] },
      dependencies: ['setup'],
    },
    {
      name: 'parent-pedagogie',
      testMatch: /parent-pedagogie\.spec\.js/,
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
