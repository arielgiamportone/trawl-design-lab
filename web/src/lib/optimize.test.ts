import { describe, expect, it } from 'vitest';
import type { OptimizeResponse } from '../api/client';
import optimize from '../test/fixtures/optimize.json';
import {
  buildOptimize,
  DEFAULT_FORM,
  gridData,
  heatCells,
  paretoPoints,
  samePoint,
} from './optimize';

const r = optimize as unknown as OptimizeResponse;

describe('optimize', () => {
  it('arma el pedido desde el formulario (coma decimal, margen en %)', () => {
    const b = buildOptimize({ ...DEFAULT_FORM, margin: '15', sMin: '0,7', vMax: '3.5' });
    expect(b.errors).toEqual({});
    expect(b.body).toMatchObject({
      objective: 'area',
      margin: 0.15,
      s_bounds: [0.7, 1.4],
      v_bounds: [1.5, 3.5],
      grid: { n_s: 9, n_v: 11 },
      refine: false,
    });
  });

  it('valida rangos, enteros y orden de los límites', () => {
    const b = buildOptimize({ ...DEFAULT_FORM, sMin: '1,5', sMax: '1,2', nS: '2,5', vMin: 'x' });
    expect(b.body).toBeNull();
    expect(b.errors.sMax).toBe('Debe ser mayor que el mínimo');
    expect(b.errors.nS).toBe('Debe ser entero');
    expect(b.errors.vMin).toBe('Ingrese un número');
    expect(buildOptimize({ ...DEFAULT_FORM, nV: '30' }).errors.nV).toMatch(/Entre 2 y 25/);
  });

  it('mapa de factibilidad: una celda por (s, v), escala sólo en las factibles', () => {
    const g = gridData(r);
    const { cells, min, max } = heatCells(r);
    expect(cells).toHaveLength(g.s_values.length * g.v_values.length);
    const feasible = cells.filter((c) => c.feasible);
    expect(feasible.length).toBeGreaterThan(0);
    expect(cells.filter((c) => !c.feasible).every((c) => c.t === null)).toBe(true);
    expect(feasible.every((c) => c.t !== null && c.t >= 0 && c.t <= 1)).toBe(true);
    expect(min).not.toBeNull();
    const best = cells.filter((c) => c.best);
    expect(best).toHaveLength(1);
    expect(best[0]!.value).toBe(max); // área: el mejor es el máximo
    expect(best[0]!.t).toBe(1);
  });

  it('energía: el mejor es el mínimo y la escala se invierte', () => {
    const e = { ...r, objective: 'energy' } as OptimizeResponse;
    const { cells, min } = heatCells(e);
    const best = cells.find((c) => c.best)!;
    expect(best.value).toBe(min);
    expect(best.t).toBe(1);
  });

  it('frente de Pareto ordenado por área y en miles de m²/h', () => {
    const pts = paretoPoints(r);
    expect(pts.length).toBe(r.pareto.length);
    for (let i = 1; i < pts.length; i++)
      expect(pts[i]!.area).toBeGreaterThanOrEqual(pts[i - 1]!.area);
    expect(pts[0]!.area).toBeLessThan(1000);
    expect(samePoint(r.best, r.best)).toBe(true);
    expect(samePoint(r.best, { s: r.best.s + 0.1, v_kn: r.best.v_kn })).toBe(false);
  });
});
