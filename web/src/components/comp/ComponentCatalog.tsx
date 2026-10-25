import { useQuery } from '@tanstack/react-query';
import { useId, useMemo, useState } from 'react';
import { api } from '../../api/client';
import { KIND_LABEL as PROV_LABEL, type ProvenanceKind } from '../../lib/catalog';
import {
  applyComponent,
  brands,
  cellText,
  COLUMNS,
  COMPONENT_KINDS,
  COMPONENT_LABEL,
  DEFAULT_COMPONENT_FILTERS,
  filterComponents,
  inCase,
  isGeneric,
  REGION_LABEL,
  STATUS_LABEL,
  type Component,
  type ComponentFilters,
  type ComponentKind,
} from '../../lib/components';
import { useCase } from '../../state/useCase';

/** Catálogo de componentes: tabla por tipo con filtros, ficha con procedencia y genérico. */
export function ComponentCatalog() {
  const { state } = useCase();
  const [kind, setKind] = useState<ComponentKind>('wire');
  const [f, setF] = useState<ComponentFilters>(DEFAULT_COMPONENT_FILTERS);
  const [selected, setSelected] = useState<string | null>(null);
  const q = useQuery({
    queryKey: ['components', kind],
    queryFn: ({ signal }) => api.components(kind, signal),
    staleTime: Infinity,
  });
  const own = useMemo(
    () => state.contributions.filter((c) => c.kind === kind),
    [state.contributions, kind],
  );
  const items = useMemo(() => [...own, ...(q.data ?? [])], [own, q.data]);
  const shown = useMemo(() => filterComponents(items, f), [items, f]);
  const brandList = useMemo(() => brands(items), [items]);
  const item = items.find((i) => i.id === selected) ?? shown[0];
  const set = (patch: Partial<ComponentFilters>) => setF((old) => ({ ...old, ...patch }));
  const cols = COLUMNS[kind];

  return (
    <div className="components-catalog">
      <div className="segmented" role="group" aria-label="Tipo de componente">
        {COMPONENT_KINDS.map((k) => (
          <button
            key={k}
            type="button"
            aria-pressed={kind === k}
            onClick={() => {
              setKind(k);
              setSelected(null);
              set({ brand: '' });
            }}
          >
            {COMPONENT_LABEL[k]}
          </button>
        ))}
      </div>
      <div className="catalog-filters" role="search" aria-label="Filtros de componentes">
        <input
          type="search"
          aria-label="Buscar componente"
          placeholder="Buscar (nombre, marca, material)…"
          value={f.text}
          onChange={(e) => set({ text: e.target.value })}
        />
        <select aria-label="Marca" value={f.brand} onChange={(e) => set({ brand: e.target.value })}>
          <option value="">Todas las marcas</option>
          <option value="-">Sólo genéricos y aportes</option>
          {brandList.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <select
          aria-label="Región"
          value={f.region}
          onChange={(e) => set({ region: e.target.value })}
        >
          <option value="">Todas las regiones</option>
          {Object.entries(REGION_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <label className="check">
          <input
            type="checkbox"
            checked={f.genericOnly}
            onChange={(e) => set({ genericOnly: e.target.checked })}
          />
          Sólo genéricos
        </label>
      </div>
      {q.isLoading && <p className="empty">Cargando…</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      <div className="table-wrap">
        <table className="data" aria-label={`Componentes: ${COMPONENT_LABEL[kind]}`}>
          <thead>
            <tr>
              <th scope="col">Componente</th>
              {cols.map((c) => (
                <th key={c.field} scope="col" className={c.unit ? 'num' : undefined}>
                  {c.label}
                  {c.unit ? ` [${c.unit}]` : ''}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((it) => (
              <tr
                key={it.id}
                data-component={it.id}
                className={it.id === item?.id ? 'selected' : undefined}
                onClick={() => setSelected(it.id)}
              >
                <td>
                  <button type="button" className="link-button" onClick={() => setSelected(it.id)}>
                    {it.name}
                  </button>{' '}
                  <ComponentBadges item={it} active={inCase(state, it)} />
                </td>
                {cols.map((c) => (
                  <td key={c.field} className={c.unit ? 'num' : undefined}>
                    {cellText(it, c.field)}
                  </td>
                ))}
              </tr>
            ))}
            {!q.isLoading && shown.length === 0 && (
              <tr>
                <td colSpan={cols.length + 1} className="empty">
                  Ningún componente cumple los filtros.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      {item && <ComponentCard key={item.id} item={item} onSelect={setSelected} />}
    </div>
  );
}

export function ComponentBadges({ item, active }: { item: Component; active?: boolean }) {
  return (
    <>
      {item.status === 'user' ? (
        <span className="badge warn">{STATUS_LABEL.user}</span>
      ) : isGeneric(item) ? (
        <span className="badge good">genérico</span>
      ) : (
        <span className="badge">{item.brand}</span>
      )}
      {active && <span className="badge accent">en el caso</span>}
    </>
  );
}

function ComponentCard({ item, onSelect }: { item: Component; onSelect: (id: string) => void }) {
  const { state, update } = useCase();
  const ids = useId();
  const own = item.status === 'user';
  const detail = useQuery({
    queryKey: ['component', item.kind, item.id],
    queryFn: ({ signal }) => api.component(item.kind, item.id, signal),
    enabled: !own,
    staleTime: Infinity,
  });
  const active = inCase(state, item);
  const prov = Object.entries(item.provenance ?? {});
  const generic = detail.data?.generic;

  return (
    <section className="card card-pad catalog-card" aria-labelledby={`${ids}-c`}>
      <h3 className="section-title" id={`${ids}-c`}>
        <span>
          {item.name} <ComponentBadges item={item} active={active} />
        </span>
      </h3>
      <p className="help">
        {COMPONENT_LABEL[item.kind]}
        {item.product ? ` · ${item.product}` : ''}
        {item.country ? ` · ${item.country}` : ''}
        {item.regions?.length
          ? ` · ${item.regions.map((r) => REGION_LABEL[r] ?? r).join(', ')}`
          : ''}
      </p>
      {item.sources?.map((s) => (
        <p key={s.key} className="help">
          Fuente:{' '}
          {s.url ? (
            <a href={s.url} target="_blank" rel="noreferrer">
              {s.title}
            </a>
          ) : (
            s.title
          )}
        </p>
      ))}
      {item.price && (
        <p className="help">
          Precio orientativo: {item.price.value} {item.price.currency}/{item.price.unit} (
          {item.price.date}, {item.price.source})
        </p>
      )}
      <div className="catalog-actions">
        {item.kind === 'rope' ? (
          <>
            <button
              type="button"
              className="btn primary"
              onClick={() => update((s) => applyComponent(s, item, 'headrope_rope'))}
            >
              Usar en la lima
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => update((s) => applyComponent(s, item, 'footrope_rope'))}
            >
              Usar en el burlón
            </button>
          </>
        ) : (
          <button
            type="button"
            className="btn primary"
            disabled={active || (own && !state.useContributions)}
            onClick={() => update((s) => applyComponent(s, item))}
          >
            {active ? 'Es el del caso' : 'Usar en el caso'}
          </button>
        )}
        {generic && (
          <button type="button" className="btn" onClick={() => onSelect(generic.id)}>
            Ver genérico equivalente: {generic.name}
          </button>
        )}
        {own && !state.useContributions && (
          <span className="alert warn" role="note">
            Para usar un aporte, habilite «Usar mis aportes» en la sección Aportar.
          </span>
        )}
      </div>
      {detail.data?.issues && detail.data.issues.length > 0 && (
        <ul className="issues">
          {detail.data.issues.map((i, k) => (
            <li key={k} className={i.level === 'error' ? 'crit' : 'warn'}>
              {i.message}
            </li>
          ))}
        </ul>
      )}
      {item.notes?.map((n, k) => (
        <p key={k} className="help">
          {n}
        </p>
      ))}
      {prov.length > 0 && (
        <div className="table-wrap prov-table">
          <table className="data" aria-label="Procedencia de los valores">
            <thead>
              <tr>
                <th scope="col">Valor</th>
                <th scope="col" className="num">
                  Dato
                </th>
                <th scope="col">Tipo</th>
                <th scope="col">Nota</th>
              </tr>
            </thead>
            <tbody>
              {prov.map(([field, p]) => (
                <tr key={field}>
                  <td>{field}</td>
                  <td className="num">{cellText(item, field)}</td>
                  <td className="kind">
                    <span className={`prov-dot prov-${p.kind}`} aria-hidden="true" />{' '}
                    {PROV_LABEL[p.kind as ProvenanceKind] ?? p.kind}
                  </td>
                  <td className="note">{p.note ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
