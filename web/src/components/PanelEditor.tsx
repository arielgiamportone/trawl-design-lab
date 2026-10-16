import { useId, useState } from 'react';
import type { NetSpec } from '../api/client';
import { toInput } from '../lib/format';
import { PLANE_LABELS, SECTION_LABELS } from '../lib/labels';
import {
  countEdits,
  isEdited,
  PANEL_FIELD_ORDER,
  PANEL_FIELDS,
  validateField,
  type PanelEdits,
  type PanelField,
} from '../lib/panels';
import { useCase } from '../state/useCase';

export function PanelEditor() {
  const { state, update, specs } = useCase();
  const [variant, setVariant] = useState<'std' | 'mod'>('std');
  const v = state.netModified ? variant : 'std';
  const spec = specs[v];
  const edits = state.edits[v];

  const setEdits = (fn: (e: PanelEdits) => PanelEdits) =>
    update((s) => ({ ...s, edits: { ...s.edits, [v]: fn(s.edits[v]) } }));

  return (
    <div>
      <div className="panel-toolbar">
        <div>
          <h2 className="section-title">Editor de paneles</h2>
          <p className="section-sub">
            Edite mallas, malleros e hilos; el caso se recalcula con la red modificada en línea.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {state.netModified && (
            <div className="segmented" role="group" aria-label="Red a editar">
              <button type="button" aria-pressed={v === 'std'} onClick={() => setVariant('std')}>
                Estándar
              </button>
              <button type="button" aria-pressed={v === 'mod'} onClick={() => setVariant('mod')}>
                Modificada
              </button>
            </div>
          )}
          <button
            type="button"
            className="btn small"
            onClick={() => setEdits(() => ({}))}
            disabled={Object.keys(edits).length === 0}
          >
            Restablecer red
          </button>
        </div>
      </div>
      {!spec ? (
        <p className="empty">Cargando la especificación de la red…</p>
      ) : (
        <PanelTable spec={spec} edits={edits} setEdits={setEdits} />
      )}
    </div>
  );
}

interface TableProps {
  spec: NetSpec;
  edits: PanelEdits;
  setEdits: (fn: (e: PanelEdits) => PanelEdits) => void;
}

export function PanelTable({ spec, edits, setEdits }: TableProps) {
  const ids = useId();
  const n = countEdits(spec, edits);

  const onChange = (
    pid: string,
    field: PanelField,
    text: string,
    original: number | null | undefined,
  ) =>
    setEdits((e) => {
      const next: PanelEdits = { ...e, [pid]: { ...e[pid], [field]: text } };
      // si vuelve al valor original y es válido, se quita la edición
      const r = validateField(field, text);
      if ((r.ok && r.value === (original ?? null)) || (text.trim() === '' && original == null)) {
        const p = { ...next[pid] };
        delete p[field];
        if (Object.keys(p).length === 0) delete next[pid];
        else next[pid] = p;
      }
      return next;
    });

  return (
    <>
      <p className="legend-inline" style={{ marginBottom: 8 }}>
        <span className="swatch-edited" aria-hidden="true" />
        {n === 0
          ? 'Sin cambios respecto del preset.'
          : `${n} ${n === 1 ? 'celda editada' : 'celdas editadas'} respecto del preset.`}
        <span className="sr-only">Las celdas editadas se marcan con fondo amarillo.</span>
      </p>
      <div className="table-wrap">
        <table className="data panels">
          <caption className="sr-only">Paneles de la red {spec.name}</caption>
          <thead>
            <tr>
              <th scope="col">Panel</th>
              <th scope="col">Plano</th>
              <th scope="col">Sección</th>
              {PANEL_FIELD_ORDER.map((f) => (
                <th scope="col" key={f} className="num" title={PANEL_FIELDS[f].label}>
                  {PANEL_FIELDS[f].short}
                  {PANEL_FIELDS[f].unit && <span className="unit"> [{PANEL_FIELDS[f].unit}]</span>}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {spec.panels.map((p) => (
              <tr key={p.id} data-panel={p.id}>
                <th scope="row" className="pid">
                  {p.id}
                  {p.name && <span className="pname">{p.name}</span>}
                </th>
                <td>{PLANE_LABELS[p.plane] ?? p.plane}</td>
                <td>{SECTION_LABELS[p.section] ?? p.section}</td>
                {PANEL_FIELD_ORDER.map((f) => {
                  const text = edits[p.id]?.[f];
                  const original = p[f] as number | null | undefined;
                  const value = text ?? toInput(original);
                  const res = text !== undefined ? validateField(f, text) : null;
                  const invalid = res !== null && !res.ok;
                  const edited = isEdited(p, f, text);
                  const errId = `${ids}-${p.id}-${f}-err`;
                  return (
                    <td
                      key={f}
                      className={`num${edited ? ' edited' : ''}${invalid ? ' invalid' : ''}`}
                    >
                      <input
                        type="text"
                        inputMode={PANEL_FIELDS[f].integer ? 'numeric' : 'decimal'}
                        autoComplete="off"
                        aria-label={`${PANEL_FIELDS[f].label} del panel ${p.id}`}
                        aria-invalid={invalid || undefined}
                        aria-describedby={invalid ? errId : undefined}
                        data-field={f}
                        value={value}
                        placeholder={original == null ? '—' : undefined}
                        onChange={(e) => onChange(p.id, f, e.target.value, original)}
                      />
                      {res && !res.ok && (
                        <span className="cell-error" id={errId}>
                          {res.error}
                        </span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="help" style={{ marginTop: 8 }}>
        «Mallas boca» y «mallas bolsa» son los bordes del panel más cercanos a la boca y a la bolsa;
        U1 es el coeficiente de armado horizontal (0–1].
      </p>
    </>
  );
}
