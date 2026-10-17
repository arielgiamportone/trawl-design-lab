import { describe, expect, it } from 'vitest';
import type { NetSpec } from '../api/client';
import netStd from '../test/fixtures/net_std.json';
import { buildRequest, DEFAULT_CASE, sanitizeCase } from './model';

const spec = { ...(netStd as unknown as NetSpec), id: 'fao_a3_standard_s0.80' };

describe('red escalada en el caso', () => {
  it('sanitizeCase acepta una red escalada válida y descarta la corrupta', () => {
    const ok = sanitizeCase({
      ...DEFAULT_CASE,
      scaled: { s: 0.8, std: spec, mod: null, speed: 3 },
    });
    expect(ok.scaled?.s).toBe(0.8);
    expect(sanitizeCase({ ...DEFAULT_CASE, scaled: { s: 'x', std: spec } }).scaled).toBeNull();
    expect(sanitizeCase({ ...DEFAULT_CASE, scaled: { s: 1, std: {} } }).scaled).toBeNull();
    expect(sanitizeCase({ net: 'fao_a3_standard' }).scaled).toBeNull();
  });

  it('buildRequest envía la red escalada en línea', () => {
    const state = { ...DEFAULT_CASE, scaled: { s: 0.8, std: spec, mod: null, speed: null } };
    const { request } = buildRequest(state, [], { std: spec });
    expect((request.net as NetSpec).id).toBe('fao_a3_standard_s0.80');
    expect(request.net_modified).toBe('fao_a3_modified'); // la modificada no se escaló
  });
});
