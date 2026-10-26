/**
 * Formato numérico según el idioma de la interfaz: en español coma decimal y punto de miles
 * (``es-AR``); en inglés, al revés (``en-US``).
 */
import { getLang, locale } from '../i18n';

const cache = new Map<string, Intl.NumberFormat>();

function nf(opts: Intl.NumberFormatOptions): Intl.NumberFormat {
  const loc = locale();
  const key = `${loc}|${JSON.stringify(opts)}`;
  let f = cache.get(key);
  if (!f) {
    f = new Intl.NumberFormat(loc, opts);
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

/** Número con el formato del idioma activo y opciones de ``Intl`` (reemplaza ``toLocaleString``). */
export function fmtNum(value: number | null | undefined, opts: Intl.NumberFormatOptions = {}): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  return nf(opts).format(value);
}

/** Fecha y hora con el formato del idioma activo. */
export function fmtDate(date: Date, opts: Intl.DateTimeFormatOptions): string {
  return date.toLocaleString(locale(), opts);
}

/** Separador decimal del idioma activo. */
export function decimalSep(): string {
  return getLang() === 'en' ? '.' : ',';
}

/** Porcentaje con signo (``+12,3 %``). */
export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—';
  const s = nf({
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
    signDisplay: 'exceptZero',
  }).format(value);
  return getLang() === 'en' ? `${s}%` : `${s} %`;
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
  // Con los dos separadores, el último es el decimal: «1.234,5» (es) y «1,234.5» (en) → 1234.5;
  // con uno solo, es el decimal: «1,5» y «1.5» → 1.5.
  const both = t.includes(',') && t.includes('.');
  const norm = !both
    ? t.replace(',', '.')
    : t.lastIndexOf(',') > t.lastIndexOf('.')
      ? t.replace(/\./g, '').replace(',', '.')
      : t.replace(/,/g, '');
  if (!/^[-+]?(\d+\.?\d*|\.\d+)(e[-+]?\d+)?$/i.test(norm)) return null;
  const n = Number(norm);
  return Number.isFinite(n) ? n : null;
}

/** Número en formato editable (separador decimal del idioma, sin separador de miles). */
export function toInput(value: number | null | undefined): string {
  if (value === null || value === undefined) return '';
  return String(value).replace('.', decimalSep());
}
