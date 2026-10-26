import { useEffect, useState } from 'react';
import { apiBase } from '../api/client';
import { statusLabel } from '../lib/connection';
import { DOCS_URL } from '../lib/docs';
import type { UiMode } from '../lib/mode';
import { applyThemePref, initialThemePref, type ThemePref } from '../lib/theme';
import { LANGS, setLang, useLang, useT } from '../i18n';
import { setUnits, useUnits, type UnitSystem } from '../lib/units';
import { useConnection } from '../state/connectionContext';

const THEMES: ThemePref[] = ['auto', 'light', 'dark'];
const MODES: UiMode[] = ['simple', 'expert', 'aula'];
const SYSTEMS: UnitSystem[] = ['metric', 'imperial'];

interface Props {
  mode: UiMode;
  onModeChange: (mode: UiMode) => void;
}

export function Header({ mode, onModeChange }: Props) {
  const [theme, setTheme] = useState<ThemePref>(initialThemePref);
  useEffect(() => applyThemePref(theme), [theme]);
  const conn = useConnection();
  const T = useT();
  const lang = useLang();
  const system = useUnits();
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
          trawl-design-lab <span className="dot">·</span> {T.app.title}
        </h1>
      </div>
      <div className="header-tools">
        <div className="segmented mode-switch" role="group" aria-label={T.app.modesLabel}>
          {MODES.map((m) => (
            <button
              key={m}
              type="button"
              aria-pressed={mode === m}
              title={T.app.modes[m].title}
              onClick={() => onModeChange(m)}
            >
              {T.app.modes[m].label}
            </button>
          ))}
        </div>
        {DOCS_URL && (
          <a className="docs-link" href={DOCS_URL}>
            {T.app.docs}
          </a>
        )}
        <span
          className={`api-status ${status}`}
          title={conn.outdated ? T.app.outdated(apiBase()) : apiBase()}
          role="status"
        >
          <span className="led" aria-hidden="true" />
          {statusLabel(conn.status, conn.version, conn.outdated, conn.local)}
        </span>
        {conn.status === 'down' && (
          <button type="button" className="api-retry" onClick={conn.retry}>
            {T.common.retry}
          </button>
        )}
        <div className="segmented" role="group" aria-label={T.units.language}>
          {LANGS.map((l) => (
            <button
              key={l}
              type="button"
              lang={l}
              aria-pressed={lang === l}
              title={l === 'es' ? 'Español' : 'English'}
              onClick={() => setLang(l)}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>
        <div className="segmented" role="group" aria-label={T.units.system}>
          {SYSTEMS.map((u) => (
            <button
              key={u}
              type="button"
              aria-pressed={system === u}
              title={u === 'metric' ? T.units.metricTitle : T.units.imperialTitle}
              onClick={() => setUnits(u)}
            >
              {T.units[u]}
            </button>
          ))}
        </div>
        <div className="segmented" role="group" aria-label={T.app.themeLabel}>
          {THEMES.map((t) => (
            <button key={t} type="button" aria-pressed={theme === t} onClick={() => setTheme(t)}>
              {T.app.themes[t]}
            </button>
          ))}
        </div>
      </div>
    </header>
  );
}
