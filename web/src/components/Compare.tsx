import { useState } from 'react';
import type { DesignData } from '../api/result';
import { diffSummaries } from '../lib/diff';
import { fmt, fmtDelta, fmtPct } from '../lib/format';
import { at } from '../lib/series';
import { useChartColors } from '../lib/theme';
import { useCase } from '../state/useCase';
import { ChartCard, DataTable, type SeriesDef } from './charts/ChartParts';
import { SpeedLineChart } from './charts/SpeedLineChart';

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
  const b = design.data;
  const a = pinned?.data;

  const slots = (
    <div className="compare-head">
      <div className="compare-slot">
        <span className="slot-tag" style={{ background: c.s3 }} aria-hidden="true">
          A
        </span>
        <div className="slot-body">
          <strong>A · resultado fijado</strong>
          {pinned
            ? `${pinned.label} · fijado a las ${pinned.at}`
            : 'Todavía no fijó ningún resultado.'}
          <div style={{ display: 'flex', gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
            <button type="button" className="btn small primary" onClick={pin} disabled={!b}>
              {pinned ? 'Reemplazar A por el actual' : 'Fijar el resultado actual como A'}
            </button>
            {pinned && (
              <button type="button" className="btn small" onClick={unpin}>
                Quitar A
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
          <strong>B · caso en vivo</strong>
          {b
            ? `${String(b.summary.net_id)} · ${String(b.summary.vessel_id)} · ${b.case.compat === 'excel' ? 'Excel' : 'corregido'}`
            : 'Calculando…'}
          <div style={{ marginTop: 6 }}>
            Cambie red, buque, parámetros o paneles y compare con A.
          </div>
        </div>
      </div>
    </div>
  );

  if (!a || !b) {
    return (
      <div>
        <h2 className="section-title" style={{ marginBottom: 12 }}>
          Comparar casos
        </h2>
        {slots}
        <p className="empty">
          Fije el resultado actual como «A», modifique el caso y vea aquí las diferencias con el
          resultado en vivo «B».
        </p>
      </div>
    );
  }

  const rows = diffSummaries(a.summary, b.summary);
  const shown = onlyChanged ? rows.filter((r) => r.changed) : rows;
  const nSig = rows.filter((r) => r.significant).length;
  const series: SeriesDef[] = [
    { key: 'a', name: 'A (fijado)', color: c.s3 },
    { key: 'b', name: 'B (en vivo)', color: c.s1 },
  ];
  const legend = [
    { name: 'A (fijado)', color: c.s3, kind: 'line' as const },
    { name: 'B (en vivo)', color: c.s1, kind: 'line' as const },
  ];
  const demand = overlay(a, b, (d) => d.result.performance.demand.std);
  const avail = overlay(
    a,
    b,
    (d) => d.result.performance.windows[d.result.performance.design_key]?.available_kgf ?? [],
  );
  const av = overlay(a, b, (d) => d.result.spread.vertical.fridman.std.av_m);
  const rn = overlay(a, b, (d) => d.result.drag.rn.std);

  return (
    <div className={design.isFetching ? 'stale' : undefined}>
      <h2 className="section-title" style={{ marginBottom: 12 }}>
        Comparar casos
      </h2>
      {slots}
      <div className="panel-toolbar">
        <p className="section-sub" role="status">
          {rows.filter((r) => r.changed).length} magnitudes cambian · {nSig} con variación ≥ 1 %
          (resaltadas).
        </p>
        <label className="toggle-line">
          <input
            type="checkbox"
            checked={onlyChanged}
            onChange={(e) => setOnlyChanged(e.target.checked)}
          />
          Mostrar sólo lo que cambia
        </label>
      </div>
      <div className="table-wrap" style={{ marginBottom: 16 }}>
        <table className="data" data-testid="compare-table">
          <thead>
            <tr>
              <th scope="col">Magnitud</th>
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
              <th scope="col">Unidad</th>
            </tr>
          </thead>
          <tbody>
            {shown.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  A y B son idénticos.
                </td>
              </tr>
            )}
            {shown.map((r) => (
              <tr key={r.key} className={r.significant ? 'diff-sig' : undefined} data-key={r.key}>
                <th scope="row" style={{ fontWeight: r.significant ? 650 : 500 }}>
                  {r.label}
                </th>
                <td className="num">{fmt(r.a)}</td>
                <td className="num">{fmt(r.b)}</td>
                <td className="num col-abs">
                  {r.abs === null ? (r.changed ? 'cambia' : '') : fmtDelta(r.abs)}
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
                <td className="unit">{r.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="charts-grid">
        <ChartCard
          id="cmp-resistencia"
          title="Resistencia total, red estándar"
          sub="Tiro disponible de diseño en línea fina"
          legend={[
            ...legend,
            { name: 'Tiro disponible (línea fina)', color: c.text2, kind: 'thin' },
          ]}
          table={
            <DataTable
              caption="Resistencia total A y B"
              columns={[
                { key: 'speed', label: 'Velocidad [kn]' },
                { key: 'a', label: 'A [kgf]' },
                { key: 'b', label: 'B [kgf]' },
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
              { key: 'availA', name: 'Tiro disponible A', color: c.s3, width: 1, quiet: true },
              { key: 'availB', name: 'Tiro disponible B', color: c.s1, width: 1, quiet: true },
              ...series,
            ]}
            yUnit="kgf"
            ariaLabel="Resistencia total de A y B en función de la velocidad"
          />
        </ChartCard>
        <ChartCard
          id="cmp-rn"
          title="Resistencia de la red (RN de diseño)"
          legend={legend}
          table={
            <DataTable
              caption="RN A y B"
              columns={[
                { key: 'speed', label: 'Velocidad [kn]' },
                { key: 'a', label: 'A [kgf]' },
                { key: 'b', label: 'B [kgf]' },
              ]}
              rows={rn}
            />
          }
        >
          <SpeedLineChart
            rows={rn}
            series={series}
            yUnit="kgf"
            ariaLabel="RN de A y B en función de la velocidad"
          />
        </ChartCard>
        <ChartCard
          id="cmp-av"
          title="Abertura vertical (Fridman), red estándar"
          legend={legend}
          table={
            <DataTable
              caption="AV A y B"
              columns={[
                { key: 'speed', label: 'Velocidad [kn]' },
                { key: 'a', label: 'A [m]' },
                { key: 'b', label: 'B [m]' },
              ]}
              rows={av}
            />
          }
        >
          <SpeedLineChart
            rows={av}
            series={series.map((s) => ({ ...s, unit: 'm' }))}
            yUnit="m"
            ariaLabel="Abertura vertical de A y B"
          />
        </ChartCard>
      </div>
    </div>
  );
}
