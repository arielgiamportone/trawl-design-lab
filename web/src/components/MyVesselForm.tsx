import { useId } from 'react';
import { useT } from '../i18n';
import { REGION_LABEL } from '../lib/components';
import { useUnitText } from '../lib/params';
import { unitLabel, useUnits } from '../lib/units';
import { EMPTY_MY_VESSEL, type MyVessel, type NumField } from '../lib/vessel';
import { useCase } from '../state/useCase';

/** Campo numérico de «Mi buque»: muestra y lee en el sistema activo, guarda en métrico. */
function NumberField({
  id,
  label,
  unit,
  value,
  error,
  help,
  onChange,
}: {
  id: string;
  label: string;
  unit: string;
  value: string;
  error?: string;
  help?: string;
  onChange: (canonical: string) => void;
}) {
  useUnits();
  const [text, setText] = useUnitText(value, unit, onChange);
  const u = unitLabel(unit);
  return (
    <div className="field">
      <label htmlFor={id}>
        {label} [{u}]
      </label>
      <input
        id={id}
        type="text"
        inputMode="decimal"
        value={text}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || help ? `${id}-msg` : undefined}
        onChange={(e) => setText(e.target.value)}
      />
      {(error || help) && (
        <p
          id={`${id}-msg`}
          className={error ? 'field-error' : 'help'}
          role={error ? 'alert' : undefined}
        >
          {error ?? help}
        </p>
      )}
    </div>
  );
}

/**
 * Formulario «Mi buque» (Fase 19.4), común al panel del caso (modo experto) y al paso «Buque» del
 * modo guiado. Los errores salen del armado del pedido (``vessel.<campo>`` en ``errors``).
 */
export function MyVesselForm() {
  const { state, update, errors } = useCase();
  const ids = useId();
  const T = useT().vessel;
  const mv = state.myVessel ?? EMPTY_MY_VESSEL;
  const set = (patch: Partial<MyVessel>) =>
    update((s) => ({ ...s, myVessel: { ...(s.myVessel ?? EMPTY_MY_VESSEL), ...patch } }));
  const err = (k: string) => errors[`vessel.${k}`];
  const num = (k: NumField, label: string, unit: string, help?: string) => (
    <NumberField
      id={`${ids}-${k}`}
      label={label}
      unit={unit}
      value={mv[k]}
      error={err(k)}
      help={help}
      onChange={(v) => set({ [k]: v } as Partial<MyVessel>)}
    />
  );
  return (
    <fieldset className="field my-vessel" data-testid="my-vessel">
      <legend>{T.legend}</legend>
      <p className="help">{T.useMineHelp}</p>
      <div className="field">
        <label htmlFor={`${ids}-name`}>{T.name}</label>
        <input
          id={`${ids}-name`}
          type="text"
          value={mv.name}
          onChange={(e) => set({ name: e.target.value })}
        />
      </div>
      {num('bhp', T.bhp, 'hp')}
      {num('length_m', T.length, 'm')}
      {num('beam_m', T.beam, 'm')}
      {num('depth_m', T.depth, 'm')}
      <div className="field">
        <label htmlFor={`${ids}-pitch`}>{T.pitch}</label>
        <select
          id={`${ids}-pitch`}
          value={mv.pitch}
          aria-invalid={err('propeller') ? true : undefined}
          onChange={(e) => set({ pitch: e.target.value === 'variable' ? 'variable' : 'fixed' })}
        >
          <option value="fixed">{T.pitchFixed}</option>
          <option value="variable">{T.pitchVariable}</option>
        </select>
        <label className="check">
          <input
            type="checkbox"
            checked={mv.nozzle}
            onChange={(e) => set({ nozzle: e.target.checked })}
          />
          {T.nozzle}
        </label>
        {err('propeller') && (
          <p className="field-error" role="alert">
            {err('propeller')}
          </p>
        )}
      </div>
      {num('propeller_diameter_m', T.diameter, 'm', T.diameterHelp)}
      {num('winch_drum_capacity_m', T.winch, 'm', T.winchHelp)}
      <div className="field">
        <label htmlFor={`${ids}-region`}>{T.region}</label>
        <select
          id={`${ids}-region`}
          value={mv.region}
          onChange={(e) => set({ region: e.target.value })}
        >
          <option value="">{T.noRegion}</option>
          {Object.entries(REGION_LABEL).map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </div>
    </fieldset>
  );
}
