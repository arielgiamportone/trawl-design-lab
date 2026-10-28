import { describe, expect, it } from 'vitest';
import { asDesignData } from '../api/result';
import design from '../test/fixtures/design.json';
import type { DesignResponseRaw } from '../api/client';
import { assess, interp, NM_M, overall } from './verdict';

const d = asDesignData(design as unknown as DesignResponseRaw);
const byKey = (speed: number) => Object.fromEntries(assess(d, speed).map((c) => [c.key, c]));

describe('diagnóstico del modo guiado', () => {
  it('interpola linealmente y devuelve null fuera de rango', () => {
    expect(interp([1, 2], [10, 20], 1.5)).toBe(15);
    expect(interp([1, 2], [10, 20], 2)).toBe(20);
    expect(interp([1, 2], [10, 20], 3)).toBeNull();
    expect(interp([1, 2], [10, null], 1.5)).toBeNull();
  });

  it('a 1,5 kn el tiro sobra y el diseño es viable', () => {
    const c = byKey(1.5);
    // disponible 1342,5 kgf vs demanda 691,8 kgf (fixture del caso FAO A-3)
    expect(c.pull?.tone).toBe('ok');
    expect(c.pull?.value).toBe('Sí: sobra 94 %');
    expect(c.max_speed?.tone).toBe('ok');
    expect(c.max_speed?.value).toBe('2,27 kn');
    expect(c.warp?.tone).toBe('ok');
    expect(overall(assess(d, 1.5))).toBe('ok');
  });

  it('cerca del límite avisa y por encima marca el problema', () => {
    expect(byKey(2.2).pull?.tone).toBe('warn');
    const c = byKey(3);
    expect(c.pull?.tone).toBe('crit');
    expect(c.pull?.value).toMatch(/^No: falta 782 kgf$/);
    expect(c.max_speed?.tone).toBe('crit');
    expect(overall(assess(d, 3))).toBe('crit');
  });

  it('área barrida = ancho de la boca × velocidad × 1852 m', () => {
    const ah = d.summary.horizontal_opening_m as number;
    const expected = Math.round((ah * 2 * NM_M) / 1000);
    expect(byKey(2).swept?.value).toBe(`${expected} mil m²/h`);
    expect(byKey(2).opening?.value).toBe('AH 13,1 m × AV 1,98 m');
    expect(byKey(2).cfp_av).toBeUndefined();
  });

  it('tangones: aberturas de cada red, DP, límite de AV de la Res. CFP 7/2018 y dos bocas', () => {
    const shrimp = (av: number) => ({
      ...d,
      summary: {
        ...d.summary,
        vertical_opening_m: av,
        horizontal_opening_m: 14.4,
        door_spread_m: 17.5,
        n_nets: 2,
        cfp_av_limit_m: 1.5,
      },
    });
    const c = Object.fromEntries(assess(shrimp(1.42), 2).map((x) => [x.key, x]));
    expect(c.opening?.title).toBe('Boca de cada red (2 redes)');
    expect(c.opening?.value).toBe('AH 14,4 m × AV 1,42 m');
    expect(c.opening?.why).toContain('(DP): 17,5 m');
    expect(c.cfp_av?.tone).toBe('ok');
    expect(c.cfp_av?.value).toBe('AV 1,42 m ≤ 1,5 m');
    expect(c.swept?.value).toBe(`${Math.round((2 * 14.4 * 2 * NM_M) / 1000)} mil m²/h`);
    const over = assess(shrimp(1.58), 2);
    expect(over.find((x) => x.key === 'cfp_av')?.tone).toBe('crit');
    expect(over.find((x) => x.key === 'cfp_av')?.value).toBe('AV 1,58 m: supera 1,5 m');
    expect(overall(over)).toBe('crit');
  });
});
