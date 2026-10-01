import { defineConfig, devices } from '@playwright/test';
import { randomUUID } from 'node:crypto';

const e2eRunId = randomUUID();
const e2eDatabaseUrl = `sqlite:///./artifacts/validation/e2e-${e2eRunId}.sqlite`;
const apiPort = 8_011;
const webPort = 3_011;

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 30_000,
  expect: { timeout: 7_000 },
  fullyParallel: false,
  retries: 0,
  reporter: [['list']],
  use: {
    baseURL: `http://127.0.0.1:${webPort}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 1000 } } },
  ],
  webServer: [
    {
      command: `python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port ${apiPort}`,
      url: `http://127.0.0.1:${apiPort}/health/ready`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        ...process.env,
        ENVIRONMENT: 'test',
        DATABASE_URL: e2eDatabaseUrl,
        STORAGE_PATH: `./artifacts/validation/e2e-uploads-${e2eRunId}`,
        CELERY_TASK_ALWAYS_EAGER: 'true',
      },
    },
    {
      command: 'npx tsx server.ts',
      url: `http://127.0.0.1:${webPort}/health/ready`,
      reuseExistingServer: false,
      timeout: 180_000,
      env: {
        ...process.env,
        PORT: String(webPort),
        CLICKO_API_ORIGIN: `http://127.0.0.1:${apiPort}`,
        CLICKO_E2E: 'true',
        DISABLE_HMR: 'true',
      },
    },
  ],
});
