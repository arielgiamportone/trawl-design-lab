import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../i18n';
import {
  backoffDelay,
  docsUrl,
  statusAfterFailure,
  statusLabel,
  waitForApi,
  type ConnStatus,
} from './connection';

describe('backoff y transiciones', () => {
  it('espera creciente con tope de 8 s', () => {
    expect([0, 1, 2, 3, 4, 10].map(backoffDelay)).toEqual([1000, 2000, 4000, 8000, 8000, 8000]);
  });

  it('pasa a «no disponible» sólo cuando no queda presupuesto', () => {
    expect(statusAfterFailure(1_000, 1_000, 90_000)).toBe('waking');
    expect(statusAfterFailure(85_000, 4_000, 90_000)).toBe('waking');
    expect(statusAfterFailure(86_000, 4_000, 90_000)).toBe('down');
  });

  it('textos del indicador', () => {
    expect(statusLabel('connecting')).toBe('Conectando…');
    expect(statusLabel('waking')).toBe('Despertando la API (puede tardar hasta un minuto)…');
    expect(statusLabel('ok', '0.1.0')).toBe('API conectada · v0.1.0');
    expect(statusLabel('ok')).toBe('API conectada');
    expect(statusLabel('down')).toBe('API no disponible');
    setLang('en');
    expect(statusLabel('ok', '0.1.0')).toBe('API connected · v0.1.0');
    expect(statusLabel('ok', undefined, false, true)).toBe('Offline · on-device engine');
    setLang('es');
  });

  it('enlace a la documentación', () => {
    expect(docsUrl({ VITE_DOCS_URL: 'https://x/book/', BASE_URL: '/' })).toBe('https://x/book/');
    expect(docsUrl({ BASE_URL: '/trawl-design-lab/app/' })).toBe('../');
    expect(docsUrl({ VITE_DOCS_URL: '  ', BASE_URL: '/' })).toBeNull();
    expect(docsUrl({ BASE_URL: '/' })).toBeNull();
  });
});

describe('waitForApi', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  const fail = () => Promise.reject(new TypeError('Failed to fetch'));

  it('API despierta: conecta al primer intento', async () => {
    const seen: ConnStatus[] = [];
    const out = await waitForApi(
      () => Promise.resolve('h'),
      (s) => seen.push(s),
    );
    expect(out).toBe('h');
    expect(seen).toEqual(['connecting', 'ok']);
  });

  it('arranque en frío: reintenta, avisa «despertando» y se recupera', async () => {
    const seen: ConnStatus[] = [];
    let n = 0;
    const check = vi.fn(() => (++n < 4 ? fail() : Promise.resolve({ version: '0.1.0' })));
    const p = waitForApi(check, (s) => seen.push(s));
    await vi.runAllTimersAsync();
    await expect(p).resolves.toEqual({ version: '0.1.0' });
    expect(check).toHaveBeenCalledTimes(4);
    expect(seen).toEqual(['connecting', 'waking', 'ok']);
  });

  it('un primer pedido lento pasa a «despertando» sin esperar a que falle', async () => {
    const seen: ConnStatus[] = [];
    const check = (signal: AbortSignal) =>
      new Promise<string>((resolve, reject) => {
        const t = setTimeout(() => resolve('h'), 40_000);
        signal.addEventListener('abort', () => {
          clearTimeout(t);
          reject(new Error('abort'));
        });
      });
    const p = waitForApi(check, (s) => seen.push(s), { attemptTimeoutMs: 60_000 });
    await vi.advanceTimersByTimeAsync(3_100);
    expect(seen).toEqual(['connecting', 'waking']);
    await vi.advanceTimersByTimeAsync(40_000);
    await expect(p).resolves.toBe('h');
    expect(seen).toEqual(['connecting', 'waking', 'ok']);
  });

  it('se agota el presupuesto: «no disponible» y devuelve null', async () => {
    const seen: ConnStatus[] = [];
    const check = vi.fn(fail);
    const p = waitForApi(check, (s) => seen.push(s), { budgetMs: 20_000 });
    await vi.runAllTimersAsync();
    await expect(p).resolves.toBeNull();
    expect(seen).toEqual(['connecting', 'waking', 'down']);
    // 1 + 2 + 4 + 8 s de espera entre 5 intentos; el siguiente ya no cabe en 20 s.
    expect(check).toHaveBeenCalledTimes(5);
  });

  it('cada intento tiene tiempo máximo', async () => {
    const seen: ConnStatus[] = [];
    let n = 0;
    const check = (signal: AbortSignal) =>
      ++n === 1
        ? new Promise<string>((_, reject) =>
            signal.addEventListener('abort', () => reject(new Error('timeout'))),
          )
        : Promise.resolve('h');
    const p = waitForApi(check, (s) => seen.push(s), { attemptTimeoutMs: 5_000 });
    await vi.runAllTimersAsync();
    await expect(p).resolves.toBe('h');
    expect(n).toBe(2);
  });

  it('cancelar rechaza y no sigue reintentando', async () => {
    const ctrl = new AbortController();
    const check = vi.fn(fail);
    const p = waitForApi(check, () => {}, { signal: ctrl.signal });
    const settled = expect(p).rejects.toThrow('cancelado');
    await vi.advanceTimersByTimeAsync(500);
    ctrl.abort(new Error('cancelado'));
    await settled;
    await vi.runAllTimersAsync();
    expect(check).toHaveBeenCalledTimes(1);
  });
});

describe('API desactualizada', () => {
  it('compara la huella de rutas de /health con la de la app', async () => {
    const { APP_CONTRACT, isOutdated, statusLabel } = await import('./connection');
    expect(APP_CONTRACT).toMatch(/^[0-9a-f]{12}$/);
    expect(isOutdated(APP_CONTRACT)).toBe(false);
    expect(isOutdated('000000000000')).toBe(true);
    expect(isOutdated(undefined)).toBe(true); // API vieja, sin huella
    expect(isOutdated('x', '')).toBe(false); // app sin huella (no se puede comparar)
    expect(statusLabel('ok', '1.0.0', true)).toBe('API desactualizada · v1.0.0');
    expect(statusLabel('ok', '1.0.0')).toBe('API conectada · v1.0.0');
  });
});

describe('statusLabel con el motor del teléfono', () => {
  it('lo dice en lugar de «API conectada»', async () => {
    const { statusLabel } = await import('./connection');
    expect(statusLabel('ok', '1.0.0', false, true)).toBe('Sin conexión · motor del teléfono');
  });
});
