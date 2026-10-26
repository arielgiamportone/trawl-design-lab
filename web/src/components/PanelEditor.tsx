import { useId, useState } from 'react';
import type { NetSpec } from '../api/client';
import { useT } from '../i18n';
import { toInput } from '../lib/format';
import { PLANE_LABELS, SECTION_LABELS } from '../lib/labels';
import {
  countEdits,
  isEdited,
  PANEL_FIELD_ORDER,
  PANEL_FIELDS,
  validateField,
  withEdit,
  type PanelEdits,
  type PanelField,
} from '../lib/panels';
import { useCase } from '../state/useCase';

export function PanelEditor() {
  const { state, update, specs } = useCase();
  const T = useT();
  const P = T.expert.panels;
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
          <h2 className="section-title">{P.title}</h2>
          <p className="section-sub">{P.sub}</p>
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          {state.netModified && (
            <div className="segmented" role="group" aria-label={P.netToEdit}>
              <button type="button" aria-pressed={v === 'std'} onClick={() => setVariant('std')}>
                {T.labels.variantsTitle.std}
              </button>
              <button type="button" aria-pressed={v === 'mod'} onClick={() => setVariant('mod')}>
                {T.labels.variantsTitle.mod}
              </button>
            </div>
          )}
          <button
            type="button"
            className="btn small"
            onClick={() => setEdits(() => ({}))}
            disabled={Object.keys(edits).length === 0}
          >
            {P.resetNet}
          </button>
        </div>
      </div>
      {!spec ? (
        <p className="empty">{P.loadingSpec}</p>
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
  const P = useT().expert.panels;
  const n = countEdits(spec, edits);

  const onChange = (
    pid: string,
    field: PanelField,
    text: string,
    original: number | null | undefined,
  ) => setEdits((e) => withEdit(e, pid, field, text, original));

  return (
    <>
      <p className="legend-inline" style={{ marginBottom: 8 }}>
        <span className="swatch-edited" aria-hidden="true" />
        {P.edited(n)}
        <span className="sr-only">{P.editedSr}</span>
      </p>
      <div className="table-wrap">
        <table className="data panels">
          <caption className="sr-only">{P.caption(spec.name)}</caption>
          <thead>
            <tr>
              <th scope="col">{P.panel}</th>
              <th scope="col">{P.plane}</th>
              <th scope="col">{P.section}</th>
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
                        aria-label={P.cellLabel(PANEL_FIELDS[f].label, p.id)}
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
        {P.help}
      </p>
    </>
  );
}
