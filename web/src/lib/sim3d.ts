/**
 * Datos para la vista 3D de la forma simulada (``POST /simulate`` con ``include_geometry``):
 * buffers de triángulos coloreados por la tensión del hilo y líneas del aparejo.
 *
 * Ejes: la simulación usa ``x`` hacia popa, ``y`` lateral y ``z`` sobre el fondo; three.js usa
 * ``y`` hacia arriba, así que se pasa (x, y, z)_sim → (x, z, y)_three.
 */

export interface SimGeometry {
  speed_kn: number;
  nodes: [number, number, number][];
  triangles: [number, number, number][];
  /** Tensión del hilo por triángulo [N] (dos direcciones de malla). */
  twine_tension_n: (number | number[])[];
  bars: [number, number][];
  bar_kind: string[];
  float_nodes: number[];
  ah_m: number;
  av_m: number;
}

/** Rampa secuencial azul (claro → oscuro) de la paleta de referencia. */
export const RAMP_LIGHT = ['#b7d3f6', '#86b6ef', '#5598e7', '#2a78d6', '#1c5cab', '#104281'];
/** En modo oscuro la tensión baja se funde con el fondo (oscuro) y la alta resalta (claro). */
export const RAMP_DARK = ['#184f95', '#1c5cab', '#2a78d6', '#5598e7', '#86b6ef', '#cde2fb'];

export function isSimGeometry(r: unknown): r is SimGeometry {
  const g = r as Partial<SimGeometry> | null;
  return !!g && Array.isArray(g.nodes) && Array.isArray(g.triangles) && g.nodes.length > 0;
}

/** Tensión representativa de un triángulo: la mayor de sus dos direcciones de malla. */
export function tensionOf(t: number | number[]): number {
  return Array.isArray(t) ? Math.max(0, ...t.map((x) => Math.abs(x))) : Math.abs(t);
}

/** Escala de color: de 0 al percentil 95 (un nudo muy cargado no aplana el resto). */
export function tensionRange(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const sorted = [...values].sort((a, b) => a - b);
  const p95 = sorted[Math.min(sorted.length - 1, Math.floor(0.95 * (sorted.length - 1)))] ?? 1;
  return [0, p95 > 0 ? p95 : 1];
}

function hexToRgb(hex: string): [number, number, number] {
  const n = parseInt(hex.slice(1), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

/** Color de la rampa en ``t`` ∈ [0, 1] (interpolación lineal entre pasos), RGB 0–1. */
export function rampColor(t: number, ramp: readonly string[]): [number, number, number] {
  const x = Math.min(1, Math.max(0, Number.isFinite(t) ? t : 0)) * (ramp.length - 1);
  const i = Math.min(ramp.length - 2, Math.floor(x));
  const f = x - i;
  const a = hexToRgb(ramp[i] as string);
  const b = hexToRgb(ramp[i + 1] as string);
  return [a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, a[2] + (b[2] - a[2]) * f];
}

const toThree = (p: [number, number, number]): [number, number, number] => [p[0], p[2], p[1]];

export interface Buffers {
  /** Triángulos sin índice (3 vértices × 3 coordenadas por triángulo). */
  positions: Float32Array;
  /** Color por vértice (el del triángulo), RGB 0–1. */
  colors: Float32Array;
  /** Segmentos por tipo: ``headrope``/``footrope`` resaltados; el resto, aparejo. */
  lines: Record<'ropes' | 'rigging', Float32Array>;
  floats: Float32Array;
  range: [number, number];
  center: [number, number, number];
  radius: number;
}

export function buildBuffers(g: SimGeometry, ramp: readonly string[]): Buffers {
  const tensions = g.twine_tension_n.map(tensionOf);
  const range = tensionRange(tensions);
  const positions = new Float32Array(g.triangles.length * 9);
  const colors = new Float32Array(g.triangles.length * 9);
  g.triangles.forEach((tri, k) => {
    const c = rampColor((tensions[k] ?? 0) / range[1], ramp);
    tri.forEach((n, j) => {
      const p = toThree(g.nodes[n] ?? [0, 0, 0]);
      positions.set(p, k * 9 + j * 3);
      colors.set(c, k * 9 + j * 3);
    });
  });
  const ropes: number[] = [];
  const rigging: number[] = [];
  g.bars.forEach(([a, b], k) => {
    const kind = g.bar_kind[k] ?? '';
    const target = kind === 'headrope' || kind === 'footrope' ? ropes : rigging;
    target.push(...toThree(g.nodes[a] ?? [0, 0, 0]), ...toThree(g.nodes[b] ?? [0, 0, 0]));
  });
  const floats = new Float32Array(g.float_nodes.flatMap((n) => toThree(g.nodes[n] ?? [0, 0, 0])));

  // El encuadre sigue al paño (no a las patentes, que llegan hasta los portones).
  const netNodes = new Set(g.triangles.flat());
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  for (const i of netNodes) {
    const p = toThree(g.nodes[i] ?? [0, 0, 0]);
    for (let i = 0; i < 3; i++) {
      min[i] = Math.min(min[i] as number, p[i] as number);
      max[i] = Math.max(max[i] as number, p[i] as number);
    }
  }
  const center = [0, 1, 2].map((i) => ((min[i] as number) + (max[i] as number)) / 2) as [
    number,
    number,
    number,
  ];
  const radius =
    Math.hypot(...[0, 1, 2].map((i) => (max[i] as number) - (min[i] as number))) / 2 || 1;
  return {
    positions,
    colors,
    lines: { ropes: new Float32Array(ropes), rigging: new Float32Array(rigging) },
    floats,
    range,
    center,
    radius,
  };
}

export type CameraView = 'iso' | 'plan' | 'profile' | 'front';

/** Posición de la cámara (en coordenadas three.js) para una vista estándar. */
export function cameraPosition(
  view: CameraView,
  center: [number, number, number],
  radius: number,
): [number, number, number] {
  const d = radius * 2.2;
  const [cx, cy, cz] = center;
  switch (view) {
    case 'plan':
      return [cx, cy + d, cz + 0.001];
    case 'profile':
      return [cx, cy, cz + d];
    case 'front':
      return [cx - d, cy, cz];
    default:
      return [cx - d * 0.6, cy + d * 0.45, cz + d * 0.65];
  }
}
