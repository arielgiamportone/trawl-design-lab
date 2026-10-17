import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, type DesignRequest } from '../api/client';
import { asDesignData } from '../api/result';
import { paramMeta } from '../lib/params';
import { loadJson, saveJson } from '../lib/storage';
import { CaseContext, type CaseContextValue, type Pinned } from './context';
import { buildRequest, DEFAULT_CASE, sanitizeCase, STORAGE_KEY, type CaseState } from './model';

const DEBOUNCE_MS = 450;

export function CaseProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<CaseState>(() => sanitizeCase(loadJson(STORAGE_KEY)));
  const [pinned, setPinned] = useState<Pinned | null>(null);
  const qc = useQueryClient();

  useEffect(() => saveJson(STORAGE_KEY, state), [state]);

  const update = useCallback<CaseContextValue['update']>((patch) => {
    setState((s) => (typeof patch === 'function' ? patch(s) : { ...s, ...patch }));
  }, []);
  const reset = useCallback(() => setState(DEFAULT_CASE), []);

  const nets = useQuery({
    queryKey: ['nets'],
    queryFn: ({ signal }) => api.nets(signal),
    staleTime: Infinity,
  });
  const vessels = useQuery({
    queryKey: ['vessels'],
    queryFn: ({ signal }) => api.vessels(signal),
    staleTime: Infinity,
  });
  const doors = useQuery({
    queryKey: ['doors'],
    queryFn: ({ signal }) => api.doors(signal),
    staleTime: Infinity,
  });
  const params = useQuery({
    queryKey: ['params'],
    queryFn: ({ signal }) => api.params(signal),
    staleTime: Infinity,
  });
  const errata = useQuery({
    queryKey: ['errata'],
    queryFn: ({ signal }) => api.errata(signal),
    staleTime: Infinity,
  });
  const stdSpec = useQuery({
    queryKey: ['net', state.net],
    queryFn: ({ signal }) => api.net(state.net, signal),
    staleTime: Infinity,
  });
  const modSpec = useQuery({
    queryKey: ['net', state.netModified],
    queryFn: ({ signal }) => api.net(state.netModified as string, signal),
    enabled: !!state.netModified,
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
    enabled: committed !== null,
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
    catalogs: {
      nets: nets.data ?? [],
      vessels: vessels.data ?? [],
      doors: doors.data ?? [],
      params: metas,
      errata: errata.data ?? [],
      loading: nets.isLoading || vessels.isLoading || doors.isLoading || params.isLoading,
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
