import { useState } from 'react';
import type { DesignData } from '../api/result';
import { useT } from '../i18n';
import { diffSummaries } from '../lib/diff';
import { fmt, fmtDelta, fmtPct } from '../lib/format';
import { at, displayRows } from '../lib/series';
import { useChartColors } from '../lib/theme';
import { fmtU, toDisplay, unitLabel } from '../lib/units';
import { useCase } from '../state/useCase';
import { ChartCard, DataTable, type SeriesDef } from './charts/ChartParts';
import { SpeedLineChart } from './charts/SpeedLineChart';

/** Valor de una celda (número en el sistema de unidades activo, o texto). */
const val = (v: number | string | null, unit: string) =>
  typeof v === 'number' ? fmtU(v, unit, { unit: false }) : fmt(v);

function overlay(a: DesignData, b: DesignData, pick: (d: DesignData) => (number | null)[]) {
  const speeds = [...new Set([...a.case.speeds_kn, ...b.case.speeds_kn])].sort((x, y) => x - y);
  const pa = pick(a);
  const pb = pick(b);
  return speeds.map((speed) => ({
    speed,
    a: at(pa, a.case.speeds_kn.indexOf(speed)),
    b: at(pb, b.case.speeds_kn.indexOf(speed)),
  }));
}

export function Compare() {
  const { design, pinned, pin, unpin } = useCase();
  const c = useChartColors();
  const [onlyChanged, setOnlyChanged] = useState(true);
  const T = useT();
  const C = T.expert.compare;
  const b = design.data;
  const a = pinned?.data;

  const slots = (
    <div className="compare-head">
      <div className="compare-slot">
        <span className="slot-tag" style={{ background: c.s3 }} aria-hidden="true">
          A
        </span>
        <div className="slot-body">
          <strong>{C.aTitle}</strong>
          {pinned ? C.pinnedAt(pinned.label, pinned.at) : C.nonePinned}
          <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn small primary" onClick={pin} disabled={!b}>
              {pinned ? C.replace : C.pin}
            </button>
            {pinned && (
              <button type="button" className="btn small" onClick={unpin}>
                {C.unpin}
              </button>
            )}
          </div>
        </div>
      </div>
      <div className="compare-slot">
        <span className="slot-tag" style={{ background: c.s1 }} aria-hidden="true">
          B
        </span>
        <div className="slot-body">
          <strong>{C.bTitle}</strong>
          {b
            ? `${String(b.summary.net_id)} · ${String(b.summary.vessel_id)} · ${b.case.compat === 'excel' ? 'Excel' : C.corrected}`
            : C.calculating}
          <div style={{ marginTop: 6 }}>{C.bHelp}</div>
        </div>
      </div>
    </div>
  );

  if (!a || !b) {
    return (
      <div>
        <h2 className="section-title" style={{ marginBottom: 12 }}>
          {C.title}
        </h2>
        {slots}
        <p className="empty">{C.empty}</p>
      </div>
    );
  }

  const rows = diffSummaries(a.summary, b.summary);
  const shown = onlyChanged ? rows.filter((r) => r.changed) : rows;
  const nSig = rows.filter((r) => r.significant).length;
  const series: SeriesDef[] = [
    { key: 'a', name: C.aPinned, color: c.s3 },
    { key: 'b', name: C.bLive, color: c.s1 },
  ];
  const legend = [
    { name: C.aPinned, color: c.s3, kind: 'line' as const },
    { name: C.bLive, color: c.s1, kind: 'line' as const },
  ];
  const kgf = unitLabel('kgf');
  const m = unitLabel('m');
  const ab = (unit: string) => ({ a: unit, b: unit });
  const demand = displayRows(
    overlay(a, b, (d) => d.result.performance.demand.std),
    ab('kgf'),
  );
  const avail = displayRows(
    overlay(
      a,
      b,
      (d) => d.result.performance.windows[d.result.performance.design_key]?.available_kgf ?? [],
    ),
    ab('kgf'),
  );
  const av = displayRows(
    overlay(a, b, (d) => d.result.spread.vertical.fridman.std.av_m),
    ab('m'),
  );
  const rn = displayRows(
    overlay(a, b, (d) => d.result.drag.rn.std),
    ab('kgf'),
  );
  const speedCol = { key: 'speed', label: T.charts.speedAxis };

  return (
    <div className={design.isFetching ? 'stale' : undefined}>
      <h2 className="section-title" style={{ marginBottom: 12 }}>
        {C.title}
      </h2>
      {slots}
      <div className="panel-toolbar">
        <p className="section-sub" role="status">
          {C.status(rows.filter((r) => r.changed).length, nSig)}
        </p>
        <label className="toggle-line">
          <input
            type="checkbox"
            checked={onlyChanged}
            onChange={(e) => setOnlyChanged(e.target.checked)}
          />
          {C.onlyChanged}
        </label>
      </div>
      <div className="table-wrap" style={{ marginBottom: 16 }}>
        <table className="data" data-testid="compare-table">
          <thead>
            <tr>
              <th scope="col">{T.expert.summary.quantity}</th>
              <th scope="col" className="num">
                A
              </th>
              <th scope="col" className="num">
                B
              </th>
              <th scope="col" className="num col-abs">
                B − A
              </th>
              <th scope="col" className="num">
                Δ %
              </th>
              <th scope="col">{T.expert.summary.unit}</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  {C.identical}
                </td>
              </tr>
            )}
            {shown.map((r) => (
              <tr key={r.key} className={r.significant ? 'diff-sig' : undefined} data-key={r.key}>
                <th scope="row" style={{ fontWeight: r.significant ? 650 : 500 }}>
                  {r.label}
                </th>
                <td className="num">{val(r.a, r.unit)}</td>
                <td className="num">{val(r.b, r.unit)}</td>
                <td className="num col-abs">
                  {r.abs === null
                    ? r.changed
                      ? C.changes
                      : ''
                    : fmtDelta(toDisplay(r.abs, r.unit))}
                </td>
                <td className="num">
                  {r.pct === null ? (
                    '—'
                  ) : (
                    <span>
                      {r.pct > 0 ? '▲ ' : r.pct < 0 ? '▼ ' : ''}
                      {fmtPct(r.pct)}
                    </span>
                  )}
                </td>
                <td className="unit">{r.unit ? unitLabel(r.unit) : ''}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="charts-grid">
        <ChartCard
          id="cmp-resistencia"
          title={C.totalTitle}
          sub={C.totalSub}
          legend={[...legend, { name: C.availThin, color: c.text2, kind: 'thin' }]}
          table={
            <DataTable
              caption={C.totalCaption}
              columns={[
                speedCol,
                { key: 'a', label: `A [${kgf}]` },
                { key: 'b', label: `B [${kgf}]` },
              ]}
              rows={demand}
            />
          }
        >
          <SpeedLineChart
            rows={demand.map((r, i) => ({
              ...r,
              availA: avail[i]?.a ?? null,
              availB: avail[i]?.b ?? null,
            }))}
            series={[
              { key: 'availA', name: C.availOf('A'), color: c.s3, width: 1, quiet: true },
              { key: 'availB', name: C.availOf('B'), color: c.s1, width: 1, quiet: true },
              ...series,
            ]}
            yUnit={kgf}
            ariaLabel={C.totalAria}
          />
        </ChartCard>
        <ChartCard
          id="cmp-rn"
          title={C.rnTitle}
          legend={legend}
          table={
            <DataTable
              caption={C.rnCaption}
              columns={[
                speedCol,
                { key: 'a', label: `A [${kgf}]` },
                { key: 'b', label: `B [${kgf}]` },
              ]}
              rows={rn}
            />
          }
        >
          <SpeedLineChart rows={rn} series={series} yUnit={kgf} ariaLabel={C.rnAria} />
        </ChartCard>
        <ChartCard
          id="cmp-av"
          title={C.avTitle}
          legend={legend}
          table={
            <DataTable
              caption={C.avCaption}
              columns={[speedCol, { key: 'a', label: `A [${m}]` }, { key: 'b', label: `B [${m}]` }]}
              rows={av}
            />
          }
        >
          <SpeedLineChart
            rows={av}
            series={series.map((s) => ({ ...s, unit: m }))}
            yUnit={m}
            ariaLabel={C.avAria}
          />
        </ChartCard>
      </div>
    </div>
  );
}
