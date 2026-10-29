/** Catálogo de redes FAO: filtros, etiquetas y procedencia (Fase 12). */
import type { CatalogItem } from '../api/client';
import { msg } from '../i18n';
import { fmtNum } from './format';
import { liveRecord } from './liveRecord';
import { CONVERSIONS, fmtU, getUnits } from './units';

export type ProvenanceKind = 'excel' | 'transcribed' | 'derived' | 'calibrated' | 'assumed';

/** Familias de red en el idioma activo (objeto vivo: se lee al usarlo). */
export const FAMILY_LABEL: Record<string, string> = liveRecord(() => msg().catalog.family);

/** Aparejos que calcula el motor (``trawlkit.rigging.multirig.RIGS``; Fase 19.5). */
export const RIGS = ['otter', 'pair', 'outrigger', 'twin', 'beam'] as const;

/** Aparejos en el idioma activo (lo importa también el asistente: ``wizard/StepNet``). */
export const RIG_LABEL: Record<string, string> = liveRecord(() => msg().catalog.rig);

export const KIND_LABEL: Record<ProvenanceKind, string> = liveRecord(() => msg().catalog.kind);

/** Orden de los tipos de procedencia (de más a menos directo). */
export const KINDS: ProvenanceKind[] = ['excel', 'transcribed', 'derived', 'calibrated', 'assumed'];

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

/** Aparejo de la red (``otter`` si no lo indica). */
export function rigOf(item: CatalogItem | undefined): string {
  return item?.rig ?? 'otter';
}

/**
 * Redes para comparar con ``main``: primero las del mismo aparejo y después el resto, cada grupo
 * en el orden del catálogo (Fase 19.9).
 */
export function comparisonNets(items: CatalogItem[], main: string): CatalogItem[] {
  const rig = rigOf(items.find((n) => n.id === main));
  const others = items.filter((n) => n.id !== main);
  return [...others.filter((n) => rigOf(n) === rig), ...others.filter((n) => rigOf(n) !== rig)];
}

/** Primera red publicada del mismo aparejo que ``main`` (sin contarla), o ``null``. */
export function sameRigComparison(items: CatalogItem[], main: string): string | null {
  const rig = rigOf(items.find((n) => n.id === main));
  return items.find((n) => n.id !== main && !isDraft(n) && rigOf(n) === rig)?.id ?? null;
}

/**
 * Red que se propone para comparar con ``main``: una del mismo aparejo que no sea borrador (con
 * una langostinera de tangones, otra langostinera); si no hay, la primera del catálogo.
 */
export function proposedComparison(items: CatalogItem[], main: string): string | null {
  return sameRigComparison(items, main) ?? items.find((n) => n.id !== main)?.id ?? null;
}

/**
 * Red de comparación al cambiar la red principal a ``main``: si la actual es de otro aparejo, se
 * reemplaza por una del mismo cuando la hay; si es la misma red, se quita.
 */
export function comparisonAfterChange(
  items: CatalogItem[],
  main: string,
  current: string | null,
): string | null {
  if (!current || current === main) return null;
  const byId = (id: string) => items.find((n) => n.id === id);
  if (rigOf(byId(current)) === rigOf(byId(main))) return current;
  return sameRigComparison(items, main) ?? current;
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
export function pathLabel(path: string): string {
  const FIELD_LABEL = msg().catalog.field;
  const GROUP_LABEL = msg().catalog.group;
  const parts = path.split('.');
  if (parts[0] === 'panels' && parts.length === 3) {
    return `${parts[1]} · ${FIELD_LABEL[parts[2] ?? ''] ?? parts[2]}`;
  }
  const group = GROUP_LABEL[parts[0] ?? ''] ?? parts[0];
  if (parts.length === 1) return group ?? path;
  return `${group} · ${FIELD_LABEL[parts[1] ?? ''] ?? parts[1]}`;
}

/**
 * Unidad métrica del motor que se deduce del nombre de un campo (``length_m`` → ``'m'``,
 * ``weight_kg_per_m`` → ``'kg/m'``, ``mesh_mm`` → ``'mesh_mm'``); ``''`` si no tiene.
 */
export function fieldUnit(field: string): string {
  const f = field.split('.').at(-1) ?? field;
  if (f.endsWith('_kg_per_m')) return 'kg/m';
  if (f.endsWith('_m_per_kg')) return 'm/kg';
  if (f === 'mesh_mm' || f.endsWith('mesh_mm')) return 'mesh_mm';
  if (f.endsWith('_mm')) return 'mm';
  if (f.endsWith('_m2')) return 'm²';
  if (f.endsWith('_m')) return 'm';
  if (f.endsWith('_kgf')) return 'kgf';
  if (f.endsWith('_kg')) return 'kg';
  if (f.endsWith('_t')) return 't';
  return '';
}

/**
 * Valor de una tabla de procedencia: en métrico, el número como siempre (sin unidad, hasta 3
 * decimales); en imperial, convertido y con su unidad para que no se confunda.
 */
export function provValueText(value: unknown, unit: string): string {
  if (typeof value !== 'number') return String(value);
  if (unit && getUnits() === 'imperial' && (unit === 'mesh_mm' || CONVERSIONS[unit])) {
    return fmtU(value, unit, { digits: 3 });
  }
  return fmtNum(value, { maximumFractionDigits: 3 });
}
