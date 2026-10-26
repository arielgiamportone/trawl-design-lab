import { useState } from 'react';
import { api, type ReportFormat } from '../api/client';
import { useT } from '../i18n';
import { downloadBlob } from '../lib/download';
import { useCase } from '../state/useCase';

const FORMATS: (ReportFormat | 'json')[] = ['html', 'pdf', 'xlsx', 'json'];

export function Downloads() {
  const { committed, design, state } = useCase();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const T = useT().expert.downloads;
  const base = `trawl-${state.net}${state.netModified ? '-vs-mod' : ''}-${state.compat}`;

  const run = async (format: ReportFormat | 'json') => {
    setError(null);
    if (format === 'json') {
      if (!design.data) return;
      downloadBlob(
        new Blob([JSON.stringify(design.data, null, 2)], { type: 'application/json' }),
        `${base}.json`,
      );
      return;
    }
    if (!committed) return;
    setBusy(format);
    try {
      const blob = await api.report(committed, format);
      downloadBlob(blob, `${base}.${format}`);
    } catch (e) {
      setError(T.error(format.toUpperCase(), (e as Error).message));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <h2 className="section-title">{T.title}</h2>
      <p className="section-sub" style={{ marginBottom: 12 }}>
        {T.sub}
      </p>
      <div className="downloads">
        {FORMATS.map((format) => ({ format, ...T.items[format] })).map((it) => (
          <div className="download-card" key={it.format}>
            <h3>{it.title}</h3>
            <p>{it.desc}</p>
            <button
              type="button"
              className="btn"
              onClick={() => void run(it.format)}
              disabled={busy !== null || (it.format === 'json' ? !design.data : !committed)}
              data-download={it.format}
            >
              {busy === it.format ? (
                <>
                  <span className="spinner" aria-hidden="true" /> {T.generating}
                </>
              ) : (
                T.download(it.format)
              )}
            </button>
          </div>
        ))}
      </div>
      <div role="status" aria-live="polite">
        {error && <div className="alert error">{error}</div>}
      </div>
    </div>
  );
}
