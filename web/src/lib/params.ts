/** Formulario de parámetros avanzados generado desde ``GET /params``. */
import type { ParamInfo } from '../api/client';
import { fmt, parseNumber } from './format';
import { PROPELLER_LABELS } from './labels';

export type ParamKind = 'float' | 'int' | 'tuple' | 'enum' | 'string';

export interface ParamMeta {
  name: string;
  kind: ParamKind;
  nullable: boolean;
  /** Largo fijo de la tupla (``null`` = variable). */
  tupleLen: number | null;
  options?: { value: string; label: string }[];
  default: unknown;
  comment: string;
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
  };
  if (base === 'float') meta.kind = 'float';
  else if (base === 'int') meta.kind = 'int';
  else if (base.startsWith('tuple[')) {
    meta.kind = 'tuple';
    const inner = base.slice(6, -1).split(',');
    meta.tupleLen = inner.includes('...') ? null : inner.length;
  } else if (base === 'PropellerType') {
    meta.kind = 'enum';
    meta.options = Object.entries(PROPELLER_LABELS).map(([value, label]) => ({ value, label }));
  }
  return meta;
}

/** Texto del valor por defecto (para el placeholder). */
export function defaultText(meta: ParamMeta): string {
  const d = meta.default;
  if (d === null || d === undefined) return 'automático';
  if (Array.isArray(d)) return d.map((x) => fmt(x as number)).join('; ');
  if (typeof d === 'number') return fmt(d);
  if (meta.kind === 'enum') return PROPELLER_LABELS[String(d)] ?? String(d);
  return String(d);
}

export type ParseResult = { ok: true; value: unknown } | { ok: false; error: string };

/** Interpreta el texto ingresado para un parámetro. Texto vacío = usar el valor por defecto. */
export function parseParam(meta: ParamMeta, text: string): ParseResult | null {
  const t = text.trim();
  if (!t) return null;
  switch (meta.kind) {
    case 'float': {
      const n = parseNumber(t);
      return n === null ? { ok: false, error: 'Ingrese un número' } : { ok: true, value: n };
    }
    case 'int': {
      const n = parseNumber(t);
      if (n === null || !Number.isInteger(n))
        return { ok: false, error: 'Ingrese un número entero' };
      return { ok: true, value: n };
    }
    case 'tuple': {
      const parts = t.split(/[;\s]+/).filter(Boolean);
      const nums = parts.map(parseNumber);
      if (nums.some((n) => n === null)) {
        return { ok: false, error: 'Lista de números separados por «;»' };
      }
      if (meta.tupleLen !== null && nums.length !== meta.tupleLen) {
        return { ok: false, error: `Se esperan ${meta.tupleLen} valores separados por «;»` };
      }
      if (nums.length === 0) return { ok: false, error: 'Lista vacía' };
      return { ok: true, value: nums };
    }
    case 'enum':
      return meta.options?.some((o) => o.value === t)
        ? { ok: true, value: t }
        : { ok: false, error: 'Opción no válida' };
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
  const units: [RegExp, string][] = [
    [/_kn$/, ' [kn]'],
    [/_deg$/, ' [°]'],
    [/_mm$/, ' [mm]'],
    [/_m$/, ' [m]'],
    [/_kg$/, ' [kg]'],
    [/_hp$/, ' [HP]'],
  ];
  let unit = '';
  let base = name;
  for (const [re, u] of units) {
    if (re.test(base)) {
      unit = u;
      base = base.replace(re, '');
      break;
    }
  }
  return base.replace(/_/g, ' ') + unit;
}

/** Nombres en español de los parámetros de ``DesignCase``. */
export const PARAM_LABELS: Record<string, string> = {
  speeds_kn: 'Velocidades de arrastre [kn]',
  depth_m: 'Profundidad de trabajo [m]',
  gallows_m: 'Separación de pastecas [m]',
  vessel_depth_m: 'Puntal del buque [m]',
  ft_propeller: 'Hélice para el tiro (Fridman)',
  fridman_kf: 'Coeficiente kf de Fridman',
  koyama_k: 'Coeficiente k de Koyama',
  nomura_k3: 'Coeficiente k3 de Nomura',
  nomura_nhp: 'Potencias de Nomura [HP]',
  spread_per_m: 'Apertura por metro de cable',
  spread_correction_factor: 'Factor de corrección de la apertura',
  door_attack_angle_deg: 'Ángulo de ataque del portón [°]',
  rob_share: 'Fracción ROB del tiro',
  required_area_speed_range_kn: 'Rango de velocidades para el área del portón [kn]',
  sweep_lever_m: 'Brazo de palanca de las patentes [m]',
  bridle_angle_deg: 'Ángulo de las bridas [°]',
  dan_leno_m: 'Dan leno [m]',
  bridle_chain_ratio: 'Razón cadena/brida',
  sweeps_m: 'Patentes [m]',
  crowfoot_extension_m: 'Alargue de pies de gallo [m]',
  dremiere_ratio: 'Razón de Dremière',
  sweeps_martini_delta_deg: 'Δ ángulo de patentes (Martini) [°]',
  sweeps_factor: 'Factor de patentes',
  working_u2: 'U2 de la red trabajando',
  warp_shallow_factor: 'Factor de cable, aguas someras',
  warp_deep_factor: 'Factor de cable, aguas profundas',
  catenary_ratio: 'Razón de catenaria fL/L',
  martini_mr_meshes: 'Mallas MR (Martini)',
  martini_factor: 'Factor de Martini',
  martini_mesh_mm: 'Mallero para Martini [mm]',
  prado_flotation_k: 'k de flotación (Prado)',
  prado_ballast_k: 'k de lastre (Prado)',
  flotation_max_speed_kn: 'Velocidad máxima para flotación [kn]',
  float_count: 'Cantidad de boyas',
  float_diameter_mm: 'Diámetro de boya [mm]',
  float_wing_share: 'Fracción de boyas en las alas',
  float_front_fifth_share: 'Fracción en el primer quinto del ala',
  headrope_rope: 'Cabo de la lima (id)',
  footrope_rope: 'Cabo del burlón (id)',
  ballast_min_speed_kn: 'Velocidad para lastre mínimo [kn]',
  ballast_max_speed_kn: 'Velocidad para lastre máximo [kn]',
  adjust_chain_m: 'Cadena de ajuste [m]',
  warp_nhp_hp: 'Potencia para dimensionar el cable [HP]',
  warp_safety_factor: 'Factor de seguridad del cable',
  warp_design_speed_kn: 'Velocidad de diseño del cable [kn]',
  warp_spare_fraction: 'Fracción de cable de repuesto',
  warp_drag_shares: 'Fracciones de resistencia del cable',
  report_speeds_kn: 'Velocidades de RN en el resumen [kn]',
};

export function paramLabel(name: string): string {
  return PARAM_LABELS[name] ?? paramTitle(name);
}
