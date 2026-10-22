import { describe, expect, it } from 'vitest';
import layout from '../test/fixtures/layout.json';
import {
  arrangePlanes,
  dragMeshes,
  ghostPoints,
  handlePoint,
  keyNudge,
  type LayoutResponse,
  type LayoutShape,
} from './interactive';

const lay = layout as unknown as LayoutResponse;
const shape = (id: string, side: string): LayoutShape => {
  const s = lay.planes.flatMap((p) => p.shapes).find((x) => x.id === id && x.side === side);
  if (!s) throw new Error(`${id} ${side}`);
  return s;
};

describe('editor interactivo: arrastre → mallas', () => {
  const cRight = shape('C', 'right'); // 57 → 117 mallas, N 120, 80 mm
  const cLeft = shape('C', 'left');
  const g = shape('G', 'center'); // 372 → 162, N 210, 60 mm

  it('el alto sigue al desplazamiento vertical (Δ·1000/mallero)', () => {
    expect(dragMeshes(cRight, 'depth', 0, 0)).toBe(120);
    expect(dragMeshes(cRight, 'depth', 0, 0.8)).toBe(130); // 0,8 m / 80 mm = 10 mallas
    expect(dragMeshes(cRight, 'depth', 5, -100)).toBe(1); // nunca menos de 1
  });

  it('las esquinas crecen hacia afuera; los centrales cuentan el doble', () => {
    expect(dragMeshes(cRight, 'bottom', 0.4, 0)).toBe(122);
    expect(dragMeshes(cLeft, 'bottom', -0.4, 0)).toBe(122);
    expect(dragMeshes(cLeft, 'bottom', 0.4, 0)).toBe(112);
    expect(dragMeshes(g, 'bottom', 0.3, 0)).toBe(172); // 2 · 0,3 m / 60 mm
    expect(dragMeshes(g, 'top', -50, 0)).toBe(0);
  });

  it('la forma fantasma respeta ancho = mallas·mallero y alto = N·mallero', () => {
    const [tl, , br, bl] = ghostPoints(cRight, 'depth', 130) as [number, number][] as [
      [number, number],
      [number, number],
      [number, number],
      [number, number],
    ];
    expect(br[1] - tl[1]).toBeCloseTo(130 * 0.08, 9);
    const wide = ghostPoints(g, 'bottom', 172);
    const w = (wide[2] as [number, number])[0] - (wide[3] as [number, number])[0];
    expect(w).toBeCloseTo(172 * 0.06, 9);
    // el lado interior del ala izquierda queda fijo
    const left = ghostPoints(cLeft, 'bottom', 130);
    expect((left[2] as [number, number])[0]).toBeCloseTo(cLeft.x_bottom[1], 9);
    expect(bl[0]).toBeCloseTo(cRight.x_bottom[0], 9);
  });

  it('tiradores en el borde inferior y en las esquinas exteriores', () => {
    expect(handlePoint(cLeft, 'bottom')).toEqual([cLeft.x_bottom[0], cLeft.y_bottom]);
    expect(handlePoint(cRight, 'top')).toEqual([cRight.x_top[1], cRight.y_top]);
  });

  it('teclado: flechas con paso 1 (2 en centrales) y Shift ×10', () => {
    const cur = { depth: 120, bottom: 117 };
    expect(keyNudge(cRight, cur, 'ArrowDown', false)).toEqual({
      field: 'meshes_depth',
      value: 121,
    });
    expect(keyNudge(cRight, cur, 'ArrowUp', true)).toEqual({ field: 'meshes_depth', value: 110 });
    expect(keyNudge(g, { depth: 210, bottom: 162 }, 'ArrowRight', false)).toEqual({
      field: 'meshes_bottom',
      value: 164,
    });
    expect(keyNudge(g, cur, 'Enter', false)).toBeNull();
  });

  it('dispone los planos lado a lado con separación', () => {
    const { offsets, bbox } = arrangePlanes(lay.planes, 2);
    const [upper, lower] = lay.planes as [LayoutResponse['planes'][0], LayoutResponse['planes'][0]];
    expect(offsets.upper).toBeCloseTo(-upper.bbox[0], 9);
    const wU = upper.bbox[2] - upper.bbox[0];
    expect(offsets.lower).toBeCloseTo(wU + 2 - lower.bbox[0], 9);
    expect(bbox[2]).toBeCloseTo(wU + 2 + lower.bbox[2] - lower.bbox[0], 9);
  });
});
