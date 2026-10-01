import { defineConfig, devices } from "@playwright/test";

process.env.CONTEXTUAL_COMPONENT_TEST = "1";

// This test mocks the API boundary. Worker/API integration is covered by Python
// tests; launching another backend here only increases memory use on local hosts.
export default defineConfig({
  testDir: "./tests/e2e",
  testMatch: "contextual-editing.spec.ts",
  workers: 1,
  retries: 0,
  reporter: "list",
  expect: { timeout: 10_000 },
  use: {
    baseURL: "http://127.0.0.1:3012",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1100, height: 900 } } }],
  webServer: {
    command: "node tests/fixtures/contextual-editing-server.mjs",
    url: "http://127.0.0.1:3012/",
    timeout: 180_000,
    reuseExistingServer: false,
  },
});
