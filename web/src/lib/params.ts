/** Formulario de parámetros avanzados generado desde ``GET /params``. */
import { useState } from 'react';
import type { ParamInfo } from '../api/client';
import { msg } from '../i18n';
import { fmt, parseNumber, toInput } from './format';
import { REGION_LABEL } from './components';
import { localized, PROPELLER_LABELS, SEABED_LABELS } from './labels';
import { toCanonical, toDisplay, unitLabel } from './units';

function boolOptions() {
  return [
    { value: 'true', label: msg().common.yes },
    { value: 'false', label: msg().common.no },
  ];
}

/**
 * Unidad métrica (del motor) de cada parámetro con unidad. Los de largo, masa y fuerza se
 * muestran e ingresan en el sistema activo (``toDisplay``/``toCanonical``); el texto guardado en
 * el caso y lo que se envía a la API quedan siempre en métrico. Las mallas siguen en mm.
 */
export const PARAM_UNITS: Record<string, string> = {
  speeds_kn: 'kn',
  depth_m: 'm',
  gallows_m: 'm',
  vessel_depth_m: 'm',
  nomura_nhp: 'HP',
  spread_per_m: '',
  door_attack_angle_deg: '°',
  required_area_speed_range_kn: 'kn',
  sweep_lever_m: 'm',
  bridle_angle_deg: '°',
  dan_leno_m: 'm',
  sweeps_m: 'm',
  crowfoot_extension_m: 'm',
  sweeps_martini_delta_deg: '°',
  martini_mesh_mm: 'mesh_mm',
  flotation_max_speed_kn: 'kn',
  float_diameter_mm: 'mm',
  ballast_min_speed_kn: 'kn',
  ballast_max_speed_kn: 'kn',
  adjust_chain_m: 'm',
  warp_nhp_hp: 'HP',
  warp_design_speed_kn: 'kn',
  report_speeds_kn: 'kn',
  clump_frontal_area_m2: 'm²',
  beam_shoe_area_m2: 'm²',
};

const SUFFIX_UNITS: [RegExp, string][] = [
  [/_kn$/, 'kn'],
  [/_deg$/, '°'],
  [/_mm$/, 'mm'],
  [/_m$/, 'm'],
  [/_kgf$/, 'kgf'],
  [/_kg$/, 'kg'],
  [/_hp$/, 'HP'],
];

/** Unidad métrica de un parámetro (``''`` = adimensional). */
export function paramUnit(name: string): string {
  const known = PARAM_UNITS[name];
  if (known !== undefined) return known;
  return SUFFIX_UNITS.find(([re]) => re.test(name))?.[1] ?? '';
}

/** ¿La unidad cambia de valor en el sistema activo (m → ft…)? */
export function converts(unit: string): boolean {
  return !!unit && toDisplay(1, unit) !== 1;
}

const round = (v: number) => Number(v.toPrecision(6));

/** Texto a mostrar (sistema activo) de un texto guardado en métrico; si no se entiende, tal cual. */
export function displayText(unit: string, canonical: string): string {
  if (!converts(unit) || !canonical.trim()) return canonical;
  const parts = canonical.split(/[;\s]+/).filter(Boolean);
  const nums = parts.map(parseNumber);
  if (nums.some((n) => n === null)) return canonical;
  return nums.map((n) => toInput(round(toDisplay(n as number, unit)))).join('; ');
}

/** Texto a guardar (métrico) a partir del ingresado en el sistema activo. */
export function canonicalText(unit: string, text: string): string {
  if (!converts(unit) || !text.trim()) return text;
  const parts = text.split(/[;\s]+/).filter(Boolean);
  const nums = parts.map(parseNumber);
  if (nums.some((n) => n === null)) return text;
  return nums.map((n) => String(round(toCanonical(n as number, unit)))).join('; ');
}

/**
 * Campo de texto de un valor con unidad: muestra el texto en el sistema activo y entrega a
 * ``onChange`` el texto en métrico. Si el valor guardado cambia desde afuera (restablecer,
 * deshacer), el borrador se rehace.
 */
export function useUnitText(
  value: string,
  unit: string,
  onChange: (canonical: string) => void,
): [string, (text: string) => void] {
  const conv = converts(unit);
  const [draft, setDraft] = useState(() => displayText(unit, value));
  const [synced, setSynced] = useState(value);
  if (conv && value !== synced) {
    setSynced(value);
    setDraft(displayText(unit, value));
  }
  if (!conv) return [value, onChange];
  return [
    draft,
    (text: string) => {
      const canon = canonicalText(unit, text);
      setDraft(text);
      setSynced(canon);
      onChange(canon);
    },
  ];
}

export type ParamKind = 'float' | 'int' | 'tuple' | 'enum' | 'string' | 'bool' | 'strlist';

export interface ParamMeta {
  name: string;
  kind: ParamKind;
  nullable: boolean;
  /** Largo fijo de la tupla (``null`` = variable). */
  tupleLen: number | null;
  options?: { value: string; label: string }[];
  default: unknown;
  comment: string;
  /** Unidad métrica del motor (``''`` o ausente = sin unidad). */
  unit?: string;
}

/** Valores crudos (texto) del formulario por nombre de parámetro. */
export type ParamValues = Record<string, string>;

export function paramMeta(p: ParamInfo): ParamMeta {
  const t = p.type.replace(/\s/g, '');
  const nullable = /\|None$/.test(t) || p.default === null;
  const base = t.replace(/\|None$/, '');
  const meta: ParamMeta = {
    name: p.name,
    kind: 'string',
    nullable,
    tupleLen: null,
    default: p.default,
    comment: p.comment ?? '',
    unit: paramUnit(p.name),
  };
  if (base === 'float') meta.kind = 'float';
  else if (base === 'int') meta.kind = 'int';
  else if (base === 'bool') {
    meta.kind = 'bool';
    meta.options = boolOptions();
  } else if (base === 'tuple[str,...]') meta.kind = 'strlist';
  else if (p.name === 'component_region') {
    meta.kind = 'enum';
    meta.options = Object.entries(REGION_LABEL).map(([value, label]) => ({ value, label }));
  } else if (base.startsWith('tuple[')) {
    meta.kind = 'tuple';
    const inner = base.slice(6, -1).split(',');
    meta.tupleLen = inner.includes('...') ? null : inner.length;
  } else if (base === 'PropellerType') {
    meta.kind = 'enum';
    meta.options = Object.entries(PROPELLER_LABELS).map(([value, label]) => ({ value, label }));
  } else if (p.name === 'seabed') {
    meta.kind = 'enum';
    meta.options = Object.entries(SEABED_LABELS).map(([value, label]) => ({ value, label }));
  } else if (p.name === 'rig') {
    meta.kind = 'enum';
    meta.options = Object.entries(msg().catalog.rig).map(([value, label]) => ({ value, label }));
  } else if (p.name === 'opening_method') {
    meta.kind = 'enum';
    meta.options = Object.entries(msg().catalog.openingMethod).map(([value, label]) => ({
      value,
      label,
    }));
  }
  return meta;
}

/** Texto del valor por defecto (para el placeholder), en el sistema de unidades activo. */
export function defaultText(meta: ParamMeta): string {
  const d = meta.default;
  const M = msg();
  const unit = meta.unit ?? '';
  if (meta.name === 'seabed' && d == null) return M.labels.paramDefaults.noSeabed;
  if (meta.name === 'rig' && d == null) return M.labels.paramDefaults.rigFromNet;
  if (meta.kind === 'bool') return d ? M.common.yes : M.common.no;
  if (meta.kind === 'strlist' && d == null) return M.labels.paramDefaults.all;
  if (d === null || d === undefined) return M.labels.paramDefaults.auto;
  if (Array.isArray(d)) return d.map((x) => fmt(toDisplay(x as number, unit))).join('; ');
  if (typeof d === 'number') return fmt(toDisplay(d, unit));
  if (meta.kind === 'enum')
    return (
      PROPELLER_LABELS[String(d)] ??
      SEABED_LABELS[String(d)] ??
      REGION_LABEL[String(d)] ??
      M.catalog.openingMethod[String(d)] ??
      String(d)
    );
  return String(d);
}

export type ParseResult = { ok: true; value: unknown } | { ok: false; error: string };

/** Interpreta el texto ingresado para un parámetro. Texto vacío = usar el valor por defecto. */
export function parseParam(meta: ParamMeta, text: string): ParseResult | null {
  const t = text.trim();
  if (!t) return null;
  const E = msg().labels.paramErrors;
  switch (meta.kind) {
    case 'float': {
      const n = parseNumber(t);
      return n === null ? { ok: false, error: E.number } : { ok: true, value: n };
    }
    case 'int': {
      const n = parseNumber(t);
      if (n === null || !Number.isInteger(n)) return { ok: false, error: E.integer };
      return { ok: true, value: n };
    }
    case 'tuple': {
      const parts = t.split(/[;\s]+/).filter(Boolean);
      const nums = parts.map(parseNumber);
      if (nums.some((n) => n === null)) {
        return { ok: false, error: E.list };
      }
      if (meta.tupleLen !== null && nums.length !== meta.tupleLen) {
        return { ok: false, error: E.tupleLen(meta.tupleLen) };
      }
      if (nums.length === 0) return { ok: false, error: E.empty };
      return { ok: true, value: nums };
    }
    case 'bool':
      if (t === 'true' || t === 'false') return { ok: true, value: t === 'true' };
      return { ok: false, error: E.yesNo };
    case 'strlist': {
      const parts = t
        .split(/[;,]/)
        .map((x) => x.trim())
        .filter(Boolean);
      return parts.length ? { ok: true, value: parts } : { ok: false, error: E.empty };
    }
    case 'enum':
      return meta.options?.some((o) => o.value === t)
        ? { ok: true, value: t }
        : { ok: false, error: E.option };
    default:
      return { ok: true, value: t };
  }
}

/** Objeto ``params`` para ``DesignRequest`` y errores por parámetro. */
export function buildParams(
  metas: ParamMeta[],
  values: ParamValues,
): { params: Record<string, unknown>; errors: Record<string, string> } {
  const params: Record<string, unknown> = {};
  const errors: Record<string, string> = {};
  for (const m of metas) {
    const text = values[m.name];
    if (text === undefined) continue;
    const r = parseParam(m, text);
    if (r === null) continue;
    if (r.ok) params[m.name] = r.value;
    else errors[m.name] = r.error;
  }
  return { params, errors };
}

/** Nombre legible de un parámetro (``door_attack_angle_deg`` → «door attack angle [°]»). */
export function paramTitle(name: string): string {
  let unit = '';
  let base = name;
  for (const [re, u] of SUFFIX_UNITS) {
    if (re.test(base)) {
      unit = ` [${unitLabel(u)}]`;
      base = base.replace(re, '');
      break;
    }
  }
  return base.replace(/_/g, ' ') + unit;
}

/** Nombres (idioma activo) de los parámetros de ``DesignCase``, con la unidad que se muestra. */
export const PARAM_LABELS: Record<string, string> = localized(() => {
  const out: Record<string, string> = {};
  for (const [k, name] of Object.entries(msg().labels.params)) {
    const unit = paramUnit(k);
    out[k] = unit ? `${name} [${unitLabel(unit)}]` : name;
  }
  return out;
});

export function paramLabel(name: string): string {
  return PARAM_LABELS[name] ?? paramTitle(name);
}
