import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.E2E_PORT ?? 4173);
const API_PORT = Number(process.env.E2E_API_PORT ?? 8000);

/**
 * E2E contra `vite preview` (build de producción) y la API real.
 * Si la API o el preview ya están corriendo se reutilizan; si no, Playwright los inicia
 * (la API con `uv run trawlkit serve`, que requiere `uv sync` en la raíz del repo).
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 60_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    acceptDownloads: true,
    locale: 'es-AR',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: [
    {
      command: `uv run trawlkit serve --port ${API_PORT}`,
      cwd: '..',
      url: `http://127.0.0.1:${API_PORT}/health`,
      reuseExistingServer: true,
      timeout: 120_000,
    },
    {
      command: `npm run build && npx vite preview --port ${PORT} --strictPort --host 127.0.0.1`,
      url: `http://127.0.0.1:${PORT}`,
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      env: { VITE_API_URL: `http://127.0.0.1:${API_PORT}` },
    },
  ],
});
