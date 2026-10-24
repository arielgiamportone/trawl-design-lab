import { describe, expect, it } from 'vitest';
import type { DesignRequest } from '../api/client';
import selectivity from '../test/fixtures/selectivity.json';
import {
  asVariants,
  clearOpenings,
  curveRows,
  DEFAULT_SEL,
  defaultTriangle,
  l50Text,
  maxPassing,
  meshAt,
  openFraction,
  patchKnots,
  selectivityRequest,
  type SelCurve,
} from './selectivity';

const round = { height: 0.1, width: 0.1, compression: 1, unit: 'cm' };

describe('prueba de paso', () => {
  it('una sección circular pasa por una malla cuadrada de su mismo diámetro', () => {
    // Malla cuadrada de 22 mm de lado con hilo de 2 mm: luz de 20 mm → pasa L = 20 cm.
    const m = { openingDeg: 90, legIMm: 22, legJMm: 22, twineMm: 2 };
    expect(clearOpenings(m)).toEqual({ clearI: 20, clearJ: 20 });
    expect(maxPassing(m, round).length).toBeCloseTo(20, 6);
  });

  it('una malla cerrada retiene todo y abrirla deja pasar tallas mayores', () => {
    const at = (deg: number) =>
      maxPassing({ openingDeg: deg, legIMm: 50, legJMm: 50, twineMm: 2 }, round).length;
    expect(at(1)).toBe(0);
    expect(at(20)).toBeLessThan(at(40));
    expect(at(40)).toBeLessThan(at(90));
  });

  it('un pez aplanado pasa girado por una malla rómbica abierta', () => {
    const flat = { height: 0.4, width: 0.075, compression: 0.9, unit: 'cm' };
    const r = maxPassing({ openingDeg: 60, legIMm: 30, legJMm: 30, twineMm: 1 }, flat);
    expect(r.length).toBeGreaterThan(0);
    expect(r.theta).toBeGreaterThan(0);
  });

  it('fracción abierta y nudos del parche', () => {
    expect(openFraction(90)).toBeCloseTo(1);
    expect(openFraction(30)).toBeCloseTo(0.5);
    const k = patchKnots({ openingDeg: 90, legIMm: 10, legJMm: 10, twineMm: 1 }, 2);
    expect(k).toHaveLength(3);
    expect(k[2]?.[2]?.[0]).toBeCloseTo(20);
    expect(k[2]?.[2]?.[1]).toBeCloseTo(20);
  });
});

describe('pedido y respuesta', () => {
  it('arma el pedido con las variantes y el mallero', () => {
    const base = { net: 'fao_a3_standard', compat: 'corrected' } as DesignRequest;
    const req = selectivityRequest(base, { ...DEFAULT_SEL, meshMm: 120, variants: ['t90'] });
    expect(req.variants).toEqual([
      { orientation: 't90', mesh_mm: 120, hanging_ratio: null, label: null },
    ]);
    expect(req.scenario?.mesh_bending).toBe(true);
    expect(req.species).toEqual(['hake_hubbsi']);
  });

  it('curvas por variante, triángulo por defecto y forma de malla', () => {
    const vs = asVariants(selectivity as never);
    const { rows, keys } = curveRows(vs, 'cod');
    expect(keys).toEqual(['Rombo 40 mm', 'T90 40 mm']);
    expect(rows.length).toBe(vs[0]?.curves[1]?.lengths.length);
    const v = vs[0];
    if (!v) throw new Error('sin variante');
    const k = defaultTriangle(v);
    expect(k).not.toBeNull();
    const m = meshAt(v.geometry, v.frame, k as number);
    expect(m?.section).toMatch(/codend|extension/);
    expect(m?.legIMm).toBeGreaterThan(0);
  });

  it('L50 fuera del rango de tallas', () => {
    const c = {
      l50: null,
      lengths: [5, 10, 70],
      unit: 'cm',
      range: 'above',
    } as unknown as SelCurve;
    expect(l50Text(c, String)).toBe('> 70 cm');
    expect(l50Text({ ...c, range: 'below' }, String)).toBe('< 5 cm');
    expect(l50Text({ ...c, l50: 12.5 }, (v) => v.toFixed(1))).toBe('12.5 cm');
  });
});
