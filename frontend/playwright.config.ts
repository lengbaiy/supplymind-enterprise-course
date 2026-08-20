import { defineConfig, devices } from "@playwright/test";

const systemChrome = process.platform === "win32" ? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" : undefined;

export default defineConfig({
  testDir: "./e2e",
  retries: process.env.CI ? 1 : 0,
  use: { baseURL: "http://127.0.0.1:4173", trace: "on-first-retry" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], ...(systemChrome ? { launchOptions: { executablePath: systemChrome } } : {}) } }],
  webServer: { command: "npx vite --host 127.0.0.1 --port 4173", url: "http://127.0.0.1:4173", reuseExistingServer: !process.env.CI },
});
