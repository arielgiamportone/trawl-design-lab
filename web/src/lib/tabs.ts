import { saveJson } from './storage';

/** Pestañas del modo experto (la elegida se recuerda). */
export const TAB_KEY = 'trawl-design-lab:tab';
export const TAB_IDS = [
  'resumen',
  'graficos',
  'diseno',
  'paneles',
  'plano',
  'comparar',
  'optimizar',
  'simulacion',
  'descargas',
  'catalogo',
  'componentes',
  'construccion',
  'economia',
  'lotes',
  'notas',
];

/** Evento con que otras partes de la app (el laboratorio) abren una pestaña del modo experto. */
export const TAB_EVENT = 'trawl-design-lab:tab';

/** Abre la pestaña ``id`` del modo experto (la recuerda y avisa a la vista abierta). */
export function goToTab(id: string): void {
  saveJson(TAB_KEY, id);
  window.dispatchEvent(new CustomEvent<string>(TAB_EVENT, { detail: id }));
}
