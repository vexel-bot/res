import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/craft", timeout: 30000, expect: { timeout: 8000 }, fullyParallel: false, retries: 0,
  reporter: [["list"]], use: { baseURL: "http://127.0.0.1:3016", screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1440, height: 1000 } } }],
  webServer: { command: "node tests/fixtures/craft-server.mjs", url: "http://127.0.0.1:3016", reuseExistingServer: false, timeout: 60000 },
});
