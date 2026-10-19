import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, type DesignRequest } from '../api/client';
import { asDesignData } from '../api/result';
import { initHistory, record, redo as redoH, undo as undoH, type History } from '../lib/history';
import { paramMeta } from '../lib/params';
import { loadJson, saveJson } from '../lib/storage';
import { useConnection } from './connectionContext';
import { CaseContext, type CaseContextValue, type Pinned } from './context';
import { buildRequest, DEFAULT_CASE, sanitizeCase, STORAGE_KEY, type CaseState } from './model';

const DEBOUNCE_MS = 450;

export function CaseProvider({ children }: { children: ReactNode }) {
  const [hist, setHist] = useState<History<CaseState>>(() =>
    initHistory(sanitizeCase(loadJson(STORAGE_KEY))),
  );
  const state = hist.present;
  const [pinned, setPinned] = useState<Pinned | null>(null);
  const qc = useQueryClient();
  // Nada se pide a la API hasta que responde /health (arranque en frío del despliegue gratuito).
  const online = useConnection().status === 'ok';

  useEffect(() => saveJson(STORAGE_KEY, state), [state]);

  // Cada cambio entra al historial; los cambios seguidos (escribir un número) se agrupan.
  const update = useCallback<CaseContextValue['update']>((patch) => {
    setHist((h) =>
      record(
        h,
        typeof patch === 'function' ? patch(h.present) : { ...h.present, ...patch },
        Date.now(),
      ),
    );
  }, []);
  const replace = useCallback((next: CaseState) => {
    setHist((h) => record(h, next, Date.now(), false));
  }, []);
  const reset = useCallback(() => replace(DEFAULT_CASE), [replace]);
  const undo = useCallback(() => setHist(undoH), []);
  const redo = useCallback(() => setHist(redoH), []);

  const nets = useQuery({
    queryKey: ['nets'],
    queryFn: ({ signal }) => api.nets(signal),
    staleTime: Infinity,
    enabled: online,
  });
  const vessels = useQuery({
    queryKey: ['vessels'],
    queryFn: ({ signal }) => api.vessels(signal),
    staleTime: Infinity,
    enabled: online,
  });
  const doors = useQuery({
    queryKey: ['doors'],
    queryFn: ({ signal }) => api.doors(signal),
    staleTime: Infinity,
    enabled: online,
  });
  const params = useQuery({
    queryKey: ['params'],
    queryFn: ({ signal }) => api.params(signal),
    staleTime: Infinity,
    enabled: online,
  });
  const errata = useQuery({
    queryKey: ['errata'],
    queryFn: ({ signal }) => api.errata(signal),
    staleTime: Infinity,
    enabled: online,
  });
  const stdSpec = useQuery({
    queryKey: ['net', state.net],
    queryFn: ({ signal }) => api.net(state.net, signal),
    staleTime: Infinity,
    enabled: online,
  });
  const modSpec = useQuery({
    queryKey: ['net', state.netModified],
    queryFn: ({ signal }) => api.net(state.netModified as string, signal),
    enabled: online && !!state.netModified,
    staleTime: Infinity,
  });

  const metas = useMemo(() => (params.data ?? []).map(paramMeta), [params.data]);
  // Una red escalada desde «Optimizar» reemplaza a la del catálogo (también en el editor).
  const specs = useMemo(
    () => ({
      std: state.scaled?.std ?? stdSpec.data,
      mod: state.netModified ? (state.scaled?.mod ?? modSpec.data) : undefined,
    }),
    [stdSpec.data, modSpec.data, state.netModified, state.scaled],
  );
  const built = useMemo(() => buildRequest(state, metas, specs), [state, metas, specs]);
  const valid = Object.keys(built.errors).length === 0 && !built.pending && params.isSuccess;
  const key = valid ? JSON.stringify(built.request) : null;

  // Debounce: el pedido confirmado sigue al pedido válido con DEBOUNCE_MS de retraso.
  const [committedKey, setCommittedKey] = useState<string | null>(null);
  useEffect(() => {
    if (key === null || key === committedKey) return;
    const delay = committedKey === null ? 0 : DEBOUNCE_MS;
    const t = window.setTimeout(() => setCommittedKey(key), delay);
    return () => window.clearTimeout(t);
  }, [key, committedKey]);

  const committed = useMemo<DesignRequest | null>(
    () => (committedKey ? (JSON.parse(committedKey) as DesignRequest) : null),
    [committedKey],
  );

  const design = useQuery({
    queryKey: ['design', committedKey],
    queryFn: async ({ signal }) =>
      asDesignData(await api.design(committed as DesignRequest, signal)),
    enabled: online && committed !== null,
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const calculate = useCallback(() => {
    if (key === null) return;
    if (key === committedKey) void qc.invalidateQueries({ queryKey: ['design', key] });
    else setCommittedKey(key);
  }, [key, committedKey, qc]);

  const pin = useCallback(() => {
    if (!design.data || !committed) return;
    const s = design.data.summary;
    setPinned({
      data: design.data,
      request: committed,
      label: `${String(s.net_id ?? '')} · ${String(s.vessel_id ?? '')} · ${state.compat === 'excel' ? 'Excel' : 'corregido'}`,
      at: new Date().toLocaleTimeString('es-AR', { hour: '2-digit', minute: '2-digit' }),
    });
  }, [design.data, committed, state.compat]);
  const unpin = useCallback(() => setPinned(null), []);

  const catalogError = (nets.error ??
    vessels.error ??
    doors.error ??
    params.error ??
    errata.error ??
    null) as Error | null;

  const value: CaseContextValue = {
    state,
    update,
    reset,
    replace,
    undo,
    redo,
    canUndo: hist.past.length > 0,
    canRedo: hist.future.length > 0,
    catalogs: {
      nets: nets.data ?? [],
      vessels: vessels.data ?? [],
      doors: doors.data ?? [],
      params: metas,
      errata: errata.data ?? [],
      loading:
        !online || nets.isLoading || vessels.isLoading || doors.isLoading || params.isLoading,
      error: catalogError,
    },
    specs,
    errors: built.errors,
    committed,
    design,
    calculate,
    dirty: key !== null && key !== committedKey,
    pinned,
    pin,
    unpin,
  };
  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>;
}
