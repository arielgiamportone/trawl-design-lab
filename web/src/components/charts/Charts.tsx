import { useId, useState } from 'react';
import type { DesignData } from '../../api/result';
import { msg, useT } from '../../i18n';
import { fmtFixed } from '../../lib/format';
import { DRAG_METHODS, PROPELLER_LABELS, PULL_METHODS, dragMethodLabel } from '../../lib/labels';
import {
  composition,
  designPropeller,
  dragRows,
  feasibleWindow,
  hasModified,
  nearestIndex,
  perfWindow,
  pullRows,
  spreadRows,
  windowPropellers,
} from '../../lib/series';
import { useChartColors, type ChartColors } from '../../lib/theme';
import { toDisplay, unitLabel } from '../../lib/units';
import { useCase } from '../../state/useCase';
import {
  ChartCard,
  DataTable,
  displayRows,
  type LegendItem,
  type SeriesDef,
} from './ChartParts';
import { COMPONENTS } from './components';
import { CompositionChart } from './CompositionChart';
import { SpeedLineChart } from './SpeedLineChart';

/** Rótulo de la columna de velocidad de las tablas. */
const T_SPEED = () => msg().charts.speedAxis;

export function Charts() {
  const { design } = useCase();
  const d = design.data;
  const T = useT().expert.summary;
  if (!d) return <p className="empty">{design.isFetching ? T.calculating : T.noResults}</p>;
  return <ChartsBody d={d} stale={design.isFetching} />;
}

function ChartsBody({ d, stale }: { d: DesignData; stale: boolean }) {
  const c = useChartColors();
  const ids = useId();
  const T = useT();
  const C = T.charts;
  const props = windowPropellers(d);
  const [propSel, setProp] = useState<string | null>(null);
  const prop = propSel && props.includes(propSel) ? propSel : designPropeller(d);
  const mod = hasModified(d);
  const [variantSel, setVariant] = useState<'std' | 'mod'>('std');
  const variant = mod ? variantSel : 'std';
  const speeds = d.case.speeds_kn;
  const [speedSel, setSpeed] = useState<number | null>(null);
  const speedIdx =
    speedSel !== null && speeds.includes(speedSel)
      ? speeds.indexOf(speedSel)
      : nearestIndex(speeds, 3);
  const speed = speeds[speedIdx] ?? speeds[0] ?? 0;

  return (
    <div className={stale ? 'stale' : undefined}>
      <div className="charts-toolbar" role="group" aria-label={C.options}>
        <div className="field">
          <label htmlFor={`${ids}-prop`}>{C.propeller}</label>
          <select id={`${ids}-prop`} value={prop} onChange={(e) => setProp(e.target.value)}>
            {props.map((p) => (
              <option key={p} value={p}>
                {PROPELLER_LABELS[p] ?? p}
                {p === designPropeller(d) ? C.designSuffix : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-speed`}>{C.speedComposition}</label>
          <select
            id={`${ids}-speed`}
            value={speed}
            onChange={(e) => setSpeed(Number(e.target.value))}
          >
            {speeds.map((s) => (
              <option key={s} value={s}>
                {fmtFixed(s, 1)} kn
              </option>
            ))}
          </select>
        </div>
        {mod && (
          <div className="field">
            <span className="label" id={`${ids}-var`} style={{ fontSize: 13, fontWeight: 600 }}>
              {C.netByMethod}
            </span>
            <div className="segmented" role="group" aria-labelledby={`${ids}-var`}>
              <button
                type="button"
                aria-pressed={variant === 'std'}
                onClick={() => setVariant('std')}
              >
                {T.labels.variantsTitle.std}
              </button>
              <button
                type="button"
                aria-pressed={variant === 'mod'}
                onClick={() => setVariant('mod')}
              >
                {T.labels.variantsTitle.mod}
              </button>
            </div>
          </div>
        )}
      </div>
      <div className="charts-grid">
        <PullCard d={d} c={c} prop={prop} />
        <DragCard d={d} c={c} variant={variant} />
        <CompositionCard d={d} idx={speedIdx} speed={speed} />
        <SpreadCard d={d} c={c} />
      </div>
    </div>
  );
}

function PullCard({ d, c, prop }: { d: DesignData; c: ChartColors; prop: string }) {
  const C = useT().charts.pull;
  const u = unitLabel('kgf');
  const raw = pullRows(d, prop);
  const mod = hasModified(d);
  const w = perfWindow(d, prop, 'std');
  const win = feasibleWindow(w);
  const others = PULL_METHODS.filter(([k]) => k !== 'fridman_kgf');
  const series: SeriesDef[] = [
    ...others.map(([k, name]) => ({ key: k, name: C.pullOf(name), color: c.quiet, quiet: true })),
    {
      key: 'available',
      name: C.available,
      color: c.s3,
    },
    { key: 'demandStd', name: C.dragStd, color: c.s1 },
    ...(mod ? [{ key: 'demandMod', name: C.dragMod, color: c.s2 }] : []),
  ];
  const rows = displayRows(raw, Object.fromEntries(series.map((s) => [s.key, 'kgf'])));
  const legend: LegendItem[] = [
    { name: C.available, color: c.s3, kind: 'line' },
    { name: C.dragStd, color: c.s1, kind: 'line' },
    ...(mod ? [{ name: C.dragMod, color: c.s2, kind: 'line' as const }] : []),
    { name: C.otherMethods, color: c.quiet, kind: 'thin' },
    ...(win ? [{ name: C.window, color: c.window, kind: 'area' as const }] : []),
  ];
  const vmax = w?.max_speed_kn ?? null;
  return (
    <ChartCard
      id="tiro"
      title={C.title}
      sub={vmax !== null ? C.maxSpeed(fmtFixed(vmax, 2)) : C.notEnough}
      legend={legend}
      note={C.note}
      table={
        <DataTable
          caption={C.caption}
          columns={[
            { key: 'speed', label: T_SPEED() },
            ...series.map((s) => ({ key: s.key, label: `${s.name} [${u}]` })),
          ]}
          rows={rows}
        />
      }
    >
      <SpeedLineChart
        rows={rows}
        series={series}
        yUnit={u}
        window={win ? { ...win, label: C.towable } : null}
        refX={vmax !== null ? { x: vmax, label: C.vmax(fmtFixed(vmax, 2)) } : null}
        ariaLabel={C.aria}
      />
    </ChartCard>
  );
}

function DragCard({ d, c, variant }: { d: DesignData; c: ChartColors; variant: 'std' | 'mod' }) {
  const T = useT();
  const C = T.charts.drag;
  const u = unitLabel('kgf');
  const rows = displayRows(
    dragRows(d, variant),
    Object.fromEntries(DRAG_METHODS.map(([k]) => [k, 'kgf'])),
  );
  const design = d.result.drag.design_method;
  const series: SeriesDef[] = DRAG_METHODS.map(([k, name]) => ({
    key: k,
    name,
    color: k === design ? c.s1 : c.quiet,
    quiet: k !== design,
  }));
  return (
    <ChartCard
      id="rn"
      title={C.title(DRAG_METHODS.length, T.labels.variants[variant])}
      sub={C.designMethod(dragMethodLabel(design))}
      legend={[
        { name: C.design(dragMethodLabel(design)), color: c.s1, kind: 'line' },
        { name: C.others(DRAG_METHODS.length - 1), color: c.quiet, kind: 'thin' },
      ]}
      note={C.note}
      table={
        <DataTable
          caption={C.caption(u)}
          columns={[
            { key: 'speed', label: T_SPEED() },
            ...DRAG_METHODS.map(([k, n]) => ({ key: k, label: n })),
          ]}
          rows={rows}
        />
      }
    >
      <SpeedLineChart
        rows={rows}
        series={series}
        yUnit={u}
        sortTooltip
        ariaLabel={C.aria}
      />
    </ChartCard>
  );
}

function CompositionCard({ d, idx, speed }: { d: DesignData; idx: number; speed: number }) {
  const c = useChartColors();
  const C = useT().charts.composition;
  const u = unitLabel('kgf');
  const rows = composition(d, idx);
  const speedLabel = `${fmtFixed(speed, 1)} kn`;
  const pct = (v: number, total: number) => fmtFixed((v / total) * 100, 1);
  return (
    <ChartCard
      id="composicion"
      title={C.title(speedLabel)}
      sub={C.sub}
      legend={COMPONENTS.map((s) => ({ name: s.name, color: c[s.color], kind: 'rect' as const }))}
      table={
        <DataTable
          caption={`${C.title(speedLabel)} [${u}]`}
          columns={[
            { key: 'variant', label: C.net },
            ...COMPONENTS.map((s) => ({ key: s.key, label: `${s.name} [${u}]` })),
            { key: 'total', label: `${C.total} [${u}]` },
          ]}
          rows={rows.map((r) => ({
            ...r,
            rn: toDisplay(r.rn, 'kgf'),
            floats: toDisplay(r.floats, 'kgf'),
            warps: toDisplay(r.warps, 'kgf'),
            doors: toDisplay(r.doors, 'kgf'),
            total: toDisplay(r.total, 'kgf'),
          }))}
        />
      }
      note={rows
        .map((r) =>
          C.note(
            r.variant,
            pct(r.rn, r.total),
            pct(r.floats, r.total),
            pct(r.warps, r.total),
            pct(r.doors, r.total),
          ),
        )
        .join(' — ')}
    >
      <CompositionChart rows={rows} speedLabel={speedLabel} />
    </ChartCard>
  );
}

function SpreadCard({ d, c }: { d: DesignData; c: ChartColors }) {
  const C = useT().charts.spread;
  const u = unitLabel('m');
  const rows = displayRows(spreadRows(d), {
    dpaStd: 'm',
    dpaMod: 'm',
    avStd: 'm',
    avMod: 'm',
  });
  const mod = hasModified(d);
  const mk = (std: string, modKey: string): SeriesDef[] => [
    { key: std, name: C.std, color: c.s1, unit: u },
    ...(mod ? [{ key: modKey, name: C.mod, color: c.s2, unit: u }] : []),
  ];
  return (
    <ChartCard
      id="aberturas"
      title={C.title}
      sub={C.sub}
      legend={[
        { name: C.std, color: c.s1, kind: 'line' },
        ...(mod ? [{ name: C.mod, color: c.s2, kind: 'line' as const }] : []),
      ]}
      table={
        <DataTable
          caption={C.caption(u)}
          columns={[
            { key: 'speed', label: T_SPEED() },
            { key: 'dpaStd', label: C.col('DPA', 'std', u) },
            ...(mod ? [{ key: 'dpaMod', label: C.col('DPA', 'mod', u) }] : []),
            { key: 'avStd', label: C.col('AV', 'std', u) },
            ...(mod ? [{ key: 'avMod', label: C.col('AV', 'mod', u) }] : []),
          ]}
          rows={rows as unknown as Record<string, number | null>[]}
        />
      }
    >
      <div className="spread-pair">
        <div>
          <h4 className="chart-sub" style={{ fontWeight: 600 }}>
            DPA [{u}]
          </h4>
          <SpeedLineChart
            rows={rows as unknown as Record<string, number | null>[]}
            series={mk('dpaStd', 'dpaMod')}
            yUnit={u}
            ariaLabel={C.ariaDpa}
          />
        </div>
        <div>
          <h4 className="chart-sub" style={{ fontWeight: 600 }}>
            AV [{u}]
          </h4>
          <SpeedLineChart
            rows={rows as unknown as Record<string, number | null>[]}
            series={mk('avStd', 'avMod')}
            yUnit={u}
            ariaLabel={C.ariaAv}
          />
        </div>
      </div>
    </ChartCard>
  );
}
