import { describe, expect, it } from 'vitest';
import type { DesignRequest } from '../api/client';
import calibrate from '../test/fixtures/calibrate.json';
import uncertainty from '../test/fixtures/uncertainty.json';
import {
  asCalibration,
  asUncertainty,
  atBound,
  bandPct,
  calibrateRequest,
  DEFAULT_CAL,
  DEFAULT_UNC,
  relativeSpan,
  tornado,
  uncertaintyRequest,
} from './uncertainty';

const base = { net: 'fao_a3_standard', compat: 'corrected' } as DesignRequest;

describe('incertidumbre', () => {
  it('arma el pedido con el escenario completo', () => {
    const req = uncertaintyRequest(base, { ...DEFAULT_UNC, species: 'cod', catchKg: 500 });
    expect(req.samples).toBe(10);
    expect(req.species).toEqual(['cod']);
    expect(req.scenario?.catch_kg).toBe(500);
    expect(req.scenario?.door_cl_factor).toBe(1);
  });

  it('lee bandas, ordena el tornado y fija una escala común', () => {
    const r = asUncertainty(uncertainty as never);
    expect(r.n).toBe(6);
    const dp = r.outputs.find((o) => o.key === 'door_spread_m');
    if (!dp) throw new Error('sin DP');
    expect(dp.p10).toBeLessThanOrEqual(dp.p50);
    expect(dp.p50).toBeLessThanOrEqual(dp.p90);
    expect(bandPct(dp)).toBeGreaterThan(0);
    const t = tornado(dp, r.inputs);
    expect(t).toHaveLength(r.inputs.length);
    for (let k = 1; k < t.length; k++)
      expect(Math.abs(t[k - 1]?.rho ?? 0)).toBeGreaterThanOrEqual(Math.abs(t[k]?.rho ?? 0));
    const span = relativeSpan(r.outputs);
    expect(span % 5).toBe(0);
    expect(span).toBeGreaterThanOrEqual(5);
  });
});

describe('calibración', () => {
  it('DynamiT no manda observaciones ni fondo; sensores manda las observaciones', () => {
    const obs = [
      { quantity: 'door_spread_m', value: 42, speed_kn: 3, catch_kg: 0, weight: 1, source: '' },
    ];
    const dyn = calibrateRequest(base, { ...DEFAULT_CAL, source: 'dynamit' }, obs as never);
    expect(dyn.reference).toBe('dynamit');
    expect(dyn.observations).toEqual([]);
    expect(dyn.scenario?.seabed).toBeNull();
    const sen = calibrateRequest(base, DEFAULT_CAL, obs as never);
    expect(sen.reference).toBeNull();
    expect(sen.observations).toHaveLength(1);
    expect(sen.params).toEqual(['door_cl_factor']);
  });

  it('lee el resultado y detecta parámetros en el límite', () => {
    const r = asCalibration(calibrate as never);
    expect(r.rmse_after_pct).toBeLessThan(r.rmse_before_pct);
    const p = r.params[0];
    if (!p) throw new Error('sin parámetro');
    expect(p.fitted).toBeCloseTo(0.9, 1);
    expect(atBound(p)).toBe(false);
    expect(atBound({ ...p, fitted: p.high })).toBe(true);
  });
});
