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
    expect(byKey(2).opening?.value).toBe('13,1 m × 1,98 m');
  });
});
