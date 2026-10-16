import { describe, expect, it } from 'vitest';
import { diffSummaries } from './diff';

describe('diffSummaries', () => {
  const a = {
    net_id: 'fao_a3_standard',
    headrope_m: 28.698,
    float_count: 12,
    max_speed_kn: 2.5,
    x: 0,
  };
  const b = { net_id: 'otra', headrope_m: 32.058, float_count: 12, max_speed_kn: 2.49, x: 1 };
  const rows = diffSummaries(a, b);
  const row = (k: string) => rows.find((r) => r.key === k)!;

  it('calcula diferencia absoluta y porcentual', () => {
    expect(row('headrope_m').abs).toBeCloseTo(3.36);
    expect(row('headrope_m').pct).toBeCloseTo(11.708, 2);
    expect(row('headrope_m').significant).toBe(true);
    expect(row('headrope_m').label).toBe('Lima');
    expect(row('headrope_m').unit).toBe('m');
  });
  it('marca sin cambios', () => {
    expect(row('float_count').changed).toBe(false);
    expect(row('float_count').significant).toBe(false);
  });
  it('cambios menores al umbral no se resaltan', () => {
    expect(row('max_speed_kn').changed).toBe(true);
    expect(row('max_speed_kn').significant).toBe(false);
  });
  it('A = 0 → sin porcentaje pero significativo', () => {
    expect(row('x').pct).toBeNull();
    expect(row('x').significant).toBe(true);
  });
  it('textos distintos cambian', () => {
    expect(row('net_id').changed).toBe(true);
    expect(row('net_id').abs).toBeNull();
  });
});
