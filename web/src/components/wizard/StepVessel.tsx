import { useId } from 'react';
import { useT } from '../../i18n';
import { PROPELLER_LABELS } from '../../lib/labels';
import { fmtU } from '../../lib/units';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';
import { ChoiceCards } from './ChoiceCards';

export function StepVessel({ onBatch }: { onBatch?: () => void }) {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const T = useT().wizard.vessel;
  const vessel = state.vessel ?? catalogs.vessels[0]?.id ?? '';
  const propDefault = String(
    catalogs.params.find((p) => p.name === 'ft_propeller')?.default ?? 'fixed_pitch',
  );
  const propeller = state.params.ft_propeller || propDefault;
  return (
    <>
      <p className="wizard-lead">
        {T.lead}
      </p>
      {catalogs.loading && catalogs.vessels.length === 0 ? (
        <p className="help">{T.loading}</p>
      ) : (
        <ChoiceCards
          name={`${ids}-vessel`}
          legend={
            <>
              {T.vessel} <HelpTip topic="vessel" label={T.vessel} />
            </>
          }
          value={vessel}
          onChange={(v) => update({ vessel: v, fromBatch: null })}
          choices={catalogs.vessels.map((v) => ({
            value: v.id,
            title: `${v.bhp} BHP${v.length_m ? ` · ${T.length(fmtU(v.length_m, 'm'))}` : ''}`,
            detail: v.name ?? v.id,
          }))}
        />
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
