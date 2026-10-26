import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { ECO_KEY, EMPTY_FORM, filled, toInputs } from '../../lib/economics';
import { forgetAll } from '../../lib/memo';
import { MODE_KEY } from '../../lib/mode';
import { mockApi } from '../../test/mockApi';

const SLOW = 20_000;

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  forgetAll();
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
});
afterEach(() => vi.unstubAllGlobals());

async function openTab() {
  await screen.findByText('2,27', {}, { timeout: 3000 });
  await userEvent.click(screen.getByRole('tab', { name: 'Economía' }));
  return screen.findByTestId('economics', {}, { timeout: 5000 });
}

describe('lib/economics', () => {
  it('convierte el formulario: % a fracción, vacíos fuera', () => {
    const form = {
      ...EMPTY_FORM,
      currency: 'ars',
      values: { crew_share: '40', fuel_price_l: '1.200,5', hauls_per_trip: '3,6', price_kg: '' },
    };
    const inp = toInputs(form) as Record<string, unknown>;
    expect(inp.currency).toBe('ARS');
    expect(inp.crew_share).toBeCloseTo(0.4);
    expect(inp.fuel_price_l).toBeCloseTo(1200.5);
    expect(inp.hauls_per_trip).toBe(4);
    expect('price_kg' in inp).toBe(false);
    expect(filled(form)).toBe(3);
  });
});

describe('Economía', () => {
  it(
    'muestra la mejor velocidad, la curva y lo que falta; guarda los datos',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      const summary = await screen.findByTestId('eco-summary', {}, { timeout: 5000 });
      expect(summary).toHaveTextContent('Velocidad de mayor margen');
      expect(summary).toHaveTextContent('Faltan datos');
      const table = screen.getByTestId('eco-table');
      expect(within(table).getAllByRole('row').length).toBeGreaterThan(5);
      await userEvent.type(screen.getByLabelText('Precio del gasoil'), '1200');
      await waitFor(() =>
        expect(
          calls.some(
            (c) =>
              c.url.endsWith('/economics') &&
              (c.body as { economics: { fuel_price_l?: number } }).economics.fuel_price_l === 1200,
          ),
        ).toBe(true),
      );
      const saved = JSON.parse(localStorage.getItem(ECO_KEY)!);
      expect(saved.values.fuel_price_l).toBe('1200');
    },
    SLOW,
  );

  it(
    'compara con otra red del catálogo: ahorro y repago',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      await userEvent.click(await screen.findByRole('button', { name: 'Comparar redes' }));
      const box = screen.getByTestId('eco-compare');
      const select = within(box).getByLabelText('Red a comparar');
      const option = within(select).getAllByRole('option')[1] as HTMLOptionElement;
      await userEvent.selectOptions(select, option.value);
      await userEvent.type(within(box).getByLabelText('Costo de la red nueva'), '2000000');
      await userEvent.click(within(box).getByRole('button', { name: 'Calcular' }));
      const table = await within(box).findByRole('table', { name: 'Comparación económica' });
      expect(within(table).getAllByRole('row')).toHaveLength(3);
      const req = calls.find((c) => c.url.endsWith('/economics/compare'))!;
      const body = req.body as { cases: { gear_cost?: number }[] };
      expect(body.cases[1]!.gear_cost).toBe(2000000);
    },
    SLOW,
  );
});
