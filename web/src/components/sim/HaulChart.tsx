import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { fmt, fmtAxis } from '../../lib/format';
import { niceTicks, type HaulRow } from '../../lib/haul';
import { useChartColors, useMediaQuery } from '../../lib/theme';
import { TooltipBox } from '../charts/ChartParts';

interface Props {
  id: string;
  title: string;
  unit: string;
  rows: HaulRow[];
  value: (r: HaulRow) => number | null;
  digits?: number;
  /** Referencia del motor empírico (línea horizontal discontinua). */
  reference?: { value: number; label: string } | null;
}

interface TipProps {
  active?: boolean;
  label?: number | string;
  payload?: readonly { payload?: { y: number | null } }[];
}

/** Un panel de los múltiplos chicos: una magnitud contra la captura en el copo. */
export function HaulChart({ id, title, unit, rows, value, digits = 1, reference }: Props) {
  const c = useChartColors();
  const narrow = useMediaQuery('(max-width: 560px)');
  const data = rows.map((r) => ({ x: r.catchKg, y: value(r) }));
  const ys = data.map((d) => d.y).filter((v): v is number => v !== null);
  if (reference) ys.push(reference.value);
  const ticks = niceTicks(Math.min(...ys), Math.max(...ys));
  const tip = ({ active, payload, label }: TipProps) => {
    const y = payload?.[0]?.payload?.y ?? null;
    if (!active || y === null) return null;
    return (
      <TooltipBox
        title={`${fmt(Number(label))} kg de captura`}
        rows={[{ name: title, color: c.s1, value: Number(y.toFixed(digits)), unit, strong: true }]}
      />
    );
  };
  return (
    <figure className="haul-chart" data-chart={id} style={{ margin: 0 }}>
      <figcaption>
        {title} <span className="unit">[{unit}]</span>
      </figcaption>
      <div className="haul-chart-box" role="img" aria-label={`${title} según la captura`}>
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart
            data={data}
            margin={{ top: 10, right: 12, bottom: 2, left: narrow ? -14 : -4 }}
          >
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis
              dataKey="x"
              type="number"
              domain={['dataMin', 'dataMax']}
              ticks={data.map((d) => d.x)}
              tickFormatter={(v: number) => fmt(v)}
              stroke={c.axis}
              tick={{ fill: c.muted, fontSize: 11 }}
              tickLine={false}
              height={22}
            />
            <YAxis
              domain={[ticks[0] ?? 'auto', ticks[ticks.length - 1] ?? 'auto']}
              ticks={ticks}
              tickFormatter={fmtAxis}
              stroke={c.axis}
              tick={{ fill: c.muted, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={56}
            />
            <Tooltip content={tip} cursor={{ stroke: c.axis }} isAnimationActive={false} />
            {reference && (
              <ReferenceLine
                y={reference.value}
                stroke={c.text2}
                strokeDasharray="4 3"
                ifOverflow="extendDomain"
                label={{
                  value: reference.label,
                  position: 'insideTopRight',
                  fill: c.text2,
                  fontSize: 11,
                }}
              />
            )}
            <Line
              dataKey="y"
              type="monotone"
              stroke={c.s1}
              strokeWidth={2}
              dot={{ r: 4, fill: c.s1, stroke: c.surface, strokeWidth: 2 }}
              activeDot={{ r: 5, fill: c.s1, stroke: c.surface, strokeWidth: 2 }}
              isAnimationActive={false}
              connectNulls
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
