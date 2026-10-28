/**
 * Diagnóstico en lenguaje llano para el modo guiado: semáforos sobre el tiro, la velocidad
 * máxima, el cable, la boca de la red y el área barrida a la velocidad elegida.
 */
import type { DesignData, PerformanceWindow } from '../api/result';
import { msg } from '../i18n';
import { fmt, fmtFixed } from './format';
import { fmtU, toDisplay, unitLabel } from './units';
import { designPropeller, hasModified, perfWindow, warpMeetsBreakingLoad } from './series';

export type Tone = 'ok' | 'warn' | 'crit' | 'info';

export interface Check {
  key: string;
  tone: Tone;
  title: string;
  value: string;
  /** Explicación breve («¿por qué?»). */
  why: string;
  /** Capítulo del libro que lo desarrolla. */
  chapter?: string;
}

/** Metros por milla náutica (1 kn = 1852 m/h). */
export const NM_M = 1852;
/** Margen de tiro por debajo del cual se avisa (10 %). */
export const PULL_MARGIN = 1.1;

/** Interpolación lineal de ``ys`` en ``x`` (``null`` fuera de rango o sin datos). */
export function interp(xs: number[], ys: (number | null)[], x: number): number | null {
  for (let i = 0; i < xs.length - 1; i++) {
    const x0 = xs[i] as number;
    const x1 = xs[i + 1] as number;
    if (x < x0 || x > x1) continue;
    const y0 = ys[i];
    const y1 = ys[i + 1];
    if (typeof y0 !== 'number' || typeof y1 !== 'number') return null;
    return x1 === x0 ? y0 : y0 + ((y1 - y0) * (x - x0)) / (x1 - x0);
  }
  return null;
}

export function pullAt(w: PerformanceWindow | undefined, speed: number) {
  if (!w) return null;
  const available = interp(w.speeds_kn, w.available_kgf, speed);
  const demand = interp(w.speeds_kn, w.demand_kgf, speed);
  if (available === null || demand === null) return null;
  return { available, demand };
}

const kgf = (v: number) => `${fmt(Math.round(toDisplay(v, 'kgf')))} ${unitLabel('kgf')}`;
const kn = (v: number) => `${fmtFixed(v, 2)} kn`;
const len = (v: number, digits: number) =>
  `${fmtFixed(toDisplay(v, 'm'), digits)} ${unitLabel('m')}`;

export function assess(d: DesignData, targetSpeed: number): Check[] {
  const V = msg().wizard.verdict;
  const prop = designPropeller(d);
  const w = perfWindow(d, prop, 'std');
  const checks: Check[] = [];

  const pull = pullAt(w, targetSpeed);
  if (pull) {
    const ratio = pull.available / pull.demand;
    const tone: Tone = ratio >= PULL_MARGIN ? 'ok' : ratio >= 1 ? 'warn' : 'crit';
    const pct = Math.round(Math.abs(ratio - 1) * 100);
    checks.push({
      key: 'pull',
      tone,
      title: V.pullTitle,
      value:
        tone === 'crit'
          ? V.pullShort(kgf(pull.demand - pull.available))
          : tone === 'warn'
            ? V.pullTight(pct)
            : V.pullYes(pct),
      why:
        V.pullWhy(kn(targetSpeed), kgf(pull.available), kgf(pull.demand)) +
        (typeof d.summary.seabed_friction_kgf === 'number'
          ? V.pullFriction(kgf(d.summary.seabed_friction_kgf))
          : '') +
        '. ' +
        (tone === 'crit' ? V.pullWhyCrit : tone === 'warn' ? V.pullWhyWarn : V.pullWhyOk),
      chapter: '19_ventana_velocidad',
    });
  } else {
    checks.push({
      key: 'pull',
      tone: 'info',
      title: V.pullTitle,
      value: V.pullNoData,
      why: V.pullNoDataWhy,
      chapter: '19_ventana_velocidad',
    });
  }

  const max = w?.max_speed_kn ?? null;
  const minFeasible = w?.feasible_speeds_kn[0];
  const maxMod = hasModified(d) ? (perfWindow(d, prop, 'mod')?.max_speed_kn ?? null) : null;
  checks.push({
    key: 'max_speed',
    tone: max === null ? 'crit' : max >= targetSpeed ? 'ok' : 'crit',
    title: V.maxTitle,
    value: max === null ? V.maxNone : kn(max),
    why:
      max === null
        ? V.maxNoneWhy
        : V.maxWhy +
          (minFeasible !== undefined ? V.maxRange(kn(minFeasible), kn(max)) : '.') +
          (maxMod !== null ? V.maxMod(kn(maxMod)) : ''),
    chapter: '19_ventana_velocidad',
  });

  const meets = warpMeetsBreakingLoad(d);
  const sel = d.result.warps?.selection;
  checks.push({
    key: 'warp',
    tone: meets === null ? 'info' : meets ? 'ok' : 'crit',
    title: V.warpTitle,
    value: sel
      ? `Ø ${fmtU(sel.diameter_mm, 'mm', { digits: 2 })}`
      : String(d.summary.warp_selected ?? '—'),
    why:
      meets === null
        ? V.warpNone
        : meets
          ? V.warpOk(`${fmt(toDisplay(sel?.breaking_load_t ?? NaN, 't'))} ${unitLabel('t')}`)
          : V.warpFail,
    chapter: '18_cables',
  });

  const av = d.summary.vertical_opening_m;
  const ah = d.summary.horizontal_opening_m;
  if (typeof av === 'number' && typeof ah === 'number') {
    // Tangones y gemelo (Fase 19.5): las aberturas son las de cada red; barren todas las bocas.
    const nets = typeof d.summary.n_nets === 'number' ? d.summary.n_nets : 1;
    const dp = d.summary.door_spread_m;
    checks.push({
      key: 'opening',
      tone: 'info',
      title: nets > 1 ? V.openingTitleEach(nets) : V.openingTitle,
      value: V.openingValue(len(ah, 1), len(av, 2)),
      why: V.openingWhy + (typeof dp === 'number' ? V.openingDoors(len(dp, 1)) : ''),
      chapter: '16_aberturas',
    });
    const limit = d.summary.cfp_av_limit_m;
    if (typeof limit === 'number') {
      const over = av > limit;
      checks.push({
        key: 'cfp_av',
        tone: over ? 'crit' : 'ok',
        title: V.cfpTitle,
        value: over ? V.cfpOver(len(av, 2), len(limit, 2)) : V.cfpOk(len(av, 2), len(limit, 2)),
        why: V.cfpWhy(len(limit, 2)) + (over ? V.cfpWhyOver : ''),
        chapter: '16_aberturas',
      });
    }
    const area = nets * ah * targetSpeed * NM_M;
    checks.push({
      key: 'swept',
      tone: 'info',
      title: V.sweptTitle,
      value: V.swept(fmt(Math.round(toDisplay(area, 'm²') / 1000)), unitLabel('m²')),
      why:
        nets > 1
          ? V.sweptWhyNets(nets, len(ah, 1), kn(targetSpeed))
          : V.sweptWhy(len(ah, 1), kn(targetSpeed)),
      chapter: '20_optimizacion',
    });
  }
  return checks;
}

/** Peor tono de la lista (para el resumen general). */
export function overall(checks: Check[]): Tone {
  if (checks.some((c) => c.tone === 'crit')) return 'crit';
  if (checks.some((c) => c.tone === 'warn')) return 'warn';
  return 'ok';
}
