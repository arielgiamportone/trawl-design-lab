import { useId } from 'react';
import type { Panel } from '../../api/client';
import { useT } from '../../i18n';
import { toInput } from '../../lib/format';
import { HelpTip } from '../HelpTip';
import { PLANE_LABELS, SECTION_LABELS } from '../../lib/labels';
import {
  currentValue,
  isEdited,
  MESH_ORIENTATIONS,
  orientationOf,
  PANEL_FIELD_ORDER,
  PANEL_FIELDS,
  validateField,
  type MeshOrientation,
  type PanelEdits,
  type PanelField,
} from '../../lib/panels';

interface Props {
  panel: Panel;
  edits: PanelEdits;
  onEdit: (field: PanelField, text: string) => void;
  /** Cambio de la orientación de la malla (sin él, el selector no se muestra). */
  onOrientation?: (value: MeshOrientation) => void;
  onReset: () => void;
  onClose: () => void;
}

/** Datos del panel seleccionado, con −/+ en los campos enteros. */
export function PanelInspector({ panel, edits, onEdit, onOrientation, onReset, onClose }: Props) {
  const ids = useId();
  const T = useT().interactive.inspector;
  const pe = edits[panel.id] ?? {};
  const orientation = orientationOf(panel, edits);
  const presetOrientation = orientationOf(panel, {});
  const anyEdited =
    PANEL_FIELD_ORDER.some((f) => isEdited(panel, f, pe[f])) || orientation !== presetOrientation;
  return (
    <section className="inspector" aria-labelledby={`${ids}-t`} data-testid="panel-inspector">
      <div className="inspector-head">
        <h3 id={`${ids}-t`}>
          {T.panel(panel.id)}
          {panel.name && <span className="pname"> · {panel.name}</span>}
        </h3>
        <button
          type="button"
          className="btn small ghost"
          onClick={onClose}
          aria-label={T.close}
        >
          ✕
        </button>
      </div>
      <p className="help">
        {SECTION_LABELS[panel.section] ?? panel.section} ·{' '}
        {T.plane(PLANE_LABELS[panel.plane] ?? panel.plane)}
      </p>
      {PANEL_FIELD_ORDER.map((f) => {
        const rule = PANEL_FIELDS[f];
        const text = pe[f];
        const original = panel[f] as number | null | undefined;
        const res = text !== undefined ? validateField(f, text) : null;
        const value = currentValue(panel, edits, f);
        const step = (d: number) => {
          if (value === null) return;
          const next = Math.max(rule.exclusiveMin ? rule.min + 1 : rule.min, value + d);
          onEdit(f, String(next));
        };
        const id = `${ids}-${f}`;
        return (
          <div className={`insp-row${isEdited(panel, f, text) ? ' edited' : ''}`} key={f}>
            <label htmlFor={id}>
              {rule.label}
              {rule.unit && <span className="unit"> [{rule.unit}]</span>}
            </label>
            <div className="insp-input">
              {rule.integer && (
                <button
                  type="button"
                  className="btn small"
                  onClick={() => step(-1)}
                  aria-label={T.minus(rule.label)}
                >
                  −
                </button>
              )}
              <input
                id={id}
                type="text"
                inputMode={rule.integer ? 'numeric' : 'decimal'}
                autoComplete="off"
                value={text ?? toInput(original)}
                aria-invalid={res !== null && !res.ok ? true : undefined}
                onChange={(e) => onEdit(f, e.target.value)}
              />
              {rule.integer && (
                <button
                  type="button"
                  className="btn small"
                  onClick={() => step(1)}
                  aria-label={T.plus(rule.label)}
                >
                  +
                </button>
              )}
            </div>
            {res && !res.ok && <p className="field-error">{res.error}</p>}
          </div>
        );
      })}
      {onOrientation && (
        <div className={`insp-row${orientation !== presetOrientation ? ' edited' : ''}`}>
          <label htmlFor={`${ids}-orient`}>
            {T.orientation} <HelpTip topic="mesh_orientation" label={T.orientation} />
          </label>
          <div className="insp-input">
            <select
              id={`${ids}-orient`}
              value={orientation}
              onChange={(e) => onOrientation(e.target.value as MeshOrientation)}
            >
              {MESH_ORIENTATIONS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>
          {orientation === 'square' && (
            <p className="help">
              {T.squareHelp}
            </p>
          )}
        </div>
      )}
      <button type="button" className="btn small" onClick={onReset} disabled={!anyEdited}>
        {T.reset}
      </button>
    </section>
  );
}
