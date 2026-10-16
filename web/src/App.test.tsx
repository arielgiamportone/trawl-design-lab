import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from './App';
import { mockApi } from './test/mockApi';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

describe('App', () => {
  it('calcula el caso por defecto y muestra KPI y resumen', async () => {
    const { calls } = mockApi();
    renderApp();
    expect(screen.getByRole('heading', { name: /trawl-design-lab/ })).toBeInTheDocument();
    const kpi = await screen.findByText('2,27', {}, { timeout: 3000 });
    expect(kpi.closest('[data-kpi]')).toHaveAttribute('data-kpi', 'max_speed_kn');
    expect(screen.getByText('✓ Cumple la rotura')).toBeInTheDocument();
    expect(screen.getByRole('row', { name: /Lima 28,698 m/ })).toBeInTheDocument();
    const post = calls.find((c) => c.url.endsWith('/design'));
    expect(post?.body).toMatchObject({
      net: 'fao_a3_standard',
      net_modified: 'fao_a3_modified',
      compat: 'corrected',
    });
    expect(await screen.findByText('API conectada · v0.1.0')).toBeInTheDocument();
  });

  it('pestañas accesibles con flechas', async () => {
    mockApi();
    renderApp();
    const tab = screen.getByRole('tab', { name: 'Resumen' });
    expect(tab).toHaveAttribute('aria-selected', 'true');
    tab.focus();
    await userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Gráficos' })).toHaveAttribute('aria-selected', 'true');
    expect(screen.getByRole('tab', { name: 'Gráficos' })).toHaveFocus();
  });

  it('modo Excel muestra la advertencia del cable y envía compat', async () => {
    const { calls } = mockApi();
    renderApp();
    await screen.findByText('2,27', {}, { timeout: 3000 });
    await userEvent.click(screen.getByLabelText('Reproducir Excel'));
    expect(
      await screen.findByText('⚠ No cumple la rotura', {}, { timeout: 3000 }),
    ).toBeInTheDocument();
    expect(calls.some((c) => (c.body as { compat?: string } | undefined)?.compat === 'excel')).toBe(
      true,
    );
  });

  it('muestra el detail de un error 422 de la API', async () => {
    mockApi({
      design: () =>
        new Response(
          JSON.stringify({ detail: 'el caso no se puede calcular: división por cero' }),
          { status: 422 },
        ),
    });
    renderApp();
    const alert = await screen.findByRole('alert', {}, { timeout: 3000 });
    expect(within(alert).getByText(/Error 422/)).toBeInTheDocument();
    expect(alert).toHaveTextContent('división por cero');
  });

  it('una edición de panel inválida bloquea el cálculo; una válida envía la NetSpec en línea', async () => {
    const { calls } = mockApi();
    renderApp();
    await screen.findByText('2,27', {}, { timeout: 3000 });
    await userEvent.click(screen.getByRole('tab', { name: 'Editor de paneles' }));
    const input = await screen.findByLabelText('Mallas de alto (N) del panel C');
    await userEvent.clear(input);
    await userEvent.type(input, '0');
    expect(screen.getByRole('button', { name: 'Calcular' })).toBeDisabled();
    await userEvent.clear(input);
    await userEvent.type(input, '140');
    await userEvent.click(screen.getByRole('button', { name: 'Calcular' }));
    await waitFor(() => {
      const last = [...calls].reverse().find((c) => c.url.endsWith('/design'));
      const net = (last?.body as { net?: { panels?: { id: string; meshes_depth: number }[] } }).net;
      expect(typeof net).toBe('object');
      expect(net?.panels?.find((p) => p.id === 'C')?.meshes_depth).toBe(140);
    });
    // persistido en localStorage
    expect(window.localStorage.getItem('trawl-design-lab:case:v1')).toMatch(/"meshes_depth":"140"/);
  });
});
