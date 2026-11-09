import { render, screen, within } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { DesignResponseRaw } from '../api/client';
import { asDesignData, type DesignData } from '../api/result';
import { setLang } from '../i18n';
import { setUnits } from '../lib/units';
import design from '../test/fixtures/design.json';
import { SummaryTable } from './SummaryTable';

const state: { data: DesignData | null } = { data: null };

vi.mock('../state/useCase', () => ({
  useCase: () => ({ design: { data: state.data, isFetching: false } }),
}));

/** Caso del fixture (A-3: cruce a 2,27 kn), con tiro de sobra si ``beyond``. */
function data(beyond: boolean, flag: boolean): DesignData {
  const d = asDesignData(JSON.parse(JSON.stringify(design)) as DesignResponseRaw);
  if (beyond) {
    for (const w of Object.values(d.result.performance.windows)) {
      w.feasible = w.speeds_kn.map(() => true);
      w.max_speed_kn = w.speeds_kn[w.speeds_kn.length - 1]!;
      w.beyond_grid = flag ? true : undefined;
    }
    d.summary.max_speed_kn = 5;
  }
  if (flag) (d.summary as Record<string, unknown>).max_speed_beyond_grid = beyond;
  return d;
}

function maxSpeedRow(): HTMLElement {
  const row = screen.getByTestId('summary').querySelector<HTMLElement>('[data-key="max_speed_kn"]');
  expect(row).not.toBeNull();
  return row!;
}

afterEach(() => {
  setLang('es');
  setUnits('metric');
});

describe('SummaryTable: velocidad máxima fuera de la grilla (Fase 20.8)', () => {
  it('con la marca muestra «> 5 (fuera de la grilla)» y no muestra la marca como fila', () => {
    setLang('es');
    state.data = data(true, true);
    render(<SummaryTable />);
    const row = maxSpeedRow();
    expect(within(row).getByText('> 5 (fuera de la grilla)')).toBeInTheDocument();
    expect(row.textContent).toMatch(/> 5 \(fuera de la grilla\)kn$/);
    expect(screen.getByTestId('summary').querySelector('[data-key$="beyond_grid"]')).toBeNull();
  });

  it('sin la marca (respuesta vieja) la deduce de performance.design', () => {
    setLang('es');
    state.data = data(true, false);
    render(<SummaryTable />);
    expect(within(maxSpeedRow()).getByText('> 5 (fuera de la grilla)')).toBeInTheDocument();
  });

  it('en inglés y en unidades imperiales', () => {
    setLang('en');
    setUnits('imperial');
    state.data = data(true, true);
    render(<SummaryTable />);
    expect(within(maxSpeedRow()).getByText('> 5 (beyond the grid)')).toBeInTheDocument();
  });

  it('con cruce dentro de la grilla muestra el número (2,27 kn)', () => {
    setLang('es');
    for (const flag of [true, false]) {
      state.data = data(false, flag);
      const { unmount } = render(<SummaryTable />);
      const cell = maxSpeedRow().querySelector('td')!;
      expect(cell.textContent).toMatch(/^2,26?8/);
      expect(cell.textContent).not.toMatch(/>|grilla/);
      unmount();
    }
  });
});
