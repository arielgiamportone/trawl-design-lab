/**
 * Conexión con la API y «arranque en frío».
 *
 * En el despliegue de vista previa (Render, plan gratuito) la API se duerme tras un rato sin
 * tráfico y el primer pedido tarda 30–60 s en responder. ``waitForApi`` consulta ``/health`` con
 * reintentos y espera creciente (backoff) dentro de un presupuesto total, e informa el estado:
 *
 * - ``connecting``: primer intento en curso (lo normal es que responda enseguida);
 * - ``waking``: el primer intento tarda o falló, se sigue reintentando («Despertando la API…»);
 * - ``ok``: ``/health`` respondió;
 * - ``down``: se agotó el presupuesto sin respuesta (la interfaz ofrece «Reintentar»).
 */

export type ConnStatus = 'connecting' | 'waking' | 'ok' | 'down';

export interface WaitOptions {
  /** Tiempo total máximo de espera [ms] (90 s: un arranque en frío de Render cabe holgado). */
  budgetMs?: number;
  /** Tras este tiempo sin respuesta el estado pasa de ``connecting`` a ``waking`` [ms]. */
  wakeAfterMs?: number;
  /** Tiempo máximo de cada intento [ms] (Render retiene el pedido mientras arranca). */
  attemptTimeoutMs?: number;
  /** Cancela la espera (desmontaje del componente o «Reintentar»). */
  signal?: AbortSignal;
}

export const WAIT_DEFAULTS = {
  budgetMs: 90_000,
  wakeAfterMs: 3_000,
  attemptTimeoutMs: 30_000,
} as const;

/** Espera antes del reintento ``attempt`` (0, 1, 2…): 1 s, 2 s, 4 s, 8 s, 8 s… */
export function backoffDelay(attempt: number): number {
  return Math.min(1_000 * 2 ** Math.max(0, attempt), 8_000);
}

/** Estado tras un intento fallido: ``down`` si no queda presupuesto para otro, si no ``waking``. */
export function statusAfterFailure(
  elapsedMs: number,
  nextDelayMs: number,
  budgetMs: number = WAIT_DEFAULTS.budgetMs,
): ConnStatus {
  return elapsedMs + nextDelayMs >= budgetMs ? 'down' : 'waking';
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) return reject(signal.reason as Error);
    const t = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);
    const onAbort = () => {
      clearTimeout(t);
      reject(signal?.reason as Error);
    };
    signal?.addEventListener('abort', onAbort, { once: true });
  });
}

/**
 * Llama a ``check`` hasta que responda o se agote el presupuesto; ``onStatus`` recibe cada cambio
 * de estado. Devuelve la respuesta de ``check`` o ``null`` si la API no está disponible. Si
 * ``signal`` se cancela, rechaza con el motivo de la cancelación.
 */
export async function waitForApi<T>(
  check: (signal: AbortSignal) => Promise<T>,
  onStatus: (s: ConnStatus) => void,
  opts: WaitOptions = {},
): Promise<T | null> {
  const budgetMs = opts.budgetMs ?? WAIT_DEFAULTS.budgetMs;
  const wakeAfterMs = opts.wakeAfterMs ?? WAIT_DEFAULTS.wakeAfterMs;
  const attemptTimeoutMs = opts.attemptTimeoutMs ?? WAIT_DEFAULTS.attemptTimeoutMs;
  const outer = opts.signal;
  const start = Date.now();
  let status: ConnStatus | null = null;
  const set = (s: ConnStatus) => {
    if (s !== status) {
      status = s;
      onStatus(s);
    }
  };

  set('connecting');
  // Si el primer intento tarda (la API está arrancando), se avisa sin esperar a que falle.
  const wakeTimer = setTimeout(() => {
    if (status === 'connecting') set('waking');
  }, wakeAfterMs);

  try {
    for (let attempt = 0; ; attempt++) {
      if (outer?.aborted) throw outer.reason as Error;
      const ctrl = new AbortController();
      const remaining = budgetMs - (Date.now() - start);
      const timer = setTimeout(
        () => ctrl.abort(new Error('timeout')),
        Math.max(1, Math.min(attemptTimeoutMs, remaining)),
      );
      const onAbort = () => ctrl.abort(outer?.reason);
      outer?.addEventListener('abort', onAbort, { once: true });
      try {
        const out = await check(ctrl.signal);
        set('ok');
        return out;
      } catch (err) {
        if (outer?.aborted) throw outer.reason as Error;
        void err;
      } finally {
        clearTimeout(timer);
        outer?.removeEventListener('abort', onAbort);
      }
      const delay = backoffDelay(attempt);
      const next = statusAfterFailure(Date.now() - start, delay, budgetMs);
      set(next);
      if (next === 'down') return null;
      await sleep(delay, outer);
    }
  } finally {
    clearTimeout(wakeTimer);
  }
}

/** Huella de rutas con la que se compiló la app (``vite.config.ts``). */
export const APP_CONTRACT: string = typeof __API_CONTRACT__ === 'string' ? __API_CONTRACT__ : '';

/**
 * ¿La API en línea es de otra versión que la app? Sólo si ambas huellas existen y difieren (una
 * API vieja sin ``contract`` en ``/health`` también cuenta como desactualizada).
 */
export function isOutdated(
  apiContract: string | null | undefined,
  appContract: string = APP_CONTRACT,
): boolean {
  if (!appContract) return false;
  return apiContract !== appContract;
}

/** Texto del indicador de conexión para cada estado. */
export function statusLabel(
  status: ConnStatus,
  version?: string,
  outdated = false,
  local = false,
): string {
  if (status === 'ok' && local) return 'Sin conexión · motor del teléfono';
  switch (status) {
    case 'connecting':
      return 'Conectando…';
    case 'waking':
      return 'Despertando la API (puede tardar hasta un minuto)…';
    case 'ok':
      if (outdated) return version ? `API desactualizada · v${version}` : 'API desactualizada';
      return version ? `API conectada · v${version}` : 'API conectada';
    case 'down':
      return 'API no disponible';
  }
}

/**
 * Enlace a la documentación (el libro): ``VITE_DOCS_URL`` si está definida; si no, ``../`` cuando
 * la app se publica bajo ``…/app/`` (junto al libro); ``null`` en desarrollo (enlace oculto).
 */
export function docsUrl(env: { VITE_DOCS_URL?: string; BASE_URL?: string }): string | null {
  const explicit = env.VITE_DOCS_URL?.trim();
  if (explicit) return explicit;
  return env.BASE_URL && /\/app\/$/.test(env.BASE_URL) ? '../' : null;
}
