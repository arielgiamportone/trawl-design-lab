import { useMutation } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { api, type ComponentCheckOut } from '../../api/client';
import { downloadBlob } from '../../lib/download';
import {
  COMPONENT_KINDS,
  COMPONENT_LABEL,
  CONTRIB_FIELDS,
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
      <p className="section-sub">
        ¿Usa un cable, un cabo o una boya que no está en el catálogo? Cárguelo con los datos de la
        etiqueta o la ficha del proveedor. Queda guardado sólo en este navegador, marcado como
        aporte sin verificar, y entra en el cálculo sólo si lo habilita abajo.
      </p>
      <form
        className="contribute-form"
        onSubmit={(e) => {
          e.preventDefault();
          check.mutate(draft);
        }}
      >
        <label className="field">
          <span>Tipo</span>
          <select
            aria-label="Tipo de componente del aporte"
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
        {field('name', 'Nombre (como lo conoce en el puerto)')}
        {field('brand', 'Marca (vacío si no tiene)')}
        {field('country', 'País (código, p. ej. AR)')}
        {CONTRIB_FIELDS[kind].map((f) => field(f.field, f.label, f.num))}
        {field('source', 'Fuente del dato (etiqueta, ficha, proveedor)')}
        <div className="catalog-actions">
          <button type="submit" className="btn" disabled={!draft.name || check.isPending}>
            {check.isPending ? 'Validando…' : 'Validar'}
          </button>
          <button type="button" className="btn primary" disabled={!check.data?.ok} onClick={save}>
            Guardar en este navegador
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
            <p className="alert good">Los datos son coherentes con el tipo de componente.</p>
          )}
          {check.data.issues.length > 0 && (
            <ul className="issues">
              {check.data.issues.map((i, k) => (
                <li key={k} className={i.level === 'error' ? 'crit' : 'warn'}>
                  <span className={`badge ${i.level === 'error' ? 'crit' : 'warn'}`}>
                    {i.level === 'error' ? 'error' : 'aviso'}
                  </span>{' '}
                  {i.message}
                </li>
              ))}
            </ul>
          )}
          {check.data.generic && (
            <p className="help">
              Genérico equivalente: {(check.data.generic as { name?: string }).name}
            </p>
          )}
        </div>
      )}

      <h4>Mis aportes</h4>
      <label className="check">
        <input
          type="checkbox"
          checked={state.useContributions}
          onChange={(e) => update({ useContributions: e.target.checked })}
        />
        Usar mis aportes en el cálculo y en el armado
      </label>
      {state.contributions.length === 0 && <p className="empty">Todavía no cargó aportes.</p>}
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
                Exportar
              </button>
              <a className="btn small" href={issueUrl(c)} target="_blank" rel="noreferrer">
                Proponer al catálogo
              </a>
              <button type="button" className="btn small ghost" onClick={() => remove(c.id)}>
                Borrar
              </button>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
