import { defineConfig, devices } from '@playwright/test';

// Exercises the running isolated DEV application, including its real session
// and bridge. Only the test cast catalog is intercepted; no media is generated.
export default defineConfig({
  testDir: './tests/team-sync', timeout: 60000, expect: { timeout: 15000 }, workers: 1,
  outputDir: '.codex-runtime/team-sync/playwright', reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:3000', ...devices['Desktop Chrome'], trace: 'retain-on-failure' },
});
