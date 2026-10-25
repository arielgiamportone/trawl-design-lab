import { useEffect, useState } from 'react';
import { apiBase } from '../api/client';
import { statusLabel } from '../lib/connection';
import { DOCS_URL } from '../lib/docs';
import type { UiMode } from '../lib/mode';
import { applyThemePref, initialThemePref, type ThemePref } from '../lib/theme';
import { useConnection } from '../state/connectionContext';

const THEMES: { value: ThemePref; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' },
];

const MODES: { value: UiMode; label: string; title: string }[] = [
  {
    value: 'simple',
    label: 'Guiado',
    title: 'Asistente paso a paso con diagnóstico en lenguaje llano',
  },
  { value: 'expert', label: 'Experto', title: 'Todos los parámetros, pestañas y herramientas' },
];

interface Props {
  mode: UiMode;
  onModeChange: (mode: UiMode) => void;
}

export function Header({ mode, onModeChange }: Props) {
  const [theme, setTheme] = useState<ThemePref>(initialThemePref);
  useEffect(() => applyThemePref(theme), [theme]);
  const conn = useConnection();
  const status =
    conn.status === 'ok'
      ? conn.outdated
        ? 'outdated'
        : conn.local
          ? 'local'
          : 'ok'
      : conn.status === 'down'
        ? 'down'
        : 'wait';

  return (
    <header className="app-header">
      <div className="brand">
        <h1>
          trawl-design-lab <span className="dot">·</span> Diseño de redes de arrastre
        </h1>
      </div>
      <div className="header-tools">
        <div className="segmented mode-switch" role="group" aria-label="Modo de la interfaz">
          {MODES.map((m) => (
            <button
              key={m.value}
              type="button"
              aria-pressed={mode === m.value}
              title={m.title}
              onClick={() => onModeChange(m.value)}
            >
              {m.label}
            </button>
          ))}
        </div>
        {DOCS_URL && (
          <a className="docs-link" href={DOCS_URL}>
            Documentación
          </a>
        )}
        <span
          className={`api-status ${status}`}
          title={
            conn.outdated
              ? `${apiBase()}: la API es de otra versión que la app; algunas funciones pueden dar error hasta que se redespliegue`
              : apiBase()
          }
          role="status"
        >
          <span className="led" aria-hidden="true" />
          {statusLabel(conn.status, conn.version, conn.outdated, conn.local)}
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
