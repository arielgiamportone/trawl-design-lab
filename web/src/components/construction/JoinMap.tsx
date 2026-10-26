import type { LayoutResponse } from '../../api/client';
import { useT } from '../../i18n';

interface Props {
  layout: LayoutResponse;
  planes: string[];
  highlight: string[] | 'all';
  label: string;
}

/**
 * Croquis de las caras de la red con los paños de la unión resaltados. Usa la misma disposición
 * que el plano y el diseño interactivo (``POST /design/layout``, malla estirada).
 */
export function JoinMap({ layout, planes, highlight, label }: Props) {
  const PLANE_NAME = useT().construction.plane;
  const shown = layout.planes.filter((p) => planes.includes(p.plane));
  if (shown.length === 0) return null;
  const gap = 0.6;
  const widths = shown.map((p) => p.bbox[2] - p.bbox[0]);
  const height = Math.max(...shown.map((p) => p.bbox[3] - p.bbox[1]));
  const total = widths.reduce((a, b) => a + b, 0) + gap * (shown.length - 1);
  const fs = Math.max(height, total) / 40;
  const offsets = widths.map((_, i) => widths.slice(0, i).reduce((a, w) => a + w + gap, 0));
  return (
    <svg
      className="join-map"
      viewBox={`${-fs} ${-fs * 2.6} ${total + 2 * fs} ${height + fs * 3.6}`}
      role="img"
      aria-label={label}
      data-testid="join-map"
      preserveAspectRatio="xMidYMin meet"
    >
      {shown.map((p, i) => {
        const dx = (offsets[i] ?? 0) - p.bbox[0];
        return (
          <g key={p.plane} transform={`translate(${dx} ${-p.bbox[1]})`}>
            <text
              x={(p.bbox[0] + p.bbox[2]) / 2}
              y={p.bbox[1] - fs}
              textAnchor="middle"
              fontSize={fs * 1.4}
              className="join-map-title"
            >
              {PLANE_NAME[p.plane] ?? p.plane}
            </text>
            {p.shapes.map((s) => {
              const on = highlight === 'all' || highlight.includes(s.id);
              return (
                <g key={`${s.id}-${s.side}`} data-panel={s.id} data-on={on ? 'true' : undefined}>
                  <polygon
                    points={s.points.map(([x, y]) => `${x},${y}`).join(' ')}
                    className={on ? 'join-on' : 'join-off'}
                    vectorEffect="non-scaling-stroke"
                  />
                  <text
                    x={(s.x_top[0] + s.x_top[1] + s.x_bottom[0] + s.x_bottom[1]) / 4}
                    y={(s.y_top + s.y_bottom) / 2}
                    textAnchor="middle"
                    dominantBaseline="middle"
                    fontSize={fs}
                    className="join-map-id"
                  >
                    {s.id}
                  </text>
                </g>
              );
            })}
          </g>
        );
      })}
    </svg>
  );
}
