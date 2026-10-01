import { defineConfig } from "@playwright/test";

import baseConfig from "./playwright.config";

export default defineConfig({
  ...baseConfig,
  testDir: "./tests/accessibility",
  reporter: [["list"]],
  use: {
    ...baseConfig.use,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
