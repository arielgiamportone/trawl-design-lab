import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { forgetAll } from '../lib/memo';
import { MODE_KEY } from '../lib/mode';
import { mockApi } from '../test/mockApi';

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
  await userEvent.click(screen.getByRole('tab', { name: 'Componentes' }));
  return screen.findByTestId('components', {}, { timeout: 5000 });
}

describe('Componentes', () => {
  it(
    'filtra el catálogo y usa un cable en el caso',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      const table = await screen.findByRole('table', { name: 'Componentes: Cable de acero' });
      await waitFor(() => expect(within(table).getAllByRole('row').length).toBeGreaterThan(5));
      await userEvent.click(screen.getByLabelText('Sólo genéricos'));
      expect(within(table).queryByText('Bridon-Bekaert')).not.toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Usar en el caso' }));
      expect(
        (await screen.findAllByText('en el caso', {}, { timeout: 3000 })).length,
      ).toBeGreaterThan(0);
      expect(screen.getByRole('button', { name: 'Es el del caso' })).toBeDisabled();
      await waitFor(
        () =>
          expect(
            calls.some(
              (c) =>
                c.url.endsWith('/design') &&
                typeof (c.body as { params: { warp_id?: string } }).params.warp_id === 'string',
            ),
          ).toBe(true),
        { timeout: 3000 },
      );
    },
    SLOW,
  );

  it(
    'lista de materiales con total y líneas sin precio; armado aplicado al caso',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      await userEvent.click(screen.getByRole('button', { name: 'Lista de materiales' }));
      expect(await screen.findByTestId('bom-total-USD', {}, { timeout: 3000 })).toHaveTextContent(
        '900',
      );
      expect(screen.getAllByText('sin precio').length).toBeGreaterThan(0);
      await userEvent.click(screen.getByRole('button', { name: 'Armar con el catálogo' }));
      await userEvent.click(screen.getByLabelText('Sólo genéricos'));
      await userEvent.click(
        within(screen.getByTestId('assembly')).getByRole('button', {
          name: 'Armar con el catálogo',
        }),
      );
      const cards = await screen.findAllByTestId('assembly-card', {}, { timeout: 3000 });
      const req = calls.find((c) => c.url.endsWith('/optimize/components'))?.body;
      expect(req).toMatchObject({ objective: 'drag', params: { generic_only: true } });
      await userEvent.click(within(cards[0]!).getByRole('button', { name: 'Aplicar al caso' }));
      await waitFor(
        () =>
          expect(
            calls.some(
              (c) =>
                c.url.endsWith('/design') &&
                (c.body as { params: { float_id?: string } }).params.float_id !== undefined,
            ),
          ).toBe(true),
        { timeout: 3000 },
      );
    },
    SLOW,
  );

  it(
    'importa y exporta la lista de precios (CSV/XLSX) y la guarda en el navegador',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      await userEvent.click(screen.getByRole('button', { name: 'Lista de materiales' }));
      await screen.findByTestId('bom-total-USD', {}, { timeout: 3000 });
      const file = new File(['clave;precio;moneda;unidad\ndoors;450;USD;u.\n'], 'p.csv', {
        type: 'text/csv',
      });
      await userEvent.upload(screen.getByLabelText('Importar precios (CSV o XLSX)'), file);
      expect(await screen.findByTestId('prices-imported')).toHaveTextContent(
        '1 precio importado de 2 filas.',
      );
      expect(screen.getByTestId('prices-imported')).toHaveTextContent('Fila 2: unidad inválida');
      const req = calls.find((c) => c.url.endsWith('/prices/parse'))?.body as {
        file: { filename: string; content: string };
      };
      expect(req.file.filename).toBe('p.csv');
      const saved = JSON.parse(localStorage.getItem('trawl-design-lab:prices:v1') ?? '{}');
      expect(saved.doors.value).toBe(450);
      await userEvent.click(screen.getByRole('button', { name: 'Exportar precios (XLSX)' }));
      await waitFor(() =>
        expect(calls.some((c) => c.url.includes('/prices/export?format=xlsx'))).toBe(true),
      );
      const exp = calls.find((c) => c.url.includes('/prices/export'))?.body as {
        prices: Record<string, unknown>;
        lines: unknown[];
      };
      expect(exp.prices).toHaveProperty('doors');
      expect(exp.lines.length).toBeGreaterThan(0);
    },
    SLOW,
  );

  it(
    'valida y guarda un aporte, marcado sin verificar',
    async () => {
      mockApi();
      renderApp();
      await openTab();
      await userEvent.click(screen.getByRole('button', { name: 'Aportar' }));
      const form = screen.getByTestId('contribute');
      await userEvent.type(
        within(form).getByLabelText('Nombre (como lo conoce en el puerto)'),
        'Cable del puerto',
      );
      await userEvent.click(within(form).getByRole('button', { name: 'Validar' }));
      expect(await within(form).findByText(/diameter_mm/)).toBeInTheDocument();
      await userEvent.type(within(form).getByLabelText('Diámetro [mm]'), '12');
      await userEvent.click(within(form).getByRole('button', { name: 'Validar' }));
      await within(form).findByText(/coherentes/);
      await userEvent.click(
        within(form).getByRole('button', { name: 'Guardar en este navegador' }),
      );
      const item = await within(form).findByText('Cable del puerto');
      expect(item.closest('li')).toHaveTextContent('aporte, sin verificar');
      expect(within(form).getByRole('link', { name: 'Proponer al catálogo' })).toHaveAttribute(
        'href',
        expect.stringContaining('componente.yml'),
      );
    },
    SLOW,
  );
});
