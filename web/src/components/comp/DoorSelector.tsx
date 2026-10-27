import { useMutation } from '@tanstack/react-query';
import { useState } from 'react';
import {
  api,
  ApiError,
  type DoorCandidateOut,
  type DoorSelectRequest,
  type DoorSelectResponse,
} from '../../api/client';
import { useT } from '../../i18n';
import { REGION_LABEL } from '../../lib/components';
import { fmtFixed, fmtPct } from '../../lib/format';
import { toDisplay, unitLabel } from '../../lib/units';
import { useCase } from '../../state/useCase';

/** Tipos de portón con polar representativa (``trawlkit.rigging.polars.DOOR_TYPES``). */
const DOOR_TYPES = ['flat', 'v', 'oval', 'cambered', 'multifoil', 'high_aspect'] as const;

/**
 * «Elegir portón» (Fase 19.3): portones del catálogo que alcanzan la superficie equivalente a la
 * requerida por el caso (A₂ = A₁·CL₁/CL₂ + 10 %, Seafish 1993), con el peso, el ángulo de ataque
 * recomendado y el largo de las patas de gallo.
 */
export function DoorSelector() {
  const { committed, state, update } = useCase();
  const T = useT().components;
  const D = T.doorSel;
  const [type, setType] = useState('');
  const [region, setRegion] = useState('');
  const [genericOnly, setGenericOnly] = useState(false);
  const run = useMutation<DoorSelectResponse, Error, DoorSelectRequest>({
    mutationFn: (req) => api.selectDoors(req),
  });

  const start = () => {
    if (!committed) return;
    run.mutate({
      net: committed.net,
      vessel: committed.vessel,
      door: committed.door,
      params: committed.params,
      components: committed.components ?? [],
      compat: 'corrected',
      types: type ? [type] : null,
      region: region || null,
      generic_only: genericOnly,
      margin: 0.1,
      max_results: 20,
      include_light: true,
    });
  };
  const res = run.data;
  const area = (v: number) => `${fmtFixed(toDisplay(v, 'm²'), 2)} ${unitLabel('m²')}`;
  const weight = (c: DoorCandidateOut) =>
    c.weight_air_kg == null
      ? D.noWeight
      : `${fmtFixed(toDisplay(c.weight_air_kg, 'kg'), 0)} ${unitLabel('kg')}`;
  const angle = (c: DoorCandidateOut) => {
    const r = c.attack_angle;
    if (!r) return `${fmtFixed(c.angle_deg, 1)}°`;
    return r.min_deg === r.max_deg
      ? `${fmtFixed(r.min_deg, 0)}°`
      : `${fmtFixed(r.min_deg, 0)}–${fmtFixed(r.max_deg, 0)}°`;
  };
  const backstrop = (c: DoorCandidateOut) => {
    const [lo, hi] = c.backstrop_m ?? [];
    if (lo == null || hi == null) return '—';
    const m = (v: number) => fmtFixed(toDisplay(v, 'm'), 1);
    return `${m(lo)}–${m(hi)} ${unitLabel('m')}`;
  };

  return (
    <div className="door-selector" data-testid="door-selector">
      <p className="section-sub">{D.intro}</p>
      <div className="catalog-filters">
        <label className="inline-field">
          {D.typeLabel}
          <select aria-label={D.typeLabel} value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">{D.anyType}</option>
            {DOOR_TYPES.map((k) => (
              <option key={k} value={k}>
                {D.types[k]}
              </option>
            ))}
          </select>
        </label>
        <label className="inline-field">
          {T.port}
          <select
            aria-label={T.portAria}
            value={region}
            onChange={(e) => setRegion(e.target.value)}
          >
            <option value="">{T.anyRegion}</option>
            {Object.entries(REGION_LABEL).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={genericOnly}
            onChange={(e) => setGenericOnly(e.target.checked)}
          />
          {T.genericOnly}
        </label>
        <button
          type="button"
          className="btn primary"
          disabled={!committed || run.isPending}
          onClick={start}
        >
          {run.isPending ? D.searching : D.search}
        </button>
      </div>
      {run.error && (
        <p className="alert crit" role="alert">
          {run.error instanceof ApiError && run.error.status ? T.errorStatus(run.error.status) : ''}
          {run.error.message}
        </p>
      )}
      {res && (
        <>
          <p className="help" data-testid="door-required">
            {D.required(area(res.required_m2), String(res.case_door.id ?? ''))}
          </p>
          {res.candidates.length === 0 ? (
            <p className="help">{D.none}</p>
          ) : (
            <div className="table-wrap">
              <table className="data" aria-label={D.table}>
                <thead>
                  <tr>
                    <th scope="col">{D.colDoor}</th>
                    <th scope="col">{D.colType}</th>
                    <th scope="col">{D.colArea}</th>
                    <th scope="col">{D.colRequired}</th>
                    <th scope="col">{D.colMargin}</th>
                    <th scope="col">{D.colWeight}</th>
                    <th scope="col">{D.colAngle}</th>
                    <th scope="col">{D.colBackstrop}</th>
                    <th scope="col">
                      <span className="sr-only">{D.colAction}</span>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {res.candidates.map((c) => {
                    const active = state.door === c.id;
                    return (
                      <tr key={c.id} data-testid="door-candidate">
                        <th scope="row">
                          {c.name}
                          {c.generic && <span className="badge good"> {T.generic}</span>}
                          {c.warnings.length > 0 && (
                            <ul className="issues">
                              {c.warnings.map((w, k) => (
                                <li key={k} className="warn">
                                  {w}
                                </li>
                              ))}
                            </ul>
                          )}
                        </th>
                        <td>{c.type_label ?? c.type ?? '—'}</td>
                        <td>{area(c.area_m2)}</td>
                        <td>
                          {area(c.required_m2)}
                          {c.margin_applied && <span className="help"> {D.marginApplied}</span>}
                        </td>
                        <td>{fmtPct(c.area_margin * 100, 0)}</td>
                        <td>
                          {weight(c)}
                          {c.weight_status === 'light' && (
                            <span className="badge warn"> {D.light}</span>
                          )}
                        </td>
                        <td>{angle(c)}</td>
                        <td>{backstrop(c)}</td>
                        <td>
                          <button
                            type="button"
                            className="btn"
                            disabled={active}
                            onClick={() => update((s) => ({ ...s, door: c.id }))}
                          >
                            {active ? T.isCase : D.use}
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
          {res.rejected > 0 && <p className="help">{D.rejected(res.rejected)}</p>}
          {res.notes.length > 0 && (
            <ul className="issues">
              {res.notes.map((n, k) => (
                <li key={k} className="warn">
                  {n}
                </li>
              ))}
            </ul>
          )}
          <details>
            <summary>{D.rules}</summary>
            <ul>
              {res.rules.map((r, k) => (
                <li key={k}>
                  {r.rule} ({r.document}, {r.page})
                </li>
              ))}
            </ul>
          </details>
        </>
      )}
    </div>
  );
}
