import { useQuery } from '@tanstack/react-query';
import { useId, useMemo, useState } from 'react';
import { api, type CatalogItem } from '../api/client';
import {
  DEFAULT_FILTERS,
  FAMILY_LABEL,
  filterNets,
  hpLabel,
  isDraft,
  KIND_LABEL,
  kindShares,
  KINDS,
  pathLabel,
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

  const use = (id: string) =>
    update((s) => ({
      ...s,
      net: id,
      netModified: null,
      vessel: null,
      door: null,
      edits: { std: {}, mod: {} },
      scaled: null,
    }));

  return (
    <div className="catalog" data-testid="catalog">
      <p className="section-sub">
        Redes de documentos públicos de la FAO digitalizadas con la procedencia de cada valor. Al
        usar una red del catálogo se calcula con su propio caso: un buque de su potencia de diseño,
        el portón y la profundidad del plano.
      </p>
      <div className="catalog-filters" role="search" aria-label="Filtros del catálogo">
        <input
          type="search"
          aria-label="Buscar red"
          placeholder="Buscar (nombre, especie, documento)…"
          value={f.text}
          onChange={(e) => set({ text: e.target.value })}
        />
        <select
          aria-label="Familia"
          value={f.family}
          onChange={(e) => set({ family: e.target.value })}
        >
          <option value="">Todas las familias</option>
          {Object.entries(FAMILY_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select aria-label="Aparejo" value={f.rig} onChange={(e) => set({ rig: e.target.value })}>
          <option value="">Todos los aparejos</option>
          {Object.entries(RIG_LABEL).map(([k, v]) => (
            <option key={k} value={k}>
              {v}
            </option>
          ))}
        </select>
        <select
          aria-label="Fuente"
          value={f.source}
          onChange={(e) => set({ source: e.target.value })}
        >
          <option value="">Todas las fuentes</option>
          {srcs.map((s) => (
            <option key={s.key} value={s.key}>
              {s.title.split(',')[0]}
            </option>
          ))}
        </select>
        <label className="inline-field">
          Buque de
          <input
            type="number"
            min={0}
            step={5}
            aria-label="Potencia del buque [hp]"
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
          Mostrar borradores
        </label>
      </div>

      <div className="table-wrap">
        <table className="data" aria-label="Redes del catálogo">
          <thead>
            <tr>
              <th scope="col">Red</th>
              <th scope="col">Familia</th>
              <th scope="col">Aparejo</th>
              <th scope="col">Potencia</th>
              <th scope="col" className="num">
                Paños
              </th>
              <th scope="col">Fuente</th>
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
                <td>{n.family ? FAMILY_LABEL[n.family] : 'Fondo'}</td>
                <td>{RIG_LABEL[n.rig ?? 'otter']}</td>
                <td>{hpLabel(n)}</td>
                <td className="num">{n.panels ?? '—'}</td>
                <td>{n.source?.title.split(',')[0] ?? 'Libro Excel FAO A-3'}</td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  Ninguna red cumple los filtros.
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

function pct(share: number): string {
  return share > 0 && share < 0.01 ? '< 1 %' : `${Math.round(share * 100)} %`;
}

function fmtValue(v: unknown): string {
  return typeof v === 'number'
    ? v.toLocaleString('es-AR', { maximumFractionDigits: 3 })
    : String(v);
}

function Badges({ n }: { n: CatalogItem }) {
  return (
    <>
      {isDraft(n) && <span className="badge warn">borrador</span>}
      {n.rig === 'pair' && <span className="badge accent">pareja</span>}
      {n.four_panel && <span className="badge accent">4 paneles</span>}
      {n.family === 'pelagic' && <span className="badge accent">pelágica</span>}
      {n.check && n.check.errors > 0 && (
        <span className="badge crit">
          {n.check.errors} {n.check.errors === 1 ? 'error' : 'errores'}
        </span>
      )}
      {n.check && n.check.errors === 0 && n.check.warnings > 0 && (
        <span className="badge" title="Avisos del validador de consistencia">
          {n.check.warnings} {n.check.warnings === 1 ? 'aviso' : 'avisos'}
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
            Fuente:{' '}
            <a href={n.source.url} target="_blank" rel="noreferrer">
              {n.source.title}
            </a>
            {n.source.page ? ` · ${n.source.page}` : ''}
          </>
        ) : (
          'Fuente: libro Excel original de la red FAO A-3 (celda por celda).'
        )}
        {n.target_species ? ` · Especies: ${n.target_species}` : ''}
      </p>
      <div className="catalog-actions">
        <button type="button" className="btn primary" disabled={active} onClick={() => onUse(n.id)}>
          {active ? 'Es la red del caso' : 'Usar esta red'}
        </button>
        {isDraft(n) && (
          <span className="alert warn" role="note">
            Borrador: hay valores supuestos o el validador encontró errores; revíselo antes de
            usarla.
          </span>
        )}
      </div>

      {shares.length > 0 && (
        <figure className="prov-bar-wrap">
          <figcaption>
            Procedencia de {n.coverage?.values ?? 0} valores (
            {Math.round((n.coverage?.fraction ?? 0) * 100)} % con fuente)
          </figcaption>
          <div className="prov-bar" role="img" aria-label="Procedencia por tipo">
            {shares.map((s) => (
              <span
                key={s.kind}
                className={`prov prov-${s.kind}`}
                style={{ width: `${s.share * 100}%` }}
                title={`${KIND_LABEL[s.kind as ProvenanceKind] ?? s.kind}: ${Math.round(s.share * 100)} %`}
              />
            ))}
          </div>
          <ul className="prov-legend">
            {shares.map((s) => (
              <li key={s.kind}>
                <span className={`prov-dot prov-${s.kind}`} aria-hidden="true" />
                {KIND_LABEL[s.kind as ProvenanceKind] ?? s.kind} {pct(s.share)}
              </li>
            ))}
          </ul>
        </figure>
      )}

      <h4>Validador de consistencia</h4>
      {check.isLoading && <p className="empty">Cargando…</p>}
      {check.data && check.data.issues.length === 0 && (
        <p className="alert good" role="status">
          La red cierra: empalmes, bocana, cortes y costados sin observaciones.
        </p>
      )}
      {check.data && check.data.issues.length > 0 && (
        <ul className="issues" data-testid="net-issues">
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

      <h4>Procedencia valor por valor</h4>
      <div className="segmented" role="group" aria-label="Tipo de procedencia">
        <button type="button" aria-pressed={kind === ''} onClick={() => setKind('')}>
          Todos
        </button>
        {KINDS.map((k) => (
          <button key={k} type="button" aria-pressed={kind === k} onClick={() => setKind(k)}>
            {KIND_LABEL[k]}
          </button>
        ))}
      </div>
      {prov.isLoading && <p className="empty">Cargando…</p>}
      {prov.data && (
        <div className="table-wrap prov-table">
          <table className="data" aria-label="Procedencia de los valores" data-testid="provenance">
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
              {rows.map((r) => {
                const k = r.provenance?.kind as ProvenanceKind | undefined;
                return (
                  <tr key={r.path} data-path={r.path}>
                    <td>{pathLabel(r.path)}</td>
                    <td className="num">{fmtValue(r.value)}</td>
                    <td className="kind">
                      {k ? (
                        <>
                          <span className={`prov-dot prov-${k}`} aria-hidden="true" />{' '}
                          {KIND_LABEL[k]}
                        </>
                      ) : (
                        <span className="badge crit">sin fuente</span>
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
