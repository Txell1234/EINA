import { defineConfig, devices } from '@playwright/test'

const PORT = process.env.E2E_PORT ?? '5173'
const baseURL = `http://127.0.0.1:${PORT}`

export default defineConfig({
  testDir: './e2e/tests',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [['github'], ['list']] : [['list']],
  use: {
    baseURL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: `npm run dev -- --host 127.0.0.1 --port ${PORT} --mode e2e`,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 120_000,
  },
})
