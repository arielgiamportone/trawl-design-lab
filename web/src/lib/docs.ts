/** Enlaces al libro (Jupyter Book) desde la app. */
import { getLang } from '../i18n';
import { docsUrl } from './connection';

/** Raíz del libro (en español); el libro en inglés está en ``<DOCS_URL>/en/``. */
export const DOCS_URL = docsUrl({
  VITE_DOCS_URL: import.meta.env.VITE_DOCS_URL as string | undefined,
  BASE_URL: import.meta.env.BASE_URL,
});

/** Raíz del libro en el idioma activo (``…/en/`` en inglés), o ``null``. */
export function docsRoot(base: string | null = DOCS_URL): string | null {
  if (!base) return null;
  const root = base.endsWith('/') ? base : `${base}/`;
  return getLang() === 'en' ? `${root}en/` : root;
}

/** URL de un capítulo del libro (``'10_potencia'`` → ``…/10_potencia.html``), o ``null``. */
export function chapterUrl(chapter: string, base: string | null = DOCS_URL): string | null {
  const root = docsRoot(base);
  return root ? `${root}${chapter}.html` : null;
}
