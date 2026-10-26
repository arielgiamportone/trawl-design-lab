import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import type { ConstructionGuide } from '../../api/client';
import {
  completion,
  joinPanels,
  joinPlanes,
  loadProgress,
  progressKey,
  toggle,
} from '../../lib/construction';
import { forgetAll } from '../../lib/memo';
import { MODE_KEY } from '../../lib/mode';
import { fixtures, mockApi } from '../../test/mockApi';

const SLOW = 20_000;
const guide = fixtures.construction as unknown as ConstructionGuide;

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
  await userEvent.click(screen.getByRole('tab', { name: 'Construcción' }));
  return screen.findByTestId('construction', {}, { timeout: 5000 });
}

describe('lib/construction', () => {
  it('avance, uniones y planos', () => {
    expect(toggle([1, 2], 2)).toEqual([1]);
    expect(toggle([1], 3)).toEqual([1, 3]);
    expect(completion(guide, { cut: [], joins: [] })).toBe(0);
    const all = { cut: guide.pieces.map((p) => p.id), joins: guide.joins.map((j) => j.step) };
    expect(completion(guide, all)).toBe(1);
    const side = guide.joins.find((j) => j.kind === 'side_seam')!;
    expect(joinPanels(side)).toBe('all');
    expect(joinPlanes(side)).toEqual(['upper', 'lower']);
    const lower = guide.joins.find((j) => j.plane === 'vientre')!;
    expect(joinPlanes(lower)).toEqual(['lower']);
    expect(loadProgress('x', 'std')).toEqual({ cut: [], joins: [] });
  });
});

describe('Construcción', () => {
  it(
    'muestra la hoja de corte y recuerda lo tildado',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      const sheet = await screen.findByTestId('cut-sheet', {}, { timeout: 5000 });
      expect(within(sheet).getByRole('table', { name: 'Paño a comprar' })).toBeInTheDocument();
      expect(within(sheet).getAllByText(/1N2B: 1 punta y 2 malletas/).length).toBeGreaterThan(0);
      expect(within(sheet).getAllByText('inferido').length).toBeGreaterThan(0);
      await userEvent.click(screen.getByLabelText('Paño A cortado'));
      const saved = JSON.parse(localStorage.getItem(progressKey(guide.net_id, 'std'))!);
      expect(saved.cut).toEqual(['A']);
      expect(screen.getByTestId('guide-summary')).toHaveTextContent(
        `${Math.round(100 / (guide.pieces.length + guide.joins.length))} %`,
      );
      expect(calls.some((c) => c.url.includes('/design/construction?variant=std'))).toBe(true);
    },
    SLOW,
  );

  it(
    'recorre las uniones paso a paso con el plano resaltado',
    async () => {
      mockApi();
      renderApp();
      await openTab();
      await userEvent.click(await screen.findByRole('button', { name: 'Armado paso a paso' }));
      const asm = await screen.findByTestId('assembly');
      expect(asm).toHaveTextContent(`Paso 1 de ${guide.joins.length}`);
      const map = await screen.findByTestId('join-map', {}, { timeout: 5000 });
      const first = guide.joins[0]!;
      await waitFor(() =>
        expect(map.querySelector(`[data-panel="${first.a}"][data-on="true"]`)).not.toBeNull(),
      );
      await userEvent.click(screen.getByRole('button', { name: 'Hecho, siguiente →' }));
      expect(asm).toHaveTextContent(`Paso 2 de ${guide.joins.length}`);
      expect(screen.getByLabelText('Paso 1 hecho')).toBeChecked();
    },
    SLOW,
  );

  it(
    'montaje, cortes y sobrante por gaza',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await openTab();
      await userEvent.click(await screen.findByRole('button', { name: 'Montaje en relingas' }));
      expect(await screen.findByTestId('float-line')).toBeInTheDocument();
      expect(screen.getByRole('table', { name: 'Montaje en relingas' })).toHaveTextContent('lima');
      await userEvent.click(screen.getByRole('button', { name: 'Cabos y cables' }));
      expect(screen.getByTestId('rope-cuts')).toHaveTextContent('Lima (relinga superior)');
      const eye = screen.getByLabelText('Sobrante por gaza');
      await userEvent.clear(eye);
      await userEvent.type(eye, '0,3');
      await waitFor(() =>
        expect(calls.some((c) => c.url.includes('eye_allowance_m=0.3'))).toBe(true),
      );
    },
    SLOW,
  );
});
