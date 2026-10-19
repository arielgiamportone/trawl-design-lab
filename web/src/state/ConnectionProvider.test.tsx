import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { MODE_KEY } from '../lib/mode';
import { App } from '../App';
import { Header } from '../components/Header';
import { mockApi } from '../test/mockApi';
import { ConnectionProvider } from './ConnectionProvider';

afterEach(() => vi.unstubAllGlobals());

// Estas pruebas recorren el modo experto (el guiado tiene las suyas en Wizard.test.tsx).
beforeEach(() => window.localStorage.setItem(MODE_KEY, JSON.stringify('expert')));
describe('ConnectionProvider + indicador', () => {
  it('sin respuesta: «despertando», luego «no disponible» y «Reintentar» recupera', async () => {
    let up = false;
    const fetchFn = vi.fn(async () => {
      if (!up) throw new TypeError('Failed to fetch');
      return new Response(JSON.stringify({ status: 'ok', version: '0.1.0' }), {
        headers: { 'Content-Type': 'application/json' },
      });
    });
    vi.stubGlobal('fetch', fetchFn);
    render(
      <ConnectionProvider options={{ budgetMs: 2_500, wakeAfterMs: 50 }}>
        <Header mode="expert" onModeChange={() => {}} />
      </ConnectionProvider>,
    );
    expect(await screen.findByText(/Despertando la API/)).toBeInTheDocument();
    expect(await screen.findByText('API no disponible', {}, { timeout: 4000 })).toBeInTheDocument();
    up = true;
    await userEvent.click(screen.getByRole('button', { name: 'Reintentar' }));
    expect(await screen.findByText('API conectada · v0.1.0')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Reintentar' })).not.toBeInTheDocument();
  });

  it('el primer cálculo espera a /health', async () => {
    const { fn, calls } = mockApi();
    const ok = fn.getMockImplementation()!;
    let healthCalls = 0;
    fn.mockImplementation(async (input, init) => {
      if (String(input).endsWith('/health') && ++healthCalls === 1) {
        calls.push({ url: String(input), method: 'GET', body: undefined });
        throw new TypeError('Failed to fetch');
      }
      return ok(input, init);
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    expect(await screen.findByText('API conectada · v0.1.0', {}, { timeout: 4000 })).toBeVisible();
    await screen.findByText('2,27', {}, { timeout: 3000 });
    const paths = calls.map((c) => new URL(c.url).pathname);
    const firstOther = paths.findIndex((p) => p !== '/health');
    // Dos /health (el fallido y el bueno) antes de cualquier catálogo o cálculo.
    expect(paths.slice(0, firstOther)).toEqual(['/health', '/health']);
    expect(paths).toContain('/design');
  });
});
