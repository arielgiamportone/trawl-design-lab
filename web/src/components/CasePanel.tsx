import { useId } from 'react';
import { ApiError, type CatalogItem } from '../api/client';
import { msg, useT } from '../i18n';
import { fmtFixed, fmtNum } from '../lib/format';
import { fmtU, toDisplay, unitLabel } from '../lib/units';
import { countEdits } from '../lib/panels';
import { useCase } from '../state/useCase';
import type { Compat } from '../state/model';
import { ParamsForm } from './ParamsForm';
import { MyVesselForm } from './MyVesselForm';
import { myVesselFrom, vesselTypes } from '../lib/vessel';
import { usesMyVessel } from '../state/model';

/** Redes agrupadas por documento de origen, para el selector. */
function netGroups(nets: CatalogItem[]): [string, CatalogItem[]][] {
  const out = new Map<string, CatalogItem[]>();
  for (const n of nets) {
    const g = n.source
      ? (n.source.title.split(',')[0] ?? n.source.key)
      : msg().expert.case.faoGroup;
    out.set(g, [...(out.get(g) ?? []), n]);
  }
  return [...out];
}

export function CasePanel() {
  const { state, update, catalogs, errors, design, calculate, dirty, committed, specs } = useCase();
  const ids = useId();
  const T = useT();
  const C = T.expert.case;
  const nErrors = Object.keys(errors).length;
  const busy = design.isFetching;
  const err = design.error;
  const net = catalogs.nets.find((n) => n.id === state.net);
  // Red del catálogo FAO sin buque ni portón elegidos: la API arma su propio caso.
  const fromPlan = !!net?.vessel_hp && !state.netModified;
  const vesselValue = state.vessel ?? (fromPlan ? '' : (catalogs.vessels[0]?.id ?? ''));
  const doorValue = state.door ?? (fromPlan ? '' : (catalogs.doors[0]?.id ?? ''));
  const groups = netGroups(catalogs.nets);
  const vessel = catalogs.vessels.find((v) => v.id === vesselValue);
  const door = catalogs.doors.find((d) => d.id === doorValue);
  const edited = countEdits(specs.std, state.edits.std) + countEdits(specs.mod, state.edits.mod);
  const V = T.vessel;
  const mine = usesMyVessel(state);
  const types = vesselTypes(catalogs.vessels);

  return (
    <aside className="card card-pad case-panel" aria-labelledby={`${ids}-title`}>
      <h2 className="section-title" id={`${ids}-title`}>
        {C.title}
        {edited > 0 && <span className="badge warn">{C.editedCells(edited)}</span>}
      </h2>
      <p className="section-sub">{C.sub}</p>

      {catalogs.error && (
        <div className="alert error" role="alert">
          <span>
            <strong>{C.catalogError}</strong> {catalogs.error.message}
          </span>
        </div>
      )}

      <div className="field">
        <label htmlFor={`${ids}-net`}>{C.net}</label>
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
          {groups.map(([group, nets]) => (
            <optgroup key={group} label={group}>
              {nets.map((n) => (
                <option key={n.id} value={n.id}>
                  {n.name ?? n.id}
                  {n.status === 'draft' ? C.draft : ''}
                </option>
              ))}
            </optgroup>
          ))}
        </select>
        {net?.description && <p className="help">{net.description}</p>}
        {state.scaled && (
          <div className="alert info" role="status" data-testid="scaled-net">
            <span>
              <strong>{C.scaled(fmtFixed(state.scaled.s, 3))}</strong>
              {state.scaled.speed !== null && C.optimizedAt(fmtFixed(state.scaled.speed, 2))}
              {state.netModified && !state.scaled.mod && C.modNotScaled}.{' '}
              <button
                type="button"
                className="btn small ghost"
                onClick={() => update((s) => ({ ...s, scaled: null, edits: { std: {}, mod: {} } }))}
              >
                {C.backToCatalogue}
              </button>
            </span>
          </div>
        )}
      </div>

      <div className="field">
        <label htmlFor={`${ids}-mod`}>{C.modVariant}</label>
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
          <option value="">{C.noVariant}</option>
          {catalogs.nets.map((n) => (
            <option key={n.id} value={n.id}>
              {n.name ?? n.id}
            </option>
          ))}
        </select>
        <p className="help">{C.modHelp}</p>
      </div>

      {state.fromBatch && (
        <div className="alert info" role="status" data-testid="from-batch">
          <span>
            <strong>{C.fromBatch(state.fromBatch.label)}</strong>{' '}
            {C.fromBatchVessel(state.fromBatch.vessel.bhp, state.fromBatch.door?.name ?? null)}{' '}
            <button
              type="button"
              className="btn small ghost"
              onClick={() => update({ fromBatch: null })}
            >
              {C.useCatalogueVessel}
            </button>
          </span>
        </div>
      )}

      <div className="field">
        <label htmlFor={`${ids}-vessel`}>{C.vessel}</label>
        <select
          id={`${ids}-vessel`}
          value={vesselValue}
          disabled={mine}
          onChange={(e) => update({ vessel: e.target.value || null, fromBatch: null })}
        >
          {fromPlan && <option value="">{C.vesselFromPlan}</option>}
          {catalogs.vessels
            .filter((v) => !v.vessel_type)
            .map((v) => (
              <option key={v.id} value={v.id}>
                {v.name ?? v.id}
              </option>
            ))}
          {types.map((type) => (
            <optgroup key={type} label={V.types[type] ?? type}>
              {catalogs.vessels
                .filter((v) => v.vessel_type === type)
                .map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.name ?? v.id}
                    {v.status === 'draft' ? ` (${V.draft})` : ''}
                  </option>
                ))}
            </optgroup>
          ))}
        </select>
        {vessel && !mine && (
          <p className="help">
            {vessel.bhp} BHP
            {vessel.length_m ? ` · ${C.length(fmtU(vessel.length_m, 'm'))}` : ''}
          </p>
        )}
        <label className="check">
          <input
            type="checkbox"
            checked={mine}
            onChange={(e) =>
              update((s) => ({
                ...s,
                useMyVessel: e.target.checked,
                fromBatch: null,
                myVessel: s.myVessel ?? (e.target.checked ? myVesselFrom(vessel) : null),
              }))
            }
          />
          {V.useMine}
        </label>
      </div>
      {mine && <MyVesselForm />}

      <div className="field">
        <label htmlFor={`${ids}-door`}>{C.door}</label>
        <select
          id={`${ids}-door`}
          value={doorValue}
          onChange={(e) =>
            update((s) => ({
              ...s,
              door: e.target.value || null,
              fromBatch: s.fromBatch ? { ...s.fromBatch, door: null } : null,
            }))
          }
        >
          {fromPlan && <option value="">{C.doorFromPlan}</option>}
          {catalogs.doors.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
            </option>
          ))}
        </select>
        {door?.area_m2 != null && (
          <p className="help">
            {C.area(
              `${fmtNum(toDisplay(door.area_m2, 'm²'), { maximumFractionDigits: 2 })} ${unitLabel('m²')}`,
            )}
            {door.weight_air_kg != null
              ? ` · ${C.weightInAir(fmtU(door.weight_air_kg, 'kg'))}`
              : ''}
          </p>
        )}
      </div>

      <fieldset className="field" style={{ border: 0, padding: 0, margin: '12px 0 0' }}>
        <legend
          className="label"
          style={{ fontSize: 13, fontWeight: 600, padding: 0, marginBottom: 4 }}
        >
          {C.mode}
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
              {c === 'corrected' ? T.labels.compatCorrected : T.labels.compatExcel}
            </label>
          ))}
        </div>
        <p className="help">{C.compatHelp[state.compat as Compat]}</p>
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
          {C.calculate}
        </button>
      </div>
      <div className="status-line" id={`${ids}-status`} role="status" aria-live="polite">
        {busy ? (
          <>
            <span className="spinner" aria-hidden="true" /> {C.calculating}
          </>
        ) : nErrors > 0 ? (
          <span>{C.fix(nErrors)}</span>
        ) : dirty ? (
          <span>{C.pending}</span>
        ) : design.isSuccess && committed ? (
          <span>{C.upToDate}</span>
        ) : null}
      </div>
      {err && (
        <div className="alert error" role="alert">
          <span>
            <strong>
              {err instanceof ApiError && err.status ? C.errorStatus(err.status) : C.error}:
            </strong>{' '}
            {err.message}
          </span>
        </div>
      )}
    </aside>
  );
}
