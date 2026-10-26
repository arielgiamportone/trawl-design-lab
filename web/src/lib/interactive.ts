/**
 * Editor interactivo sobre el plano: conversión de arrastres y teclas en mallas, y forma
 * «fantasma» del panel mientras se arrastra.
 *
 * La geometría viene de ``POST /design/layout`` en modo ``schematic`` (malla estirada), donde el
 * ancho de un borde es ``mallas · mallero / 1000`` y el alto ``N · mallero / 1000`` [m]: un
 * arrastre de Δ metros equivale exactamente a ``Δ · 1000 / mallero`` mallas.
 */
import type { components } from '../api/schema';
import { msg } from '../i18n';
import { localized } from './labels';
import { PANEL_FIELDS, type PanelField } from './panels';

export type LayoutShape = components['schemas']['LayoutShape'];
export type LayoutPlane = components['schemas']['LayoutPlane'];
export type LayoutResponse = components['schemas']['LayoutResponse'];
export type Point = [number, number];

/** Tirador: borde inferior (alto N), esquina inferior (borde bolsa) o superior (borde boca). */
export type Handle = 'depth' | 'bottom' | 'top';

export const HANDLE_FIELD: Record<Handle, PanelField> = {
  depth: 'meshes_depth',
  bottom: 'meshes_bottom',
  top: 'meshes_top',
};

export const HANDLE_LABEL: Record<Handle, string> = localized(() => msg().labels.handles);

function startValue(shape: LayoutShape, handle: Handle): number {
  if (handle === 'depth') return shape.meshes_depth;
  return handle === 'bottom' ? shape.meshes_bottom : shape.meshes_top;
}

/** Límite inferior entero del campo (``meshes_depth`` ≥ 1, bordes ≥ 0). */
function minOf(field: PanelField): number {
  const r = PANEL_FIELDS[field];
  return r.exclusiveMin ? Math.floor(r.min) + 1 : Math.ceil(r.min);
}

/**
 * Mallas resultantes de arrastrar ``handle`` (dx, dy) metros. Las esquinas se toman en el lado
 * exterior: hacia afuera agranda. Los paneles centrales son simétricos, así que el ancho cambia el
 * doble del desplazamiento.
 */
export function dragMeshes(shape: LayoutShape, handle: Handle, dx: number, dy: number): number {
  const perMeter = 1000 / shape.mesh_mm;
  let delta: number;
  if (handle === 'depth') delta = dy * perMeter;
  else {
    const outward = shape.side === 'left' ? -dx : dx;
    delta = outward * perMeter * (shape.side === 'center' ? 2 : 1);
  }
  const value = Math.round(startValue(shape, handle) + delta);
  return Math.max(minOf(HANDLE_FIELD[handle]), value);
}

/** Polígono del panel con el campo del tirador en ``value`` mallas (vista previa del arrastre). */
export function ghostPoints(shape: LayoutShape, handle: Handle, value: number): Point[] {
  const m = shape.mesh_mm / 1000;
  let [yTop, yBottom] = [shape.y_top, shape.y_bottom];
  let xTop: Point = [shape.x_top[0], shape.x_top[1]];
  let xBottom: Point = [shape.x_bottom[0], shape.x_bottom[1]];
  const resize = (x: Point, w: number): Point => {
    if (shape.side === 'center') {
      const mid = (x[0] + x[1]) / 2;
      return [mid - w / 2, mid + w / 2];
    }
    // se mueve la esquina exterior; la interior queda fija
    return shape.side === 'left' ? [x[1] - w, x[1]] : [x[0], x[0] + w];
  };
  if (handle === 'depth') yBottom = yTop + value * m;
  else if (handle === 'bottom') xBottom = resize(xBottom, value * m);
  else xTop = resize(xTop, value * m);
  [yTop, yBottom] = [Math.min(yTop, yBottom), Math.max(yTop, yBottom)];
  return [
    [xTop[0], yTop],
    [xTop[1], yTop],
    [xBottom[1], yBottom],
    [xBottom[0], yBottom],
  ];
}

/** Posición del tirador en el polígono (borde inferior al medio; esquinas del lado exterior). */
export function handlePoint(shape: LayoutShape, handle: Handle): Point {
  const outer = shape.side === 'left' ? 0 : 1;
  if (handle === 'depth') return [(shape.x_bottom[0] + shape.x_bottom[1]) / 2, shape.y_bottom];
  if (handle === 'bottom') return [shape.x_bottom[outer], shape.y_bottom];
  return [shape.x_top[outer], shape.y_top];
}

export interface Nudge {
  field: PanelField;
  value: number;
}

/**
 * Ajuste por teclado del panel seleccionado: ↑/↓ alto N (↓ alarga), ←/→ borde hacia la bolsa
 * (→ agranda; ±2 en paneles centrales, que son simétricos). Shift multiplica por 10.
 */
export function keyNudge(
  shape: LayoutShape,
  current: { depth: number; bottom: number },
  key: string,
  shift: boolean,
): Nudge | null {
  const k = shift ? 10 : 1;
  if (key === 'ArrowDown' || key === 'ArrowUp') {
    const v = current.depth + (key === 'ArrowDown' ? k : -k);
    return { field: 'meshes_depth', value: Math.max(minOf('meshes_depth'), v) };
  }
  if (key === 'ArrowRight' || key === 'ArrowLeft') {
    const step = (shape.side === 'center' ? 2 : 1) * k;
    const v = current.bottom + (key === 'ArrowRight' ? step : -step);
    return { field: 'meshes_bottom', value: Math.max(minOf('meshes_bottom'), v) };
  }
  return null;
}

/** Disposición de los planos lado a lado: desplazamiento x de cada uno y recuadro total [m]. */
export function arrangePlanes(planes: LayoutPlane[], gap: number) {
  let x = 0;
  const offsets: Record<string, number> = {};
  let ymin = Infinity;
  let ymax = -Infinity;
  for (const p of planes) {
    const [x0, y0, x1, y1] = p.bbox;
    offsets[p.plane] = x - x0;
    x += x1 - x0 + gap;
    ymin = Math.min(ymin, y0);
    ymax = Math.max(ymax, y1);
  }
  const width = Math.max(0, x - gap);
  return { offsets, bbox: [0, ymin, width, ymax] as [number, number, number, number] };
}

export const pointsAttr = (pts: readonly (readonly [number, number])[], dx = 0) =>
  pts.map(([x, y]) => `${(x + dx).toFixed(4)},${y.toFixed(4)}`).join(' ');
