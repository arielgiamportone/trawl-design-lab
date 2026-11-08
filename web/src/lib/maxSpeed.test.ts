import { describe, expect, it } from 'vitest';
import { asDesignData, type DesignData } from '../api/result';
import type { DesignResponseRaw } from '../api/client';
import { setLang } from '../i18n';
import design from '../test/fixtures/design.json';
import { tiles } from './kpis';
import { beyondGrid, maxSpeedText, perfWindow, designPropeller } from './series';
import { assess } from './verdict';

/** Caso con tiro de sobra en toda la grilla (como el Angelescu con la red de IAT 151/18). */
function beyond(): DesignData {
  const d = asDesignData(JSON.parse(JSON.stringify(design)) as DesignResponseRaw);
  for (const w of Object.values(d.result.performance.windows)) {
    w.available_kgf = w.demand_kgf.map((x) => (x ?? 0) * 3);
    w.margin_kgf = w.demand_kgf.map((x) => (x ?? 0) * 2);
    w.feasible = w.speeds_kn.map(() => true);
    w.feasible_speeds_kn = [...w.speeds_kn];
    w.max_speed_kn = w.speeds_kn[w.speeds_kn.length - 1]!;
    w.beyond_grid = true;
  }
  d.summary.max_speed_kn = 5;
  return d;
}

describe('velocidad máxima fuera de la grilla (Fase 20.7)', () => {
  it('la ventana del fixture tiene cruce y no queda fuera de la grilla', () => {
    setLang('es');
    const d = asDesignData(design as unknown as DesignResponseRaw);
    const w = perfWindow(d, designPropeller(d), 'std');
    expect(beyondGrid(w)).toBe(false);
    expect(maxSpeedText(w)).not.toMatch(/^>/);
    const tile = tiles(d).find((t) => t.key === 'max_speed_kn')!;
    expect(tile.value).not.toMatch(/^>/);
  });

  it('con tiro de sobra muestra «> 5 kn (fuera de la grilla)», no 5 kn', () => {
    setLang('es');
    const d = beyond();
    const w = perfWindow(d, designPropeller(d), 'std');
    expect(beyondGrid(w)).toBe(true);
    // Sin el campo de la API, se deduce de «feasible».
    expect(beyondGrid({ ...w!, beyond_grid: undefined })).toBe(true);
    expect(maxSpeedText(w)).toBe('> 5');
    const tile = tiles(d).find((t) => t.key === 'max_speed_kn')!;
    expect(tile.value).toBe('> 5');
    expect(tile.sub).toBe('modificada: > 5 kn');
    const single = { ...d, case: { ...d.case, net_modified: null } };
    const sub = tiles(single).find((t) => t.key === 'max_speed_kn')!.sub;
    expect(sub).toMatch(/fuera de la grilla/);
    expect(sub).not.toMatch(/tiro disponible = resistencia/);
    const check = assess(d, 3).find((c) => c.key === 'max_speed')!;
    expect(check.value).toBe('> 5 kn (fuera de la grilla)');
    expect(check.why).toMatch(/más allá/);
  });

  it('en inglés', () => {
    setLang('en');
    const check = assess(beyond(), 3).find((c) => c.key === 'max_speed')!;
    expect(check.value).toBe('> 5 kn (beyond the grid)');
    setLang('es');
  });
});
