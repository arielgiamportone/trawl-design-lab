/** Edición de paneles: campos editables, validación y armado de la NetSpec en línea. */
import type { NetSpec, Panel } from '../api/client';
import { parseNumber } from './format';

export type PanelField =
  | 'mesh_mm'
  | 'twine_diameter_mm'
  | 'meshes_top'
  | 'meshes_bottom'
  | 'meshes_depth'
  | 'hanging_ratio'
  | 'count';

export interface FieldRule {
  label: string;
  short: string;
  unit: string;
  integer: boolean;
  /** Mínimo (inclusive salvo ``exclusiveMin``). */
  min: number;
  exclusiveMin?: boolean;
  max?: number;
}

export const PANEL_FIELDS: Record<PanelField, FieldRule> = {
  mesh_mm: {
    label: 'Mallero (malla estirada)',
    short: 'Mallero',
    unit: 'mm',
    integer: false,
    min: 0,
    exclusiveMin: true,
  },
  twine_diameter_mm: {
    label: 'Diámetro del hilo',
    short: 'Ø hilo',
    unit: 'mm',
    integer: false,
    min: 0,
    exclusiveMin: true,
  },
  meshes_top: {
    label: 'Mallas del borde hacia la boca',
    short: 'Mallas boca',
    unit: '',
    integer: true,
    min: 0,
  },
  meshes_bottom: {
    label: 'Mallas del borde hacia la bolsa',
    short: 'Mallas bolsa',
    unit: '',
    integer: true,
    min: 0,
  },
  meshes_depth: {
    label: 'Mallas de alto (N)',
    short: 'Mallas alto',
    unit: '',
    integer: true,
    min: 1,
  },
  hanging_ratio: {
    label: 'Coeficiente de armado U1',
    short: 'U1',
    unit: '',
    integer: false,
    min: 0,
    exclusiveMin: true,
    max: 1,
  },
  count: {
    label: 'Cantidad de paneles iguales',
    short: 'Cantidad',
    unit: '',
    integer: true,
    min: 1,
  },
};

export const PANEL_FIELD_ORDER: PanelField[] = [
  'mesh_mm',
  'twine_diameter_mm',
  'meshes_top',
  'meshes_bottom',
  'meshes_depth',
  'hanging_ratio',
  'count',
];

/** Orientación de la malla del paño (campo de texto, no numérico). */
export const ORIENTATION_FIELD = 'mesh_orientation';
export type MeshOrientation = 'diamond' | 't90' | 'square';
export const MESH_ORIENTATIONS: { id: MeshOrientation; label: string }[] = [
  { id: 'diamond', label: 'Rombo' },
  { id: 't90', label: 'T90 (girada 90°)' },
  { id: 'square', label: 'Cuadrada' },
];

/** Ediciones crudas (texto) por panel y campo. */
export type PanelEdits = Record<
  string,
  Partial<Record<PanelField | typeof ORIENTATION_FIELD, string>>
>;

const isOrientation = (v: string | undefined): v is MeshOrientation =>
  MESH_ORIENTATIONS.some((o) => o.id === v);

/** Orientación vigente del panel: la editada o la del preset (rombo por defecto). */
export function orientationOf(panel: Panel, edits: PanelEdits): MeshOrientation {
  const e = edits[panel.id]?.[ORIENTATION_FIELD];
  if (isOrientation(e)) return e;
  const v = (panel as { mesh_orientation?: string }).mesh_orientation;
  return isOrientation(v) ? v : 'diamond';
}

function presetOrientation(panel: Panel): MeshOrientation {
  const v = (panel as { mesh_orientation?: string }).mesh_orientation;
  return isOrientation(v) ? v : 'diamond';
}

/** Ediciones con la orientación del panel ``pid``; si vuelve a la del preset, se quita. */
export function withOrientation(
  edits: PanelEdits,
  panel: Panel,
  value: MeshOrientation,
): PanelEdits {
  const next: PanelEdits = {
    ...edits,
    [panel.id]: { ...edits[panel.id], [ORIENTATION_FIELD]: value },
  };
  if (value === presetOrientation(panel)) {
    const p = { ...next[panel.id] };
    delete p[ORIENTATION_FIELD];
    if (Object.keys(p).length === 0) delete next[panel.id];
    else next[panel.id] = p;
  }
  return next;
}

/** Valida el texto de una celda. Devuelve el número o un mensaje de error. */
export function validateField(
  field: PanelField,
  text: string,
): { ok: true; value: number } | { ok: false; error: string } {
  const rule = PANEL_FIELDS[field];
  const n = parseNumber(text);
  if (n === null) return { ok: false, error: 'Ingrese un número' };
  if (rule.integer && !Number.isInteger(n))
    return { ok: false, error: 'Debe ser un número entero' };
  if (rule.exclusiveMin ? n <= rule.min : n < rule.min) {
    return {
      ok: false,
      error: rule.exclusiveMin ? `Debe ser mayor que ${rule.min}` : `Debe ser ≥ ${rule.min}`,
    };
  }
  if (rule.max !== undefined && n > rule.max) return { ok: false, error: `Debe ser ≤ ${rule.max}` };
  return { ok: true, value: n };
}

/** Errores de validación de todas las ediciones (clave ``panelId.field``). */
export function editErrors(edits: PanelEdits): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [pid, fields] of Object.entries(edits)) {
    for (const [f, text] of Object.entries(fields)) {
      if (text === undefined) continue;
      if (f === ORIENTATION_FIELD) {
        if (!isOrientation(text)) out[`${pid}.${f}`] = 'Orientación desconocida';
        continue;
      }
      const r = validateField(f as PanelField, text);
      if (!r.ok) out[`${pid}.${f}`] = r.error;
    }
  }
  return out;
}

/** ¿El valor editado difiere del preset? */
export function isEdited(panel: Panel, field: PanelField, text: string | undefined): boolean {
  if (text === undefined) return false;
  const r = validateField(field, text);
  if (!r.ok) return true;
  return r.value !== (panel[field] ?? null);
}

/**
 * Ediciones con ``field`` del panel ``pid`` puesto en ``text``. Si vuelve al valor original del
 * preset (o queda vacío y el preset no tenía valor), la edición se quita.
 */
export function withEdit(
  edits: PanelEdits,
  pid: string,
  field: PanelField,
  text: string,
  original: number | null | undefined,
): PanelEdits {
  const next: PanelEdits = { ...edits, [pid]: { ...edits[pid], [field]: text } };
  const r = validateField(field, text);
  if ((r.ok && r.value === (original ?? null)) || (text.trim() === '' && original == null)) {
    const p = { ...next[pid] };
    delete p[field];
    if (Object.keys(p).length === 0) delete next[pid];
    else next[pid] = p;
  }
  return next;
}

/** Valor vigente de un campo: el editado (si es válido) o el del preset. */
export function currentValue(panel: Panel, edits: PanelEdits, field: PanelField): number | null {
  const text = edits[panel.id]?.[field];
  if (text !== undefined) {
    const r = validateField(field, text);
    if (r.ok) return r.value;
  }
  const v = panel[field];
  return typeof v === 'number' ? v : null;
}

/** Cantidad de celdas efectivamente modificadas. */
export function countEdits(spec: NetSpec | undefined, edits: PanelEdits): number {
  if (!spec) return 0;
  let n = 0;
  for (const p of spec.panels) {
    const e = edits[p.id];
    if (!e) continue;
    for (const f of PANEL_FIELD_ORDER) if (isEdited(p, f, e[f])) n += 1;
    const o = e[ORIENTATION_FIELD];
    if (isOrientation(o) && o !== presetOrientation(p)) n += 1;
  }
  return n;
}

/**
 * Aplica las ediciones a un panel. El motor usa los extras ``meshes_a``/``meshes_b`` (bordes T1/T2
 * del Excel) cuando existen, así que se actualizan en espejo de ``meshes_top``/``meshes_bottom``
 * conservando la correspondencia original del preset.
 */
export function applyPanelEdits(
  panel: Panel,
  edits: Partial<Record<PanelField | typeof ORIENTATION_FIELD, string>>,
): Panel {
  const out: Panel & Record<string, unknown> = { ...panel };
  const o = edits[ORIENTATION_FIELD];
  if (isOrientation(o)) out.mesh_orientation = o;
  for (const f of PANEL_FIELD_ORDER) {
    const text = edits[f];
    if (text === undefined) continue;
    const r = validateField(f, text);
    if (r.ok) (out as Record<string, unknown>)[f] = r.value;
  }
  const a = (panel as Record<string, unknown>).meshes_a;
  const b = (panel as Record<string, unknown>).meshes_b;
  if (typeof a === 'number' && typeof b === 'number') {
    if (a === panel.meshes_top && b === panel.meshes_bottom) {
      out.meshes_a = out.meshes_top;
      out.meshes_b = out.meshes_bottom;
    } else if (a === panel.meshes_bottom && b === panel.meshes_top) {
      out.meshes_a = out.meshes_bottom;
      out.meshes_b = out.meshes_top;
    } else if (out.meshes_top !== panel.meshes_top || out.meshes_bottom !== panel.meshes_bottom) {
      // correspondencia desconocida: se descartan los extras y el motor usa top/bottom
      delete out.meshes_a;
      delete out.meshes_b;
    }
  }
  return out;
}

/** NetSpec con las ediciones aplicadas, o ``null`` si no hay cambios efectivos. */
export function editedSpec(spec: NetSpec, edits: PanelEdits): NetSpec | null {
  if (countEdits(spec, edits) === 0) return null;
  return {
    ...spec,
    panels: spec.panels.map((p) => (edits[p.id] ? applyPanelEdits(p, edits[p.id] ?? {}) : p)),
  };
}
