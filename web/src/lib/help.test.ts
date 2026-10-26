import { describe, expect, it } from 'vitest';
import { setLang } from '../i18n';
import { chapterUrl } from './docs';
import { setUnits } from './units';
import { checkRange, HELP } from './help';

describe('ayuda contextual', () => {
  it('avisa fuera del rango habitual sin bloquear', () => {
    expect(checkRange('depth_m', 40)).toEqual({ ok: true });
    const r = checkRange('depth_m', 2000);
    expect(r.ok).toBe(false);
    expect(!r.ok && r.message).toContain('10–800 m');
    expect(checkRange('speeds_kn', [1, 2, 9]).ok).toBe(false);
    expect(checkRange('desconocido', 1e9)).toEqual({ ok: true });
  });

  it('todos los capítulos citados existen en el libro', () => {
    const chapters = new Set([
      '10_potencia',
      '11_panos_y_cortes',
      '15_portones_aparejo',
      '16_aberturas',
      '17_flotacion_lastre',
      '18_cables',
      '19_ventana_velocidad',
      '20_optimizacion',
      '22_simulacion_realista',
      '24_malla_selectividad',
      '25_incertidumbre_calibracion',
      '30_caso_beagle',
    ]);
    for (const [k, h] of Object.entries(HELP)) {
      if (h.chapter) expect(chapters.has(h.chapter), k).toBe(true);
    }
  });

  it('arma la URL del capítulo', () => {
    expect(chapterUrl('18_cables', '../')).toBe('../18_cables.html');
    expect(chapterUrl('18_cables', 'https://x.io/libro')).toBe('https://x.io/libro/18_cables.html');
    expect(chapterUrl('18_cables', null)).toBeNull();
  });
  it('en inglés apunta al libro en inglés y muestra el rango en pies', () => {
    setLang('en');
    setUnits('imperial');
    expect(chapterUrl('18_cables', '../')).toBe('../en/18_cables.html');
    expect(HELP.depth_m?.text).toMatch(/^Depth of the fishing ground/);
    const r = checkRange('depth_m', 2000);
    expect(!r.ok && r.message).toBe(
      'Outside the usual range (32.808–2,624.7 ft). It is computed anyway; check the value.',
    );
  });
});
