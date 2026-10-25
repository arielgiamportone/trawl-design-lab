import { useId, useState } from 'react';
import { hpLabel, hpMatches, isDraft, RIG_LABEL } from '../../lib/catalog';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';
import { ChoiceCards } from './ChoiceCards';

export function StepNet() {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const door = state.door ?? catalogs.doors[0]?.id ?? '';
  const others = catalogs.nets.filter((n) => n.id !== state.net);
  const [all, setAll] = useState(false);
  const vessel = catalogs.vessels.find((v) => v.id === state.vessel) ?? catalogs.vessels[0];
  const bhp = vessel?.bhp ?? null;
  // Redes adecuadas a la potencia del buque elegido (±25 % del rango de diseño de la red);
  // los borradores del catálogo no se ofrecen en el modo guiado.
  const suited = catalogs.nets.filter(
    (n) => !isDraft(n) && (all || hpMatches(n, bhp) || n.id === state.net),
  );
  const hidden = catalogs.nets.filter((n) => !isDraft(n)).length - suited.length;
  return (
    <>
      <p className="wizard-lead">Elija la red y los portones que la abren.</p>
      <ChoiceCards
        name={`${ids}-net`}
        legend={
          <>
            Red <HelpTip topic="net" label="Red" />
          </>
        }
        value={state.net}
        onChange={(v) =>
          update((s) => ({
            ...s,
            net: v,
            netModified: s.netModified === v ? null : s.netModified,
            edits: { std: {}, mod: {} },
            scaled: null,
          }))
        }
        choices={suited.map((n) => ({
          value: n.id,
          title: n.name ?? n.id,
          detail: n.vessel_hp
            ? `${hpLabel(n)} · ${RIG_LABEL[n.rig ?? 'otter']} · ${n.description ?? ''}`
            : n.description,
        }))}
      />
      {(hidden > 0 || all) && (
        <p className="help" data-testid="net-filter">
          {all ? (
            'Se muestran todas las redes del catálogo.'
          ) : (
            <>
              Se muestran las redes para un buque de {bhp} hp; {hidden} más no son de esa potencia.
            </>
          )}{' '}
          <button type="button" className="link-button" onClick={() => setAll((a) => !a)}>
            {all ? 'Filtrar por potencia' : 'Ver todas'}
          </button>
        </p>
      )}
      {state.scaled && (
        <p className="alert info" role="status">
          <span>Se está usando una versión escalada de esta red (desde «Optimizar»).</span>
        </p>
      )}

      <div className="field">
        <label className="check">
          <input
            type="checkbox"
            checked={!!state.netModified}
            disabled={others.length === 0}
            onChange={(e) =>
              update((s) => ({
                ...s,
                netModified: e.target.checked ? (others[0]?.id ?? null) : null,
                edits: { ...s.edits, mod: {} },
              }))
            }
          />
          Comparar con otra red <HelpTip topic="net_modified" label="Red para comparar" />
        </label>
        {state.netModified && (
          <select
            aria-label="Red para comparar"
            value={state.netModified}
            onChange={(e) =>
              update((s) => ({ ...s, netModified: e.target.value, edits: { ...s.edits, mod: {} } }))
            }
          >
            {others.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name ?? n.id}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="field">
        <label htmlFor={`${ids}-door`}>
          Portones <HelpTip topic="door" label="Portones" />
        </label>
        <select id={`${ids}-door`} value={door} onChange={(e) => update({ door: e.target.value })}>
          {catalogs.doors.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
              {d.area_m2 != null
                ? ` (${d.area_m2.toLocaleString('es-AR', { maximumFractionDigits: 2 })} m²)`
                : ''}
            </option>
          ))}
        </select>
      </div>
    </>
  );
}
