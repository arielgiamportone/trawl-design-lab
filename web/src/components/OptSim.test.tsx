import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { forgetAll } from '../lib/memo';
import { mockApi } from '../test/mockApi';

// Recorridos largos de interfaz (varias pestañas y pedidos): margen para máquinas lentas.
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
});
afterEach(() => vi.unstubAllGlobals());

describe('Optimizar', () => {
  it(
    'optimiza, muestra el mejor diseño y lo aplica al caso',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await screen.findByText('2,27', {}, { timeout: 3000 });
      await userEvent.click(screen.getByRole('tab', { name: 'Optimizar' }));
      const btn = await screen.findByRole('button', { name: 'Optimizar' });
      await userEvent.click(screen.getByLabelText('Volumen'));
      await userEvent.clear(screen.getByLabelText('Reserva de tiro [%]'));
      await userEvent.type(screen.getByLabelText('Reserva de tiro [%]'), '20');
      await userEvent.click(btn);
      const best = await screen.findByTestId('opt-best', {}, { timeout: 3000 });
      const req = calls.find((c) => c.url.endsWith('/optimize'))?.body;
      expect(req).toMatchObject({ net: 'fao_a3_standard', objective: 'volume', margin: 0.2 });
      expect(within(best).getByText('Factible')).toBeInTheDocument();
      expect(within(best).getByText('0,6')).toBeInTheDocument(); // escala
      expect(within(screen.getByTestId('opt-constraints')).getAllByText('OK')).toHaveLength(5);
      expect(screen.getByTestId('opt-heatmap')).toBeInTheDocument();
      await userEvent.click(within(best).getByRole('button', { name: 'Usar este diseño' }));
      expect(await screen.findByTestId('scaled-net', {}, { timeout: 3000 })).toHaveTextContent(
        'Red escalada s = 0,6',
      );
      expect(screen.getByRole('tab', { name: 'Resumen' })).toHaveAttribute('aria-selected', 'true');
      const scaled = calls.filter((c) => c.url.endsWith('/optimize/scaled-net'));
      expect(scaled.map((c) => (c.body as { net: string }).net)).toEqual([
        'fao_a3_standard',
        'fao_a3_modified',
      ]);
      // el caso se recalcula con la red escalada en línea
      await vi.waitFor(() => {
        const last = calls.filter((c) => c.url.endsWith('/design')).at(-1)?.body as {
          net: { id?: string };
        };
        expect(last.net.id).toBe('fao_a3_standard_s0.60');
      });
      await userEvent.click(screen.getByRole('button', { name: 'Volver a la red del catálogo' }));
      expect(screen.queryByTestId('scaled-net')).toBeNull();
    },
    SLOW,
  );

  it(
    'el formulario inválido bloquea el botón',
    async () => {
      mockApi();
      renderApp();
      await userEvent.click(screen.getByRole('tab', { name: 'Optimizar' }));
      const input = await screen.findByLabelText('Escala mínima');
      await userEvent.clear(input);
      await userEvent.type(input, '3');
      expect(screen.getByText('Entre 0,3 y 2')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Optimizar' })).toBeDisabled();
    },
    SLOW,
  );
});

describe('Simulación', () => {
  it(
    'simula las velocidades elegidas y muestra proyecciones y tabla',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await screen.findByText('2,27', {}, { timeout: 3000 });
      await userEvent.click(screen.getByRole('tab', { name: 'Simulación' }));
      await screen.findByRole('button', { name: 'Simular' });
      await userEvent.click(screen.getByRole('button', { name: '2,0' }));
      await userEvent.click(screen.getByRole('button', { name: '4,0' }));
      // máximo tres velocidades
      expect(screen.getByRole('button', { name: '5,0' })).toBeDisabled();
      await userEvent.click(screen.getByLabelText('Normal (6)'));
      await userEvent.click(screen.getByRole('button', { name: 'Simular' }));
      const table = await screen.findByTestId('sim-table', {}, { timeout: 3000 });
      const req = calls.find((c) => c.url.endsWith('/simulate'))?.body;
      expect(req).toMatchObject({ speeds_kn: [2, 3, 4], resolution: 6, net: 'fao_a3_standard' });
      expect(screen.getAllByTestId('sim-svg')).toHaveLength(3); // planta, perfil, frente (fixture: 3 kn)
      expect(within(table).getByText('DynamiT')).toBeInTheDocument();
      expect(screen.getByText(/Sobre la resistencia/)).toBeInTheDocument();
    },
    SLOW,
  );
});
