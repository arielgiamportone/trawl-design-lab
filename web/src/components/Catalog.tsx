import { useQuery } from '@tanstack/react-query';
import { useId, useMemo, useState } from 'react';
import { api, type CatalogItem } from '../api/client';
import { useT } from '../i18n';
import {
  DEFAULT_FILTERS,
  FAMILY_LABEL,
  fieldUnit,
  filterNets,
  hpLabel,
  isDraft,
  KIND_LABEL,
  kindShares,
  KINDS,
  pathLabel,
  provValueText,
  RIG_LABEL,
  sources,
  type CatalogFilters,
  type ProvenanceKind,
} from '../lib/catalog';
import { useCase } from '../state/useCase';

/** Pestaña «Catálogo»: redes FAO con filtros, procedencia por valor y validador. */
export function Catalog() {
  const { state, update, catalogs } = useCase();
  const ids = useId();
  const [f, setF] = useState<CatalogFilters>(DEFAULT_FILTERS);
  const [selected, setSelected] = useState<string>(state.net);
  const items = catalogs.nets;
  const shown = useMemo(() => filterNets(items, f), [items, f]);
  const srcs = useMemo(() => sources(items), [items]);
  const net = items.find((n) => n.id === selected) ?? shown[0];
  const set = (patch: Partial<CatalogFilters>) => setF((old) => ({ ...old, ...patch }));
  const T = useT().catalog;

  const use = (id: string) =>
    update((s) => ({
      ...s,
      net: id,
      netModified: null,
      vessel: null,
      door: null,
      fromBatch: null,
      edits: { std: {}, mod: {} },
      scaled: null,
    }));

  return (
    <div className="catalog" data-testid="catalog">
      <p className="section-sub">{T.intro}</p>
      <div className="catalog-filters" role="search" aria-label={T.filters}>
        <input
          type="search"
          aria-label={T.search}
          placeholder={T.searchPlaceholder}
          value={f.text}
          onChange={(e) => set({ text: e.target.value })}
        />
        <select
          aria-label={T.familyLabel}
          value={f.family}
          onChange={(e) => set({ family: e.target.value })}
        >
          <option value="">{T.allFamilies}</option>
          {Object.entries(FAMILY_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          aria-label={T.rigLabel}
          value={f.rig}
          onChange={(e) => set({ rig: e.target.value })}
        >
          <option value="">{T.allRigs}</option>
          {Object.entries(RIG_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          aria-label={T.sourceLabel}
          value={f.source}
          onChange={(e) => set({ source: e.target.value })}
        >
          <option value="">{T.allSources}</option>
          {srcs.map((s) => (
            <option key={s.key} value={s.key}>
              {s.title.split(',')[0]}
            </option>
          ))}
        </select>
        <label className="inline-field">
          {T.vesselOf}
          <input
            type="number"
            min={0}
            step={5}
            aria-label={T.vesselHp}
            value={f.hp ?? ''}
            placeholder="—"
            onChange={(e) => set({ hp: e.target.value === '' ? null : Number(e.target.value) })}
          />
          hp
        </label>
        <label className="check">
          <input
            type="checkbox"
            checked={f.drafts}
            onChange={(e) => set({ drafts: e.target.checked })}
          />
          {T.showDrafts}
        </label>
      </div>

      <div className="table-wrap">
        <table className="data" aria-label={T.table}>
          <thead>
            <tr>
              <th scope="col">{T.colNet}</th>
              <th scope="col">{T.colFamily}</th>
              <th scope="col">{T.colRig}</th>
              <th scope="col">{T.colPower}</th>
              <th scope="col" className="num">
                {T.colPanels}
              </th>
              <th scope="col">{T.colSource}</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((n) => (
              <tr
                key={n.id}
                className={n.id === net?.id ? 'selected' : undefined}
                data-net={n.id}
                onClick={() => setSelected(n.id)}
              >
                <td>
                  <button type="button" className="link-button" onClick={() => setSelected(n.id)}>
                    {n.name ?? n.id}
                  </button>{' '}
                  <Badges n={n} />
                </td>
                <td>{n.family ? FAMILY_LABEL[n.family] : FAMILY_LABEL.bottom}</td>
                <td>{RIG_LABEL[n.rig ?? 'otter']}</td>
                <td>{hpLabel(n)}</td>
                <td className="num">{n.panels ?? '—'}</td>
                <td>{n.source?.title.split(',')[0] ?? T.defaultSource}</td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  {T.noMatch}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {net && <NetCard key={net.id} n={net} active={state.net === net.id} onUse={use} ids={ids} />}
    </div>
  );
}

function pct(share: number, T: ReturnType<typeof useT>['catalog']): string {
  return share > 0 && share < 0.01 ? T.lessThan1 : T.pct(Math.round(share * 100));
}

function Badges({ n }: { n: CatalogItem }) {
  const T = useT().catalog;
  return (
    <>
      {isDraft(n) && <span className="badge warn">{T.draft}</span>}
      {n.rig === 'pair' && <span className="badge accent">{T.pair}</span>}
      {n.four_panel && <span className="badge accent">{T.fourPanel}</span>}
      {n.family === 'pelagic' && <span className="badge accent">{T.pelagic}</span>}
      {n.check && n.check.errors > 0 && (
        <span className="badge crit">{T.errors(n.check.errors)}</span>
      )}
      {n.check && n.check.errors === 0 && n.check.warnings > 0 && (
        <span className="badge" title={T.warningsTitle}>
          {T.warnings(n.check.warnings)}
        </span>
      )}
    </>
  );
}

function NetCard({
  n,
  active,
  onUse,
  ids,
}: {
  n: CatalogItem;
  active: boolean;
  onUse: (id: string) => void;
  ids: string;
}) {
  const L = useT().common;
  const T = useT().catalog;
  const [kind, setKind] = useState<ProvenanceKind | ''>('');
  const prov = useQuery({
    queryKey: ['provenance', n.id],
    queryFn: ({ signal }) => api.netProvenance(n.id, signal),
    staleTime: Infinity,
  });
  const check = useQuery({
    queryKey: ['netcheck', n.id],
    queryFn: ({ signal }) => api.netCheck(n.id, signal),
    staleTime: Infinity,
  });
  const shares = kindShares(n.coverage?.by_kind ?? {});
  const rows = (prov.data ?? []).filter((r) => !kind || r.provenance?.kind === kind);

  return (
    <section className="card card-pad catalog-card" aria-labelledby={`${ids}-net`}>
      <h3 className="section-title" id={`${ids}-net`}>
        <span>
          {n.name ?? n.id} <Badges n={n} />
        </span>
      </h3>
      {n.description && <p>{n.description}</p>}
      <p className="help">
        {n.source ? (
          <>
            {T.source}{' '}
            <a href={n.source.url} target="_blank" rel="noreferrer">
              {n.source.title}
            </a>
            {n.source.page ? ` · ${n.source.page}` : ''}
          </>
        ) : (
          T.sourceA3
        )}
        {n.target_species ? T.species(n.target_species) : ''}
      </p>
      <div className="catalog-actions">
        <button type="button" className="btn primary" disabled={active} onClick={() => onUse(n.id)}>
          {active ? T.isCaseNet : T.useNet}
        </button>
        {isDraft(n) && (
          <span className="alert warn" role="note">
            {T.draftNote}
          </span>
        )}
      </div>

      {shares.length > 0 && (
        <figure className="prov-bar-wrap">
          <figcaption>
            {T.provCaption(n.coverage?.values ?? 0, Math.round((n.coverage?.fraction ?? 0) * 100))}
          </figcaption>
          <div className="prov-bar" role="img" aria-label={T.provByKind}>
            {shares.map((s) => (
              <span
                key={s.kind}
                className={`prov prov-${s.kind}`}
                style={{ width: `${s.share * 100}%` }}
                title={`${KIND_LABEL[s.kind as ProvenanceKind] ?? s.kind}: ${T.pct(Math.round(s.share * 100))}`}
              />
            ))}
          </div>
          <ul className="prov-legend">
            {shares.map((s) => (
              <li key={s.kind}>
                <span className={`prov-dot prov-${s.kind}`} aria-hidden="true" />
                {KIND_LABEL[s.kind as ProvenanceKind] ?? s.kind} {pct(s.share, T)}
              </li>
            ))}
          </ul>
        </figure>
      )}

      <h4>{T.validator}</h4>
      {check.isLoading && <p className="empty">{L.loading}</p>}
      {check.data && check.data.issues.length === 0 && (
        <p className="alert good" role="status">
          {T.closes}
        </p>
      )}
      {check.data && check.data.issues.length > 0 && (
        <ul className="issues" data-testid="net-issues">
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

      <h4>{T.provTitle}</h4>
      <div className="segmented" role="group" aria-label={T.provKind}>
        <button type="button" aria-pressed={kind === ''} onClick={() => setKind('')}>
          {T.all}
        </button>
        {KINDS.map((k) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>
            {KIND_LABEL[k]}
          </button>
        ))}
      </div>
      {prov.isLoading && <p className="empty">{L.loading}</p>}
      {prov.data && (
        // Tabla con scroll propio: enfocable para recorrerla con el teclado.
        <div className="table-wrap prov-table" tabIndex={0} role="region" aria-label={T.provTable}>
          <table className="data" aria-label={T.provTable} data-testid="provenance">
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
              {rows.map((r) => {
                const k = r.provenance?.kind as ProvenanceKind | undefined;
                return (
                  <tr key={r.path} data-path={r.path}>
                    <td>{pathLabel(r.path)}</td>
                    <td className="num">{provValueText(r.value, fieldUnit(r.path))}</td>
                    <td className="kind">
                      {k ? (
                        <>
                          <span className={`prov-dot prov-${k}`} aria-hidden="true" />{' '}
                          {KIND_LABEL[k]}
                        </>
                      ) : (
                        <span className="badge crit">{T.noSource}</span>
                      )}
                    </td>
                    <td className="note">{(r.provenance?.note as string | undefined) ?? ''}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
