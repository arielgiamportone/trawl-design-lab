import { useId } from 'react';
import { ApiError } from '../api/client';
import { fmtFixed } from '../lib/format';
import { countEdits } from '../lib/panels';
import { useCase } from '../state/useCase';
import type { Compat } from '../state/model';
import { ParamsForm } from './ParamsForm';

const COMPAT_HELP: Record<Compat, string> = {
  corrected: 'Aplica las fórmulas correctas: el modo recomendado para diseñar.',
  excel: 'Reproduce el libro Excel original con sus erratas, para validar contra él.',
};

export function CasePanel() {
  const { state, update, catalogs, errors, design, calculate, dirty, committed, specs } = useCase();
  const ids = useId();
  const nErrors = Object.keys(errors).length;
  const busy = design.isFetching;
  const err = design.error;
  const vesselValue = state.vessel ?? catalogs.vessels[0]?.id ?? '';
  const doorValue = state.door ?? catalogs.doors[0]?.id ?? '';
  const vessel = catalogs.vessels.find((v) => v.id === vesselValue);
  const door = catalogs.doors.find((d) => d.id === doorValue);
  const net = catalogs.nets.find((n) => n.id === state.net);
  const edited = countEdits(specs.std, state.edits.std) + countEdits(specs.mod, state.edits.mod);

  return (
    <aside className="card card-pad case-panel" aria-labelledby={`${ids}-title`}>
      <h2 className="section-title" id={`${ids}-title`}>
        Caso de diseño
        {edited > 0 && (
          <span className="badge warn">
            {edited} {edited === 1 ? 'celda editada' : 'celdas editadas'}
          </span>
        )}
      </h2>
      <p className="section-sub">
        Elija la red, el buque y el portón. El cálculo se actualiza solo.
      </p>

      {catalogs.error && (
        <div className="alert error" role="alert">
          <span>
            <strong>No se pudieron cargar los catálogos.</strong> {catalogs.error.message}
          </span>
        </div>
      )}

      <div className="field">
        <label htmlFor={`${ids}-net`}>Red</label>
        <select
          id={`${ids}-net`}
          value={state.net}
          onChange={(e) =>
            update((s) => ({
              ...s,
              net: e.target.value,
              edits: { ...s.edits, std: {} },
              scaled: null,
            }))
          }
        >
          {catalogs.nets.length === 0 && <option value={state.net}>{state.net}</option>}
          {catalogs.nets.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name ?? n.id}
            </option>
          ))}
        </select>
        {net?.description && <p className="help">{net.description}</p>}
        {state.scaled && (
          <div className="alert info" role="status" data-testid="scaled-net">
            <span>
              <strong>Red escalada s = {fmtFixed(state.scaled.s, 3)}</strong>
              {state.scaled.speed !== null &&
                ` · diseño optimizado a ${fmtFixed(state.scaled.speed, 2)} kn`}
              {state.netModified && !state.scaled.mod && ' (la variante modificada no se escaló)'}.{' '}
              <button
                type="button"
                className="btn small ghost"
                onClick={() => update((s) => ({ ...s, scaled: null, edits: { std: {}, mod: {} } }))}
              >
                Volver a la red del catálogo
              </button>
            </span>
          </div>
        )}
      </div>

      <div className="field">
        <label htmlFor={`${ids}-mod`}>Variante modificada (opcional)</label>
        <select
          id={`${ids}-mod`}
          value={state.netModified ?? ''}
          onChange={(e) =>
            update((s) => ({
              ...s,
              netModified: e.target.value || null,
              edits: { ...s.edits, mod: {} },
              scaled: s.scaled ? { ...s.scaled, mod: null } : null,
            }))
          }
        >
          <option value="">— Sin variante —</option>
          {catalogs.nets.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name ?? n.id}
            </option>
          ))}
        </select>
        <p className="help">Se calcula en paralelo y se compara con la red estándar.</p>
      </div>

      <div className="field">
        <label htmlFor={`${ids}-vessel`}>Buque</label>
        <select
          id={`${ids}-vessel`}
          value={vesselValue}
          onChange={(e) => update({ vessel: e.target.value })}
        >
          {catalogs.vessels.map((v) => (
            <option key={v.id} value={v.id}>
              {v.name ?? v.id}
            </option>
          ))}
        </select>
        {vessel && (
          <p className="help">
            {vessel.bhp} BHP
            {vessel.length_m ? ` · eslora ${String(vessel.length_m).replace('.', ',')} m` : ''}
          </p>
        )}
      </div>

      <div className="field">
        <label htmlFor={`${ids}-door`}>Portón</label>
        <select
          id={`${ids}-door`}
          value={doorValue}
          onChange={(e) => update({ door: e.target.value })}
        >
          {catalogs.doors.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        {door?.area_m2 != null && (
          <p className="help">
            Área {door.area_m2.toLocaleString('es-AR', { maximumFractionDigits: 2 })} m²
            {door.weight_air_kg != null ? ` · ${door.weight_air_kg} kg en aire` : ''}
          </p>
        )}
      </div>

      <fieldset className="field" style={{ border: 0, padding: 0, margin: '12px 0 0' }}>
        <legend
          className="label"
          style={{ fontSize: 13, fontWeight: 600, padding: 0, marginBottom: 4 }}
        >
          Modo de cálculo
        </legend>
        <div className="segmented full">
          {(['corrected', 'excel'] as const).map((c) => (
            <label key={c}>
              <input
                type="radio"
                name={`${ids}-compat`}
                value={c}
                checked={state.compat === c}
                onChange={() => update({ compat: c })}
              />
              {c === 'corrected' ? 'Corregido' : 'Reproducir Excel'}
            </label>
          ))}
        </div>
        <p className="help">{COMPAT_HELP[state.compat]}</p>
      </fieldset>

      <ParamsForm />

      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          onClick={calculate}
          disabled={nErrors > 0 || catalogs.loading}
          aria-describedby={`${ids}-status`}
        >
          Calcular
        </button>
      </div>
      <div className="status-line" id={`${ids}-status`} role="status" aria-live="polite">
        {busy ? (
          <>
            <span className="spinner" aria-hidden="true" /> Calculando…
          </>
        ) : nErrors > 0 ? (
          <span>
            Corrija {nErrors === 1 ? 'el valor marcado' : `los ${nErrors} valores marcados`} para
            calcular.
          </span>
        ) : dirty ? (
          <span>Cambios pendientes…</span>
        ) : design.isSuccess && committed ? (
          <span>Resultados al día.</span>
        ) : null}
      </div>
      {err && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {err instanceof ApiError && err.status ? `Error ${err.status}` : 'Error'}:
            </strong>{' '}
            {err.message}
          </span>
        </div>
      )}
    </aside>
  );
}
