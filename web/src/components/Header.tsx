import { useEffect, useState } from 'react';
import { apiBase } from '../api/client';
import { docsUrl, statusLabel } from '../lib/connection';
import { applyThemePref, initialThemePref, type ThemePref } from '../lib/theme';
import { useConnection } from '../state/connectionContext';

const DOCS_URL = docsUrl({
  VITE_DOCS_URL: import.meta.env.VITE_DOCS_URL as string | undefined,
  BASE_URL: import.meta.env.BASE_URL,
});

const THEMES: { value: ThemePref; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' },
];

export function Header() {
  const [theme, setTheme] = useState<ThemePref>(initialThemePref);
  useEffect(() => applyThemePref(theme), [theme]);
  const conn = useConnection();
  const status = conn.status === 'ok' ? 'ok' : conn.status === 'down' ? 'down' : 'wait';

  return (
    <header className="app-header">
      <div className="brand">
        <h1>
          trawl-design-lab <span className="dot">·</span> Diseño de redes de arrastre
        </h1>
      </div>
      <div className="header-tools">
        {DOCS_URL && (
          <a className="docs-link" href={DOCS_URL}>
            Documentación
          </a>
        )}
        <span className={`api-status ${status}`} title={apiBase()} role="status">
          <span className="led" aria-hidden="true" />
          {statusLabel(conn.status, conn.version)}
        </span>
        {conn.status === 'down' && (
          <button type="button" className="api-retry" onClick={conn.retry}>
            Reintentar
          </button>
        )}
        <div className="segmented" role="group" aria-label="Tema de color">
          {THEMES.map((t) => (
            <button
              key={t.value}
              type="button"
              aria-pressed={theme === t.value}
              onClick={() => setTheme(t.value)}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
