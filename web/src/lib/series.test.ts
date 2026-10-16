import { describe, expect, it } from 'vitest';
import { asDesignData } from '../api/result';
import type { DesignResponseRaw } from '../api/client';
import design from '../test/fixtures/design.json';
import designExcel from '../test/fixtures/design_excel.json';
import { tiles } from './kpis';
import {
  composition,
  dragRows,
  feasibleWindow,
  perfWindow,
  pullRows,
  spreadRows,
  warpMeetsBreakingLoad,
} from './series';

const d = asDesignData(design as unknown as DesignResponseRaw);
const dx = asDesignData(designExcel as unknown as DesignResponseRaw);

describe('series', () => {
  it('composición suma la resistencia total del motor', () => {
    const i = d.case.speeds_kn.indexOf(3);
    const [std, mod] = composition(d, i);
    expect(std!.total).toBeCloseTo(d.result.performance.demand.std[i]!, 6);
    expect(mod!.total).toBeCloseTo(d.result.performance.demand.mod![i]!, 6);
  });
  it('RN por método en kgf coincide con la RN de diseño', () => {
    const rows = dragRows(d, 'std');
    expect(rows[0]![d.result.drag.design_method]).toBeCloseTo(d.result.drag.rn.std[0]!, 6);
  });
  it('ventana factible y filas de tiro', () => {
    const w = perfWindow(d, 'fixed_pitch', 'std');
    expect(feasibleWindow(w)).toEqual({ from: 1, to: w!.max_speed_kn });
    expect(pullRows(d, 'fixed_pitch')[0]).toMatchObject({ speed: 1, available: 1395 });
  });
  it('sin variante modificada no hay series «mod»', () => {
    expect(spreadRows(dx)[0]!.dpaMod).toBeNull();
    expect(composition(dx, 0)).toHaveLength(1);
  });
});

describe('KPI del cable', () => {
  it('corregido: cumple la rotura', () => {
    expect(warpMeetsBreakingLoad(d)).toBe(true);
    expect(tiles(d).find((t) => t.key === 'warp_selected')!.badge).toMatchObject({ tone: 'good' });
  });
  it('Excel: cable de 12 mm no cumple (errata warp_undersized)', () => {
    expect(warpMeetsBreakingLoad(dx)).toBe(false);
    const t = tiles(dx).find((x) => x.key === 'warp_selected')!;
    expect(t.badge).toMatchObject({ tone: 'crit', text: expect.stringMatching(/No cumple/) });
    expect(t.value).toMatch(/12 mm/);
  });
});
