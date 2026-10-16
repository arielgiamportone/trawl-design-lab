import { describe, expect, it } from 'vitest';
import { fmt, fmtDelta, fmtFixed, fmtPct, parseNumber, toInput } from './format';

describe('fmt (es-AR)', () => {
  it('usa coma decimal y punto de miles', () => {
    expect(fmt(1592.17048)).toBe('1.592,2');
    expect(fmt(28.698)).toBe('28,698');
    expect(fmt(0.02127777)).toBe('0,02128');
  });
  it('enteros sin decimales', () => {
    expect(fmt(9217)).toBe('9.217');
    expect(fmt(12)).toBe('12');
  });
  it('nulos y textos', () => {
    expect(fmt(null)).toBe('—');
    expect(fmt(undefined)).toBe('—');
    expect(fmt(Number.NaN)).toBe('—');
    expect(fmt('steel_6x19')).toBe('steel_6x19');
  });
  it('decimales fijos, porcentajes y deltas', () => {
    expect(fmtFixed(2.3884628, 2)).toBe('2,39');
    expect(fmtPct(11.71)).toBe('+11,7 %');
    expect(fmtPct(-5.555)).toBe('-5,6 %');
    expect(fmtDelta(-1)).toBe('−1');
    expect(fmtDelta(3.36)).toBe('+3,36');
  });
});

describe('parseNumber', () => {
  it.each([
    ['1,5', 1.5],
    ['1.5', 1.5],
    [' 2 ', 2],
    ['1.234,5', 1234.5],
    ['-0,3', -0.3],
    ['1e3', 1000],
  ])('%s → %s', (text, n) => {
    expect(parseNumber(text)).toBe(n);
  });
  it.each(['', 'abc', '1,2,3', '--1', '1..2'])('rechaza %j', (text) => {
    expect(parseNumber(text)).toBeNull();
  });
  it('toInput usa coma', () => {
    expect(toInput(1.37)).toBe('1,37');
    expect(toInput(null)).toBe('');
  });
});
