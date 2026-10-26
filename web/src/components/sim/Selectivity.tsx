import { useQuery } from '@tanstack/react-query';
import { lazy, Suspense, useId, useMemo, useState } from 'react';
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { api, ApiError, type SelectivityRequest } from '../../api/client';
import { fmt, fmtFixed } from '../../lib/format';
import { recall, remember } from '../../lib/memo';
import {
  asVariants,
  curveRows,
  DEFAULT_SEL,
  defaultTriangle,
  l50Text,
  meshAt,
  ORIENTATIONS,
  SEL_FORM_KEY,
  selectivityRequest,
  type Orientation,
  type SelForm,
  type SelVariant,
} from '../../lib/selectivity';
import {
  fromInput,
  inputStep,
  inputValue,
  resolutionLabel,
  SIM_SPEEDS,
  speedLabel,
} from '../../lib/simulate';
import { useT } from '../../i18n';
import { fmtU, unitLabel } from '../../lib/units';
import { useChartColors, useMediaQuery } from '../../lib/theme';
import { useCase } from '../../state/useCase';
import type { AnimColor } from '../sim3d/NetAnim';
import { HelpTip } from '../HelpTip';
import { MeshZoom } from './MeshZoom';

const NetAnim = lazy(() => import('../sim3d/NetAnim').then((m) => ({ default: m.NetAnim })));
const REQ_KEY = 'selectivity:request';

/** Selectividad del copo por tamaño: curvas por especie y variante, mapa de mallas y zoom. */
export function Selectivity() {
  const { committed, state } = useCase();
  const ids = useId();
  const M = useT();
  const T = M.selectivity;
  const S = M.simulate;
  const [form, setFormState] = useState<SelForm>(
    () =>
      recall<SelForm>(SEL_FORM_KEY) ?? {
        ...DEFAULT_SEL,
        speed: state.targetSpeed,
        catchKg: state.expectedCatchKg || DEFAULT_SEL.catchKg,
        seabed: state.params.seabed || DEFAULT_SEL.seabed,
      },
  );
  const setForm = (patch: Partial<SelForm>) =>
    setFormState((f) => {
      const next = { ...f, ...patch };
      remember(SEL_FORM_KEY, next);
      return next;
    });
  const [submitted, setSubmitted] = useState<string | null>(() => recall<string>(REQ_KEY) ?? null);
  const speciesQ = useQuery({
    queryKey: ['species'],
    queryFn: ({ signal }) => api.species(signal),
    staleTime: Infinity,
  });
  const seabeds = useQuery({
    queryKey: ['seabeds'],
    queryFn: ({ signal }) => api.seabeds(signal),
    staleTime: Infinity,
  });
  const query = useQuery({
    queryKey: ['selectivity', submitted],
    queryFn: ({ signal }) =>
      api.selectivity(JSON.parse(submitted as string) as SelectivityRequest, signal),
    enabled: submitted !== null,
    staleTime: Infinity,
    gcTime: 30 * 60_000,
    retry: false,
  });
  const run = () => {
    if (!committed) return;
    const key = JSON.stringify(selectivityRequest(committed, form));
    remember(REQ_KEY, key);
    setPicked(null);
    if (key === submitted) void query.refetch();
    else setSubmitted(key);
  };
  const species = useMemo(() => speciesQ.data ?? [], [speciesQ.data]);
  const toggle = <T,>(list: T[], v: T): T[] =>
    list.includes(v) ? list.filter((x) => x !== v) : [...list, v];

  const r = query.data;
  const variants = useMemo(() => (r ? asVariants(r) : []), [r]);
  const [chartSp, setChartSp] = useState<string | null>(null);
  const shownSp =
    chartSp && r?.species.includes(chartSp) ? chartSp : (r?.species[0] ?? form.species[0] ?? '');
  const [vIdx, setVIdx] = useState(0);
  const vSel = variants[Math.min(vIdx, Math.max(0, variants.length - 1))];
  const [color, setColor] = useState<AnimColor>('opening');
  const [picked, setPicked] = useState<number | null>(null);
  const zoomTri = picked ?? (vSel ? defaultTriangle(vSel) : null);
  const zoomMesh = vSel && zoomTri !== null ? meshAt(vSel.geometry, vSel.frame, zoomTri) : null;
  const fitTri = vSel?.curves.find((c) => c.species === shownSp)?.fit_tri;
  const unit = vSel?.curves.find((c) => c.species === shownSp)?.unit ?? '';

  return (
    <div className="selectivity">
      <p className="section-sub">{T.intro}</p>
      <div className="opt-form explore-form" role="group" aria-label={T.formLabel}>
        <fieldset className="field">
          <legend className="label">
            {T.species} <HelpTip topic="fishselect" label={T.escapeModel} />
          </legend>
          <div className="check-grid">
            {species.map((s) => (
              <label key={s.id} title={s.scientific_name}>
                <input
                  type="checkbox"
                  checked={form.species.includes(s.id)}
                  onChange={() => setForm({ species: toggle(form.species, s.id) })}
                />{' '}
                {s.name}
              </label>
            ))}
          </div>
        </fieldset>
        <fieldset className="field">
          <legend className="label">
            {T.codends} <HelpTip topic="mesh_orientation" label={T.meshOrientation} />
          </legend>
          <div className="check-grid">
            {ORIENTATIONS.map((o) => (
              <label key={o.id} title={o.help}>
                <input
                  type="checkbox"
                  checked={form.variants.includes(o.id)}
                  onChange={() => setForm({ variants: toggle<Orientation>(form.variants, o.id) })}
                />{' '}
                {o.label}
              </label>
            ))}
          </div>
          <span className="help">{T.upTo3}</span>
        </fieldset>
        <div className="field">
          <label htmlFor={`${ids}-mesh`}>{T.mesh} [mm]</label>
          <input
            id={`${ids}-mesh`}
            type="number"
            min={10}
            max={400}
            step={5}
            placeholder={T.meshPlaceholder}
            value={form.meshMm ?? ''}
            onChange={(e) => setForm({ meshMm: e.target.value ? Number(e.target.value) : null })}
          />
        </div>
        <div className="field">
          <label htmlFor={`${ids}-catch`}>
            {S.catchCodend} [{unitLabel('kg')}]
          </label>
          <input
            id={`${ids}-catch`}
            type="number"
            min={0}
            max={inputValue(20000, 'kg', 0)}
            step={inputStep(50, 'kg')}
            value={inputValue(form.catchKg, 'kg')}
            onChange={(e) =>
              setForm({ catchKg: Math.max(0, fromInput(Number(e.target.value) || 0, 'kg')) })
            }
          />
        </div>
        <div className="field">
          <label htmlFor={`${ids}-seabed`}>{S.seabed}</label>
          <select
            id={`${ids}-seabed`}
            value={form.seabed ?? ''}
            onChange={(e) => setForm({ seabed: e.target.value || null })}
          >
            {(seabeds.data ?? []).map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-speed`}>{S.speed} [kn]</label>
          <select
            id={`${ids}-speed`}
            value={form.speed}
            onChange={(e) => setForm({ speed: Number(e.target.value) })}
          >
            {SIM_SPEEDS.map((v) => (
              <option key={v} value={v}>
                {speedLabel(v)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-res`}>{S.resolution}</label>
          <select
            id={`${ids}-res`}
            value={form.resolution}
            onChange={(e) => setForm({ resolution: Number(e.target.value) })}
          >
            {[2, 3, 4].map((n) => (
              <option key={n} value={n}>
                {resolutionLabel(n)}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={run}
          disabled={!committed || query.isFetching || !form.variants.length || !form.species.length}
        >
          {T.run}
        </button>
      </div>
      <div className="status-line" role="status" aria-live="polite">
        {query.isFetching ? (
          <>
            <span className="spinner" aria-hidden="true" /> {T.running(form.variants.length)}
          </>
        ) : r ? (
          <span>{T.done(variants.length, fmtFixed(r.runtime_s, 1))}</span>
        ) : null}
      </div>
      {query.error && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {query.error instanceof ApiError && query.error.status
                ? S.errorStatus(query.error.status)
                : S.error}
              :
            </strong>{' '}
            {query.error.message}
          </span>
        </div>
      )}
      {r && variants.length > 0 && (
        <div className={`row-gap${query.isFetching ? ' stale' : ''}`}>
          <SelTable variants={variants} />
          <div className="explore-tools">
            <label className="inline-field">
              {T.curveOf}{' '}
              <select value={shownSp} onChange={(e) => setChartSp(e.target.value)}>
                {r.species.map((s) => (
                  <option key={s} value={s}>
                    {variants[0]?.curves.find((c) => c.species === s)?.name ?? s}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <RetentionChart variants={variants} species={shownSp} />
          <div className="explore-tools">
            <div className="segmented" role="group" aria-label={T.mapCodend}>
              {variants.map((v, i) => (
                <button
                  key={v.label}
                  type="button"
                  aria-pressed={vSel === v}
                  onClick={() => {
                    setVIdx(i);
                    setPicked(null);
                  }}
                >
                  {v.label}
                </button>
              ))}
            </div>
            <div className="segmented" role="group" aria-label={T.colorLabel}>
              {(['opening', 'values', 'tension'] as const).map((v) => (
                <button
                  key={v}
                  type="button"
                  aria-pressed={color === v}
                  onClick={() => setColor(v)}
                >
                  {T.colors[v]}
                </button>
              ))}
            </div>
          </div>
          {vSel?.geometry && vSel.frame && (
            <Suspense fallback={<p className="empty">{S.loading3d}</p>}>
              <NetAnim
                key={vSel.label}
                geometry={vSel.geometry}
                frames={[vSel.frame]}
                t={0}
                color={color}
                scope="net"
                label={T.mapLabel(vSel.label)}
                triValues={fitTri}
                valuesLabel={T.valuesLabel(unit)}
                onPick={setPicked}
                picked={zoomTri}
              />
            </Suspense>
          )}
          {zoomMesh && zoomTri !== null && species.length > 0 && (
            <MeshZoom
              key={`${vSel?.label}-${zoomTri}`}
              mesh={zoomMesh}
              triangle={zoomTri}
              species={species}
              speciesId={shownSp}
              onClose={() => setPicked(null)}
            />
          )}
          <p className="help">{T.help(fmtU(3, 'm'))}</p>
        </div>
      )}
      {!r && !query.isFetching && !query.error && <p className="empty">{T.empty}</p>}
    </div>
  );
}

function SelTable({ variants }: { variants: SelVariant[] }) {
  const T = useT().selectivity.table;
  const sp = variants[0]?.curves.map((c) => ({ id: c.species, name: c.name })) ?? [];
  const n1 = (v: number) => fmtFixed(v, 1);
  return (
    <div className="table-wrap">
      <table className="data" data-testid="selectivity-table">
        <caption>
          {T.captionA} <HelpTip topic="l50" label="L50" /> {T.captionB}{' '}
          <HelpTip topic="selection_range" label={T.selectionRange} /> {T.captionC}
        </caption>
        <thead>
          <tr>
            <th scope="col">{T.codend}</th>
            <th scope="col">{T.meanOpening}</th>
            {sp.map((s) => (
              <th scope="col" key={s.id}>
                {s.name}
                <br />
                <span className="unit">L50 · SR · SF</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {variants.map((v) => {
            const ms = v.result.mesh_summary as Record<string, number> | undefined;
            return (
              <tr key={v.label}>
                <th scope="row">
                  {v.label}
                  <br />
                  <span className="unit">
                    {v.codend_panels
                      .map((p) => `${p.id}: ${fmt(p.meshes_top)}×${fmt(p.meshes_depth)}`)
                      .join(' · ')}
                  </span>
                </th>
                <td className="num">
                  {ms
                    ? `${fmtFixed(ms.opening_deg ?? 0, 0)}° · ${fmtFixed((ms.open_fraction ?? 0) * 100, 0)} %`
                    : '—'}
                </td>
                {v.curves.map((c) => (
                  <td className="num" key={c.species} data-species={c.species}>
                    <strong>{l50Text(c, n1)}</strong>
                    <br />
                    <span className="unit">
                      SR {c.sr === null ? '—' : `${n1(c.sr)} ${c.unit}`} · SF{' '}
                      {c.sf === null ? '—' : fmtFixed(c.sf, 2)}
                    </span>
                  </td>
                ))}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RetentionChart({ variants, species }: { variants: SelVariant[]; species: string }) {
  const c = useChartColors();
  const narrow = useMediaQuery('(max-width: 560px)');
  const { rows, keys } = curveRows(variants, species);
  const curve = variants[0]?.curves.find((x) => x.species === species);
  const palette = [c.s1, c.s2, c.s3];
  const T = useT().selectivity;
  if (!rows.length || !curve) return null;
  return (
    <figure className="haul-chart sel-chart" data-chart="retention" style={{ margin: 0 }}>
      <figcaption>
        {T.retention(curve.name.toLowerCase(), curve.measure)}
        <span className="unit">{curve.unit}</span>)
      </figcaption>
      <div
        className="sel-chart-box"
        role="img"
        aria-label={T.retentionAria(curve.name, keys.join(', '))}
      >
        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
          <LineChart
            data={rows}
            margin={{ top: 10, right: 12, bottom: 2, left: narrow ? -14 : -4 }}
          >
            <CartesianGrid stroke={c.grid} vertical={false} />
            <XAxis
              dataKey="length"
              type="number"
              domain={['dataMin', 'dataMax']}
              tickFormatter={(v: number) => fmt(v)}
              stroke={c.axis}
              tick={{ fill: c.muted, fontSize: 11 }}
              tickLine={false}
              height={22}
            />
            <YAxis
              domain={[0, 1]}
              ticks={[0, 0.25, 0.5, 0.75, 1]}
              tickFormatter={(v: number) => `${Math.round(v * 100)} %`}
              stroke={c.axis}
              tick={{ fill: c.muted, fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              width={48}
            />
            <ReferenceLine y={0.5} stroke={c.text2} strokeDasharray="4 3" />
            <Tooltip
              isAnimationActive={false}
              formatter={(v) => `${Math.round(Number(v) * 100)} %`}
              labelFormatter={(l) => `${fmt(Number(l))} ${curve.unit}`}
              contentStyle={{ background: c.surface, borderColor: c.grid, color: c.text }}
            />
            <Legend verticalAlign="top" height={24} wrapperStyle={{ fontSize: 12 }} />
            {keys.map((k, i) => (
              <Line
                key={k}
                dataKey={k}
                type="monotone"
                stroke={palette[i % palette.length]}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </figure>
  );
}
