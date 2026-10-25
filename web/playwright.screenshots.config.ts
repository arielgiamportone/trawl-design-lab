import base from './playwright.config';
import { defineConfig } from '@playwright/test';

/**
 * Capturas de la documentación (`npm run screenshots`): mismo arranque que las E2E (API real y
 * `vite preview`), pero corre `screenshots/` y escribe en `docs/screenshots/`.
 */
export default defineConfig({
  ...base,
  testDir: './screenshots',
  retries: 0,
  timeout: 300_000,
  reporter: 'list',
});
