/** Indicadores clave (KPI) del caso. */
import type { DesignData } from '../api/result';
import { fmt, fmtFixed } from './format';
import { designPropeller, hasModified, perfWindow, warpMeetsBreakingLoad } from './series';

export interface Tile {
  key: string;
  label: string;
  value: string;
  unit?: string;
  sub?: string;
  text?: boolean;
  badge?: { tone: 'good' | 'crit'; text: string };
}

export function num(d: DesignData, key: string): number | null {
  const v = d.summary[key];
  return typeof v === 'number' ? v : null;
}

export function tiles(d: DesignData): Tile[] {
  const mod = hasModified(d);
  const prop = designPropeller(d);
  const maxMod = mod ? perfWindow(d, prop, 'mod')?.max_speed_kn : null;
  const meets = warpMeetsBreakingLoad(d);
  const sel = d.result.warps?.selection;
  const req = num(d, 'warp_min_breaking_load_kgf');
  const rnMod3 = mod ? d.result.drag.rn.mod[d.case.speeds_kn.indexOf(3)] : null;
  return [
    {
      key: 'vertical_opening_m',
      label: 'Abertura vertical',
      value: fmtFixed(num(d, 'vertical_opening_m'), 2),
      unit: 'm',
      sub: 'AV de diseño (Suzuki)',
    },
    {
      key: 'horizontal_opening_m',
      label: 'Abertura horizontal',
      value: fmtFixed(num(d, 'horizontal_opening_m'), 2),
      unit: 'm',
      sub: 'AH entre puntas de ala',
    },
    {
      key: 'rn_std_3kn_kgf',
      label: 'RN a 3 kn',
      value: fmt(Math.round(num(d, 'rn_std_3kn_kgf') ?? NaN)),
      unit: 'kgf',
      sub: rnMod3 != null ? `modificada: ${fmt(Math.round(rnMod3))} kgf` : 'resistencia de la red',
    },
    {
      key: 'max_speed_kn',
      label: 'Vel. máx. remolcable',
      value: fmtFixed(num(d, 'max_speed_kn'), 2),
      unit: 'kn',
      sub:
        maxMod != null ? `modificada: ${fmtFixed(maxMod, 2)} kn` : 'tiro disponible = resistencia',
    },
    {
      key: 'warp_selected',
      label: 'Cable seleccionado',
      value: sel
        ? `Ø ${fmt(sel.diameter_mm)} mm · ${fmt(sel.breaking_load_t)} t`
        : String(d.summary.warp_selected ?? '—'),
      text: true,
      sub: req != null ? `rotura mínima requerida ${fmt(Math.round(req))} kgf` : undefined,
      badge:
        meets === null
          ? undefined
          : meets
            ? { tone: 'good', text: '✓ Cumple la rotura' }
            : { tone: 'crit', text: '⚠ No cumple la rotura' },
    },
    {
      key: 'solid_surface_m2',
      label: 'Superficie sólida',
      value: fmtFixed(num(d, 'solid_surface_m2'), 2),
      unit: 'm²',
      sub: 'Ss de los paños',
    },
  ];
}
