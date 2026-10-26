import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceArea,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useT } from '../../i18n';
import { fmtAxis, fmtFixed } from '../../lib/format';
import { useChartColors, useMediaQuery } from '../../lib/theme';
import { TooltipBox, type SeriesDef } from './ChartParts';

export interface RefWindow {
  from: number;
  to: number;
  label: string;
}

interface Props {
  /** Filas ya en el sistema de unidades activo (ver ``displayRows``). */
  rows: Record<string, number | null>[];
  series: SeriesDef[];
  xKey?: string;
  /** Unidad que se muestra (``unitLabel(...)``). */
  yUnit: string;
  yLabel?: string;
  window?: RefWindow | null;
  refX?: { x: number; label: string } | null;
  /** Ordena las filas del tooltip por valor (descendente). */
  sortTooltip?: boolean;
  height?: number;
  ariaLabel: string;
}

interface TipProps {
  active?: boolean;
  label?: number | string;
  payload?: readonly { payload?: Record<string, number | null> }[];
}

export function SpeedLineChart({
  rows,
  series,
  xKey = 'speed',
  yUnit,
  yLabel,
  window,
  refX,
  sortTooltip,
  ariaLabel,
}: Props) {
  const c = useChartColors();
  const T = useT().charts;
  const narrow = useMediaQuery('(max-width: 560px)');
  const xs = rows.map((r) => r[xKey]).filter((v): v is number => typeof v === 'number');
  const xMin = Math.min(...xs);
  const xMax = Math.max(...xs);
  const ordered = [...series.filter((s) => s.quiet), ...series.filter((s) => !s.quiet)];

  const renderTip = ({ active, payload, label }: TipProps) => {
    if (!active || !payload?.length) return null;
    const row = payload[0]?.payload;
    if (!row) return null;
    let items = series.map((s) => ({
      name: s.name,
      color: s.color,
      value: row[s.key] ?? null,
      unit: s.unit ?? yUnit,
      strong: !s.quiet,
    }));
    items = items.filter((i) => i.value !== null);
    if (sortTooltip) items.sort((a, b) => (b.value ?? 0) - (a.value ?? 0));
    return <TooltipBox title={`${fmtFixed(Number(label), 2)} kn`} rows={items} />;
  };

  return (
    <div className="chart-box" role="img" aria-label={ariaLabel}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <LineChart
          data={rows}
          margin={{ top: refX ? 26 : 12, right: narrow ? 8 : 16, bottom: 4, left: narrow ? -8 : 4 }}
        >
          <CartesianGrid stroke={c.grid} vertical={false} />
          {window && (
            <ReferenceArea
              x1={window.from}
              x2={window.to}
              fill={c.window}
              fillOpacity={0.12}
              stroke="none"
              ifOverflow="hidden"
              label={{
                value: window.label,
                position: 'insideTopLeft',
                fill: c.text2,
                fontSize: 11,
              }}
            />
          )}
          <XAxis
            dataKey={xKey}
            type="number"
            domain={[xMin, xMax]}
            ticks={xs}
            tickFormatter={(v: number) => fmtFixed(v, 1)}
            stroke={c.axis}
            tick={{ fill: c.muted, fontSize: 11 }}
            tickLine={false}
            label={{
              value: T.speedAxis,
              position: 'insideBottomRight',
              offset: -2,
              fill: c.muted,
              fontSize: 11,
            }}
            height={36}
          />
          <YAxis
            tickFormatter={fmtAxis}
            stroke={c.axis}
            tick={{ fill: c.muted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={narrow ? 48 : 58}
            label={
              narrow
                ? undefined
                : {
                    value: yLabel ?? `[${yUnit}]`,
                    angle: -90,
                    position: 'insideLeft',
                    fill: c.muted,
                    fontSize: 11,
                    style: { textAnchor: 'middle' },
                  }
            }
          />
          <Tooltip
            content={renderTip}
            cursor={{ stroke: c.axis, strokeWidth: 1 }}
            isAnimationActive={false}
            wrapperStyle={{ outline: 'none', zIndex: 5 }}
          />
          {refX && (
            <ReferenceLine
              x={refX.x}
              stroke={c.text2}
              strokeWidth={1}
              ifOverflow="hidden"
              label={{ value: refX.label, position: 'top', fill: c.text, fontSize: 11 }}
            />
          )}
          {ordered.map((s) => (
            <Line
              key={s.key}
              dataKey={s.key}
              name={s.name}
              type="monotone"
              stroke={s.color}
              strokeWidth={s.width ?? (s.quiet ? 1 : 2)}
              strokeLinecap="round"
              strokeLinejoin="round"
              dot={false}
              activeDot={
                s.quiet ? false : { r: 4, stroke: c.surface, strokeWidth: 2, fill: s.color }
              }
              isAnimationActive={false}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
