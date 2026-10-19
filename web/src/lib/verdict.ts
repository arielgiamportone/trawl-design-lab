/**
 * Diagnóstico en lenguaje llano para el modo guiado: semáforos sobre el tiro, la velocidad
 * máxima, el cable, la boca de la red y el área barrida a la velocidad elegida.
 */
import type { DesignData, PerformanceWindow } from '../api/result';
import { fmt, fmtFixed } from './format';
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

const kgf = (v: number) => `${fmt(Math.round(v))} kgf`;
const kn = (v: number) => `${fmtFixed(v, 2)} kn`;

export function assess(d: DesignData, targetSpeed: number): Check[] {
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
      title: '¿Le alcanza la potencia?',
      value:
        tone === 'crit'
          ? `No: falta ${kgf(pull.demand - pull.available)}`
          : tone === 'warn'
            ? `Justo: sobra ${pct} %`
            : `Sí: sobra ${pct} %`,
      why:
        `A ${kn(targetSpeed)} el buque puede tirar unos ${kgf(pull.available)} y la red con sus ` +
        `portones y cables pide unos ${kgf(pull.demand)}. ` +
        (tone === 'crit'
          ? 'Con ese déficit el buque no llega a esa velocidad: baje la velocidad, use una red más chica o un buque más potente.'
          : tone === 'warn'
            ? 'Alcanza, pero con poco margen para corriente, fondo duro o captura en la bolsa.'
            : 'Hay margen para corriente, fondo y captura.'),
      chapter: '19_ventana_velocidad',
    });
  } else {
    checks.push({
      key: 'pull',
      tone: 'info',
      title: '¿Le alcanza la potencia?',
      value: 'Sin dato a esa velocidad',
      why: 'La velocidad elegida queda fuera de las calculadas; ajuste la lista de velocidades en el modo experto.',
      chapter: '19_ventana_velocidad',
    });
  }

  const max = w?.max_speed_kn ?? null;
  const minFeasible = w?.feasible_speeds_kn[0];
  checks.push({
    key: 'max_speed',
    tone: max === null ? 'crit' : max >= targetSpeed ? 'ok' : 'crit',
    title: 'Velocidad máxima de arrastre',
    value: max === null ? 'Ninguna velocidad viable' : kn(max),
    why:
      max === null
        ? 'En ninguna de las velocidades calculadas el tiro supera a la resistencia.'
        : `Es la velocidad a la que el tiro disponible iguala a la resistencia total` +
          (minFeasible !== undefined
            ? `; se puede arrastrar entre ${kn(minFeasible)} y ${kn(max)}.`
            : '.') +
          (hasModified(d) && perfWindow(d, prop, 'mod')?.max_speed_kn != null
            ? ` Con la red modificada: ${kn(perfWindow(d, prop, 'mod')?.max_speed_kn as number)}.`
            : ''),
    chapter: '19_ventana_velocidad',
  });

  const meets = warpMeetsBreakingLoad(d);
  const sel = d.result.warps?.selection;
  checks.push({
    key: 'warp',
    tone: meets === null ? 'info' : meets ? 'ok' : 'crit',
    title: 'Cable de arrastre',
    value: sel ? `Ø ${fmt(sel.diameter_mm)} mm` : String(d.summary.warp_selected ?? '—'),
    why:
      meets === null
        ? 'No se pudo seleccionar un cable del catálogo.'
        : meets
          ? `Su carga de rotura (${fmt(sel?.breaking_load_t ?? NaN)} t) cubre la requerida con el factor de seguridad.`
          : 'Su carga de rotura no cubre la requerida con el factor de seguridad: elija un cable más grueso.',
    chapter: '18_cables',
  });

  const av = d.summary.vertical_opening_m;
  const ah = d.summary.horizontal_opening_m;
  if (typeof av === 'number' && typeof ah === 'number') {
    checks.push({
      key: 'opening',
      tone: 'info',
      title: 'Boca de la red',
      value: `${fmtFixed(ah, 1)} m × ${fmtFixed(av, 2)} m`,
      why: 'Ancho entre puntas de ala × altura de la boca, estimados para la red trabajando.',
      chapter: '16_aberturas',
    });
    const area = ah * targetSpeed * NM_M;
    checks.push({
      key: 'swept',
      tone: 'info',
      title: 'Área barrida por hora',
      value: `${fmt(Math.round(area / 1000))} mil m²/h`,
      why: `Ancho de la boca (${fmtFixed(ah, 1)} m) × distancia recorrida en una hora a ${kn(targetSpeed)}. Es un indicador del rendimiento de pesca.`,
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
