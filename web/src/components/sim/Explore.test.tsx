import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
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

describe('explorador animado', () => {
  it('calcula estados, mueve la línea de tiempo y el tablero sigue al estado', async () => {
    const { calls } = mockApi();
    renderApp();
    await userEvent.click(
      await screen.findByRole('button', { name: 'Explorador animado' }, { timeout: 4000 }),
    );
    const fouling = await screen.findByRole('combobox', { name: 'Ensuciamiento' });
    await waitFor(() => expect(within(fouling).getAllByRole('option').length).toBe(4));
    await userEvent.selectOptions(fouling, 'algae_wings');
    const run = screen.getByRole('button', { name: 'Calcular estados' });
    await waitFor(() => expect(run).toBeEnabled(), { timeout: 3000 });
    await userEvent.click(run);

    const dash = await screen.findByTestId('explore-dashboard', {}, { timeout: 3000 });
    const dp = () =>
      within(dash).getByText('Separación de portones').closest('[data-indicator]') as HTMLElement;
    expect(dp()).toHaveTextContent('igual al primer estado');
    const slider = screen.getByRole('slider', { name: /Captura en el copo/ });
    fireEvent.change(slider, { target: { value: '2' } });
    expect(screen.getByText(/Captura en el copo:/).textContent).toMatch(/1\.000 kg/);
    expect(dp()).toHaveTextContent(/vs primer estado/);
    expect(dp()).toHaveClass('bad');
    await userEvent.click(screen.getByRole('button', { name: 'Estado anterior' }));
    expect(screen.getByText(/Captura en el copo:/).textContent).toMatch(/500 kg/);
    expect(screen.getByRole('button', { name: '▶ Reproducir' })).toBeInTheDocument();
    for (const id of ['explore-dp', 'explore-pull', 'explore-av', 'explore-fuel'])
      expect(document.querySelector(`[data-chart="${id}"]`)).toBeInTheDocument();
    expect(await screen.findByText(/no tiene WebGL/, {}, { timeout: 3000 })).toBeInTheDocument();

    const body = calls.find((c) => c.url.endsWith('/simulate/explore'))?.body as {
      variable: string;
      values: number[];
      scenario: { fouling: string };
    };
    expect(body.variable).toBe('catch_kg');
    expect(body.scenario.fouling).toBe('algae_wings');
  });

  it('el modo guiado abre el explorador configurado con la captura esperada', async () => {
    window.localStorage.setItem(MODE_KEY, JSON.stringify('simple'));
    mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    for (let i = 0; i < 3; i++)
      await userEvent.click(screen.getByRole('button', { name: /Siguiente|Ver resultado/ }));
    await userEvent.click(
      await screen.findByRole(
        'button',
        { name: 'Ver cómo trabaja la red (animación)' },
        { timeout: 3000 },
      ),
    );
    expect(
      await screen.findByRole('button', { name: 'Explorador animado' }, { timeout: 4000 }),
    ).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('spinbutton', { name: /Hasta/ })).toHaveValue(500);
  });
});
