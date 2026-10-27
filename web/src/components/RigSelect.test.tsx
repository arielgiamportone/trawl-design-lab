/**
 * Selector de aparejo (Fase 19.5): tangones, gemelo y vara en el panel del caso, en español y en
 * inglés, con el parámetro ``rig`` en el pedido; copias de la red en la vista 3D.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { CatalogItem } from '../api/client';
import type { DesignData } from '../api/result';
import { setLang } from '../i18n';
import { DEFAULT_FILTERS, filterNets } from '../lib/catalog';
import { forgetAll } from '../lib/memo';
import { paramLabel } from '../lib/params';
import { buildBuffers, RAMP_LIGHT, rigOffsets, type SimGeometry } from '../lib/sim3d';
import { composition } from '../lib/series';
import { rigParams } from '../lib/simulate';
import { setUnits } from '../lib/units';
import { CaseProvider } from '../state/CaseProvider';
import { ConnectionProvider } from '../state/ConnectionProvider';
import { fixtures, mockApi, type Call } from '../test/mockApi';
import { CasePanel } from './CasePanel';

function renderIn(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ConnectionProvider>
        <CaseProvider>{ui}</CaseProvider>
      </ConnectionProvider>
    </QueryClientProvider>,
  );
}

const lastParams = (calls: Call[]) =>
  (
    calls.filter((c) => new URL(c.url, 'http://x').pathname.endsWith('/design')).at(-1)?.body as
      { params?: Record<string, unknown> } | undefined
  )?.params;

beforeEach(() => {
  localStorage.clear();
  forgetAll();
});
afterEach(() => {
  vi.unstubAllGlobals();
  setLang('es');
  setUnits('metric');
});

describe('selector de aparejo', () => {
  it('en español: tangones, gemelo y vara; el aparejo va en el pedido', async () => {
    setLang('es');
    const { calls } = mockApi();
    renderIn(<CasePanel />);
    const box = await screen.findByTestId('rig-select');
    const select = within(box).getByRole('combobox', { name: 'Aparejo' });
    const options = within(select)
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(options).toEqual([
      'El de la red (Portones)',
      'Portones',
      'Pareja',
      'Tangones',
      'Gemelo',
      'Vara',
    ]);
    await userEvent.selectOptions(select, 'outrigger');
    expect(within(box).getByText(/una desde cada tangón/)).toBeInTheDocument();
    expect(within(box).getByText(/Parámetros avanzados/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'Calcular' }));
    await waitFor(() => expect(lastParams(calls)?.rig).toBe('outrigger'));
    await userEvent.selectOptions(select, '');
    await userEvent.click(screen.getByRole('button', { name: 'Calcular' }));
    await waitFor(() => expect(lastParams(calls)?.rig).toBeUndefined());
  });

  it('in English, with imperial units in the rig parameters', async () => {
    setLang('en');
    setUnits('imperial');
    mockApi();
    renderIn(<CasePanel />);
    const box = await screen.findByTestId('rig-select');
    const select = within(box).getByRole('combobox', { name: 'Rig' });
    const options = within(select)
      .getAllByRole('option')
      .map((o) => o.textContent);
    expect(options).toContain('Outrigger (booms)');
    expect(options).toContain('Twin');
    expect(options).toContain('Beam trawl');
    await userEvent.selectOptions(select, 'beam');
    expect(within(box).getByText(/The beam sets the horizontal opening/)).toBeInTheDocument();
    expect(paramLabel('boom_length_m')).toBe('Boom length [ft]');
    expect(paramLabel('clump_weight_kg')).toBe('Centre clump weight [lb]');
    expect(paramLabel('beam_shoe_area_m2')).toMatch(/^Frontal area of one shoe \[ft²\]$/);
  });
});

describe('aparejo en la simulación y la vista 3D', () => {
  it('sólo manda los parámetros del aparejo cuando el caso los cambia', () => {
    expect(rigParams({})).toBeUndefined();
    expect(rigParams({ depth_m: 40 })).toBeUndefined();
    expect(rigParams({ rig: 'twin', clump_weight_kg: 200, depth_m: 40 })).toEqual({
      rig: 'twin',
      clump_weight_kg: 200,
    });
  });

  it('replica la red simulada con los desplazamientos del aparejo', () => {
    const g: SimGeometry = {
      speed_kn: 3,
      nodes: [
        [0, -1, 0],
        [0, 1, 0],
        [1, 0, 1],
      ],
      triangles: [[0, 1, 2]],
      twine_tension_n: [10],
      bars: [[0, 1]],
      bar_kind: ['headrope'],
      float_nodes: [2],
      ah_m: 2,
      av_m: 1,
    };
    expect(rigOffsets(g)).toEqual([0]);
    const one = buildBuffers(g, RAMP_LIGHT);
    const two = buildBuffers(
      { ...g, rig: { kind: 'twin', n_nets: 2, offsets_m: [5, -5] } },
      RAMP_LIGHT,
    );
    expect(two.positions.length).toBe(2 * one.positions.length);
    expect(two.floats.length).toBe(2 * one.floats.length);
    // y de la simulación = z de three.js: la primera copia va 5 m a un lado.
    expect(two.positions[2]).toBeCloseTo(-1 + 5);
    expect(two.radius).toBeGreaterThan(one.radius);
  });

  it('el catálogo filtra por los aparejos nuevos', () => {
    const nets = [
      { id: 'a', rig: 'otter' },
      { id: 'b', rig: 'outrigger', status: 'draft' },
      { id: 'c', rig: 'beam' },
    ] as CatalogItem[];
    expect(filterNets(nets, { ...DEFAULT_FILTERS, rig: 'beam' }).map((n) => n.id)).toEqual(['c']);
    expect(
      filterNets(nets, { ...DEFAULT_FILTERS, rig: 'outrigger', drafts: true }).map((n) => n.id),
    ).toEqual(['b']);
  });
});

describe('composición de la resistencia con dos redes', () => {
  it('suma todas las redes, los cables y el muerto del gemelo', () => {
    const base = fixtures.design as unknown as DesignData;
    const n = base.case.speeds_kn.length;
    const one = composition(base, 4)[0];
    const twin: DesignData = {
      ...base,
      result: {
        ...base.result,
        multirig: {
          kind: 'twin',
          n_nets: 2,
          warp_drag_kgf: Array(n).fill(10),
          doors_drag_kgf: Array(n).fill(100),
          bridle_drag_kgf: null,
          clump_drag_kgf: Array(n).fill(5),
          beam: null,
        },
      },
    };
    const two = composition(twin, 4)[0];
    expect(one && two).toBeTruthy();
    expect(two?.rn).toBeCloseTo(2 * (one?.rn ?? 0));
    expect(two?.floats).toBeCloseTo(2 * (one?.floats ?? 0));
    expect(two?.warps).toBe(10);
    expect(two?.doors).toBe(105);
  });
});
