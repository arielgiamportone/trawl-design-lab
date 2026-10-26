import { useQuery } from '@tanstack/react-query';
import { useId, useMemo, useState } from 'react';
import { api } from '../../api/client';
import { useT } from '../../i18n';
import { KIND_LABEL as PROV_LABEL, type ProvenanceKind } from '../../lib/catalog';
import {
  applyComponent,
  bomUnitLabel,
  brands,
  cellText,
  columns,
  COMPONENT_KINDS,
  COMPONENT_LABEL,
  DEFAULT_COMPONENT_FILTERS,
  filterComponents,
  inCase,
  isGeneric,
  priceToDisplay,
  REGION_LABEL,
  STATUS_LABEL,
  type Component,
  type ComponentFilters,
  type ComponentKind,
} from '../../lib/components';
import { getUnits, unitLabel } from '../../lib/units';
import { fmt } from '../../lib/format';
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
  const cols = columns(kind);
  const T = useT().components;
  const L = useT().common;

  return (
    <div className="components-catalog">
      <div className="segmented" role="group" aria-label={T.kindLabel}>
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
      <div className="catalog-filters" role="search" aria-label={T.filters}>
        <input
          type="search"
          aria-label={T.search}
          placeholder={T.searchPlaceholder}
          value={f.text}
          onChange={(e) => set({ text: e.target.value })}
        />
        <select
          aria-label={T.brand}
          value={f.brand}
          onChange={(e) => set({ brand: e.target.value })}
        >
          <option value="">{T.allBrands}</option>
          <option value="-">{T.genericAndOwn}</option>
          {brandList.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
        <select
          aria-label={T.regionLabel}
          value={f.region}
          onChange={(e) => set({ region: e.target.value })}
        >
          <option value="">{T.allRegions}</option>
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
          {T.genericOnly}
        </label>
      </div>
      {q.isLoading && <p className="empty">{L.loading}</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      <div className="table-wrap">
        <table className="data" aria-label={T.table(COMPONENT_LABEL[kind])}>
          <thead>
            <tr>
              <th scope="col">{T.colComponent}</th>
              {cols.map((c) => (
                <th key={c.field} scope="col" className={c.unit ? 'num' : undefined}>
                  {c.label}
                  {c.unit ? ` [${unitLabel(c.unit)}]` : ''}
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
                    {cellText(it, c.field, c.unit)}
                  </td>
                ))}
              </tr>
            ))}
            {!q.isLoading && shown.length === 0 && (
              <tr>
                <td colSpan={cols.length + 1} className="empty">
                  {T.noMatch}
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
  const T = useT().components;
  return (
    <>
      {item.status === 'user' ? (
        <span className="badge warn">{STATUS_LABEL.user}</span>
      ) : isGeneric(item) ? (
        <span className="badge good">{T.generic}</span>
      ) : (
        <span className="badge">{item.brand}</span>
      )}
      {active && <span className="badge accent">{T.inCase}</span>}
    </>
  );
}

function ComponentCard({ item, onSelect }: { item: Component; onSelect: (id: string) => void }) {
  const { state, update } = useCase();
  const T = useT().components;
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
          {T.source}{' '}
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
          {T.indicativePrice}{' '}
          {getUnits() === 'imperial'
            ? fmt(priceToDisplay(item.price.value, item.price.unit))
            : item.price.value}{' '}
          {item.price.currency}/
          {item.price.unit === 'unit' ? T.perUnit : bomUnitLabel(item.price.unit)} (
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
              {T.useHeadrope}
            </button>
            <button
              type="button"
              className="btn"
              onClick={() => update((s) => applyComponent(s, item, 'footrope_rope'))}
            >
              {T.useFootrope}
            </button>
          </>
        ) : (
          <button
            type="button"
            className="btn primary"
            disabled={active || (own && !state.useContributions)}
            onClick={() => update((s) => applyComponent(s, item))}
          >
            {active ? T.isCase : T.useInCase}
          </button>
        )}
        {generic && (
          <button type="button" className="btn" onClick={() => onSelect(generic.id)}>
            {T.seeGeneric(generic.name)}
          </button>
        )}
        {own && !state.useContributions && (
          <span className="alert warn" role="note">
            {T.enableOwn}
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
          <table className="data" aria-label={T.provTable}>
            <thead>
              <tr>
                <th scope="col">{T.colValue}</th>
                <th scope="col" className="num">
                  {T.colData}
                </th>
                <th scope="col">{T.colKind}</th>
                <th scope="col">{T.colNote}</th>
              </tr>
            </thead>
            <tbody>
              {prov.map(([field, p]) => (
                <tr key={field}>
                  <td>{field}</td>
                  <td className="num">{cellText(item, field, undefined, true)}</td>
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
