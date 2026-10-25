import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { forgetAll } from '../lib/memo';
import { MODE_KEY } from '../lib/mode';
import { mockApi } from '../test/mockApi';

beforeEach(() => {
  localStorage.clear();
  forgetAll();
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
});
afterEach(() => vi.unstubAllGlobals());

describe('Lotes', () => {
  it('carga una flota, la proyecta y abre un buque como caso', async () => {
    const { calls } = mockApi();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    await screen.findByText('2,27', {}, { timeout: 3000 });
    await userEvent.click(screen.getByRole('tab', { name: 'Lotes y flota' }));
    const tab = await screen.findByTestId('batch', {}, { timeout: 5000 });
    const file = new File(['nombre;potencia\nDon Pedro;60\n'], 'flota.csv', { type: 'text/csv' });
    await userEvent.upload(within(tab).getByLabelText('Planilla del lote'), file);
    const preview = await screen.findByTestId('fleet-preview', {}, { timeout: 3000 });
    expect(within(preview).getAllByRole('row')).toHaveLength(3);
    expect(screen.getByTestId('batch-issues')).toHaveTextContent('falta bhp');
    // editar la potencia del primer buque antes de calcular
    const hp = within(preview).getByLabelText('bhp del buque 1');
    await userEvent.clear(hp);
    await userEvent.type(hp, '70');
    await userEvent.tab();
    await userEvent.click(screen.getByRole('button', { name: 'Calcular el lote' }));
    const results = await screen.findByTestId('batch-results', {}, { timeout: 3000 });
    const req = calls.find((c) => c.url.endsWith('/batch/run'))?.body as {
      net: string;
      file: { content: string };
    };
    expect(req.net).toBe('fao_wb_bt2p_60hp');
    expect(req.file.content).toContain('Don Pedro;70');
    expect(within(results).getAllByText('cumple').length).toBeGreaterThan(0);
    await userEvent.click(within(results).getAllByRole('button', { name: 'Abrir este caso' })[1]!);
    expect(await screen.findByTestId('from-batch', {}, { timeout: 3000 })).toHaveTextContent(
      'La Gaviota',
    );
    await waitFor(() => {
      const last = calls.filter((c) => c.url.endsWith('/design')).at(-1)?.body as {
        vessel: unknown;
      };
      expect(last.vessel).toMatchObject({ bhp: 150 });
    });
  }, 20_000);
});
