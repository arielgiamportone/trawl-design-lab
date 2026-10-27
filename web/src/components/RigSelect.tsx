import { useId } from 'react';
import { useT } from '../i18n';
import { RIG_LABEL, RIGS } from '../lib/catalog';
import { useCase } from '../state/useCase';

/**
 * Aparejo del caso (Fase 19.5): por defecto, el de la red; si no, portones, pareja, tangones,
 * gemelo o vara. Se guarda en el parámetro ``rig`` del caso; los parámetros del aparejo (tangón,
 * tijera, muerto, vara) se editan en «Parámetros avanzados».
 */
export function RigSelect() {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const T = useT().catalog.rigSelect;
  const net = catalogs.nets.find((n) => n.id === state.net);
  const netRig = net?.rig ?? 'otter';
  const value = state.params.rig ?? '';
  const current = value || netRig;
  const set = (v: string) =>
    update((s) => {
      const params = { ...s.params };
      if (v) params.rig = v;
      else delete params.rig;
      return { ...s, params };
    });
  return (
    <div className="field" data-testid="rig-select">
      <label htmlFor={`${ids}-rig`}>{T.label}</label>
      <select id={`${ids}-rig`} value={value} onChange={(e) => set(e.target.value)}>
        <option value="">{T.fromNet(RIG_LABEL[netRig] ?? netRig)}</option>
        {RIGS.map((r) => (
          <option key={r} value={r}>
            {RIG_LABEL[r]}
          </option>
        ))}
      </select>
      <p className="help">
        {T.help[current] ?? ''}
        {current === 'outrigger' || current === 'twin' || current === 'beam' ? ` ${T.params}` : ''}
      </p>
    </div>
  );
}
