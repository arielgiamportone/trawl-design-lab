import { createContext, useContext } from 'react';
import type { ConnStatus } from '../lib/connection';

export interface ConnectionValue {
  status: ConnStatus;
  /** Versión de la API (``/health``) cuando está conectada. */
  version?: string;
  /** La API en línea es de otra versión que la app (huella de rutas distinta). */
  outdated?: boolean;
  /** Los cálculos los hace el motor del teléfono (sin conexión, Pyodide). */
  local?: boolean;
  /** Vuelve a esperar a la API (botón «Reintentar»). */
  retry: () => void;
}

/** Sin proveedor (pruebas de componentes sueltos) la API se considera conectada. */
export const ConnectionContext = createContext<ConnectionValue>({ status: 'ok', retry: () => {} });

export function useConnection(): ConnectionValue {
  return useContext(ConnectionContext);
}
