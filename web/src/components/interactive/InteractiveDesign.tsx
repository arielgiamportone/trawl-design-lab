import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { api, type DesignRequest, type NetSpec } from '../../api/client';
import { asDesignData } from '../../api/result';
import { keyNudge } from '../../lib/interactive';
import {
  countEdits,
  currentValue,
  editedSpec,
  isEdited,
  PANEL_FIELD_ORDER,
  withEdit,
  withOrientation,
  type PanelEdits,
  type PanelField,
} from '../../lib/panels';
import { useCase } from '../../state/useCase';
import { LiveImpact } from './LiveImpact';
import { NetCanvas } from './NetCanvas';
import { PanelInspector } from './PanelInspector';

/** Valor que sigue a ``value`` con ``ms`` de retraso (para no pedir un plano por tecla). */
function useDebounced<T>(value: T, ms: number): T {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setV(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return v;
}

/** Pedido mínimo para ``/design/layout`` (sólo importa la red). */
const layoutRequest = (netJson: string): DesignRequest => ({
  net: JSON.parse(netJson) as NetSpec,
  net_modified: null,
  compat: 'corrected',
  params: {},
});

/** Pestaña «Diseño interactivo»: plano editable, inspector del panel e impacto en vivo. */
export function InteractiveDesign() {
  const { state, update, specs, design, committed } = useCase();
  const [variantSel, setVariant] = useState<'std' | 'mod'>('std');
  const [selected, setSelected] = useState<string | null>(null);
  const [showBase, setShowBase] = useState(true);
  const v = state.netModified ? variantSel : 'std';
  const spec = specs[v];
  const edits = state.edits[v];
  const nEdits = countEdits(spec, edits);

  const net = useMemo(() => (spec ? (editedSpec(spec, edits) ?? spec) : null), [spec, edits]);
  const netKey = useDebounced(net ? JSON.stringify(net) : null, 200);
  const layout = useQuery({
    queryKey: ['layout', netKey],
    queryFn: ({ signal }) =>
      api.layout(layoutRequest(netKey as string), 'std', 'schematic', signal),
    enabled: netKey !== null,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });
  const baseKey = spec ? JSON.stringify(spec) : null;
  const baseLayout = useQuery({
    queryKey: ['layout', baseKey],
    queryFn: ({ signal }) =>
      api.layout(layoutRequest(baseKey as string), 'std', 'schematic', signal),
    enabled: baseKey !== null && nEdits > 0,
    staleTime: Infinity,
  });

  // Caso de base: el mismo pedido confirmado, con las redes sin editar.
  const baseReq = useMemo<DesignRequest | null>(() => {
    if (!committed) return null;
    return {
      ...committed,
      net: state.scaled?.std ?? state.net,
      net_modified: state.netModified ? (state.scaled?.mod ?? state.netModified) : null,
    };
  }, [committed, state.scaled, state.net, state.netModified]);
  const anyEdits =
    countEdits(specs.std, state.edits.std) + countEdits(specs.mod, state.edits.mod) > 0;
  const baseDesign = useQuery({
    queryKey: ['design', JSON.stringify(baseReq)],
    queryFn: async ({ signal }) => asDesignData(await api.design(baseReq as DesignRequest, signal)),
    enabled: baseReq !== null && anyEdits,
    staleTime: 5 * 60_000,
  });

  const setEdits = (fn: (e: PanelEdits) => PanelEdits) =>
    update((s) => ({ ...s, edits: { ...s.edits, [v]: fn(s.edits[v]) } }));
  const panelOf = (id: string) => spec?.panels.find((p) => p.id === id);
  const edit = (pid: string, field: PanelField, text: string) => {
    const p = panelOf(pid);
    if (!p) return;
    setEdits((e) => withEdit(e, pid, field, text, p[field] as number | null | undefined));
  };
  const onNudge = (pid: string, key: string, shift: boolean) => {
    const p = panelOf(pid);
    const shape = layout.data?.planes.flatMap((pl) => pl.shapes).find((s) => s.id === pid);
    if (!p || !shape) return false;
    const n = keyNudge(
      shape,
      {
        depth: currentValue(p, edits, 'meshes_depth') ?? shape.meshes_depth,
        bottom: currentValue(p, edits, 'meshes_bottom') ?? shape.meshes_bottom,
      },
      key,
      shift,
    );
    if (!n) return false;
    edit(pid, n.field, String(n.value));
    return true;
  };

  const editedIds = useMemo(
    () =>
      new Set(
        (spec?.panels ?? [])
          .filter((p) => PANEL_FIELD_ORDER.some((f) => isEdited(p, f, edits[p.id]?.[f])))
          .map((p) => p.id),
      ),
    [spec, edits],
  );
  const panel = selected ? panelOf(selected) : undefined;

  return (
    <div className="interactive">
      <div className="panel-toolbar">
        <div>
          <h2 className="section-title">Diseño interactivo</h2>
          <p className="section-sub">
            Toque un panel y arrastre sus tiradores (alto y bordes) o use las flechas; el caso se
            recalcula al soltar. Ctrl+Z deshace.
          </p>
        </div>
        <div className="interactive-tools">
          {state.netModified && (
            <div className="segmented" role="group" aria-label="Red a editar">
              <button type="button" aria-pressed={v === 'std'} onClick={() => setVariant('std')}>
                Estándar
              </button>
              <button type="button" aria-pressed={v === 'mod'} onClick={() => setVariant('mod')}>
                Modificada
              </button>
            </div>
          )}
          <label className="check small">
            <input
              type="checkbox"
              checked={showBase}
              onChange={(e) => setShowBase(e.target.checked)}
            />
            Contorno original
          </label>
          <button
            type="button"
            className="btn small"
            onClick={() => setEdits(() => ({}))}
            disabled={nEdits === 0}
          >
            Restablecer red
          </button>
        </div>
      </div>

      <LiveImpact
        now={design.data}
        base={baseDesign.data}
        variant={v}
        speed={state.targetSpeed}
        stale={design.isFetching || design.isPlaceholderData || baseDesign.isFetching}
        hasEdits={anyEdits}
      />

      <div className={`interactive-body${panel ? ' with-inspector' : ''}`}>
        {layout.data ? (
          <NetCanvas
            layout={layout.data}
            base={nEdits > 0 ? baseLayout.data : null}
            showBase={showBase}
            selected={selected}
            edited={editedIds}
            fetching={layout.isFetching}
            onSelect={setSelected}
            onCommit={(pid, field, value) => edit(pid, field, String(value))}
            onNudge={onNudge}
          />
        ) : layout.error ? (
          <div className="alert error" role="alert">
            <span>{layout.error.message}</span>
          </div>
        ) : (
          <p className="empty">Cargando el plano…</p>
        )}
        {panel && (
          <PanelInspector
            panel={panel}
            edits={edits}
            onEdit={(f, text) => edit(panel.id, f, text)}
            onOrientation={(o) => setEdits((e) => withOrientation(e, panel, o))}
            onReset={() =>
              setEdits((e) => {
                const next = { ...e };
                delete next[panel.id];
                return next;
              })
            }
            onClose={() => setSelected(null)}
          />
        )}
      </div>
      <p className="help">
        {nEdits === 0
          ? 'Sin cambios respecto de la red de base.'
          : `${nEdits} ${nEdits === 1 ? 'valor editado' : 'valores editados'} (paneles resaltados). La línea discontinua es la red original.`}{' '}
        El plano está a malla estirada: ancho = mallas × mallero; alto = N × mallero.
      </p>
    </div>
  );
}
