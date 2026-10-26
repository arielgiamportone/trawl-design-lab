import { describe, expect, it } from 'vitest';
import { CONVERSIONS, fmtU, getUnits, setUnits, toCanonical, toDisplay, unitLabel } from './units';

describe('unidades', () => {
  it('métrico por defecto: sin conversión', () => {
    expect(getUnits()).toBe('metric');
    expect(toDisplay(10, 'm')).toBe(10);
    expect(unitLabel('kgf')).toBe('kgf');
    expect(fmtU(12.5, 'm')).toBe('12,5 m');
  });

  it('imperial: conversiones conocidas', () => {
    setUnits('imperial');
    expect(toDisplay(1, 'm')).toBeCloseTo(3.28084, 5);
    expect(toDisplay(1, 'kgf')).toBeCloseTo(2.20462, 5);
    expect(toDisplay(1, 'L')).toBeCloseTo(0.264172, 6);
    expect(toDisplay(1, '$/L')).toBeCloseTo(3.785412, 6);
    expect(toDisplay(25.4, 'mm')).toBeCloseTo(1, 9);
    expect(toDisplay(3, 'kn')).toBe(3);
    expect(unitLabel('m')).toBe('ft');
    expect(unitLabel('kn')).toBe('kn');
    expect(fmtU(120, 'mesh_mm')).toBe('120 mm (4,72 in)');
    expect(fmtU(10, 'm', { digits: 1 })).toBe('32,8 ft');
  });

  it('ida y vuelta sin pérdida para todas las magnitudes', () => {
    for (const unit of Object.keys(CONVERSIONS)) {
      const shown = toDisplay(123.456, unit, 'imperial');
      expect(toCanonical(shown, unit, 'imperial'), unit).toBeCloseTo(123.456, 9);
    }
  });
});
