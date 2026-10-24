import { useId, useMemo, useState } from 'react';
import type { SpeciesOut } from '../../api/client';
import { fmtFixed } from '../../lib/format';
import {
  clearOpenings,
  maxPassing,
  openFraction,
  orientationLabel,
  patchKnots,
  type MeshShape,
} from '../../lib/selectivity';
import { useChartColors } from '../../lib/theme';

const SECTION_LABEL: Record<string, string> = {
  codend: 'copo',
  extension: 'extensión',
  body: 'cuerpo',
  belly: 'vientre',
  square: 'cielo',
  wing: 'ala',
  wing_tip: 'punta de ala',
};

interface Props {
  mesh: MeshShape & { section: string; orientation: string; meshes: number };
  triangle: number;
  species: SpeciesOut[];
  speciesId: string;
  onClose: () => void;
}

const N = 4;

/**
 * Zoom por malla: un parche de mallas del triángulo elegido con su forma deformada (exacta dentro
 * del elemento), el hilo a escala y la sección de un pez de la talla elegida, girada a su favor.
 */
export function MeshZoom({ mesh, triangle, species, speciesId, onClose }: Props) {
  const c = useChartColors();
  const ids = useId();
  const [spId, setSpId] = useState(speciesId);
  const sp = species.find((s) => s.id === spId) ?? species[0];
  const [lengthRaw, setLength] = useState<number | null>(null);
  const fit = useMemo(() => (sp ? maxPassing(mesh, sp) : { length: 0, theta: 0 }), [mesh, sp]);
  const length =
    lengthRaw ??
    (sp ? Math.round(Math.min(sp.length_max, Math.max(sp.length_min, fit.length || 1))) : 0);
  const knots = patchKnots(mesh, N);
  const { clearI, clearJ } = clearOpenings(mesh);
  const pts = knots.flat();
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  const pad = Math.max(mesh.legIMm, mesh.legJMm) * 0.25;
  const minX = Math.min(...xs) - pad;
  const maxX = Math.max(...xs) + pad;
  const minY = Math.min(...ys) - pad;
  const maxY = Math.max(...ys) + pad;
  const passes = sp ? length <= fit.length : false;
  // Centro de una malla interior del parche.
  const k11 = knots[1]?.[1] ?? [0, 0];
  const k22 = knots[2]?.[2] ?? [0, 0];
  const cx = (k11[0] + k22[0]) / 2;
  const cy = (k11[1] + k22[1]) / 2;
  const perUnit = sp?.unit === 'cm' ? 10 : 1;
  const rx = sp ? (sp.compression * sp.height * perUnit * length) / 2 : 0;
  const ry = sp ? (sp.compression * sp.width * perUnit * length) / 2 : 0;
  const deg = (fit.theta * 180) / Math.PI;
  const area =
    (Math.max(0, clearI) * Math.max(0, clearJ)) /
    Math.max(1e-6, Math.sin((mesh.openingDeg * Math.PI) / 180));
  const w = Math.max(0.3, mesh.twineMm);
  return (
    <section className="mesh-zoom" aria-labelledby={`${ids}-title`} data-testid="mesh-zoom">
      <div className="mesh-zoom-head">
        <h3 id={`${ids}-title`} className="section-title">
          Malla del {SECTION_LABEL[mesh.section] ?? mesh.section} (triángulo {triangle})
        </h3>
        <button type="button" className="btn small" onClick={onClose}>
          Cerrar zoom
        </button>
      </div>
      <div className="mesh-zoom-body">
        <svg
          className="mesh-zoom-svg"
          viewBox={`${minX} ${-maxY} ${maxX - minX} ${maxY - minY}`}
          role="img"
          aria-label={`Parche de ${N}×${N} mallas con apertura de ${fmtFixed(mesh.openingDeg, 0)}°; un ${sp?.name.toLowerCase() ?? 'pez'} de ${length} ${sp?.unit ?? ''} ${passes ? 'pasa' : 'no pasa'}`}
        >
          <g transform="scale(1,-1)">
            {knots.map((row, a) =>
              row.map((p, b) => (
                <g key={`${a}-${b}`}>
                  {a < N && (
                    <line
                      x1={p[0]}
                      y1={p[1]}
                      x2={knots[a + 1]?.[b]?.[0]}
                      y2={knots[a + 1]?.[b]?.[1]}
                      stroke={c.s1}
                      strokeWidth={w}
                      strokeLinecap="round"
                    />
                  )}
                  {b < N && (
                    <line
                      x1={p[0]}
                      y1={p[1]}
                      x2={knots[a]?.[b + 1]?.[0]}
                      y2={knots[a]?.[b + 1]?.[1]}
                      stroke={c.s5}
                      strokeWidth={w}
                      strokeLinecap="round"
                    />
                  )}
                  <circle cx={p[0]} cy={p[1]} r={w * 1.2} fill={c.text2} />
                </g>
              )),
            )}
            {sp && rx > 0 && (
              <ellipse
                cx={cx}
                cy={cy}
                rx={rx}
                ry={ry}
                transform={`rotate(${deg} ${cx} ${cy})`}
                fill={passes ? c.s3 : c.critical}
                fillOpacity={0.35}
                stroke={passes ? c.s3 : c.critical}
                strokeWidth={w}
              />
            )}
          </g>
        </svg>
        <div className="mesh-zoom-data">
          <dl className="kv">
            <dt>Orientación</dt>
            <dd>{orientationLabel(mesh.orientation)}</dd>
            <dt>Ángulo entre hilos</dt>
            <dd>{fmtFixed(mesh.openingDeg, 1)}°</dd>
            <dt>Patas (deformadas)</dt>
            <dd>
              {fmtFixed(mesh.legIMm, 1)} · {fmtFixed(mesh.legJMm, 1)} mm
            </dd>
            <dt>Luz entre hilos</dt>
            <dd>
              {fmtFixed(Math.max(0, clearI), 1)} · {fmtFixed(Math.max(0, clearJ), 1)} mm
            </dd>
            <dt>Área libre</dt>
            <dd>{fmtFixed(area, 0)} mm²</dd>
            <dt>Apertura</dt>
            <dd>{fmtFixed(openFraction(mesh.openingDeg) * 100, 0)} % de la malla abierta</dd>
          </dl>
          {sp && (
            <div className="mesh-zoom-fish">
              <label htmlFor={`${ids}-sp`}>Especie</label>
              <select id={`${ids}-sp`} value={sp.id} onChange={(e) => setSpId(e.target.value)}>
                {species.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              <label htmlFor={`${ids}-len`}>
                Talla ({sp.measure}): {length} {sp.unit}
              </label>
              <input
                id={`${ids}-len`}
                type="range"
                min={Math.max(1, Math.floor(sp.length_min / 2))}
                max={sp.length_max}
                step={1}
                value={length}
                onChange={(e) => setLength(Number(e.target.value))}
              />
              <p className={`mesh-zoom-verdict ${passes ? 'good' : 'bad'}`} role="status">
                {passes ? 'Pasa por la malla' : 'Queda retenido'} · talla máxima que pasa:{' '}
                <strong>
                  {fmtFixed(fit.length, 1)} {sp.unit}
                </strong>
              </p>
            </div>
          )}
        </div>
      </div>
      <p className="help">
        Azul y rosa: las dos familias de hilos, con el grosor del hilo a escala. Dentro de un
        elemento del simulador todas las mallas tienen la misma forma. La elipse es la sección más
        resistente del pez, girada para pasar; con su compresión de tejidos (A VERIFICAR).
      </p>
    </section>
  );
}
