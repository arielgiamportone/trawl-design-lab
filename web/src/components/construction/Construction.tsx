import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import {
  api,
  type ConstructionGuide,
  type GuideFormat,
  type GuideJoin,
  type Variant,
} from '../../api/client';
import { useT } from '../../i18n';
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
import { fmt, fmtFixed, parseNumber, toInput } from '../../lib/format';
import { loadJson, saveJson } from '../../lib/storage';
import { fmtU, getUnits, toCanonical, toDisplay, unitLabel } from '../../lib/units';
import { useCase } from '../../state/useCase';
import { JoinMap } from './JoinMap';

const VIEWS: GuideView[] = ['corte', 'armado', 'montaje', 'cortes'];

const DOWNLOADS: GuideFormat[] = ['pdf', 'xlsx', 'html'];

/** Sobrante por gaza guardado (en m) como texto del campo, en el sistema activo. */
function eyeInput(m: number): string {
  if (getUnits() !== 'imperial') return String(m);
  return toInput(Number(toDisplay(m, 'm').toPrecision(4)));
}

/** Encabezado con unidad: «Peso [kg]» / «Peso [lb]». */
function withUnit(label: string, unit: string): string {
  return `${label} [${unitLabel(unit)}]`;
}

/** Encabezado de malla: «[mm]» y, en imperial, «[mm (in)]». */
function meshHead(label: string): string {
  return getUnits() === 'imperial' ? `${label} [mm (in)]` : `${label} [mm]`;
}

/**
 * Pestaña «Construcción» (Fase 15): del diseño al taller. Hoja de corte, uniones paso a paso con
 * el plano resaltado, montaje en relingas con boyas y lastre, y cortes de cabos. Lo que se va
 * tildando queda guardado en el navegador.
 */
export function Construction() {
  const { committed } = useCase();
  const T = useT().construction;
  const [view, setView] = useState<GuideView>(() => loadJson<GuideView>(GUIDE_VIEW_KEY) ?? 'corte');
  const [variant, setVariant] = useState<Variant>('std');
  const [eyeText, setEyeText] = useState(() => eyeInput(loadJson<number>(EYE_KEY) ?? 0.5));
  // Lo escrito está en el sistema activo (m o ft); la API recibe metros.
  const eyeOf = (text: string): number | null => {
    const v = parseNumber(text);
    if (v === null) return null;
    const m = Number(toCanonical(v, 'm').toPrecision(10));
    return m >= 0 && m <= 5 ? m : null;
  };
  const eye = eyeOf(eyeText) ?? 0.5;
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
      } else downloadBlob(blob, T.file(g?.net_id ?? T.defaultNet, format));
    } catch (e) {
      setDlError((e as Error).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="construction" data-testid="construction">
      <p className="section-sub">{T.intro}</p>
      <div className="catalog-actions no-print">
        {hasMod && (
          <div className="segmented" role="group" aria-label={T.variant}>
            {(['std', 'mod'] as const).map((x) => (
              <button key={x} type="button" aria-pressed={v === x} onClick={() => setVariant(x)}>
                {x === 'std' ? T.std : T.mod}
              </button>
            ))}
          </div>
        )}
        <label className="inline-field">
          {withUnit(T.eye, 'm')}
          <input
            aria-label={T.eye}
            inputMode="decimal"
            size={4}
            value={eyeText}
            onChange={(e) => {
              setEyeText(e.target.value);
              const n = eyeOf(e.target.value);
              if (n !== null) saveJson(EYE_KEY, n);
            }}
          />
        </label>
        {DOWNLOADS.map((d) => (
          <button
            key={d}
            type="button"
            className="btn"
            disabled={!g || busy !== null}
            onClick={() => void download(d)}
          >
            {busy === d ? T.preparing : T.downloads[d]}
          </button>
        ))}
      </div>
      {dlError && (
        <p className="alert warn" role="alert">
          {dlError}
        </p>
      )}
      {!committed && <p className="empty">{T.empty}</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {g && (
        <>
          <GuideSummary g={g} progress={progress} />
          <div className="segmented no-print" role="group" aria-label={T.section}>
            {VIEWS.map((x) => (
              <button key={x} type="button" aria-pressed={view === x} onClick={() => choose(x)}>
                {T.views[x]}
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
                <span>{T.assumptions}</span>
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
  const T = useT().construction;
  return (
    <div className="guide-summary" data-testid="guide-summary">
      <div>
        <span className="kpi-label">{T.panels}</span>
        <strong>
          {g.pieces.length} · {T.pieces(pieces)}
        </strong>
      </div>
      <div>
        <span className="kpi-label">{T.joins}</span>
        <strong>{g.joins.length}</strong>
      </div>
      <div>
        <span className="kpi-label">{T.buy}</span>
        <strong>{fmtU(kg, 'kg', { digits: 1 })}</strong>
      </div>
      <div>
        <span className="kpi-label">{T.progress}</span>
        <strong>{pct} %</strong>
        <progress max={100} value={pct} aria-label={T.progress} />
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
  const T = useT().construction;
  return (
    <div data-testid="cut-sheet">
      <h3 className="subhead">{T.buy}</h3>
      <div className="table-wrap">
        <table className="data" aria-label={T.buy}>
          <thead>
            <tr>
              <th scope="col">{T.colMaterial}</th>
              <th scope="col" className="num">
                {meshHead(T.colMesh)}
              </th>
              <th scope="col" className="num">
                {withUnit(T.colTwine, 'mm')}
              </th>
              <th scope="col" className="num">
                {T.colSize}
              </th>
              <th scope="col" className="num">
                {withUnit(T.colWeight, 'kg')}
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
                <td className="num">{fmtU(s.mesh_mm, 'mesh_mm', { unit: false })}</td>
                <td className="num">{fmtU(s.twine_mm, 'mm', { unit: false })}</td>
                <td className="num">
                  {fmt(s.width_meshes)} × {fmt(s.depth_meshes)}
                </td>
                <td className="num">{fmtU(s.weight_kg, 'kg', { digits: 2, unit: false })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 className="subhead">{T.piecesTitle}</h3>
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
                  aria-label={T.pieceCut(p.id)}
                />
                <span>
                  <strong>
                    {p.id} · {p.name}
                  </strong>{' '}
                  <span className="badge">
                    {T.pieceCount(p.pieces)}
                    {p.paired ? T.pair : ''}
                  </span>
                </span>
              </label>
              <p className="help">
                {T.pieceSpec(
                  p.planes,
                  p.material,
                  fmtU(p.mesh_mm, 'mesh_mm'),
                  fmtU(p.twine_mm, 'mm'),
                  p.meshes_mouth,
                  p.meshes_codend,
                  p.meshes_depth,
                )}
              </p>
              <ul className="guide-cuts">
                {p.sides.map((s) => (
                  <li key={s.side}>
                    <strong>{s.side}:</strong> {s.instruction}
                    {s.inferred && <span className="badge warn">{T.inferred}</span>}
                  </li>
                ))}
              </ul>
              <p className="help">
                {T.pieceStock(
                  p.start,
                  p.stock_width,
                  p.stock_depth,
                  Boolean(p.paired),
                  fmtFixed(100 * p.waste, 0),
                  fmtU(p.weight_kg, 'kg', { digits: 2 }),
                )}
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
  const T = useT().construction;
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
  if (!join) return <p className="empty">{T.noJoins}</p>;
  const go = (d: number) => {
    const next = g.joins[index + d];
    if (next) setCurrent(next.step);
  };
  return (
    <div className="guide-assembly" data-testid="assembly">
      <div className="guide-step" aria-live="polite">
        <p className="guide-step-title">
          {T.step(join.step, g.joins.length, join.plane, join.times)}
        </p>
        <p className="guide-step-text">{joinText(join)}</p>
        {join.note && <p className="help">{join.note}</p>}
        <div className="wizard-actions">
          <button type="button" className="btn" disabled={index <= 0} onClick={() => go(-1)}>
            {T.prev}
          </button>
          <label className="guide-check big">
            <input
              type="checkbox"
              checked={done.includes(join.step)}
              onChange={() => onToggle(join.step)}
            />
            {T.done}
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
            {T.doneNext}
          </button>
        </div>
        {layout.data && (
          <JoinMap
            layout={layout.data}
            planes={joinPlanes(join)}
            highlight={joinPanels(join)}
            label={T.mapLabel(join.step, join.a, join.b)}
          />
        )}
      </div>
      <ol className="guide-list" aria-label={T.allJoins}>
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
                aria-label={T.stepDone(j.step)}
              />
              <button type="button" className="link-button" onClick={() => setCurrent(j.step)}>
                {T.stepLink(j.step, j.a, j.b)}
              </button>
            </label>
            <span className="help">{T.stepMeshes(j.plane, j.meshes_a, j.meshes_b, j.rule)}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}

function FloatLine({ g }: { g: ConstructionGuide }) {
  const T = useT().construction;
  const xs = g.floats.map((f) => f.x_m);
  const half = Math.max(1, ...xs.map(Math.abs)) * 1.08;
  const w = 600;
  const sx = (x: number) => w / 2 + (x / half) * (w / 2 - 12);
  return (
    <svg
      viewBox={`0 0 ${w} 60`}
      className="float-line"
      role="img"
      aria-label={T.floatsAria(g.floats.length)}
      data-testid="float-line"
    >
      <line x1={sx(-half)} x2={sx(half)} y1={40} y2={40} className="float-rope" />
      <line x1={w / 2} x2={w / 2} y1={30} y2={50} className="float-axis" />
      {g.floats.map((f) => (
        <g key={f.number}>
          <circle cx={sx(f.x_m)} cy={30} r={7} className="float-ball" />
          <text x={sx(f.x_m)} y={14} textAnchor="middle" fontSize={10}>
            {fmtFixed(toDisplay(f.x_m, 'm'), 1)}
          </text>
        </g>
      ))}
      <text x={w / 2} y={58} textAnchor="middle" fontSize={10}>
        {T.centre}
      </text>
    </svg>
  );
}

function Rigging({ g }: { g: ConstructionGuide }) {
  const T = useT().construction;
  const per = (kg: number, kgm: number) =>
    `${fmtU(kg, 'kg', { digits: 1, unit: false })} · ${fmtU(kgm, 'kg/m', { digits: 2, unit: false })}`;
  const ballastHead = (label: string) => `${label} [${unitLabel('kg')}] · [${unitLabel('kg/m')}]`;
  return (
    <div data-testid="rigging">
      <h3 className="subhead">{T.ropesTitle}</h3>
      <div className="table-wrap">
        <table className="data" aria-label={T.ropesTable}>
          <thead>
            <tr>
              <th scope="col">{T.colRope}</th>
              <th scope="col">{T.colPart}</th>
              <th scope="col" className="num">
                {withUnit(T.colRopeLen, 'm')}
              </th>
              <th scope="col" className="num">
                {T.colMeshes}
              </th>
              <th scope="col" className="num">
                E
              </th>
              <th scope="col">{T.colSchedule}</th>
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
                <td className="num">{fmtU(h.rope_m, 'm', { digits: 2, unit: false })}</td>
                <td className="num">{h.meshes}</td>
                <td className="num">{fmtFixed(h.hanging ?? null, 2)}</td>
                <td>{h.schedule}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="help">{T.eHelp}</p>
      <h3 className="subhead">{T.floatsTitle(g.floats.length, fmtU(g.float_diameter_mm, 'mm'))}</h3>
      <FloatLine g={g} />
      <p className="help">{T.floatsHelp(getUnits() === 'imperial' ? T.feet : T.metres)}</p>
      <h3 className="subhead">{T.ballastTitle}</h3>
      <div className="table-wrap">
        <table className="data" aria-label={T.ballastTitle}>
          <thead>
            <tr>
              <th scope="col">{T.colZone}</th>
              <th scope="col">{T.colWhere}</th>
              <th scope="col" className="num">
                {ballastHead(T.colMin)}
              </th>
              <th scope="col" className="num">
                {ballastHead(T.colMax)}
              </th>
            </tr>
          </thead>
          <tbody>
            {g.ballast.map((b) => (
              <tr key={b.zone}>
                <td>{b.zone}</td>
                <td>{b.where}</td>
                <td className="num">{per(b.kg_min, b.kg_m_min)}</td>
                <td className="num">{per(b.kg_max, b.kg_m_max)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RopeCuts({ g }: { g: ConstructionGuide }) {
  const T = useT().construction;
  return (
    <div data-testid="rope-cuts">
      <div className="table-wrap">
        <table className="data" aria-label={T.cutsTable}>
          <thead>
            <tr>
              <th scope="col">{T.colPiece}</th>
              <th scope="col">{T.colMaterial}</th>
              <th scope="col" className="num">
                {T.colQuantity}
              </th>
              <th scope="col" className="num">
                {withUnit(T.colFinished, 'm')}
              </th>
              <th scope="col" className="num">
                {T.colEyes}
              </th>
              <th scope="col" className="num">
                {withUnit(T.colCut, 'm')}
              </th>
            </tr>
          </thead>
          <tbody>
            {g.ropes.map((r) => (
              <tr key={r.key} data-rope={r.key}>
                <td>{r.label}</td>
                <td>{r.material}</td>
                <td className="num">{r.pieces}</td>
                <td className="num">{fmtU(r.length_m, 'm', { digits: 2, unit: false })}</td>
                <td className="num">{r.eyes}</td>
                <td className="num">
                  <strong>{fmtU(r.cut_m, 'm', { digits: 2, unit: false })}</strong>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="help">{T.cutHelp(fmtU(g.eye_allowance_m, 'm', { digits: 2 }))}</p>
    </div>
  );
}
