import { useId, useState } from 'react';
import { useT } from '../../i18n';
import { PROPELLER_LABELS } from '../../lib/labels';
import { fmtU } from '../../lib/units';
import { filterVessels, myVesselFrom, vesselRegions, vesselTypes } from '../../lib/vessel';
import { REGION_LABEL } from '../../lib/components';
import { usesMyVessel } from '../../state/model';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';
import { MyVesselForm } from '../MyVesselForm';
import { ChoiceCards } from './ChoiceCards';

export function StepVessel({ onBatch }: { onBatch?: () => void }) {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const all = useT();
  const T = all.wizard.vessel;
  const V = all.vessel;
  const [type, setType] = useState('');
  const [region, setRegion] = useState('');
  const vessel = state.vessel ?? catalogs.vessels[0]?.id ?? '';
  const propDefault = String(
    catalogs.params.find((p) => p.name === 'ft_propeller')?.default ?? 'fixed_pitch',
  );
  const propeller = state.params.ft_propeller || propDefault;
  const mine = usesMyVessel(state);
  const types = vesselTypes(catalogs.vessels);
  const regions = vesselRegions(catalogs.vessels);
  const shown = filterVessels(catalogs.vessels, type, region);
  const selected = catalogs.vessels.find((v) => v.id === vessel);
  return (
    <>
      <p className="wizard-lead">{T.lead}</p>
      <div className="field">
        <label className="check">
          <input
            type="checkbox"
            checked={mine}
            onChange={(e) =>
              update((s) => ({
                ...s,
                useMyVessel: e.target.checked,
                fromBatch: null,
                myVessel: s.myVessel ?? (e.target.checked ? myVesselFrom(selected) : null),
              }))
            }
          />
          {V.useMine}
        </label>
      </div>
      {mine ? (
        <MyVesselForm />
      ) : catalogs.loading && catalogs.vessels.length === 0 ? (
        <p className="help">{T.loading}</p>
      ) : (
        <>
          {types.length > 0 && (
            <div className="filters-row" role="group" aria-label={V.filters.type}>
              <div className="field">
                <label htmlFor={`${ids}-type`}>{V.filters.type}</label>
                <select id={`${ids}-type`} value={type} onChange={(e) => setType(e.target.value)}>
                  <option value="">{V.filters.allTypes}</option>
                  <option value="book">{V.filters.book}</option>
                  {types.map((t) => (
                    <option key={t} value={t}>
                      {V.types[t] ?? t}
                    </option>
                  ))}
                </select>
              </div>
              {regions.length > 0 && (
                <div className="field">
                  <label htmlFor={`${ids}-region`}>{V.filters.region}</label>
                  <select
                    id={`${ids}-region`}
                    value={region}
                    onChange={(e) => setRegion(e.target.value)}
                  >
                    <option value="">{V.filters.allRegions}</option>
                    {regions.map((r) => (
                      <option key={r} value={r}>
                        {REGION_LABEL[r] ?? r}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <p className="help" role="status">
                {shown.length
                  ? V.filters.showing(shown.length, catalogs.vessels.length)
                  : V.filters.none}
              </p>
            </div>
          )}
          <ChoiceCards
            name={`${ids}-vessel`}
            legend={
              <>
                {T.vessel} <HelpTip topic="vessel" label={T.vessel} />
              </>
            }
            value={vessel}
            onChange={(v) => update({ vessel: v, fromBatch: null })}
            choices={shown.map((v) => ({
              value: v.id,
              title: `${v.bhp} BHP${v.length_m ? ` · ${T.length(fmtU(v.length_m, 'm'))}` : ''}`,
              detail: `${v.name ?? v.id}${v.status === 'draft' ? ` (${V.draft})` : ''}`,
            }))}
          />
        </>
      )}
      <ChoiceCards
        name={`${ids}-prop`}
        legend={
          <>
            {T.propeller} <HelpTip topic="propeller" label={T.propeller} />
          </>
        }
        value={propeller}
        onChange={(v) =>
          update((s) => ({
            ...s,
            params: { ...s.params, ft_propeller: v === propDefault ? '' : v },
          }))
        }
        choices={Object.entries(PROPELLER_LABELS).map(([value, title]) => ({ value, title }))}
      />
      {onBatch && (
        <p className="help">
          {T.several}{' '}
          <button type="button" className="link-button" onClick={onBatch}>
            {T.batch}
          </button>
        </p>
      )}
    </>
  );
}
