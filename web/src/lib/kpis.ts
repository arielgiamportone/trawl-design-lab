/** Indicadores clave (KPI) del caso. */
import type { DesignData } from '../api/result';
import { msg } from '../i18n';
import { fmt, fmtFixed } from './format';
import { fmtU, toDisplay, unitLabel } from './units';
import { at, designPropeller, hasModified, perfWindow, warpMeetsBreakingLoad } from './series';

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
  const rnMod3 = mod ? at(d.result.drag.rn.mod, d.case.speeds_kn.indexOf(3)) : null;
  const K = msg().labels.kpis;
  const m2 = (v: number | null) => fmtFixed(v === null ? null : toDisplay(v, 'm'), 2);
  const kgf = (v: number) => `${fmt(Math.round(toDisplay(v, 'kgf')))} ${unitLabel('kgf')}`;
  const ss = num(d, 'solid_surface_m2');
  const av = num(d, 'vertical_opening_m');
  // Método camaronero (Fase 19.7b): la AV no es la de Suzuki y la separación de portones (DP)
  // sale del equilibrio de la tijera; con tangones rige el límite de AV de la Res. CFP 7/2018.
  const shrimp = typeof d.summary.opening_method === 'string';
  const dp = num(d, 'door_spread_m');
  const limit = num(d, 'cfp_av_limit_m');
  const lim = limit === null ? '' : `${fmtFixed(toDisplay(limit, 'm'), 2)} ${unitLabel('m')}`;
  return [
    {
      key: 'vertical_opening_m',
      label: K.vertical_opening_m,
      value: m2(av),
      unit: unitLabel('m'),
      sub: shrimp ? K.avSubShrimp : K.avSub,
      badge:
        limit === null || av === null
          ? undefined
          : av <= limit
            ? { tone: 'good', text: K.cfpOk(lim) }
            : { tone: 'crit', text: K.cfpOver(lim) },
    },
    {
      key: 'horizontal_opening_m',
      label: K.horizontal_opening_m,
      value: m2(num(d, 'horizontal_opening_m')),
      unit: unitLabel('m'),
      sub: dp === null ? K.ahSub : K.ahSubDoors(`${m2(dp)} ${unitLabel('m')}`),
    },
    {
      key: 'rn_std_3kn_kgf',
      label: K.rn_std_3kn_kgf,
      value: fmt(Math.round(toDisplay(num(d, 'rn_std_3kn_kgf') ?? NaN, 'kgf'))),
      unit: unitLabel('kgf'),
      sub: rnMod3 != null ? K.modified(kgf(rnMod3)) : K.rnSub,
    },
    {
      key: 'max_speed_kn',
      label: K.max_speed_kn,
      value: fmtFixed(num(d, 'max_speed_kn'), 2),
      unit: 'kn',
      sub: maxMod != null ? K.modified(`${fmtFixed(maxMod, 2)} kn`) : K.maxSpeedSub,
    },
    {
      key: 'warp_selected',
      label: K.warp_selected,
      value: sel
        ? `Ø ${fmtU(sel.diameter_mm, 'mm', { digits: 2 })} · ${fmtU(sel.breaking_load_t, 't')}`
        : String(d.summary.warp_selected ?? '—'),
      text: true,
      sub: req != null ? K.warpReq(kgf(req)) : undefined,
      badge:
        meets === null
          ? undefined
          : meets
            ? { tone: 'good', text: K.meets }
            : { tone: 'crit', text: K.fails },
    },
    {
      key: 'solid_surface_m2',
      label: K.solid_surface_m2,
      value: fmtFixed(ss === null ? null : toDisplay(ss, 'm²'), 2),
      unit: unitLabel('m²'),
      sub: K.ssSub,
    },
  ];
}
