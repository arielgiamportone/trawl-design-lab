import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import {
  api,
  type ConstructionGuide,
  type GuideFormat,
  type GuideJoin,
  type Variant,
} from '../../api/client';
import {
  completion,
  EYE_KEY,
  GUIDE_VIEW_KEY,
  joinPanels,
  joinPlanes,
  joinText,
  loadProgress,
  saveProgress,
  toggle,
  type GuideView,
  type Progress,
} from '../../lib/construction';
import { downloadBlob } from '../../lib/download';
import { fmt, fmtFixed, parseNumber } from '../../lib/format';
import { loadJson, saveJson } from '../../lib/storage';
import { useCase } from '../../state/useCase';
import { JoinMap } from './JoinMap';

const VIEWS: { id: GuideView; label: string }[] = [
  { id: 'corte', label: 'Hoja de corte' },
  { id: 'armado', label: 'Armado paso a paso' },
  { id: 'montaje', label: 'Montaje en relingas' },
  { id: 'cortes', label: 'Cabos y cables' },
];

const DOWNLOADS: { format: GuideFormat; label: string }[] = [
  { format: 'pdf', label: 'Guía en PDF (A4)' },
  { format: 'xlsx', label: 'Planilla XLSX' },
  { format: 'html', label: 'Imprimir guía' },
];

/**
 * Pestaña «Construcción» (Fase 15): del diseño al taller. Hoja de corte, uniones paso a paso con
 * el plano resaltado, montaje en relingas con boyas y lastre, y cortes de cabos. Lo que se va
 * tildando queda guardado en el navegador.
 */
export function Construction() {
  const { committed } = useCase();
  const [view, setView] = useState<GuideView>(() => loadJson<GuideView>(GUIDE_VIEW_KEY) ?? 'corte');
  const [variant, setVariant] = useState<Variant>('std');
  const [eyeText, setEyeText] = useState(() => String(loadJson<number>(EYE_KEY) ?? 0.5));
  const eye = (() => {
    const v = parseNumber(eyeText);
    return v !== null && v >= 0 && v <= 5 ? v : 0.5;
  })();
  const hasMod = Boolean(committed?.net_modified);
  const v: Variant = hasMod ? variant : 'std';
  const q = useQuery({
    queryKey: ['construction', committed, v, eye],
    queryFn: ({ signal }) => api.construction(committed!, v, eye, signal),
    enabled: committed !== null,
    placeholderData: (prev) => prev,
  });
  const g = q.data;
  // El avance se lee del navegador para cada red y variante; lo tildado en esta sesión manda.
  const pkey = g ? `${g.net_id}:${g.variant}` : '';
  const [touched, setTouched] = useState<Record<string, Progress>>({});
  const progress: Progress =
    touched[pkey] ?? (g ? loadProgress(g.net_id, g.variant) : { cut: [], joins: [] });
  const update = (p: Progress) => {
    setTouched((t) => ({ ...t, [pkey]: p }));
    if (g) saveProgress(g.net_id, g.variant, p);
  };
  const [busy, setBusy] = useState<GuideFormat | null>(null);
  const [dlError, setDlError] = useState<string | null>(null);

  const choose = (id: GuideView) => {
    setView(id);
    saveJson(GUIDE_VIEW_KEY, id);
  };
  const download = async (format: GuideFormat) => {
    if (!committed) return;
    setBusy(format);
    setDlError(null);
    try {
      const blob = await api.constructionExport(committed, format, v, eye);
      if (format === 'html') {
        const url = URL.createObjectURL(blob);
        window.open(url, '_blank', 'noopener');
        setTimeout(() => URL.revokeObjectURL(url), 60_000);
      } else downloadBlob(blob, `guia-${g?.net_id ?? 'red'}.${format}`);
    } catch (e) {
      setDlError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="construction" data-testid="construction">
      <p className="section-sub">
        Del diseño al taller: qué paño comprar, cómo cortar cada pieza, en qué orden unirlas y cómo
        armar la red en las relingas. Vaya tildando lo que hace: queda guardado en este navegador,
        también sin conexión.
      </p>
      <div className="catalog-actions no-print">
        {hasMod && (
          <div className="segmented" role="group" aria-label="Variante de la red">
            {(['std', 'mod'] as const).map((x) => (
              <button key={x} type="button" aria-pressed={v === x} onClick={() => setVariant(x)}>
                {x === 'std' ? 'Estándar' : 'Modificada'}
              </button>
            ))}
          </div>
        )}
        <label className="inline-field">
          Sobrante por gaza [m]
          <input
            aria-label="Sobrante por gaza"
            inputMode="decimal"
            size={4}
            value={eyeText}
            onChange={(e) => {
              setEyeText(e.target.value);
              const n = parseNumber(e.target.value);
              if (n !== null && n >= 0 && n <= 5) saveJson(EYE_KEY, n);
            }}
          />
        </label>
        {DOWNLOADS.map((d) => (
          <button
            key={d.format}
            type="button"
            className="btn"
            disabled={!g || busy !== null}
            onClick={() => void download(d.format)}
          >
            {busy === d.format ? 'Preparando…' : d.label}
          </button>
        ))}
      </div>
      {dlError && (
        <p className="alert warn" role="alert">
          {dlError}
        </p>
      )}
      {!committed && <p className="empty">Complete el caso para ver la guía de construcción.</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {g && (
        <>
          <GuideSummary g={g} progress={progress} />
          <div className="segmented no-print" role="group" aria-label="Sección de la guía">
            {VIEWS.map((x) => (
              <button
                key={x.id}
                type="button"
                aria-pressed={view === x.id}
                onClick={() => choose(x.id)}
              >
                {x.label}
              </button>
            ))}
          </div>
          {view === 'corte' && (
            <CutSheet
              g={g}
              done={progress.cut}
              onToggle={(id) => update({ ...progress, cut: toggle(progress.cut, id) })}
            />
          )}
          {view === 'armado' && (
            <Assembly
              g={g}
              variant={v}
              done={progress.joins}
              onToggle={(s) => update({ ...progress, joins: toggle(progress.joins, s) })}
            />
          )}
          {view === 'montaje' && <Rigging g={g} />}
          {view === 'cortes' && <RopeCuts g={g} />}
          {g.notes.length > 0 && (
            <details className="accordion">
              <summary>
                <span>Supuestos de la guía</span>
              </summary>
              <ul className="accordion-body help">
                {g.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            </details>
          )}
        </>
      )}
    </div>
  );
}

function GuideSummary({ g, progress }: { g: ConstructionGuide; progress: Progress }) {
  const pieces = g.pieces.reduce((a, p) => a + p.pieces, 0);
  const kg = g.stock.reduce((a, s) => a + s.weight_kg, 0);
  const pct = Math.round(100 * completion(g, progress));
  return (
    <div className="guide-summary" data-testid="guide-summary">
      <div>
        <span className="kpi-label">Paños</span>
        <strong>
          {g.pieces.length} · {pieces} piezas
        </strong>
      </div>
      <div>
        <span className="kpi-label">Uniones</span>
        <strong>{g.joins.length}</strong>
      </div>
      <div>
        <span className="kpi-label">Paño a comprar</span>
        <strong>{fmtFixed(kg, 1)} kg</strong>
      </div>
      <div>
        <span className="kpi-label">Avance del taller</span>
        <strong>{pct} %</strong>
        <progress max={100} value={pct} aria-label="Avance del taller" />
      </div>
    </div>
  );
}

function CutSheet({
  g,
  done,
  onToggle,
}: {
  g: ConstructionGuide;
  done: string[];
  onToggle: (id: string) => void;
}) {
  return (
    <div data-testid="cut-sheet">
      <h3 className="subhead">Paño a comprar</h3>
      <div className="table-wrap">
        <table className="data" aria-label="Paño a comprar">
          <thead>
            <tr>
              <th scope="col">Material</th>
              <th scope="col" className="num">
                Mallero [mm]
              </th>
              <th scope="col" className="num">
                Ø hilo [mm]
              </th>
              <th scope="col" className="num">
                Ancho × alto [mallas]
              </th>
              <th scope="col" className="num">
                Peso [kg]
              </th>
            </tr>
          </thead>
          <tbody>
            {g.stock.map((s) => (
              <tr key={`${s.material}-${s.mesh_mm}-${s.twine_mm}`}>
                <td>
                  {s.material}
                  {s.rtex ? ` · R${fmt(s.rtex)} tex` : ''}
                </td>
                <td className="num">{fmt(s.mesh_mm)}</td>
                <td className="num">{fmt(s.twine_mm)}</td>
                <td className="num">
                  {fmt(s.width_meshes)} × {fmt(s.depth_meshes)}
                </td>
                <td className="num">{fmtFixed(s.weight_kg, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="subhead">Piezas</h3>
      <ul className="guide-list">
        {g.pieces.map((p) => {
          const checked = done.includes(p.id);
          return (
            <li key={p.id} className={checked ? 'done' : undefined} data-piece={p.id}>
              <label className="guide-check">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => onToggle(p.id)}
                  aria-label={`Paño ${p.id} cortado`}
                />
                <span>
                  <strong>
                    {p.id} · {p.name}
                  </strong>{' '}
                  <span className="badge">
                    {p.pieces} {p.pieces === 1 ? 'pieza' : 'piezas'}
                    {p.paired ? ' (par)' : ''}
                  </span>
                </span>
              </label>
              <p className="help">
                {p.planes} · {p.material} {fmt(p.mesh_mm)} mm, hilo Ø {fmt(p.twine_mm)} mm · mallas:
                boca {p.meshes_mouth}, bolsa {p.meshes_codend}, alto {p.meshes_depth}
              </p>
              <ul className="guide-cuts">
                {p.sides.map((s) => (
                  <li key={s.side}>
                    <strong>{s.side}:</strong> {s.instruction}
                    {s.inferred && <span className="badge warn">inferido</span>}
                  </li>
                ))}
              </ul>
              <p className="help">
                {p.start}. Rectángulo: {p.stock_width} × {p.stock_depth} mallas
                {p.paired ? ' por par' : ''}, desperdicio {fmtFixed(100 * p.waste, 0)} %; peso por
                pieza {fmtFixed(p.weight_kg, 2)} kg.
              </p>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function Assembly({
  g,
  variant,
  done,
  onToggle,
}: {
  g: ConstructionGuide;
  variant: Variant;
  done: number[];
  onToggle: (step: number) => void;
}) {
  const { committed } = useCase();
  const layout = useQuery({
    queryKey: ['layout', committed, variant, 'schematic'],
    queryFn: ({ signal }) => api.layout(committed!, variant, 'schematic', signal),
    enabled: committed !== null,
    staleTime: Infinity,
  });
  const firstOpen = g.joins.find((j) => !done.includes(j.step))?.step ?? g.joins[0]?.step ?? 1;
  const [current, setCurrent] = useState(firstOpen);
  const join: GuideJoin | undefined = g.joins.find((j) => j.step === current) ?? g.joins[0];
  const index = useMemo(() => g.joins.findIndex((j) => j.step === join?.step), [g, join]);
  if (!join) return <p className="empty">La red no tiene uniones.</p>;
  const go = (d: number) => {
    const next = g.joins[index + d];
    if (next) setCurrent(next.step);
  };
  return (
    <div className="guide-assembly" data-testid="assembly">
      <div className="guide-step" aria-live="polite">
        <p className="guide-step-title">
          Paso {join.step} de {g.joins.length} · {join.plane}
          {join.times > 1 ? ` · ${join.times} veces` : ''}
        </p>
        <p className="guide-step-text">{joinText(join)}</p>
        {join.note && <p className="help">{join.note}</p>}
        <div className="wizard-actions">
          <button type="button" className="btn" disabled={index <= 0} onClick={() => go(-1)}>
            ← Anterior
          </button>
          <label className="guide-check big">
            <input
              type="checkbox"
              checked={done.includes(join.step)}
              onChange={() => onToggle(join.step)}
            />
            Hecho
          </label>
          <button
            type="button"
            className="btn primary"
            disabled={index >= g.joins.length - 1}
            onClick={() => {
              if (!done.includes(join.step)) onToggle(join.step);
              go(1);
            }}
          >
            Hecho, siguiente →
          </button>
        </div>
        {layout.data && (
          <JoinMap
            layout={layout.data}
            planes={joinPlanes(join)}
            highlight={joinPanels(join)}
            label={`Paños de la unión ${join.step}: ${join.a} y ${join.b}`}
          />
        )}
      </div>
      <ol className="guide-list" aria-label="Todas las uniones">
        {g.joins.map((j) => (
          <li
            key={j.step}
            className={[done.includes(j.step) ? 'done' : '', j.step === join.step ? 'current' : '']
              .join(' ')
              .trim()}
            data-step={j.step}
          >
            <label className="guide-check">
              <input
                type="checkbox"
                checked={done.includes(j.step)}
                onChange={() => onToggle(j.step)}
                aria-label={`Paso ${j.step} hecho`}
              />
              <button type="button" className="link-button" onClick={() => setCurrent(j.step)}>
                Paso {j.step}: {j.a} + {j.b}
              </button>
            </label>
            <span className="help">
              {' '}
              {j.plane} · {j.meshes_a} : {j.meshes_b} mallas · {j.rule}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function FloatLine({ g }: { g: ConstructionGuide }) {
  const xs = g.floats.map((f) => f.x_m);
  const half = Math.max(1, ...xs.map(Math.abs)) * 1.08;
  const w = 600;
  const sx = (x: number) => w / 2 + (x / half) * (w / 2 - 12);
  return (
    <svg
      viewBox={`0 0 ${w} 60`}
      className="float-line"
      role="img"
      aria-label={`${g.floats.length} boyas sobre la lima`}
      data-testid="float-line"
    >
      <line x1={sx(-half)} x2={sx(half)} y1={40} y2={40} className="float-rope" />
      <line x1={w / 2} x2={w / 2} y1={30} y2={50} className="float-axis" />
      {g.floats.map((f) => (
        <g key={f.number}>
          <circle cx={sx(f.x_m)} cy={30} r={7} className="float-ball" />
          <text x={sx(f.x_m)} y={14} textAnchor="middle" fontSize={10}>
            {fmtFixed(f.x_m, 1)}
          </text>
        </g>
      ))}
      <text x={w / 2} y={58} textAnchor="middle" fontSize={10}>
        centro
      </text>
    </svg>
  );
}

function Rigging({ g }: { g: ConstructionGuide }) {
  return (
    <div data-testid="rigging">
      <h3 className="subhead">Paño en las relingas</h3>
      <div className="table-wrap">
        <table className="data" aria-label="Montaje en relingas">
          <thead>
            <tr>
              <th scope="col">Relinga</th>
              <th scope="col">Tramo</th>
              <th scope="col" className="num">
                Cabo [m]
              </th>
              <th scope="col" className="num">
                Mallas
              </th>
              <th scope="col" className="num">
                E
              </th>
              <th scope="col">Pauta</th>
            </tr>
          </thead>
          <tbody>
            {g.hanging.map((h) => (
              <tr key={`${h.rope}-${h.part}`} data-hanging={`${h.rope}-${h.part}`}>
                <td>{h.rope}</td>
                <td>
                  {h.part} ({h.panels.join(' + ')}){h.times > 1 ? ` × ${h.times}` : ''}
                  {h.warning && <p className="alert warn">{h.warning}</p>}
                </td>
                <td className="num">{fmtFixed(h.rope_m, 2)}</td>
                <td className="num">{h.meshes}</td>
                <td className="num">{fmtFixed(h.hanging ?? null, 2)}</td>
                <td>{h.schedule}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="help">
        E = largo de cabo / largo del paño estirado. En las alas el paño se arma por su costado (una
        malla por fila de alto).
      </p>
      <h3 className="subhead">
        Boyas sobre la lima ({g.floats.length} de Ø {fmt(g.float_diameter_mm)} mm)
      </h3>
      <FloatLine g={g} />
      <p className="help">Distancia al centro de la lima en metros (− izquierda, + derecha).</p>
      <h3 className="subhead">Lastre del burlón</h3>
      <div className="table-wrap">
        <table className="data" aria-label="Lastre del burlón">
          <thead>
            <tr>
              <th scope="col">Zona</th>
              <th scope="col">Dónde</th>
              <th scope="col" className="num">
                Mínimo [kg] · [kg/m]
              </th>
              <th scope="col" className="num">
                Máximo [kg] · [kg/m]
              </th>
            </tr>
          </thead>
          <tbody>
            {g.ballast.map((b) => (
              <tr key={b.zone}>
                <td>{b.zone}</td>
                <td>{b.where}</td>
                <td className="num">
                  {fmtFixed(b.kg_min, 1)} · {fmtFixed(b.kg_m_min, 2)}
                </td>
                <td className="num">
                  {fmtFixed(b.kg_max, 1)} · {fmtFixed(b.kg_m_max, 2)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RopeCuts({ g }: { g: ConstructionGuide }) {
  return (
    <div data-testid="rope-cuts">
      <div className="table-wrap">
        <table className="data" aria-label="Cortes de cabos, cables y cadenas">
          <thead>
            <tr>
              <th scope="col">Pieza</th>
              <th scope="col">Material</th>
              <th scope="col" className="num">
                Cantidad
              </th>
              <th scope="col" className="num">
                Terminado [m]
              </th>
              <th scope="col" className="num">
                Gazas
              </th>
              <th scope="col" className="num">
                Cortar [m]
              </th>
            </tr>
          </thead>
          <tbody>
            {g.ropes.map((r) => (
              <tr key={r.key} data-rope={r.key}>
                <td>{r.label}</td>
                <td>{r.material}</td>
                <td className="num">{r.pieces}</td>
                <td className="num">{fmtFixed(r.length_m, 2)}</td>
                <td className="num">{r.eyes}</td>
                <td className="num">
                  <strong>{fmtFixed(r.cut_m, 2)}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="help">
        Largo de corte = largo terminado + {fmtFixed(g.eye_allowance_m, 2)} m por gaza o empalme
        (ajústelo arriba según el cabo y el empalme que use).
      </p>
    </div>
  );
}
