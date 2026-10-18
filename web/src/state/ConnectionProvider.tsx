import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { api } from '../api/client';
import { waitForApi, type ConnStatus, type WaitOptions } from '../lib/connection';
import { ConnectionContext } from './connectionContext';

/** Intervalo de la comprobación de vida una vez conectada [ms]. */
const RECHECK_MS = 60_000;

/**
 * Espera a que la API responda ``/health`` (con reintentos, ver ``waitForApi``) antes de habilitar
 * los catálogos y el cálculo; si una comprobación periódica falla, vuelve a esperar.
 */
export function ConnectionProvider({
  children,
  options,
}: {
  children: ReactNode;
  options?: Omit<WaitOptions, 'signal'>;
}) {
  const [status, setStatus] = useState<ConnStatus>('connecting');
  const [version, setVersion] = useState<string | undefined>();
  const [round, setRound] = useState(0);
  const retry = useCallback(() => setRound((r) => r + 1), []);

  useEffect(() => {
    const ctrl = new AbortController();
    let recheck: number | undefined;
    waitForApi((signal) => api.health(signal), setStatus, { ...options, signal: ctrl.signal })
      .then((h) => {
        if (!h) return;
        setVersion(h.version);
        recheck = window.setInterval(() => {
          api.health(ctrl.signal).catch(() => {
            if (!ctrl.signal.aborted) setRound((r) => r + 1);
          });
        }, RECHECK_MS);
      })
      .catch(() => {
        /* cancelado */
      });
    return () => {
      ctrl.abort();
      window.clearInterval(recheck);
    };
    // `options` es configuración fija (pruebas); sólo «Reintentar» reinicia la espera.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [round]);

  return (
    <ConnectionContext.Provider value={{ status, version, retry }}>
      {children}
    </ConnectionContext.Provider>
  );
}
