import { describe, expect, it } from 'vitest';
import type { DesignResponseRaw } from '../api/client';
import { asDesignData } from '../api/result';
import design from '../test/fixtures/design.json';
import { impactRows } from './impact';

const base = asDesignData(design as unknown as DesignResponseRaw);
const edited = asDesignData(
  structuredClone({
    ...design,
    summary: { ...design.summary, horizontal_opening_m: 14.0, solid_surface_m2: 41.0 },
  }) as unknown as DesignResponseRaw,
);

describe('impacto de las ediciones', () => {
  it('delta y tono según si el indicador mejora o empeora', () => {
    const rows = Object.fromEntries(
      impactRows(edited, base, 'std', 2).map((r) => [r.metric.key, r]),
    );
    expect(rows.ah?.delta).toBeCloseTo(14 - 13.105879, 5);
    expect(rows.ah?.tone).toBe('good');
    expect(rows.ss?.tone).toBe('neutral');
    expect(rows.rn?.now).toBeCloseTo(866.9, 0); // RN a 2 kn
    expect(rows.max_speed?.delta).toBe(0);
  });

  it('la variante modificada sólo muestra RN y velocidad máxima', () => {
    const keys = impactRows(base, base, 'mod', 3).map((r) => r.metric.key);
    expect(keys).toEqual(['rn', 'max_speed']);
  });
});
