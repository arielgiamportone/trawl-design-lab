import { describe, expect, it } from 'vitest';
import { chapterUrl } from './docs';
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
});
