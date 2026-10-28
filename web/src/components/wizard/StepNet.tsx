import { useId, useState } from 'react';
import { useT } from '../../i18n';
import { fmtNum } from '../../lib/format';
import { toDisplay, unitLabel } from '../../lib/units';
import { hpLabel, hpMatches, isDraft, RIG_LABEL } from '../../lib/catalog';
import { useCase } from '../../state/useCase';
import { HelpTip } from '../HelpTip';
import { RigSelect } from '../RigSelect';
import { ChoiceCards } from './ChoiceCards';

export function StepNet() {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const M = useT();
  const T = M.wizard.net;
  const net = catalogs.nets.find((n) => n.id === state.net);
  // Red del catálogo sin portón elegido: el motor usa el de su fuente (plano o componentes) o el
  // de la A-3 escalado a la potencia del buque (Fase 19.8d), como en el modo experto.
  const fromPlan = !!net?.vessel_hp;
  const door = state.door ?? (fromPlan ? '' : (catalogs.doors[0]?.id ?? ''));
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
      <p className="wizard-lead">{T.lead}</p>
      <ChoiceCards
        name={`${ids}-net`}
        legend={
          <>
            {T.net} <HelpTip topic="net" label={T.net} />
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
          {all ? T.showingAll : T.showingFor(bhp, hidden)}{' '}
          <button type="button" className="link-button" onClick={() => setAll((a) => !a)}>
            {all ? T.filter : T.seeAll}
          </button>
        </p>
      )}
      {state.scaled && (
        <p className="alert info" role="status">
          <span>{T.scaled}</span>
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
          {T.compare} <HelpTip topic="net_modified" label={T.compareNet} />
        </label>
        {state.netModified && (
          <select
            aria-label={T.compareNet}
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
          {T.doors} <HelpTip topic="door" label={T.doors} />
        </label>
        <select
          id={`${ids}-door`}
          value={door}
          onChange={(e) => update({ door: e.target.value || null })}
        >
          {fromPlan && <option value="">{M.expert.case.doorFromPlan}</option>}
          {catalogs.doors.map((d) => (
            <option key={d.id} value={d.id}>
              {d.name}
              {d.area_m2 != null
                ? ` (${fmtNum(toDisplay(d.area_m2, 'm²'), { maximumFractionDigits: 2 })} ${unitLabel('m²')})`
                : ''}
            </option>
          ))}
        </select>
      </div>
      <RigSelect />
    </>
  );
}
