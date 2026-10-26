import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useT } from '../../i18n';
import type { CompositionRow } from '../../lib/series';
import { fmt, fmtAxis, fmtFixed } from '../../lib/format';
import { unitLabel } from '../../lib/units';
import { useChartColors, useMediaQuery } from '../../lib/theme';
import { displayRows, TooltipBox } from './ChartParts';
import { COMPONENTS } from './components';

interface TipProps {
  active?: boolean;
  payload?: readonly { payload?: CompositionRow }[];
}

/** Barras apiladas de la composición; ``rows`` en kgf (se muestran en el sistema activo). */
export function CompositionChart({
  rows: kgfRows,
  speedLabel,
}: {
  rows: CompositionRow[];
  speedLabel: string;
}) {
  const T = useT().charts;
  const u = unitLabel('kgf');
  const rows = displayRows(kgfRows, {
    rn: 'kgf',
    floats: 'kgf',
    warps: 'kgf',
    doors: 'kgf',
    total: 'kgf',
  });
  const c = useChartColors();
  const narrow = useMediaQuery('(max-width: 560px)');
  const color = (k: (typeof COMPONENTS)[number]['color']) => c[k];

  const renderTip = ({ active, payload }: TipProps) => {
    const row = active ? payload?.[0]?.payload : undefined;
    if (!row) return null;
    return (
      <TooltipBox
        title={`${row.variant} · ${speedLabel} · ${T.total} ${fmt(Math.round(row.total))} ${u}`}
        rows={COMPONENTS.map((s) => ({
          name: `${s.name} (${fmtFixed((row[s.key] / row.total) * 100, 1)} %)`,
          color: color(s.color),
          value: row[s.key],
          unit: u,
          kind: 'rect' as const,
        }))}
      />
    );
  };

  const height = 64 + rows.length * 56;
  return (
    <div
      style={{ width: '100%', height }}
      role="img"
      aria-label={T.compositionAria(speedLabel)}
    >
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <BarChart
          data={rows}
          layout="vertical"
          margin={{ top: 8, right: narrow ? 76 : 80, bottom: 4, left: 4 }}
          barCategoryGap={16}
        >
          <CartesianGrid stroke={c.grid} horizontal={false} />
          <XAxis
            type="number"
            tickFormatter={fmtAxis}
            stroke={c.axis}
            tick={{ fill: c.muted, fontSize: 11 }}
            tickLine={false}
            label={{
              value: `[${u}]`,
              position: 'insideBottomRight',
              offset: -2,
              fill: c.muted,
              fontSize: 11,
            }}
            height={32}
          />
          <YAxis
            type="category"
            dataKey="variant"
            stroke={c.axis}
            tick={{ fill: c.text2, fontSize: 12 }}
            tickLine={false}
            width={narrow ? 78 : 88}
          />
          <Tooltip
            content={renderTip}
            cursor={{ fill: c.grid, fillOpacity: 0.4 }}
            isAnimationActive={false}
          />
          {COMPONENTS.map((s, i) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.name}
              stackId="t"
              fill={color(s.color)}
              stroke={c.surface}
              strokeWidth={2}
              barSize={24}
              radius={i === COMPONENTS.length - 1 ? [0, 4, 4, 0] : 0}
              isAnimationActive={false}
            >
              {i === COMPONENTS.length - 1 && (
                <LabelList
                  dataKey="total"
                  position="right"
                  formatter={(v: unknown) => `${fmt(Math.round(Number(v)))} ${u}`}
                  style={{ fill: c.text, fontSize: 12, fontWeight: 600 }}
                />
              )}
            </Bar>
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
