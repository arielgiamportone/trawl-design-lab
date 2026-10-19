/** Enlaces al libro (Jupyter Book) desde la app. */
import { docsUrl } from './connection';

export const DOCS_URL = docsUrl({
  VITE_DOCS_URL: import.meta.env.VITE_DOCS_URL as string | undefined,
  BASE_URL: import.meta.env.BASE_URL,
});

/** URL de un capítulo del libro (``'10_potencia'`` → ``…/10_potencia.html``), o ``null``. */
export function chapterUrl(chapter: string, base: string | null = DOCS_URL): string | null {
  if (!base) return null;
  return `${base.endsWith('/') ? base : `${base}/`}${chapter}.html`;
}
