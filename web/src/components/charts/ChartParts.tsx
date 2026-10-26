import type { ReactNode } from 'react';
import { useT } from '../../i18n';
import { fmt } from '../../lib/format';
import { toDisplay } from '../../lib/units';

/**
 * Filas con los valores de ``units`` (clave → unidad métrica del motor) pasados al sistema de
 * unidades activo, para gráficos y tablas. Los gráficos (``SpeedLineChart``, ``TooltipBox``,
 * ``DataTable``) muestran los valores tal como llegan: convierta antes con esta función y rotule
 * con ``unitLabel``.
 */
export function displayRows<T extends object>(rows: T[], units: Record<string, string>): T[] {
  return rows.map((r) => {
    const out: Record<string, unknown> = { ...(r as Record<string, unknown>) };
    for (const [k, unit] of Object.entries(units)) {
      const v = (r as Record<string, unknown>)[k];
      if (typeof v === 'number') out[k] = toDisplay(v, unit);
    }
    return out as T;
  });
}

export interface SeriesDef {
  key: string;
  name: string;
  color: string;
  /** Grosor de la línea (2 = serie principal, 1 = contexto). */
  width?: number;
  /** Serie de contexto (atenuada): se agrupa en la leyenda. */
  quiet?: boolean;
  unit?: string;
}

export interface LegendItem {
  name: string;
  color: string;
  kind: 'line' | 'thin' | 'rect' | 'area';
}

export function Legend({ items }: { items: LegendItem[] }) {
  const T = useT().charts;
  return (
    <ul className="chart-legend" aria-label={T.legend}>
      {items.map((it) => (
        <li key={it.name}>
          {it.kind === 'rect' || it.kind === 'area' ? (
            <span
              className="key-rect"
              aria-hidden="true"
              style={{ background: it.color, opacity: it.kind === 'area' ? 0.35 : 1 }}
            />
          ) : (
            <span
              className={`key-line${it.kind === 'thin' ? ' thin' : ''}`}
              aria-hidden="true"
              style={{ color: it.color }}
            />
          )}
          {it.name}
        </li>
      ))}
    </ul>
  );
}

interface CardProps {
  id: string;
  title: string;
  sub?: ReactNode;
  legend?: LegendItem[];
  actions?: ReactNode;
  table?: ReactNode;
  note?: ReactNode;
  children: ReactNode;
}

export function ChartCard({ id, title, sub, legend, actions, table, note, children }: CardProps) {
  const T = useT().charts;
  return (
    <figure
      className="chart-card"
      aria-labelledby={`${id}-title`}
      data-chart={id}
      style={{ margin: 0 }}
    >
      <div className="chart-head">
        <div>
          <h3 id={`${id}-title`}>{title}</h3>
          {sub && <p className="chart-sub">{sub}</p>}
        </div>
        {actions}
      </div>
      {legend && legend.length > 0 && <Legend items={legend} />}
      {children}
      {note && <p className="chart-note">{note}</p>}
      {table && (
        <details className="table-view">
          <summary>{T.seeTable}</summary>
          {table}
        </details>
      )}
    </figure>
  );
}

interface TooltipRow {
  name: string;
  color: string;
  value: number | null;
  unit?: string;
  strong?: boolean;
  kind?: 'line' | 'rect';
}

export function TooltipBox({ title, rows }: { title: string; rows: TooltipRow[] }) {
  return (
    <div className="chart-tooltip">
      <div className="tt-title">{title}</div>
      <ul>
        {rows.map((r) => (
          <li key={r.name} className={r.strong ? 'tt-strong' : undefined}>
            {r.kind === 'rect' ? (
              <span className="key-rect" style={{ background: r.color }} aria-hidden="true" />
            ) : (
              <span className="key-line" style={{ color: r.color }} aria-hidden="true" />
            )}
            <span className="tt-value">
              {fmt(
                r.value === null ? null : Math.abs(r.value) >= 100 ? Math.round(r.value) : r.value,
              )}
              {r.unit ? ` ${r.unit}` : ''}
            </span>
            <span className="tt-name" title={r.name}>
              {r.name}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/** Tabla de datos genérica (vista accesible de cada gráfico). */
export function DataTable({
  caption,
  columns,
  rows,
}: {
  caption: string;
  columns: { key: string; label: string }[];
  rows: Record<string, number | string | null>[];
}) {
  return (
    <div className="table-wrap" style={{ maxHeight: 320 }}>
      <table className="data">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c, i) => (
              <th key={c.key} scope="col" className={i === 0 ? undefined : 'num'}>
                {c.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i}>
              {columns.map((c, j) => {
                const v = r[c.key] ?? null;
                const txt =
                  typeof v === 'number' ? fmt(Math.abs(v) >= 100 ? Math.round(v) : v) : (v ?? '—');
                return j === 0 ? (
                  <th key={c.key} scope="row" style={{ fontWeight: 500 }}>
                    {txt}
                  </th>
                ) : (
                  <td key={c.key} className="num">
                    {txt}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
