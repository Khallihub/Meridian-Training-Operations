import { defineConfig, devices } from '@playwright/test'

/**
 * Playwright E2E test configuration for Meridian Training Operations System.
 *
 * Prerequisites:
 *   docker-compose up --build -d   # start full stack
 *   npx playwright install          # install browser binaries
 *
 * Run:
 *   npx playwright test
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  retries: 1,
  timeout: 30_000,
  use: {
    baseURL: 'http://localhost',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'echo "Using external docker-compose stack"',
    url: 'http://localhost/api/v1/monitoring/health',
    reuseExistingServer: true,
    timeout: 120_000,
  },
})
