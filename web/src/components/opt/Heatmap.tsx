import { useId } from 'react';
import type { OptimizeResponse } from '../../api/client';
import { fmtFixed } from '../../lib/format';
import { heatCells, objectiveUnit } from '../../lib/optimize';
import { useT } from '../../i18n';
import { fmtSim } from '../../lib/simulate';
import { useMediaQuery, useResolvedTheme } from '../../lib/theme';

/** Rampa secuencial (un solo tono, claro → oscuro en tema claro; al revés en oscuro). */
const RAMP = {
  light: { lo: [214, 230, 249], hi: [28, 92, 171] },
  dark: { lo: [27, 46, 69], hi: [134, 182, 239] },
} as const;

function mix(a: readonly number[], b: readonly number[], t: number): string {
  const c = a.map((x, i) => Math.round(x + ((b[i] ?? x) - x) * t));
  return `rgb(${c.join(',')})`;
}

const PAD = { l: 44, r: 8, t: 8, b: 40 };

/**
 * Mapa de factibilidad ``s × v``: celdas factibles coloreadas por el objetivo (más oscuro =
 * mejor), no factibles rayadas en gris y el mejor punto de la malla con un anillo.
 */
export function Heatmap({ r }: { r: OptimizeResponse }) {
  const theme = useResolvedTheme();
  const T = useT().optimize.heatmap;
  // Ancho del dibujo cercano al real para que el texto no quede diminuto.
  const W = useMediaQuery('(max-width: 560px)') ? 330 : 480;
  const ramp = RAMP[theme];
  const pid = useId().replace(/:/g, '');
  const { cells, min, max } = heatCells(r);
  const sVals = [...new Set(cells.map((c) => c.s))];
  const vVals = [...new Set(cells.map((c) => c.v))];
  const nS = sVals.length;
  const nV = vVals.length;
  const cw = (W - PAD.l - PAD.r) / nV;
  const ch = Math.min(30, Math.max(16, cw * 0.65));
  const H = PAD.t + ch * nS + PAD.b;
  const unit = objectiveUnit(r.objective);
  const val = (v: number | null) => fmtSim(v, unit.unit, { digits: 0 });
  const x = (j: number) => PAD.l + j * cw;
  const y = (i: number) => PAD.t + (nS - 1 - i) * ch; // s crece hacia arriba
  const vStep = Math.max(1, Math.ceil(nV / 8));
  const sStep = Math.max(1, Math.ceil(nS / 8));
  const nFeasible = cells.filter((c) => c.feasible).length;

  return (
    <div className="heatmap">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={T.aria(nFeasible, cells.length, unit.label.toLowerCase())}
        data-testid="opt-heatmap"
      >
        <defs>
          <pattern
            id={`${pid}-hatch`}
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="6" height="6" fill="var(--surface-2)" />
            <line x1="0" y1="0" x2="0" y2="6" stroke="var(--border-strong)" strokeWidth="2" />
          </pattern>
        </defs>
        {cells.map((c) => (
          <rect
            key={`${c.i}-${c.j}`}
            x={x(c.j) + 0.5}
            y={y(c.i) + 0.5}
            width={cw - 1}
            height={ch - 1}
            rx={2}
            fill={c.feasible && c.t !== null ? mix(ramp.lo, ramp.hi, c.t) : `url(#${pid}-hatch)`}
            data-feasible={c.feasible ? 'true' : 'false'}
          >
            <title>
              {`s = ${fmtFixed(c.s, 3)}, v = ${fmtFixed(c.v, 2)} kn: ${
                c.feasible ? val(c.value) : T.infeasibleCell
              }`}
            </title>
          </rect>
        ))}
        {cells
          .filter((c) => c.best)
          .map((c) => (
            <rect
              key="best"
              x={x(c.j) + 2}
              y={y(c.i) + 2}
              width={cw - 4}
              height={ch - 4}
              rx={3}
              fill="none"
              stroke="var(--text)"
              strokeWidth={2}
            />
          ))}
        {vVals.map((v, j) =>
          j % vStep === 0 || j === nV - 1 ? (
            <text
              key={`v${j}`}
              x={x(j) + cw / 2}
              y={PAD.t + ch * nS + 14}
              textAnchor="middle"
              className="heat-tick"
            >
              {fmtFixed(v, 2)}
            </text>
          ) : null,
        )}
        {sVals.map((s, i) =>
          i % sStep === 0 || i === nS - 1 ? (
            <text
              key={`s${i}`}
              x={PAD.l - 6}
              y={y(i) + ch / 2 + 4}
              textAnchor="end"
              className="heat-tick"
            >
              {fmtFixed(s, 2)}
            </text>
          ) : null,
        )}
        <text
          x={PAD.l + (W - PAD.l - PAD.r) / 2}
          y={H - 6}
          textAnchor="middle"
          className="heat-axis"
        >
          {T.xAxis}
        </text>
        <text
          x={12}
          y={PAD.t + (ch * nS) / 2}
          textAnchor="middle"
          className="heat-axis"
          transform={`rotate(-90 12 ${PAD.t + (ch * nS) / 2})`}
        >
          {T.yAxis}
        </text>
      </svg>
      <ul className="chart-legend heat-legend" aria-label={T.legend}>
        <li>
          <span
            className="heat-ramp"
            aria-hidden="true"
            style={{
              background: `linear-gradient(90deg, ${mix(ramp.lo, ramp.hi, 0)}, ${mix(ramp.lo, ramp.hi, 1)})`,
            }}
          />
          {unit.label}:{' '}
          {min === null
            ? '—'
            : fmtSim(r.objective === 'energy' ? (max ?? 0) : min, unit.unit, {
                digits: 0,
                unit: false,
              })}{' '}
          →{' '}
          {max === null ? '—' : val(r.objective === 'energy' ? (min ?? 0) : max)}{' '}
          {T.better(theme === 'dark')}
        </li>
        <li>
          <span className="heat-hatch" aria-hidden="true" />
          {T.infeasible}
        </li>
        <li>
          <span className="heat-best" aria-hidden="true" />
          {T.bestPoint}
        </li>
      </ul>
    </div>
  );
}
