import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { setLang } from '../../i18n';
import { forgetAll } from '../../lib/memo';
import { MODE_KEY } from '../../lib/mode';
import { TAB_KEY } from '../../lib/tabs';
import { setUnits } from '../../lib/units';
import { mockApi } from '../../test/mockApi';

// Recorridos de interfaz con varios pedidos: margen para máquinas lentas.
const SLOW = 20_000;

/** Palabras de la interfaz en español que no deben quedar en inglés (no aparecen en los datos). */
const SPANISH =
  /\b(Simulación|Simular|Calcular|Velocidad|Resolución|Abrir|Cerrar|Captura|Portones|Tensión|Descargar|Elija|Pulse|Mejor|Optimizar|según|del|las|los)\b/;

/** Ruta del pedido sin la API ni la consulta (``?lang=en``). */
const path = (url: string) => new URL(url, 'http://x').pathname.replace(/^\/api/, '');

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

/** Texto visible de un bloque sin las opciones de las listas (nombres de datos del catálogo). */
function uiText(el: Element): string {
  const clone = el.cloneNode(true) as Element;
  clone.querySelectorAll('option').forEach((o) => o.remove());
  return clone.textContent ?? '';
}

beforeEach(() => {
  forgetAll();
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
  window.localStorage.setItem(TAB_KEY, JSON.stringify('simulacion'));
});
afterEach(() => vi.unstubAllGlobals());

describe('simulation in English', () => {
  it(
    'speed sweep: English labels, table and notes',
    async () => {
      const { calls } = mockApi();
      setLang('en');
      renderApp();
      const title = await screen.findByText('Shape simulation', {}, { timeout: 4000 });
      const root = title.closest('.panel-toolbar')?.parentElement as HTMLElement;
      const run = await screen.findByRole('button', { name: 'Simulate' });
      await waitFor(() => expect(run).toBeEnabled(), { timeout: 3000 });
      expect(screen.getByRole('button', { name: '3.0' })).toHaveAttribute('aria-pressed', 'true');
      await userEvent.click(screen.getByLabelText('Normal (6)'));
      await userEvent.click(run);
      const table = await screen.findByTestId('sim-table', {}, { timeout: 3000 });
      expect(within(table).getByText('Quantity')).toBeInTheDocument();
      expect(within(table).getByText('Δ sim/engine')).toBeInTheDocument();
      expect(screen.getByText('About the drag.')).toBeInTheDocument();
      expect(screen.getByText('Speed sweep')).toBeInTheDocument();
      expect(uiText(root)).not.toMatch(SPANISH);
      const req = calls.find((c) => path(c.url) === '/simulate')?.body;
      expect(req).toMatchObject({ speeds_kn: [3], resolution: 6 });
    },
    SLOW,
  );

  it(
    'explorer, selectivity and uncertainty views in English',
    async () => {
      mockApi();
      setLang('en');
      renderApp();
      await userEvent.click(
        await screen.findByRole('button', { name: 'Animated explorer' }, { timeout: 4000 }),
      );
      const runExplore = screen.getByRole('button', { name: 'Compute states' });
      await waitFor(() => expect(runExplore).toBeEnabled(), { timeout: 3000 });
      await userEvent.click(runExplore);
      const dash = await screen.findByTestId('explore-dashboard', {}, { timeout: 3000 });
      expect(within(dash).getByText('Otter board spread')).toBeInTheDocument();
      expect(within(dash).getAllByText('same as the first state').length).toBeGreaterThan(0);
      expect(screen.getByRole('slider', { name: /Catch in the codend/ })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Previous state' })).toBeInTheDocument();
      const root = screen.getByText('Shape simulation').closest('.panel-toolbar')
        ?.parentElement as HTMLElement;
      expect(uiText(root)).not.toMatch(SPANISH);

      await userEvent.click(screen.getByRole('button', { name: 'Meshes and selectivity' }));
      expect(
        await screen.findByRole('button', { name: 'Compute selectivity' }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole('spinbutton', { name: /Codend mesh size \[mm\]/ }),
      ).toBeInTheDocument();
      expect(screen.getByText('Codends to compare')).toBeInTheDocument();
      expect(uiText(root)).not.toMatch(SPANISH);

      await userEvent.click(screen.getByRole('button', { name: 'Uncertainty and calibration' }));
      expect(await screen.findByRole('button', { name: 'Compute bands' })).toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Calibration with measurements' }));
      expect(screen.getByRole('button', { name: 'Use the example log' })).toBeInTheDocument();
      expect(screen.getByText('Parameters to fit (up to 3)')).toBeInTheDocument();
      expect(screen.getByText('Otter board lift')).toBeInTheDocument();
      expect(uiText(root)).not.toMatch(SPANISH);
    },
    SLOW,
  );
});

describe('optimization in English', () => {
  it(
    'optimizes and shows the best design with English labels',
    async () => {
      const { calls } = mockApi();
      window.localStorage.setItem(TAB_KEY, JSON.stringify('optimizar'));
      setLang('en');
      renderApp();
      const title = await screen.findByText('Optimize scale and speed', {}, { timeout: 4000 });
      const root = title.parentElement as HTMLElement;
      const btn = await screen.findByRole('button', { name: 'Optimize' });
      await waitFor(() => expect(btn).toBeEnabled(), { timeout: 3000 });
      expect(screen.getByLabelText('Minimum scale')).toHaveValue('0.6');
      await userEvent.clear(screen.getByLabelText('Pull reserve [%]'));
      await userEvent.type(screen.getByLabelText('Pull reserve [%]'), '20');
      await userEvent.click(btn);
      const best = await screen.findByTestId('opt-best', {}, { timeout: 3000 });
      expect(within(best).getByText('Feasible')).toBeInTheDocument();
      expect(within(best).getByText('Net scale s')).toBeInTheDocument();
      expect(within(best).getByRole('button', { name: 'Use this design' })).toBeInTheDocument();
      const constraints = screen.getByTestId('opt-constraints');
      expect(within(constraints).getByText('Pull: F_T ≥ (1 + m)·R_T')).toBeInTheDocument();
      expect(within(constraints).getByText('1,185 kgf')).toBeInTheDocument();
      expect(screen.getByText('Pareto front')).toBeInTheDocument();
      expect(uiText(root)).not.toMatch(SPANISH);
      const req = calls.find((c) => path(c.url) === '/optimize')?.body;
      expect(req).toMatchObject({ margin: 0.2, s_bounds: [0.6, 1.4] });
    },
    SLOW,
  );

  it('validation errors in English', async () => {
    mockApi();
    window.localStorage.setItem(TAB_KEY, JSON.stringify('optimizar'));
    setLang('en');
    renderApp();
    const input = await screen.findByLabelText('Minimum scale', {}, { timeout: 4000 });
    await userEvent.clear(input);
    await userEvent.type(input, '3');
    expect(screen.getByText('Between 0.3 and 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Optimize' })).toBeDisabled();
  });
});

describe('imperial units', () => {
  it(
    'progressive haul: catch entered in lb reaches the API in kg; results in ft and lbf',
    async () => {
      const { calls } = mockApi();
      setLang('en');
      setUnits('imperial');
      renderApp();
      await userEvent.click(
        await screen.findByRole(
          'button',
          { name: 'Progressive haul (catch and seabed)' },
          { timeout: 4000 },
        ),
      );
      const max = await screen.findByRole('spinbutton', { name: /Final catch \[lb\]/ });
      expect(Number((max as HTMLInputElement).value)).not.toBe(0);
      await userEvent.clear(max);
      await userEvent.type(max, '2000');
      expect(screen.getByText(/Steps: 0 · 661 · 1,323 · 2,006 lb/)).toBeInTheDocument();
      const run = screen.getByRole('button', { name: 'Simulate haul' });
      await waitFor(() => expect(run).toBeEnabled(), { timeout: 3000 });
      await userEvent.click(run);

      const summary = await screen.findByTestId('haul-summary', {}, { timeout: 3000 });
      expect(summary).toHaveTextContent(/the otter board spread falls [\d.]+ ft/);
      expect(summary).toHaveTextContent(/the pull at the vessel rises [\d,]+ lbf/);
      expect(summary).toHaveTextContent(/^From 0 to [\d,]+ lb of catch/);
      expect(document.querySelector('[data-chart="haul-dp"] figcaption')).toHaveTextContent(
        'Otter board spread [ft]',
      );
      expect(document.querySelector('[data-chart="haul-pull"] figcaption')).toHaveTextContent(
        'Pull at the vessel [lbf]',
      );
      const body = calls.find((c) => path(c.url) === '/simulate/haul')?.body as {
        catches_kg: number[];
      };
      // 2000 lb = 907,2 kg; los pasos se redondean a 10 kg
      expect(body.catches_kg).toEqual([0, 300, 600, 910]);
    },
    SLOW,
  );
});
