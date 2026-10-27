import './locale';
import '@testing-library/jest-dom/vitest';
import { cleanup, configure } from '@testing-library/react';
import { afterEach } from 'vitest';
import { setLang } from '../i18n';
import { setUnits } from '../lib/units';

// En los runners de CI (y con varias suites a la vez) 1 s de espera no alcanza para montar la app.
configure({ asyncUtilTimeout: 5000 });

afterEach(() => {
  cleanup();
  setLang('es');
  setUnits('metric');
  try {
    window.localStorage.clear();
  } catch {
    /* sin almacenamiento */
  }
});

// jsdom no implementa ResizeObserver (Recharts lo usa en ResponsiveContainer).
class RO {
  observe() {}
  unobserve() {}
  disconnect() {}
}
(globalThis as unknown as { ResizeObserver: unknown }).ResizeObserver ??= RO;
