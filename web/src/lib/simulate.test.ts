import { describe, expect, it } from 'vitest';
import type { SimulateResponse } from '../api/client';
import simulate from '../test/fixtures/simulate.json';
import { compareRows, pctDiff, speedKey, speedLabel, toggleSpeed, unconverged } from './simulate';

const r = simulate as unknown as SimulateResponse;

describe('simulate', () => {
  it('selección de velocidades: ordenada y con máximo', () => {
    expect(toggleSpeed([3], 2)).toEqual([2, 3]);
    expect(toggleSpeed([2, 3], 3)).toEqual([2]);
    expect(toggleSpeed([1, 2, 3], 4)).toEqual([1, 2, 3]);
    expect(toggleSpeed([1, 2], 4, 2)).toEqual([1, 2]);
  });

  it('claves y etiquetas de velocidad', () => {
    expect(speedKey(3)).toBe('3');
    expect(speedKey(2.5)).toBe('2.5');
    expect(speedLabel(3)).toBe('3,0');
    expect(Object.keys(r.projections_svg)).toEqual([speedKey(3)]);
  });

  it('diferencia porcentual', () => {
    expect(pctDiff(110, 100)).toBeCloseTo(10);
    expect(pctDiff(null, 100)).toBeNull();
    expect(pctDiff(1, 0)).toBeNull();
  });

  it('tabla: tres magnitudes por velocidad, con DynamiT para la red estándar', () => {
    const rows = compareRows(r);
    expect(rows).toHaveLength(3);
    const drag = rows.find((x) => x.key === 'drag_kgf')!;
    expect(drag.dynamit).toBeCloseTo(1331.3);
    expect(drag.simVsDynamit).toBeCloseTo(r.dynamit_comparison![0]!.sim_pct.drag_kgf!, 6);
    expect(drag.engine).toBeCloseTo(r.engine[0]!.drag_kgf!, 6);
    expect(drag.simVsEngine).toBeLessThan(0); // la simulación da menos resistencia
    const sinDyn = compareRows({ ...r, dynamit_comparison: null });
    expect(sinDyn.every((x) => x.dynamit === null && x.simVsDynamit === null)).toBe(true);
    expect(unconverged(r)).toEqual([]);
  });
});
