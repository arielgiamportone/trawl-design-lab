import { describe, expect, it } from 'vitest';
import type { DesignRequest, ExploreResponse } from '../api/client';
import explore from '../test/fixtures/explore.json';
import {
  asFrames,
  asGeometry,
  catchPreset,
  DEFAULT_EXPLORE,
  exploreRequest,
  frameIndex,
  INDICATORS,
  nodesAt,
  series,
  valueAt,
  valuesFor,
  variableDef,
} from './explore';

const r = explore as unknown as ExploreResponse;

describe('explorador', () => {
  it('valores parejos redondeados al paso de la variable', () => {
    expect(valuesFor(variableDef('catch_kg'), 0, 1000, 4)).toEqual([0, 350, 650, 1000]);
    expect(valuesFor(variableDef('current_kn'), -0.8, 0.8, 3)).toEqual([-0.8, 0, 0.8]);
    expect(valuesFor(variableDef('speed_kn'), 2, 4, 50)).toHaveLength(10);
  });

  it('arma el pedido (ensuciamiento por defecto si se recorre su nivel)', () => {
    const base = { net: 'fao_a3_standard', vessel: 'fao_a3_180hp', compat: 'corrected' };
    const req = exploreRequest(base as DesignRequest, {
      ...DEFAULT_EXPLORE,
      variable: 'fouling_level',
      from: 0,
      to: 1,
      steps: 3,
      currentKn: -0.5,
      warpLength: 250,
    });
    expect(req.variable).toBe('fouling_level');
    expect(req.values).toEqual([0, 0.5, 1]);
    expect(req.scenario).toMatchObject({
      fouling: 'general',
      current_kn: -0.5,
      warp_length_m: 250,
      coupled_doors: true,
    });
    expect(req.include_geometry).toBe(true);
    expect(catchPreset(800, 'mud', 2.5)).toMatchObject({
      variable: 'catch_kg',
      from: 0,
      to: 800,
      seabed: 'mud',
      speed: 2.5,
    });
  });

  it('interpola posiciones y series entre estados', () => {
    expect(frameIndex(0, 3)).toEqual({ i: 0, f: 0 });
    expect(frameIndex(1.25, 3)).toEqual({ i: 1, f: 0.25 });
    expect(frameIndex(2, 3)).toEqual({ i: 1, f: 1 });
    expect(frameIndex(9, 3)).toEqual({ i: 1, f: 1 });
    const frames = asFrames(r);
    const a = frames[0]?.nodes[5] as number[];
    const b = frames[1]?.nodes[5] as number[];
    const mid = nodesAt(frames, 0.5);
    expect(mid[15]).toBeCloseTo(((a[0] as number) + (b[0] as number)) / 2, 4);
    expect(Array.from(nodesAt(frames, 0).slice(15, 18))).toEqual(a.map((v) => Math.fround(v)));
    expect(valueAt([10, 20, 40], 1.5)).toBe(30);
    expect(valueAt([10, null], 0.5)).toBe(10);
  });

  it('geometría común e indicadores del fixture real', () => {
    const g = asGeometry(r);
    expect(g?.doors).toHaveLength(2);
    expect(g?.warps).toHaveLength(2);
    expect(asFrames(r)[0]?.fouling_tri).toHaveLength(g?.triangles.length ?? -1);
    const dp = series(
      r,
      INDICATORS.find((i) => i.key === 'dp')!,
    );
    expect(dp[2]).toBeLessThan(dp[0] as number);
    const fuel = series(
      r,
      INDICATORS.find((i) => i.key === 'fuel_kg')!,
    );
    expect(fuel[0]).toBeNull(); // sin captura no hay L/kg
    expect(fuel[2]).toBeGreaterThan(0);
  });
});
