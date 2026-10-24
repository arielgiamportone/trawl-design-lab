import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { forgetAll } from '../../lib/memo';
import { MODE_KEY } from '../../lib/mode';
import { TAB_KEY } from '../../lib/tabs';
import { mockApi } from '../../test/mockApi';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  forgetAll();
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
  window.localStorage.setItem(TAB_KEY, JSON.stringify('simulacion'));
});
afterEach(() => vi.unstubAllGlobals());

describe('mallas y selectividad', () => {
  it('calcula la selectividad de dos copos y abre el zoom por malla', async () => {
    const { calls } = mockApi();
    renderApp();
    await userEvent.click(
      await screen.findByRole('button', { name: 'Mallas y selectividad' }, { timeout: 4000 }),
    );
    const cod = await screen.findByRole('checkbox', { name: 'Bacalao' }, { timeout: 3000 });
    await userEvent.click(cod);
    await userEvent.type(screen.getByRole('spinbutton', { name: /Mallero del copo/ }), '120');
    const run = screen.getByRole('button', { name: 'Calcular selectividad' });
    await waitFor(() => expect(run).toBeEnabled(), { timeout: 3000 });
    await userEvent.click(run);

    const table = await screen.findByTestId('selectivity-table', {}, { timeout: 3000 });
    expect(within(table).getByText('Rombo 40 mm')).toBeInTheDocument();
    expect(within(table).getByText('T90 40 mm')).toBeInTheDocument();
    expect(table.querySelectorAll('td[data-species="cod"]').length).toBe(2);
    expect(document.querySelector('[data-chart="retention"]')).toBeInTheDocument();
    const zoom = await screen.findByTestId('mesh-zoom');
    expect(within(zoom).getByText(/Ángulo entre hilos/)).toBeInTheDocument();
    expect(within(zoom).getByRole('status')).toHaveTextContent(/talla máxima que pasa/);
    await userEvent.click(within(zoom).getByRole('button', { name: 'Cerrar zoom' }));

    const body = calls.find((c) => c.url.endsWith('/simulate/selectivity'))?.body as {
      species: string[];
      variants: { orientation: string; mesh_mm: number }[];
    };
    expect(body.species).toEqual(['hake_hubbsi', 'cod']);
    expect(body.variants.map((v) => v.orientation)).toEqual(['diamond', 't90']);
    expect(body.variants[0]?.mesh_mm).toBe(120);
  });

  it('el modo guiado abre la vista de selectividad', async () => {
    window.localStorage.setItem(MODE_KEY, JSON.stringify('simple'));
    mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    for (let i = 0; i < 3; i++)
      await userEvent.click(screen.getByRole('button', { name: /Siguiente|Ver resultado/ }));
    await userEvent.click(
      await screen.findByRole(
        'button',
        { name: '¿Qué tallas retiene el copo?' },
        { timeout: 3000 },
      ),
    );
    expect(
      await screen.findByRole('button', { name: 'Mallas y selectividad' }, { timeout: 4000 }),
    ).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('spinbutton', { name: /Captura en el copo/ })).toHaveValue(500);
  });
});
