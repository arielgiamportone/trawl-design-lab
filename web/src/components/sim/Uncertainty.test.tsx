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

async function openView() {
  await userEvent.click(
    await screen.findByRole('button', { name: 'Incertidumbre y calibración' }, { timeout: 4000 }),
  );
}

describe('incertidumbre y calibración', () => {
  it('calcula bandas P10–P90 y el tornado de la salida elegida', async () => {
    const { calls } = mockApi();
    renderApp();
    await openView();
    const run = await screen.findByRole('button', { name: 'Calcular bandas' });
    await waitFor(() => expect(run).toBeEnabled(), { timeout: 3000 });
    await userEvent.click(run);
    const table = await screen.findByTestId('uncertainty-table', {}, { timeout: 3000 });
    expect(table.querySelector('[data-output="door_spread_m"]')).toBeInTheDocument();
    const tornado = screen.getByTestId('tornado');
    expect(tornado).toHaveTextContent(/separación de portones/);
    await userEvent.click(within(table).getByRole('button', { name: 'Tiro en el buque' }));
    expect(screen.getByTestId('tornado')).toHaveTextContent(/tiro en el buque/);
    const body = calls.find((c) => c.url.endsWith('/simulate/uncertainty'))?.body as {
      samples: number;
      scenario: { seabed: string };
    };
    expect(body.samples).toBe(10);
    expect(body.scenario.seabed).toBe('mixed');
  });

  it('lee el registro de ejemplo y calibra la sustentación del portón', async () => {
    const { calls } = mockApi();
    renderApp();
    await openView();
    await userEvent.click(screen.getByRole('button', { name: 'Calibración con mediciones' }));
    await userEvent.click(screen.getByRole('button', { name: 'Usar el registro de ejemplo' }));
    const summary = await screen.findByTestId('sensor-summary', {}, { timeout: 3000 });
    expect(summary).toHaveTextContent('360 filas');
    expect(summary).toHaveTextContent(/Separación de portones/);
    const run = screen.getByRole('button', { name: 'Calibrar' });
    await waitFor(() => expect(run).toBeEnabled());
    await userEvent.click(run);
    const params = await screen.findByTestId('calibration-params', {}, { timeout: 3000 });
    expect(params).toHaveTextContent('Factor de C_L del portón');
    expect(screen.getByTestId('calibration-observations')).toBeInTheDocument();
    const body = calls.find((c) => c.url.endsWith('/simulate/calibrate'))?.body as {
      observations: unknown[];
      params: string[];
      reference: string | null;
    };
    expect(body.reference).toBeNull();
    expect(body.observations.length).toBe(9);
    expect(body.params).toEqual(['door_cl_factor']);
  });
});
