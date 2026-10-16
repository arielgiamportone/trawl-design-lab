import { describe, expect, it } from 'vitest';
import design from '../test/fixtures/design.json';
import { DRAG_METHODS, label, SUMMARY_LABELS } from './labels';

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
});
