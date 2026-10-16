import { useId, useState } from 'react';
import type { DesignData } from '../../api/result';
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
import { useCase } from '../../state/useCase';
import { ChartCard, DataTable, type LegendItem, type SeriesDef } from './ChartParts';
import { COMPONENTS } from './components';
import { CompositionChart } from './CompositionChart';
import { SpeedLineChart } from './SpeedLineChart';

export function Charts() {
  const { design } = useCase();
  const d = design.data;
  if (!d)
    return <p className="empty">{design.isFetching ? 'Calculando…' : 'Sin resultados todavía.'}</p>;
  return <ChartsBody d={d} stale={design.isFetching} />;
}

function ChartsBody({ d, stale }: { d: DesignData; stale: boolean }) {
  const c = useChartColors();
  const ids = useId();
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
      <div className="charts-toolbar" role="group" aria-label="Opciones de los gráficos">
        <div className="field">
          <label htmlFor={`${ids}-prop`}>Hélice (tiro disponible)</label>
          <select id={`${ids}-prop`} value={prop} onChange={(e) => setProp(e.target.value)}>
            {props.map((p) => (
              <option key={p} value={p}>
                {PROPELLER_LABELS[p] ?? p}
                {p === designPropeller(d) ? ' · diseño' : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`${ids}-speed`}>Velocidad (composición)</label>
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
              Red (RN por método)
            </span>
            <div className="segmented" role="group" aria-labelledby={`${ids}-var`}>
              <button
                type="button"
                aria-pressed={variant === 'std'}
                onClick={() => setVariant('std')}
              >
                Estándar
              </button>
              <button
                type="button"
                aria-pressed={variant === 'mod'}
                onClick={() => setVariant('mod')}
              >
                Modificada
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
  const rows = pullRows(d, prop);
  const mod = hasModified(d);
  const w = perfWindow(d, prop, 'std');
  const win = feasibleWindow(w);
  const others = PULL_METHODS.filter(([k]) => k !== 'fridman_kgf');
  const series: SeriesDef[] = [
    ...others.map(([k, name]) => ({ key: k, name: `Tiro ${name}`, color: c.quiet, quiet: true })),
    {
      key: 'available',
      name: 'Tiro disponible (Fridman)',
      color: c.s3,
    },
    { key: 'demandStd', name: 'Resistencia estándar', color: c.s1 },
    ...(mod ? [{ key: 'demandMod', name: 'Resistencia modificada', color: c.s2 }] : []),
  ];
  const legend: LegendItem[] = [
    { name: 'Tiro disponible (Fridman)', color: c.s3, kind: 'line' },
    { name: 'Resistencia estándar', color: c.s1, kind: 'line' },
    ...(mod ? [{ name: 'Resistencia modificada', color: c.s2, kind: 'line' as const }] : []),
    { name: 'Otros métodos de tiro', color: c.quiet, kind: 'thin' },
    ...(win ? [{ name: 'Ventana remolcable', color: c.window, kind: 'area' as const }] : []),
  ];
  const vmax = w?.max_speed_kn ?? null;
  return (
    <ChartCard
      id="tiro"
      title="Tiro disponible vs resistencia total"
      sub={
        vmax !== null
          ? `Velocidad máxima remolcable (red estándar): ${fmtFixed(vmax, 2)} kn`
          : 'El tiro disponible no alcanza en el rango calculado.'
      }
      legend={legend}
      note="Gris: Prado–Dremière, Koyama, Nomura, Hamuro y su promedio (referencia)."
      table={
        <DataTable
          caption="Tiro disponible y resistencia total por velocidad"
          columns={[
            { key: 'speed', label: 'Velocidad [kn]' },
            ...series.map((s) => ({ key: s.key, label: `${s.name} [kgf]` })),
          ]}
          rows={rows}
        />
      }
    >
      <SpeedLineChart
        rows={rows}
        series={series}
        yUnit="kgf"
        window={win ? { ...win, label: 'remolcable' } : null}
        refX={vmax !== null ? { x: vmax, label: `Vmáx ${fmtFixed(vmax, 2)} kn` } : null}
        ariaLabel="Gráfico de tiro disponible por método y resistencia total en función de la velocidad"
      />
    </ChartCard>
  );
}

function DragCard({ d, c, variant }: { d: DesignData; c: ChartColors; variant: 'std' | 'mod' }) {
  const rows = dragRows(d, variant);
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
      title={`RN por los ${DRAG_METHODS.length} métodos · red ${variant === 'std' ? 'estándar' : 'modificada'}`}
      sub={`Método de diseño: ${dragMethodLabel(design)}`}
      legend={[
        { name: `${dragMethodLabel(design)} (diseño)`, color: c.s1, kind: 'line' },
        { name: `Otros ${DRAG_METHODS.length - 1} métodos`, color: c.quiet, kind: 'thin' },
      ]}
      note="Pase el cursor para ver los 13 valores ordenados a cada velocidad."
      table={
        <DataTable
          caption="Resistencia de la red por método [kgf]"
          columns={[
            { key: 'speed', label: 'Velocidad [kn]' },
            ...DRAG_METHODS.map(([k, n]) => ({ key: k, label: n })),
          ]}
          rows={rows}
        />
      }
    >
      <SpeedLineChart
        rows={rows}
        series={series}
        yUnit="kgf"
        sortTooltip
        ariaLabel="Gráfico de resistencia de la red por método en función de la velocidad"
      />
    </ChartCard>
  );
}

function CompositionCard({ d, idx, speed }: { d: DesignData; idx: number; speed: number }) {
  const c = useChartColors();
  const rows = composition(d, idx);
  const speedLabel = `${fmtFixed(speed, 1)} kn`;
  return (
    <ChartCard
      id="composicion"
      title={`Composición de la resistencia total a ${speedLabel}`}
      sub="Red + boyas + cables + portones (ROB)"
      legend={COMPONENTS.map((s) => ({ name: s.name, color: c[s.color], kind: 'rect' as const }))}
      table={
        <DataTable
          caption={`Composición de la resistencia total a ${speedLabel} [kgf]`}
          columns={[
            { key: 'variant', label: 'Red' },
            ...COMPONENTS.map((s) => ({ key: s.key, label: `${s.name} [kgf]` })),
            { key: 'total', label: 'Total [kgf]' },
          ]}
          rows={rows.map((r) => ({ ...r }))}
        />
      }
      note={rows
        .map(
          (r) =>
            `${r.variant}: red ${fmtFixed((r.rn / r.total) * 100, 1)} % · boyas ${fmtFixed((r.floats / r.total) * 100, 1)} % · cables ${fmtFixed((r.warps / r.total) * 100, 1)} % · portones ${fmtFixed((r.doors / r.total) * 100, 1)} %`,
        )
        .join(' — ')}
    >
      <CompositionChart rows={rows} speedLabel={speedLabel} />
    </ChartCard>
  );
}

function SpreadCard({ d, c }: { d: DesignData; c: ChartColors }) {
  const rows = spreadRows(d);
  const mod = hasModified(d);
  const mk = (std: string, modKey: string): SeriesDef[] => [
    { key: std, name: 'Red estándar', color: c.s1, unit: 'm' },
    ...(mod ? [{ key: modKey, name: 'Red modificada', color: c.s2, unit: 'm' }] : []),
  ];
  return (
    <ChartCard
      id="aberturas"
      title="Aberturas de Fridman vs velocidad"
      sub="DPA: distancia entre puntas de ala · AV: abertura vertical"
      legend={[
        { name: 'Red estándar', color: c.s1, kind: 'line' },
        ...(mod ? [{ name: 'Red modificada', color: c.s2, kind: 'line' as const }] : []),
      ]}
      table={
        <DataTable
          caption="DPA y AV de Fridman por velocidad [m]"
          columns={[
            { key: 'speed', label: 'Velocidad [kn]' },
            { key: 'dpaStd', label: 'DPA estándar [m]' },
            ...(mod ? [{ key: 'dpaMod', label: 'DPA modificada [m]' }] : []),
            { key: 'avStd', label: 'AV estándar [m]' },
            ...(mod ? [{ key: 'avMod', label: 'AV modificada [m]' }] : []),
          ]}
          rows={rows as unknown as Record<string, number | null>[]}
        />
      }
    >
      <div className="spread-pair">
        <div>
          <h4 className="chart-sub" style={{ fontWeight: 600 }}>
            DPA [m]
          </h4>
          <SpeedLineChart
            rows={rows as unknown as Record<string, number | null>[]}
            series={mk('dpaStd', 'dpaMod')}
            yUnit="m"
            ariaLabel="Distancia entre puntas de ala según Fridman en función de la velocidad"
          />
        </div>
        <div>
          <h4 className="chart-sub" style={{ fontWeight: 600 }}>
            AV [m]
          </h4>
          <SpeedLineChart
            rows={rows as unknown as Record<string, number | null>[]}
            series={mk('avStd', 'avMod')}
            yUnit="m"
            ariaLabel="Abertura vertical según Fridman en función de la velocidad"
          />
        </div>
      </div>
    </ChartCard>
  );
}
