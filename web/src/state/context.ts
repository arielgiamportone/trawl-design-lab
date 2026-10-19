import { createContext } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import type { CatalogItem, DesignRequest, Door, Erratum, NetSpec, Vessel } from '../api/client';
import type { DesignData } from '../api/result';
import type { ParamMeta } from '../lib/params';
import type { CaseState } from './model';

export interface Pinned {
  data: DesignData;
  request: DesignRequest;
  label: string;
  at: string;
}

export interface CaseContextValue {
  state: CaseState;
  update: (patch: Partial<CaseState> | ((s: CaseState) => CaseState)) => void;
  reset: () => void;
  /** Reemplaza el caso entero (abrir un proyecto) como un paso del historial. */
  replace: (next: CaseState) => void;
  undo: () => void;
  redo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  catalogs: {
    nets: CatalogItem[];
    vessels: Vessel[];
    doors: Door[];
    params: ParamMeta[];
    errata: Erratum[];
    loading: boolean;
    error: Error | null;
  };
  specs: { std?: NetSpec; mod?: NetSpec };
  /** Errores de validación locales (no se envía nada mientras existan). */
  errors: Record<string, string>;
  /** Pedido ya confirmado (tras el debounce) que corresponde a ``design``. */
  committed: DesignRequest | null;
  design: UseQueryResult<DesignData, Error>;
  /** Fuerza el cálculo inmediato (botón «Calcular»). */
  calculate: () => void;
  /** Hay cambios aún no enviados (debounce en curso). */
  dirty: boolean;
  pinned: Pinned | null;
  pin: () => void;
  unpin: () => void;
}

export const CaseContext = createContext<CaseContextValue | null>(null);
