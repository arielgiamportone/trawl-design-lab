import { describe, expect, it } from 'vitest';
import design from '../test/fixtures/design.json';
import { setLang } from '../i18n';
import { DRAG_METHODS, label, PROPELLER_LABELS, SEABED_LABELS, SUMMARY_LABELS } from './labels';

describe('labels', () => {
  it('cubre todas las claves del resumen de la API', () => {
    for (const k of Object.keys(design.summary)) {
      const [name] = label(k);
      expect(name, k).not.toBe(k);
    }
  });
  it('claves dinámicas de RN y ROB', () => {
    expect(label('rn_std_3_5kn_kgf')).toEqual(['RN estándar a 3,5 kn', 'kgf']);
    expect(label('rob_2kn_kgf')).toEqual(['ROB a 2 kn', 'kgf']);
  });
  it('tiene unidades', () => {
    expect(SUMMARY_LABELS.max_speed_kn).toEqual(['Velocidad máxima remolcable', 'kn']);
  });
  it('13 métodos de RN presentes en la tabla del motor', () => {
    expect(DRAG_METHODS).toHaveLength(13);
    for (const [k] of DRAG_METHODS) expect(design.result.drag.table.std).toHaveProperty(k);
  });
  it('en inglés, con las mismas claves y unidades métricas', () => {
    setLang('en');
    expect(label('headrope_m')).toEqual(['Headrope', 'm']);
    expect(label('rn_std_3_5kn_kgf')).toEqual(['Standard RN at 3.5 kn', 'kgf']);
    expect(SUMMARY_LABELS.max_speed_kn).toEqual(['Maximum towing speed', 'kn']);
    expect(DRAG_METHODS.find(([k]) => k === 'tauti_headrope')?.[1]).toBe('Tauti (headrope)');
    expect(PROPELLER_LABELS.variable_pitch_nozzle).toBe('Controllable pitch with nozzle (PV+T)');
    expect(Object.values(SEABED_LABELS)).toContain('Mud');
    setLang('es');
    expect(PROPELLER_LABELS.fixed_pitch).toBe('Paso fijo (PF)');
  });
});
