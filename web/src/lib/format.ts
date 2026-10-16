/** Formato numérico en español (coma decimal, punto de miles) con Intl es-AR. */

const LOCALE = 'es-AR';
const cache = new Map<string, Intl.NumberFormat>();

function nf(opts: Intl.NumberFormatOptions): Intl.NumberFormat {
  const key = JSON.stringify(opts);
  let f = cache.get(key);
  if (!f) {
    f = new Intl.NumberFormat(LOCALE, opts);
    cache.set(key, f);
  }
  return f;
}

/**
 * Formatea un valor como el motor (``report.labels.fmt``): enteros sin decimales y 4–5 cifras
 * significativas; ``null``/``NaN`` → «—»; textos tal cual.
 */
export function fmt(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return '—';
  if (typeof value === 'string') return value;
  if (!Number.isFinite(value)) return '—';
  if (Number.isInteger(value)) return nf({ maximumFractionDigits: 0 }).format(value);
  const sig = Math.abs(value) < 1 ? 4 : 5;
  return nf({ maximumSignificantDigits: sig }).format(value);
}

/** Número con decimales fijos (máximo ``digits``). */
export function fmtFixed(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return nf({ maximumFractionDigits: digits, minimumFractionDigits: 0 }).format(value);
}

/** Porcentaje con signo (``+12,3 %``). */
export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const s = nf({
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
    signDisplay: 'exceptZero',
  }).format(value);
  return `${s} %`;
}

/** Diferencia absoluta con signo. */
export function fmtDelta(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  if (value === 0) return '0';
  const body = fmt(Math.abs(value));
  return `${value > 0 ? '+' : '−'}${body}`;
}

/** Valores compactos para ejes (1.500 → «1,5 mil»). */
export function fmtAxis(value: number): string {
  if (Math.abs(value) >= 10000)
    return nf({ notation: 'compact', maximumFractionDigits: 1 }).format(value);
  return nf({ maximumFractionDigits: 2 }).format(value);
}

/**
 * Interpreta un número escrito por el usuario aceptando coma o punto decimal
 * (``"1,5"``, ``"1.5"``, ``" 2 "``). Devuelve ``null`` si no es un número finito.
 */
export function parseNumber(text: string): number | null {
  const t = text.trim().replace(/\s/g, '');
  if (!t) return null;
  // «1.234,5» (es-AR con miles) → 1234.5; «1,5» → 1.5
  const norm =
    t.includes(',') && t.includes('.')
      ? t.replace(/\./g, '').replace(',', '.')
      : t.replace(',', '.');
  if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(norm)) return null;
  const n = Number(norm);
  return Number.isFinite(n) ? n : null;
}

/** Número en formato editable (coma decimal, sin separador de miles). */
export function toInput(value: number | null | undefined): string {
  if (value === null || value === undefined) return '';
  return String(value).replace('.', ',');
}
