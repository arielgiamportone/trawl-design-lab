import { useState } from 'react';
import {
  enginePref,
  forgetOffline,
  prepareOffline,
  readyInfo,
  setEnginePref,
  type ReadyInfo,
} from '../engine/offline';
import { msg, useT } from '../i18n';
import { fmtNum } from '../lib/format';
import { setLowData, useLowData } from '../lib/lowdata';
import { useConnection } from '../state/connectionContext';

function mb(bytes: number): string {
  return `${fmtNum(bytes / 1e6, { maximumFractionDigits: 1 })} MB`;
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
  const T = useT().api.offlinePanel;

  const prepare = async () => {
    setError(null);
    setBusy(msg().api.offlinePanel.starting);
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
        <span>{T.title}</span>
        {info && <span className="badge good">{T.ready}</span>}
        {conn.local && <span className="badge accent">{T.local}</span>}
      </summary>
      <div className="accordion-body">
        <p className="help">{T.intro}</p>
        {!info ? (
          <button
            type="button"
            className="btn primary"
            disabled={busy !== null}
            onClick={() => void prepare()}
          >
            {busy ?? T.prepare}
          </button>
        ) : (
          <>
            <p className="alert good" role="status">
              {T.saved(mb(info.bytes), info.version)}
            </p>
            <div className="segmented" role="group" aria-label={T.where}>
              <button type="button" aria-pressed={pref === 'auto'} onClick={() => choose('auto')}>
                {T.server}
              </button>
              <button type="button" aria-pressed={pref === 'local'} onClick={() => choose('local')}>
                {T.phone}
              </button>
            </div>
            <p>
              <button type="button" className="btn small ghost" onClick={() => void forget()}>
                {T.forget}
              </button>
            </p>
          </>
        )}
        {error && (
          <p className="alert crit" role="alert">
            {T.error} {error}
          </p>
        )}
        <label className="check">
          <input type="checkbox" checked={lowData} onChange={(e) => setLowData(e.target.checked)} />
          {T.lowData}
        </label>
      </div>
    </details>
  );
}
