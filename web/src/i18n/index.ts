/**
 * Idioma de la interfaz (Fase 18.3): español (fuente) e inglés, sin dependencias.
 *
 * Los textos viven en catálogos por espacio de nombres (``es/<ns>.ts``); el inglés
 * (``en/<ns>.ts``) está tipado contra el español, así que ``tsc`` falla si falta una clave. Los
 * textos con datos son funciones (``(n: number) => `${n} redes` ``). Los componentes leen el
 * catálogo con ``useT()``; el código fuera de React, con ``msg()``. Al cambiar de idioma la app
 * vuelve a montar la interfaz (App) y vuelve a pedir a la API, que responde en el mismo idioma.
 */
import { useSyncExternalStore } from 'react';
import { en } from './en';
import { es, type Messages } from './es';
import { loadJson, saveJson } from '../lib/storage';

export type { Messages };
export type Lang = 'es' | 'en';
export const LANGS: readonly Lang[] = ['es', 'en'];
export const LANG_KEY = 'trawl-design-lab:lang:v1';
const EVENT = 'trawl-design-lab:lang';

const CATALOGS: Record<Lang, Messages> = { es, en };

/** Idioma guardado o, si no hay, el del navegador (inglés si no es español). */
export function initialLang(): Lang {
  const saved = loadJson<Lang>(LANG_KEY);
  if (saved === 'es' || saved === 'en') return saved;
  const nav = typeof navigator !== 'undefined' ? (navigator.language ?? '') : '';
  return nav.toLowerCase().startsWith('en') ? 'en' : 'es';
}

let current: Lang = initialLang();
applyDocumentLang(current);

function applyDocumentLang(lang: Lang): void {
  if (typeof document !== 'undefined') document.documentElement.lang = lang;
}

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang): void {
  saveJson(LANG_KEY, lang);
  if (lang === current) return;
  current = lang;
  applyDocumentLang(lang);
  if (typeof window !== 'undefined') window.dispatchEvent(new Event(EVENT));
}

/** Catálogo del idioma activo (fuera de React o en código que no se suscribe). */
export function msg(): Messages {
  return CATALOGS[current];
}

/** Catálogo de un idioma dado (pruebas, exportaciones en un idioma fijo). */
export function catalog(lang: Lang): Messages {
  return CATALOGS[lang];
}

/** Locale de ``Intl`` del idioma activo. */
export function locale(lang: Lang = current): string {
  return lang === 'en' ? 'en-US' : 'es-AR';
}

function subscribe(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  return () => window.removeEventListener(EVENT, cb);
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang, getLang);
}

/** Catálogo del idioma activo, con re-render al cambiar de idioma. */
export function useT(): Messages {
  return CATALOGS[useLang()];
}
