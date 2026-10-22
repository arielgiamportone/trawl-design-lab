import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { MODE_KEY } from '../../lib/mode';
import { TAB_KEY } from '../../lib/tabs';
import { mockApi, type Call } from '../../test/mockApi';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
  window.localStorage.setItem(TAB_KEY, JSON.stringify('diseno'));
});
afterEach(() => vi.unstubAllGlobals());

const lastDesignNet = (calls: Call[]) => {
  const body = calls.filter((c) => c.url.endsWith('/design')).at(-1)?.body as
    { net: { panels?: { id: string; meshes_depth: number }[] } | string } | undefined;
  return typeof body?.net === 'object' ? body.net : null;
};

describe('diseño interactivo', () => {
  it('selecciona un panel en el plano y lo ajusta con −/+ y flechas', async () => {
    const { calls } = mockApi();
    renderApp();
    const panelC = await screen.findByRole(
      'button',
      { name: /^Panel C \(ala, superior, derecha\)/ },
      { timeout: 3000 },
    );
    await userEvent.click(panelC);
    const inspector = screen.getByTestId('panel-inspector');
    expect(within(inspector).getByRole('heading', { name: /Panel C/ })).toBeInTheDocument();
    expect(document.querySelectorAll('circle[data-panel="C"]').length).toBeGreaterThan(0);

    await userEvent.click(
      within(inspector).getByRole('button', { name: 'Sumar 1 a Mallas de alto (N)' }),
    );
    expect(within(inspector).getByLabelText('Mallas de alto (N)')).toHaveValue('121');
    await waitFor(
      () => expect(lastDesignNet(calls)?.panels?.find((p) => p.id === 'C')?.meshes_depth).toBe(121),
      { timeout: 3000 },
    );
    expect(calls.some((c) => c.url.includes('/design/layout'))).toBe(true);

    fireEvent.keyDown(panelC, { key: 'ArrowDown', shiftKey: true });
    expect(within(inspector).getByLabelText('Mallas de alto (N)')).toHaveValue('131');
    expect(await screen.findByText(/2 valores editados|1 valor editado/)).toBeInTheDocument();

    await userEvent.click(
      within(inspector).getByRole('button', { name: 'Restablecer este panel' }),
    );
    expect(within(inspector).getByLabelText('Mallas de alto (N)')).toHaveValue('120');
    expect(screen.getByText(/Sin cambios respecto de la red de base/)).toBeInTheDocument();
  });

  it('muestra el impacto contra la red de base y Esc deselecciona', async () => {
    mockApi();
    renderApp();
    expect(await screen.findByText('Velocidad máxima', {}, { timeout: 3000 })).toBeInTheDocument();
    expect(screen.getAllByText('red de base').length).toBeGreaterThan(0);
    const panelG = (
      await screen.findAllByRole('button', { name: /^Panel G/ }, { timeout: 3000 })
    )[0] as HTMLElement;
    await userEvent.click(panelG);
    expect(screen.getByTestId('panel-inspector')).toBeInTheDocument();
    fireEvent.keyDown(screen.getByTestId('net-canvas'), { key: 'Escape' });
    expect(screen.queryByTestId('panel-inspector')).not.toBeInTheDocument();
  });

  it('el modo guiado lleva al plano editable', async () => {
    window.localStorage.setItem(MODE_KEY, JSON.stringify('simple'));
    window.localStorage.removeItem(TAB_KEY);
    mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    for (let i = 0; i < 3; i++)
      await userEvent.click(screen.getByRole('button', { name: /Siguiente|Ver resultado/ }));
    await userEvent.click(
      await screen.findByRole(
        'button',
        { name: 'Ajustar la red sobre el plano' },
        { timeout: 3000 },
      ),
    );
    expect(screen.getByRole('tab', { name: 'Diseño interactivo' })).toHaveAttribute(
      'aria-selected',
      'true',
    );
  });
});
