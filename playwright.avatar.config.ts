import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests/avatar',
  workers: 1,
  timeout: 60_000,
  outputDir: '.clicko-data/avatar-test-results',
  reporter: 'list',
  use: { baseURL: 'http://127.0.0.1:3109', channel: 'chrome', headless: true, viewport: { width: 1366, height: 900 } },
  webServer: { command: 'node --import tsx scripts/profile-avatar-test-server.ts', url: 'http://127.0.0.1:3109', reuseExistingServer: false },
});
