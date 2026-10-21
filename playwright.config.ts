/** Cross-engine website integration configuration by Jason Stys.
 * Functions: defineConfig, browser projects. Variables: command/PYTHON select an explicit interpreter.
 * All tests use the production Python handler and built assets. Index: docs/CODE_INDEX.md.
 */
import { defineConfig, devices } from "@playwright/test";
const python =
  process.env.PYTHON ?? (process.platform === "win32" ? ".venv/Scripts/python.exe" : "python");
const externalBaseURL = process.env.DTN_BASE_URL;
export default defineConfig({
  testDir: "tests",
  testMatch: "ui.spec.ts",
  workers: 1,
  retries: 0,
  timeout: 30000,
  reporter: "list",
  use: {
    baseURL: externalBaseURL ?? "http://127.0.0.1:8865",
    trace: "off",
    screenshot: "off",
    video: "off",
    reducedMotion: "reduce",
  },
  ...(externalBaseURL
    ? {}
    : {
        webServer: {
          command: `"${python}" -m dtnlab serve --port 8865 --no-browser`,
          url: "http://127.0.0.1:8865/api/health",
          reuseExistingServer: false,
          timeout: 20000,
        },
      }),
  projects: [
    { name: "chromium", use: { ...devices["Desktop Chrome"] } },
    { name: "firefox", use: { ...devices["Desktop Firefox"] } },
    { name: "webkit", use: { ...devices["Desktop Safari"] } },
  ],
});
