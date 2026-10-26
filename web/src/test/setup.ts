import './locale';
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';
import { setLang } from '../i18n';
import { setUnits } from '../lib/units';

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
