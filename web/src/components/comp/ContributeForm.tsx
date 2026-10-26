import { useMutation } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { api, type ComponentCheckOut } from '../../api/client';
import { useT } from '../../i18n';
import { downloadBlob } from '../../lib/download';
import {
  COMPONENT_KINDS,
  COMPONENT_LABEL,
  contribFields,
  draftComponent,
  issueUrl,
  type Component,
  type ComponentKind,
} from '../../lib/components';
import { useCase } from '../../state/useCase';
import { ComponentBadges } from './ComponentCatalog';

/**
 * «Aportar un componente»: el usuario carga lo que consigue en su puerto, se valida con
 * ``POST /components/check`` y queda en el navegador como «aporte, sin verificar». Puede
 * exportarlo o mandarlo como *issue* para que se sume al catálogo.
 */
export function ContributeForm() {
  const { state, update } = useCase();
  const T = useT().components;
  const ids = useId();
  const [kind, setKind] = useState<ComponentKind>('wire');
  const [values, setValues] = useState<Record<string, string>>({});
  const check = useMutation<ComponentCheckOut, Error, Record<string, unknown>>({
    mutationFn: (item) => api.checkComponent(item),
  });
  const draft = draftComponent(kind, values);
  const set = (k: string, v: string) => {
    setValues((old) => ({ ...old, [k]: v }));
    check.reset();
  };
  const save = () => {
    const item = (check.data?.item ?? draft) as Component;
    update((s) => ({
      ...s,
      contributions: [
        ...s.contributions.filter((c) => c.id !== item.id),
        { ...item, status: 'user' },
      ],
    }));
    setValues({});
    check.reset();
  };
  const remove = (id: string) =>
    update((s) => ({ ...s, contributions: s.contributions.filter((c) => c.id !== id) }));
  const field = (k: string, label: string, num = false) => (
    <label className="field" key={k}>
      <span>{label}</span>
      <input
        id={`${ids}-${k}`}
        inputMode={num ? 'decimal' : 'text'}
        value={values[k] ?? ''}
        onChange={(e) => set(k, e.target.value)}
      />
    </label>
  );

  return (
    <div className="contribute" data-testid="contribute">
      <p className="section-sub">{T.contribIntro}</p>
      <form
        className="contribute-form"
        onSubmit={(e) => {
          e.preventDefault();
          check.mutate(draft);
        }}
      >
        <label className="field">
          <span>{T.type}</span>
          <select
            aria-label={T.contribKind}
            value={kind}
            onChange={(e) => {
              setKind(e.target.value as ComponentKind);
              check.reset();
            }}
          >
            {COMPONENT_KINDS.map((k) => (
              <option key={k} value={k}>
                {COMPONENT_LABEL[k]}
              </option>
            ))}
          </select>
        </label>
        {field('name', T.name)}
        {field('brand', T.brandField)}
        {field('country', T.country)}
        {contribFields(kind).map((f) => field(f.field, f.label, f.num))}
        {field('source', T.sourceField)}
        <div className="catalog-actions">
          <button type="submit" className="btn" disabled={!draft.name || check.isPending}>
            {check.isPending ? T.validating : T.validate}
          </button>
          <button type="button" className="btn primary" disabled={!check.data?.ok} onClick={save}>
            {T.saveBrowser}
          </button>
        </div>
      </form>
      {check.error && (
        <p className="alert crit" role="alert">
          {check.error.message}
        </p>
      )}
      {check.data && (
        <div role="status" data-testid="contribution-check">
          {check.data.ok && check.data.issues.length === 0 && (
            <p className="alert good">{T.coherent}</p>
          )}
          {check.data.issues.length > 0 && (
            <ul className="issues">
              {check.data.issues.map((i, k) => (
                <li key={k} className={i.level === 'error' ? 'crit' : 'warn'}>
                  <span className={`badge ${i.level === 'error' ? 'crit' : 'warn'}`}>
                    {i.level === 'error' ? T.levelError : T.levelWarn}
                  </span>{' '}
                  {i.message}
                </li>
              ))}
            </ul>
          )}
          {check.data.generic && (
            <p className="help">
              {T.genericEq(String((check.data.generic as { name?: string }).name ?? ''))}
            </p>
          )}
        </div>
      )}

      <h4>{T.mine}</h4>
      <label className="check">
        <input
          type="checkbox"
          checked={state.useContributions}
          onChange={(e) => update({ useContributions: e.target.checked })}
        />
        {T.useMine}
      </label>
      {state.contributions.length === 0 && <p className="empty">{T.noneYet}</p>}
      <ul className="contrib-list">
        {state.contributions.map((c) => (
          <li key={c.id} data-contribution={c.id}>
            <strong>{c.name}</strong> · {COMPONENT_LABEL[c.kind]} <ComponentBadges item={c} />
            <span className="catalog-actions">
              <button
                type="button"
                className="btn small"
                onClick={() =>
                  downloadBlob(
                    new Blob([JSON.stringify(c, null, 2)], { type: 'application/json' }),
                    `${c.id}.json`,
                  )
                }
              >
                {T.export}
              </button>
              <a className="btn small" href={issueUrl(c)} target="_blank" rel="noreferrer">
                {T.propose}
              </a>
              <button type="button" className="btn small ghost" onClick={() => remove(c.id)}>
                {T.remove}
              </button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
