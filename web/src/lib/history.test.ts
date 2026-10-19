import { describe, expect, it } from 'vitest';
import { COALESCE_MS, initHistory, MAX_HISTORY, record, redo, undo } from './history';

describe('historial deshacer/rehacer', () => {
  it('deshace y rehace pasos separados', () => {
    let h = initHistory('a');
    h = record(h, 'b', 0);
    h = record(h, 'c', COALESCE_MS + 1);
    expect(h.past).toEqual(['a', 'b']);
    h = undo(h);
    expect(h.present).toBe('b');
    h = undo(h);
    expect(h.present).toBe('a');
    expect(undo(h)).toBe(h);
    h = redo(h);
    expect(h.present).toBe('b');
    expect(h.future).toEqual(['c']);
  });

  it('agrupa cambios seguidos (escritura) en un solo paso', () => {
    let h = initHistory('');
    h = record(h, '1', 0);
    h = record(h, '12', 100);
    h = record(h, '123', 200);
    expect(h.past).toEqual(['']);
    expect(undo(h).present).toBe('');
  });

  it('sin agrupar cuando se fuerza un paso y descarta el futuro al cambiar', () => {
    let h = record(initHistory('a'), 'b', 0);
    h = record(h, 'c', 10, false);
    expect(h.past).toEqual(['a', 'b']);
    h = record(undo(h), 'x', 5000);
    expect(h.future).toEqual([]);
    expect(h.past).toEqual(['a', 'b']);
  });

  it('ignora estados idénticos y limita el largo', () => {
    const h0 = initHistory(0);
    expect(record(h0, 0, 0)).toBe(h0);
    let h = h0;
    for (let i = 1; i <= MAX_HISTORY + 20; i++) h = record(h, i, i * 10_000);
    expect(h.past).toHaveLength(MAX_HISTORY);
  });
});
