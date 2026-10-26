import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { OptimizeResponse } from '../../api/client';
import { fmt, fmtAxis, fmtFixed } from '../../lib/format';
import { paretoPoints } from '../../lib/optimize';
import { useT } from '../../i18n';
import { simUnit, simValue } from '../../lib/simulate';
import { useChartColors, useMediaQuery } from '../../lib/theme';
import { TooltipBox } from '../charts/ChartParts';

interface Pt {
  area: number;
  energy: number;
  s: number;
  v: number;
}
interface TipProps {
  active?: boolean;
  payload?: readonly { payload?: Pt }[];
}

/** Frente de Pareto: área barrida por hora (a maximizar) frente a R_T/AH (a minimizar). */
export function ParetoChart({ r }: { r: OptimizeResponse }) {
  const c = useChartColors();
  const T = useT().optimize;
  const narrow = useMediaQuery('(max-width: 560px)');
  // Área en miles de m²/h (o ft²/h) y trabajo por área barrida, en el sistema activo.
  const area = (thousands: number) => simValue(thousands * 1000, 'm²/h') / 1000;
  const energy = (v: number) => simValue(v, 'kgf·m/m²');
  const areaUnit = simUnit('m²/h');
  const energyUnit = simUnit('kgf·m/m²');
  const pts = paretoPoints(r).map((p) => ({ ...p, area: area(p.area), energy: energy(p.energy) }));
  const best = r.best;
  const bestPt =
    best.area_rate_m2_h !== null && best.energy_kgf_m_per_m2 !== null
      ? [
          {
            area: area(best.area_rate_m2_h / 1000),
            energy: energy(best.energy_kgf_m_per_m2),
            s: best.s,
            v: best.v_kn,
          },
        ]
      : [];

  const renderTip = ({ active, payload }: TipProps) => {
    const p = active ? payload?.[0]?.payload : undefined;
    if (!p) return null;
    return (
      <TooltipBox
        title={`s = ${fmtFixed(p.s, 3)} · v = ${fmtFixed(p.v, 2)} kn`}
        rows={[
          {
            name: T.pareto.swept,
            color: c.s1,
            value: Math.round(p.area * 1000),
            unit: areaUnit,
            strong: true,
          },
          { name: 'R_T/AH', color: c.s1, value: p.energy, unit: energyUnit },
        ]}
      />
    );
  };

  return (
    <div className="chart-box" role="img" aria-label={T.pareto.aria}>
      <ResponsiveContainer width="100%" height="100%" minWidth={0}>
        <ScatterChart
          margin={{ top: 12, right: narrow ? 8 : 16, bottom: 4, left: narrow ? -8 : 4 }}
        >
          <CartesianGrid stroke={c.grid} vertical={false} />
          <XAxis
            dataKey="area"
            type="number"
            domain={['auto', 'auto']}
            tickFormatter={(v: number) => fmtAxis(v)}
            stroke={c.axis}
            tick={{ fill: c.muted, fontSize: 11 }}
            tickLine={false}
            name={T.pareto.swept}
            label={{
              value: T.pareto.axisX(areaUnit),
              position: 'insideBottomRight',
              offset: -2,
              fill: c.muted,
              fontSize: 11,
            }}
            height={36}
          />
          <YAxis
            dataKey="energy"
            type="number"
            domain={['auto', 'auto']}
            tickFormatter={(v: number) => fmt(Math.round(v))}
            stroke={c.axis}
            tick={{ fill: c.muted, fontSize: 11 }}
            tickLine={false}
            axisLine={false}
            width={narrow ? 44 : 54}
            name="R_T/AH"
            label={
              narrow
                ? undefined
                : {
                    value: `R_T/AH [${energyUnit}]`,
                    angle: -90,
                    position: 'insideLeft',
                    fill: c.muted,
                    fontSize: 11,
                    style: { textAnchor: 'middle' },
                  }
            }
          />
          <Tooltip content={renderTip} isAnimationActive={false} cursor={{ stroke: c.axis }} />
          <Scatter
            data={pts}
            name={T.paretoTitle}
            fill={c.s1}
            line={{ stroke: c.s1, strokeWidth: 2 }}
            shape="circle"
            isAnimationActive={false}
          />
          <Scatter
            data={bestPt}
            name={T.best}
            fill={c.s2}
            shape="diamond"
            isAnimationActive={false}
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
