/** Tema claro/oscuro: preferencia del usuario (auto/claro/oscuro) y colores para los gráficos. */
import { useEffect, useState, useSyncExternalStore } from 'react';
import { loadJson, saveJson } from './storage';

export type ThemePref = 'auto' | 'light' | 'dark';
const KEY = 'trawl-design-lab:theme';

export function initialThemePref(): ThemePref {
  const v = loadJson<ThemePref>(KEY);
  return v === 'light' || v === 'dark' ? v : 'auto';
}

export function applyThemePref(pref: ThemePref): void {
  const root = document.documentElement;
  if (pref === 'auto') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', pref);
  saveJson(KEY, pref);
}

function prefersDark(): boolean {
  return (
    typeof window !== 'undefined' && !!window.matchMedia?.('(prefers-color-scheme: dark)').matches
  );
}

function subscribe(cb: () => void): () => void {
  const mq = window.matchMedia?.('(prefers-color-scheme: dark)');
  mq?.addEventListener?.('change', cb);
  const mo = new MutationObserver(cb);
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });
  return () => {
    mq?.removeEventListener?.('change', cb);
    mo.disconnect();
  };
}

function snapshot(): 'light' | 'dark' {
  const t = document.documentElement.getAttribute('data-theme');
  if (t === 'light' || t === 'dark') return t;
  return prefersDark() ? 'dark' : 'light';
}

/** Tema efectivo ('light' | 'dark'), reactivo a la preferencia del sistema y al conmutador. */
export function useResolvedTheme(): 'light' | 'dark' {
  return useSyncExternalStore(subscribe, snapshot, () => 'light');
}

export interface ChartColors {
  surface: string;
  text: string;
  text2: string;
  muted: string;
  grid: string;
  axis: string;
  /** Series categóricas (orden fijo, validado con el validador de paletas). */
  s1: string;
  s2: string;
  s3: string;
  s4: string;
  s5: string;
  s7: string;
  /** Series de contexto atenuadas. */
  quiet: string;
  window: string;
  critical: string;
}

const LIGHT: ChartColors = {
  surface: '#fcfcfb',
  text: '#0b0b0b',
  text2: '#52514e',
  muted: '#6b6963',
  grid: '#e1e0d9',
  axis: '#c3c2b7',
  s1: '#2a78d6',
  s2: '#eb6834',
  s3: '#1baf7a',
  s4: '#eda100',
  s5: '#e87ba4',
  s7: '#6250d6',
  quiet: '#bdbbb3',
  window: '#1baf7a',
  critical: '#d03b3b',
};

const DARK: ChartColors = {
  surface: '#1a1a19',
  text: '#f0efec',
  text2: '#c3c2b7',
  muted: '#a3a198',
  grid: '#2c2c2a',
  axis: '#4a4a46',
  s1: '#3987e5',
  s2: '#d95926',
  s3: '#199e70',
  s4: '#c98500',
  s5: '#d55181',
  s7: '#9085e9',
  quiet: '#5a5954',
  window: '#199e70',
  critical: '#e66767',
};

export function useChartColors(): ChartColors {
  const theme = useResolvedTheme();
  return theme === 'dark' ? DARK : LIGHT;
}

/** ¿Pantalla angosta? (para ajustar alturas/márgenes de los gráficos). */
export function useMediaQuery(query: string): boolean {
  const [match, setMatch] = useState(() =>
    typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : false,
  );
  useEffect(() => {
    if (!window.matchMedia) return;
    const mq = window.matchMedia(query);
    const on = () => setMatch(mq.matches);
    on();
    mq.addEventListener?.('change', on);
    return () => mq.removeEventListener?.('change', on);
  }, [query]);
  return match;
}
