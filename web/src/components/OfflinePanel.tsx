import { useState } from 'react';
import {
  enginePref,
  forgetOffline,
  prepareOffline,
  readyInfo,
  setEnginePref,
  type ReadyInfo,
} from '../engine/offline';
import { setLowData, useLowData } from '../lib/lowdata';
import { useConnection } from '../state/connectionContext';

function mb(bytes: number): string {
  return `${(bytes / 1e6).toLocaleString('es-AR', { maximumFractionDigits: 1 })} MB`;
}

/**
 * «Uso sin conexión»: descarga el motor una sola vez (≈ 15 MB, con wifi) para calcular en el
 * teléfono sin red, y el modo de bajo consumo de datos.
 */
export function OfflinePanel() {
  const conn = useConnection();
  const lowData = useLowData();
  const [info, setInfo] = useState<ReadyInfo | null>(() => readyInfo());
  const [pref, setPref] = useState(() => enginePref());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const prepare = async () => {
    setError(null);
    setBusy('Empezando…');
    try {
      const done = await prepareOffline((stage, bytes) =>
        setBusy(bytes > 0 ? `${stage} (${mb(bytes)})` : stage),
      );
      setInfo(done);
      conn.retry();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(null);
    }
  };
  const forget = async () => {
    await forgetOffline();
    setInfo(null);
    setPref('auto');
    conn.retry();
  };
  const choose = (p: 'auto' | 'local') => {
    setEnginePref(p);
    setPref(p);
    conn.retry();
  };

  return (
    <details className="accordion offline-panel" data-testid="offline-panel">
      <summary>
        <span>Uso sin conexión y bajo consumo de datos</span>
        {info && <span className="badge good">listo sin conexión</span>}
        {conn.local && <span className="badge accent">calculando en el teléfono</span>}
      </summary>
      <div className="accordion-body">
        <p className="help">
          Descargue el motor de cálculo una sola vez (unos 15 MB; mejor con wifi). Después, sin
          señal, el diseño, la lista de materiales y el armado con componentes se calculan en este
          teléfono. La simulación, los informes PDF y los planos siguen necesitando conexión.
        </p>
        {!info ? (
          <button
            type="button"
            className="btn primary"
            disabled={busy !== null}
            onClick={() => void prepare()}
          >
            {busy ?? 'Preparar uso sin conexión'}
          </button>
        ) : (
          <>
            <p className="alert good" role="status">
              Motor guardado ({mb(info.bytes)}, trawlkit {info.version}). Sin señal se usa solo.
            </p>
            <div className="segmented" role="group" aria-label="Dónde calcular">
              <button type="button" aria-pressed={pref === 'auto'} onClick={() => choose('auto')}>
                En el servidor si hay señal
              </button>
              <button type="button" aria-pressed={pref === 'local'} onClick={() => choose('local')}>
                Siempre en el teléfono
              </button>
            </div>
            <p>
              <button type="button" className="btn small ghost" onClick={() => void forget()}>
                Borrar el motor descargado
              </button>
            </p>
          </>
        )}
        {error && (
          <p className="alert crit" role="alert">
            No se pudo preparar: {error}
          </p>
        )}
        <label className="check">
          <input type="checkbox" checked={lowData} onChange={(e) => setLowData(e.target.checked)} />
          Bajo consumo de datos: sin vistas 3D ni simulación (pestañas ocultas)
        </label>
      </div>
    </details>
  );
}
