import { useId } from 'react';
import { useT } from '../../i18n';
import { REGION_LABEL } from '../../lib/components';
import { fmtFixed } from '../../lib/format';
import { checkRange } from '../../lib/help';
import { SEABED_LABELS } from '../../lib/labels';
import { parseParam, useUnitText } from '../../lib/params';
import { fmtU, toCanonical, toDisplay, unitLabel } from '../../lib/units';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';

export function StepOperation() {
  const { state, update, catalogs, errors, design } = useCase();
  const ids = useId();
  const T = useT().wizard.operation;
  const depthMeta = catalogs.params.find((p) => p.name === 'depth_m');
  const depthText = state.params.depth_m ?? '';
  const [depthShown, setDepth] = useUnitText(depthText, 'm', (v) =>
    update((s) => ({ ...s, params: { ...s.params, depth_m: v } })),
  );
  const catchMax = Math.round(toDisplay(20000, 'kg'));
  const parsed = depthMeta ? parseParam(depthMeta, depthText) : null;
  const depthError = errors['param.depth_m'];
  const range = parsed?.ok ? checkRange('depth_m', parsed.value) : { ok: true as const };
  const autoDepth = design.data?.summary.working_depth_m;
  const speedRange = checkRange('target_speed', state.targetSpeed);

  return (
    <>
      <p className="wizard-lead">{T.lead}</p>
      <div className="field">
        <label htmlFor={`${ids}-speed`}>
          {T.speed}: <strong>{fmtFixed(state.targetSpeed, 1)} kn</strong>{' '}
          <HelpTip topic="target_speed" label={T.speed} />
        </label>
        <input
          id={`${ids}-speed`}
          type="range"
          min={1}
          max={5}
          step={0.1}
          value={state.targetSpeed}
          aria-valuetext={T.knots(fmtFixed(state.targetSpeed, 1))}
          onChange={(e) => update({ targetSpeed: Number(e.target.value) })}
        />
        <div className="range-scale" aria-hidden="true">
          <span>1 kn</span>
          <span>3 kn</span>
          <span>5 kn</span>
        </div>
        {!speedRange.ok && <p className="field-warn">{speedRange.message}</p>}
      </div>

      <div className="field">
        <label htmlFor={`${ids}-depth`}>
          {T.depth} [{unitLabel('m')}] <HelpTip topic="depth_m" label={T.depth} />
        </label>
        <input
          id={`${ids}-depth`}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          placeholder={
            typeof autoDepth === 'number'
              ? T.autoDepth(fmtU(autoDepth, 'm', { digits: 0 }))
              : T.auto
          }
          value={depthShown}
          aria-invalid={depthError ? true : undefined}
          aria-describedby={`${ids}-depth-msg`}
          onChange={(e) => setDepth(e.target.value)}
        />
        <p id={`${ids}-depth-msg`} className={depthError ? 'field-error' : 'field-warn'}>
          {depthError ?? (!range.ok ? range.message : '')}
        </p>
      </div>
      <div className="field">
        <label htmlFor={`${ids}-seabed`}>
          {T.seabed} <HelpTip topic="seabed" label={T.seabed} />
        </label>
        <select
          id={`${ids}-seabed`}
          value={state.params.seabed ?? ''}
          onChange={(e) =>
            update((s) => ({ ...s, params: { ...s.params, seabed: e.target.value } }))
          }
        >
          <option value="">{T.seabedUnknown}</option>
          {Object.entries(SEABED_LABELS).map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor={`${ids}-catch`}>
          {T.catch} [{unitLabel('kg')}] <HelpTip topic="catch_kg" label={T.catchShort} />
        </label>
        <input
          id={`${ids}-catch`}
          type="number"
          min={0}
          max={catchMax}
          step={50}
          value={Math.round(toDisplay(state.expectedCatchKg, 'kg'))}
          onChange={(e) =>
            update({
              expectedCatchKg: Math.min(
                20000,
                Math.max(0, toCanonical(Number(e.target.value) || 0, 'kg')),
              ),
            })
          }
        />
        <p className="help">{T.catchHelp}</p>
      </div>
      <fieldset className="field">
        <legend>{T.portLegend}</legend>
        <label htmlFor={`${ids}-region`}>{T.region}</label>
        <select
          id={`${ids}-region`}
          value={state.params.component_region ?? ''}
          onChange={(e) =>
            update((s) => ({ ...s, params: { ...s.params, component_region: e.target.value } }))
          }
        >
          <option value="">{T.anyRegion}</option>
          {Object.entries(REGION_LABEL).map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
        <label className="check">
          <input
            type="checkbox"
            checked={state.params.generic_only === 'true'}
            onChange={(e) =>
              update((s) => ({
                ...s,
                params: { ...s.params, generic_only: e.target.checked ? 'true' : '' },
              }))
            }
          />
          {T.genericOnly}
        </label>
        <p className="help">{T.regionHelp}</p>
      </fieldset>
      <p className="help">{T.restHelp}</p>
    </>
  );
}
