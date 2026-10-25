import { useId } from 'react';
import { REGION_LABEL } from '../../lib/components';
import { fmtFixed } from '../../lib/format';
import { checkRange } from '../../lib/help';
import { SEABED_LABELS } from '../../lib/labels';
import { parseParam } from '../../lib/params';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';

export function StepOperation() {
  const { state, update, catalogs, errors, design } = useCase();
  const ids = useId();
  const depthMeta = catalogs.params.find((p) => p.name === 'depth_m');
  const depthText = state.params.depth_m ?? '';
  const parsed = depthMeta ? parseParam(depthMeta, depthText) : null;
  const depthError = errors['param.depth_m'];
  const range = parsed?.ok ? checkRange('depth_m', parsed.value) : { ok: true as const };
  const autoDepth = design.data?.summary.working_depth_m;
  const speedRange = checkRange('target_speed', state.targetSpeed);

  return (
    <>
      <p className="wizard-lead">¿A qué velocidad y a qué profundidad piensa trabajar?</p>
      <div className="field">
        <label htmlFor={`${ids}-speed`}>
          Velocidad de arrastre: <strong>{fmtFixed(state.targetSpeed, 1)} kn</strong>{' '}
          <HelpTip topic="target_speed" label="Velocidad de arrastre" />
        </label>
        <input
          id={`${ids}-speed`}
          type="range"
          min={1}
          max={5}
          step={0.1}
          value={state.targetSpeed}
          aria-valuetext={`${fmtFixed(state.targetSpeed, 1)} nudos`}
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
          Profundidad de trabajo [m] <HelpTip topic="depth_m" label="Profundidad de trabajo" />
        </label>
        <input
          id={`${ids}-depth`}
          type="text"
          inputMode="decimal"
          autoComplete="off"
          placeholder={
            typeof autoDepth === 'number'
              ? `automático (${fmtFixed(autoDepth, 0)} m, de la especie objetivo)`
              : 'automático'
          }
          value={depthText}
          aria-invalid={depthError ? true : undefined}
          aria-describedby={`${ids}-depth-msg`}
          onChange={(e) =>
            update((s) => ({ ...s, params: { ...s.params, depth_m: e.target.value } }))
          }
        />
        <p id={`${ids}-depth-msg`} className={depthError ? 'field-error' : 'field-warn'}>
          {depthError ?? (!range.ok ? range.message : '')}
        </p>
      </div>
      <div className="field">
        <label htmlFor={`${ids}-seabed`}>
          Tipo de fondo <HelpTip topic="seabed" label="Tipo de fondo" />
        </label>
        <select
          id={`${ids}-seabed`}
          value={state.params.seabed ?? ''}
          onChange={(e) =>
            update((s) => ({ ...s, params: { ...s.params, seabed: e.target.value } }))
          }
        >
          <option value="">No lo sé (sin rozamiento de fondo)</option>
          {Object.entries(SEABED_LABELS).map(([id, label]) => (
            <option key={id} value={id}>
              {label}
            </option>
          ))}
        </select>
      </div>

      <div className="field">
        <label htmlFor={`${ids}-catch`}>
          Captura esperada por lance [kg] <HelpTip topic="catch_kg" label="Captura esperada" />
        </label>
        <input
          id={`${ids}-catch`}
          type="number"
          min={0}
          max={20000}
          step={50}
          value={state.expectedCatchKg}
          onChange={(e) =>
            update({ expectedCatchKg: Math.min(20000, Math.max(0, Number(e.target.value) || 0)) })
          }
        />
        <p className="help">
          Se usa en el simulador (pestaña «Simulación», lance progresivo) para ver cómo cambian la
          red y los portones a medida que entra la captura.
        </p>
      </div>
      <fieldset className="field">
        <legend>¿Qué consigue en su puerto?</legend>
        <label htmlFor={`${ids}-region`}>Región del puerto</label>
        <select
          id={`${ids}-region`}
          value={state.params.component_region ?? ''}
          onChange={(e) =>
            update((s) => ({ ...s, params: { ...s.params, component_region: e.target.value } }))
          }
        >
          <option value="">Cualquiera (cables y boyas del libro FAO A-3)</option>
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
          Sólo componentes genéricos (los que se consiguen en cualquier ferretería naval)
        </label>
        <p className="help">
          El cable y las boyas se eligen entre los que hay en esa región. La lista de materiales y
          el armado con el catálogo están en la pestaña «Componentes» del modo experto.
        </p>
      </fieldset>
      <p className="help">
        El resto de los parámetros (aparejo, flotación, cables, métodos de cálculo) usa valores
        recomendados; puede cambiarlos en el modo experto.
      </p>
    </>
  );
}
