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

describe('lance progresivo', () => {
  it('pide el lance con el escenario y muestra resumen, gráficos, tabla y 3D', async () => {
    const { calls } = mockApi();
    renderApp();
    await userEvent.click(
      await screen.findByRole(
        'button',
        { name: 'Lance progresivo (captura y fondo)' },
        { timeout: 4000 },
      ),
    );
    const seabed = await screen.findByRole('combobox', { name: /Fondo/ });
    await waitFor(() => expect(within(seabed).getAllByRole('option').length).toBe(5));
    await userEvent.selectOptions(seabed, 'mud');
    expect(screen.getByText(/μ tren 0,4 · μ portón 0,35/)).toBeInTheDocument();
    const max = screen.getByRole('spinbutton', { name: /Captura final/ });
    await userEvent.clear(max);
    await userEvent.type(max, '900');
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Tipo de captura' }),
      'crustacean',
    );
    const run = screen.getByRole('button', { name: 'Simular lance' });
    await waitFor(() => expect(run).toBeEnabled(), { timeout: 3000 });
    await userEvent.click(run);

    const summary = await screen.findByTestId('haul-summary', {}, { timeout: 3000 });
    expect(summary).toHaveTextContent(/separación de portones baja/);
    for (const id of ['haul-dp', 'haul-pull', 'haul-ah', 'haul-av'])
      expect(document.querySelector(`[data-chart="${id}"]`)).toBeInTheDocument();
    expect(await screen.findByText(/no tiene WebGL/, {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '1.000 kg' })).toHaveAttribute(
      'aria-pressed',
      'true',
    );

    const body = calls.find((c) => c.url.endsWith('/simulate/haul'))?.body as {
      catches_kg: number[];
      scenario: { seabed: string; catch_bulk_density: number };
    };
    expect(body.catches_kg).toEqual([0, 300, 600, 900]);
    expect(body.scenario).toMatchObject({ seabed: 'mud', catch_bulk_density: 850 });
  });
});
