import { describe, expect, it } from 'vitest';
import sim from '../test/fixtures/simulate_geometry.json';
import {
  buildBuffers,
  cameraPosition,
  isSimGeometry,
  RAMP_LIGHT,
  rampColor,
  tensionOf,
  tensionRange,
  type SimGeometry,
} from './sim3d';

const g = sim.results[0] as unknown as SimGeometry;

describe('vista 3D de la simulación', () => {
  it('reconoce resultados con geometría', () => {
    expect(isSimGeometry(g)).toBe(true);
    expect(isSimGeometry({ speed_kn: 3 })).toBe(false);
  });

  it('tensión del triángulo = mayor dirección; escala hasta el percentil 95', () => {
    expect(tensionOf([3, -7])).toBe(7);
    expect(tensionOf(-2)).toBe(2);
    const vals = Array.from({ length: 100 }, (_, i) => i);
    expect(tensionRange(vals)).toEqual([0, 94]);
    expect(tensionRange([])).toEqual([0, 1]);
    expect(tensionRange([0, 0])).toEqual([0, 1]);
  });

  it('la rampa va del primer al último paso e interpola', () => {
    const near = (a: number[], hex: string) => {
      const n = parseInt(hex.slice(1), 16);
      const rgb = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((x) => x / 255);
      a.forEach((v, i) => expect(v).toBeCloseTo(rgb[i] as number, 6));
    };
    near(rampColor(0, RAMP_LIGHT), RAMP_LIGHT[0] as string);
    near(rampColor(1, RAMP_LIGHT), RAMP_LIGHT[RAMP_LIGHT.length - 1] as string);
    near(rampColor(5, RAMP_LIGHT), RAMP_LIGHT[RAMP_LIGHT.length - 1] as string);
    near(rampColor(NaN, RAMP_LIGHT), RAMP_LIGHT[0] as string);
  });

  it('buffers: 9 valores por triángulo, ejes (x, z, y) y relingas aparte del aparejo', () => {
    const b = buildBuffers(g, RAMP_LIGHT);
    expect(b.positions.length).toBe(g.triangles.length * 9);
    expect(b.colors.length).toBe(b.positions.length);
    const [n0] = g.triangles[0] as [number, number, number];
    const node = g.nodes[n0] as [number, number, number];
    expect(Array.from(b.positions.slice(0, 3))).toEqual(
      [node[0], node[2], node[1]].map((v) => Math.fround(v)),
    );
    const ropeBars = g.bar_kind.filter((k) => k === 'headrope' || k === 'footrope').length;
    expect(b.lines.ropes.length).toBe(ropeBars * 6);
    expect(b.lines.rigging.length).toBe((g.bars.length - ropeBars) * 6);
    expect(b.floats.length).toBe(g.float_nodes.length * 3);
    expect(b.radius).toBeGreaterThan(1);
    // el encuadre sigue al paño: la altura del centro está entre el fondo y la lima
    expect(b.center[1]).toBeGreaterThanOrEqual(0);
    expect(b.center[1]).toBeLessThan(g.av_m + 1);
  });

  it('vistas estándar alrededor del centro', () => {
    const c: [number, number, number] = [10, 1, 0];
    expect(cameraPosition('plan', c, 5)[1]).toBeGreaterThan(c[1]);
    expect(cameraPosition('front', c, 5)[0]).toBeLessThan(c[0]);
    expect(cameraPosition('profile', c, 5)[2]).toBeGreaterThan(c[2]);
  });
});
