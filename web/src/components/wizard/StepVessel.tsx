import { useId } from 'react';
import { PROPELLER_LABELS } from '../../lib/labels';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';
import { ChoiceCards } from './ChoiceCards';

export function StepVessel({ onBatch }: { onBatch?: () => void }) {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const vessel = state.vessel ?? catalogs.vessels[0]?.id ?? '';
  const propDefault = String(
    catalogs.params.find((p) => p.name === 'ft_propeller')?.default ?? 'fixed_pitch',
  );
  const propeller = state.params.ft_propeller || propDefault;
  return (
    <>
      <p className="wizard-lead">
        ¿Con qué buque va a arrastrar? Su potencia define cuánta red puede remolcar.
      </p>
      {catalogs.loading && catalogs.vessels.length === 0 ? (
        <p className="help">Cargando buques…</p>
      ) : (
        <ChoiceCards
          name={`${ids}-vessel`}
          legend={
            <>
              Buque <HelpTip topic="vessel" label="Buque" />
            </>
          }
          value={vessel}
          onChange={(v) => update({ vessel: v, fromBatch: null })}
          choices={catalogs.vessels.map((v) => ({
            value: v.id,
            title: `${v.bhp} BHP${v.length_m ? ` · ${String(v.length_m).replace('.', ',')} m de eslora` : ''}`,
            detail: v.name ?? v.id,
          }))}
        />
      )}
      <ChoiceCards
        name={`${ids}-prop`}
        legend={
          <>
            Hélice <HelpTip topic="propeller" label="Hélice" />
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
          ¿Tiene varios buques?{' '}
          <button type="button" className="link-button" onClick={onBatch}>
            Cárguelos en una planilla y calcule la red para cada uno
          </button>
          .
        </p>
      )}
    </>
  );
}
