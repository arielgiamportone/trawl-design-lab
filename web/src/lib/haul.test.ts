import { describe, expect, it } from 'vitest';
import type { DesignRequest, HaulResponse } from '../api/client';
import haul from '../test/fixtures/haul.json';
import { catchSteps, DEFAULT_HAUL, haulRequest, haulRows, haulSummary, niceTicks } from './haul';

const r = haul as unknown as HaulResponse;

describe('lance progresivo', () => {
  it('marcas redondas del eje', () => {
    expect(niceTicks(511.2, 1204.16)).toEqual([400, 600, 800, 1000, 1200, 1400]);
    expect(niceTicks(42.4, 46.0)).toEqual([42, 43, 44, 45, 46]);
    expect(niceTicks(1.86, 1.93)).toEqual([1.86, 1.88, 1.9, 1.92, 1.94]);
    expect(niceTicks(5, 5).length).toBeGreaterThan(1);
  });

  it('reparte las capturas de 0 al máximo, redondeadas a 10 kg', () => {
    expect(catchSteps(1000, 4)).toEqual([0, 330, 670, 1000]);
    expect(catchSteps(500, 1)).toEqual([0, 500]);
    expect(catchSteps(-5, 3)).toEqual([0, 0, 0]);
    expect(catchSteps(1000, 20)).toHaveLength(8);
  });

  it('arma el pedido con el tipo de captura y el fondo', () => {
    const base = { net: 'fao_a3_standard', vessel: 'fao_a3_180hp', compat: 'corrected' };
    const req = haulRequest(base as DesignRequest, {
      ...DEFAULT_HAUL,
      catchType: 'crustacean',
      seabed: 'mud',
      maxCatchKg: 600,
      steps: 3,
    });
    expect(req.catches_kg).toEqual([0, 300, 600]);
    expect(req.scenario).toMatchObject({
      seabed: 'mud',
      catch_bulk_density: 850,
      catch_body_density: 1150,
      coupled_doors: true,
    });
    expect(req.vessel).toBe('fao_a3_180hp');
    expect(req.include_geometry).toBe(true);
  });

  it('filas y resumen: con captura bajan los portones y sube el tiro', () => {
    const rows = haulRows(r);
    expect(rows.map((x) => x.catchKg)).toEqual([0, 500, 1000]);
    const [a, , c] = rows as [(typeof rows)[0], (typeof rows)[0], (typeof rows)[0]];
    expect(c.doorSpread).toBeLessThan(a.doorSpread as number);
    expect(c.pull).toBeGreaterThan(a.pull as number);
    expect(a.catchLength).toBeNull();
    expect(c.catchLength).toBeGreaterThan(0);
    expect(c.friction).toBeGreaterThan(0);
    const text = haulSummary(rows);
    expect(text).toMatch(
      /^De 0 a 1\.000 kg de captura, la separación de portones baja 3,4 m \(−?-?7 %\)/,
    );
    expect(text).toContain('el tiro en el buque sube 73 kgf');
    expect(haulSummary(rows.slice(0, 1))).toBeNull();
  });
});
