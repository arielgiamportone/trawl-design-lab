/** Catálogo de redes FAO: filtros, etiquetas y procedencia (Fase 12). */
import type { CatalogItem } from '../api/client';

export type ProvenanceKind = 'excel' | 'transcribed' | 'derived' | 'assumed';

export const FAMILY_LABEL: Record<string, string> = {
  bottom: 'Fondo',
  semi_pelagic: 'Semipelágica',
  pelagic: 'Pelágica',
};

export const RIG_LABEL: Record<string, string> = {
  otter: 'Portones',
  pair: 'Pareja',
};

export const KIND_LABEL: Record<ProvenanceKind, string> = {
  excel: 'Libro Excel',
  transcribed: 'Transcripto',
  derived: 'Derivado',
  assumed: 'Supuesto',
};

/** Orden de los tipos de procedencia (de más a menos directo). */
export const KINDS: ProvenanceKind[] = ['excel', 'transcribed', 'derived', 'assumed'];

export interface CatalogFilters {
  text: string;
  family: string;
  rig: string;
  source: string;
  /** Potencia del buque [hp]; ``null`` = sin filtro. */
  hp: number | null;
  drafts: boolean;
}

export const DEFAULT_FILTERS: CatalogFilters = {
  text: '',
  family: '',
  rig: '',
  source: '',
  hp: null,
  drafts: false,
};

/** Tolerancia del filtro por potencia: el rango de diseño ±25 %. */
export const HP_TOLERANCE = 0.25;

/** ¿La red es adecuada para un buque de ``hp`` caballos? Las redes sin rango (A-3) siempre. */
export function hpMatches(item: CatalogItem, hp: number | null): boolean {
  if (hp == null || !item.vessel_hp) return true;
  const [lo, hi] = item.vessel_hp;
  return hp >= lo * (1 - HP_TOLERANCE) && hp <= hi * (1 + HP_TOLERANCE);
}

export function isDraft(item: CatalogItem): boolean {
  return item.status === 'draft';
}

/** Redes que cumplen los filtros. */
export function filterNets(items: CatalogItem[], f: CatalogFilters): CatalogItem[] {
  const text = f.text.trim().toLowerCase();
  return items.filter((n) => {
    if (!f.drafts && isDraft(n)) return false;
    if (f.family && n.family !== f.family) return false;
    if (f.rig && (n.rig ?? 'otter') !== f.rig) return false;
    if (f.source && n.source?.key !== f.source) return false;
    if (!hpMatches(n, f.hp)) return false;
    if (text) {
      const hay = [n.id, n.name, n.description, n.target_species, n.source?.title]
        .filter(Boolean)
        .join(' ')
        .toLowerCase();
      if (!hay.includes(text)) return false;
    }
    return true;
  });
}

/** Fuentes presentes en el catálogo (clave → título), para el filtro. */
export function sources(items: CatalogItem[]): { key: string; title: string }[] {
  const seen = new Map<string, string>();
  for (const n of items) {
    if (n.source && !seen.has(n.source.key)) seen.set(n.source.key, n.source.title);
  }
  return [...seen].map(([key, title]) => ({ key, title }));
}

/** Rango de potencia legible: «30–33 hp», «65 hp» o «—». */
export function hpLabel(item: CatalogItem): string {
  if (!item.vessel_hp) return '—';
  const [lo, hi] = item.vessel_hp;
  return lo === hi ? `${lo} hp` : `${lo}–${hi} hp`;
}

/** Fracción de valores por tipo de procedencia (para la barra), en el orden de ``KINDS``. */
export function kindShares(byKind: Record<string, number>): { kind: string; share: number }[] {
  const total = Object.values(byKind).reduce((a, b) => a + b, 0);
  if (total === 0) return [];
  const order = [...KINDS, 'none'];
  return order
    .filter((k) => (byKind[k] ?? 0) > 0)
    .map((k) => ({ kind: k, share: (byKind[k] ?? 0) / total }));
}

/** Etiqueta legible de una ruta de valor (``panels.C.meshes_top`` → «C · mallas de boca»). */
const FIELD_LABEL: Record<string, string> = {
  mesh_mm: 'mallero',
  twine_diameter_mm: 'Ø hilo',
  rtex: 'Rtex',
  meshes_top: 'mallas de boca',
  meshes_bottom: 'mallas de bolsa',
  meshes_depth: 'alto (mallas)',
  hanging_ratio: 'U1',
  count: 'cantidad',
  cut_code: 'corte',
  length_m: 'largo',
  diameter_mm: 'diámetro',
  depth_m: 'profundidad',
  sweeps_m: 'patentes',
  door_length_m: 'largo del portón',
  door_height_m: 'alto del portón',
  door_weight_air_kg: 'peso del portón',
  vessel_length_m: 'eslora del buque',
};

const GROUP_LABEL: Record<string, string> = {
  headrope: 'Lima',
  footrope: 'Burlón',
  floats: 'Boyas',
  design: 'Caso de diseño',
  ballast_kg: 'Lastre',
};

export function pathLabel(path: string): string {
  const parts = path.split('.');
  if (parts[0] === 'panels' && parts.length === 3) {
    return `${parts[1]} · ${FIELD_LABEL[parts[2] ?? ''] ?? parts[2]}`;
  }
  const group = GROUP_LABEL[parts[0] ?? ''] ?? parts[0];
  if (parts.length === 1) return group ?? path;
  return `${group} · ${FIELD_LABEL[parts[1] ?? ''] ?? parts[1]}`;
}
