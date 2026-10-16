import { useQuery } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api, apiBase } from '../api/client';
import { applyThemePref, initialThemePref, type ThemePref } from '../lib/theme';

const THEMES: { value: ThemePref; label: string }[] = [
  { value: 'auto', label: 'Auto' },
  { value: 'light', label: 'Claro' },
  { value: 'dark', label: 'Oscuro' },
];

export function Header() {
  const [theme, setTheme] = useState<ThemePref>(initialThemePref);
  useEffect(() => applyThemePref(theme), [theme]);
  const health = useQuery({
    queryKey: ['health'],
    queryFn: ({ signal }) => api.health(signal),
    refetchInterval: 30_000,
    retry: false,
  });
  const status = health.isSuccess ? 'ok' : health.isError ? 'down' : 'wait';
  const statusText = health.isSuccess
    ? `API conectada · v${health.data.version}`
    : health.isError
      ? 'API sin conexión'
      : 'Conectando con la API…';

  return (
    <header className="app-header">
      <div className="brand">
        <h1>
          trawl-design-lab <span className="dot">·</span> Diseño de redes de arrastre
        </h1>
      </div>
      <div className="header-tools">
        <span className={`api-status ${status}`} title={apiBase()} role="status">
          <span className="led" aria-hidden="true" />
          {statusText}
        </span>
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
