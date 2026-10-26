import { describe, expect, it } from 'vitest';
import type { BatchParseResponse, BatchRunResponse } from '../api/client';
import { DEFAULT_CASE, buildRequest } from '../state/model';
import parse from '../test/fixtures/batch_parse.json';
import run from '../test/fixtures/batch_run.json';
import {
  chunks,
  chunkSize,
  fleetCsv,
  fleetRecords,
  mergeResults,
  openFleetCase,
  resultColumns,
  resultsCsv,
  type BatchRow,
} from './batch';

describe('lotes', () => {
  it('flota editable desde la vista previa y de vuelta a CSV', () => {
    const recs = fleetRecords(parse as unknown as BatchParseResponse);
    expect(recs.map((r) => r.name)).toEqual(['Don Pedro', 'La Gaviota']);
    expect(recs[0]).toMatchObject({ bhp: 60, length_m: 11, fishing_depth_m: 30 });
    const csv = fleetCsv([{ ...recs[0]!, speed_kn: 2.5, generic_only: true }]);
    const [head, row] = csv.trim().split('\n');
    expect(head).toMatch(/^nombre;potencia \[hp\];eslora \[m\]/);
    expect(row).toContain('Don Pedro;60;11;');
    expect(row).toContain(';2,5;');
    expect(row!.endsWith(';sí')).toBe(true);
  });
  it('tramos: 10 en el teléfono, la guarda con margen en el servidor', () => {
    expect(chunkSize(100, 120, 50, true)).toBe(10);
    expect(chunkSize(50, 120, 50, false)).toBe(50);
    expect(chunkSize(100, 120, 50, false)).toBe(48);
    expect(chunkSize(300, 120, 50, false)).toBe(16);
    expect(chunks([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
  });
  it('une tramos y exporta el resumen', () => {
    const r = run as unknown as BatchRunResponse;
    const merged = mergeResults([r, r])!;
    expect(merged.rows).toHaveLength(r.rows.length * 2);
    expect((merged.rows as BatchRow[]).map((x) => x.index)).toEqual([0, 1, 2, 3]);
    expect(merged.counts.ok).toBe(2 * (r.counts.ok ?? 0));
    const csv = resultsCsv(merged, resultColumns('fleet'));
    expect(csv.split('\n')[0]).toBe(
      'Fila;Nombre;Estado;hp;Escala por semejanza;Escala;v [kn];Lima [m];R_T [kgf];Área [m²/h];Portón;Cable;Costo',
    );
    expect(mergeResults([])).toBeNull();
  });
  it('abre un buque del lote como caso: red escalada, buque y portón en línea', () => {
    const row = (run as unknown as BatchRunResponse).rows[1] as BatchRow;
    const s = openFleetCase({ ...DEFAULT_CASE, params: { sweeps_m: '30' } }, row);
    expect(s.scaled?.s).toBe(row.summary.s);
    expect(s.netModified).toBeNull();
    expect(s.fromBatch?.label).toBe('La Gaviota');
    expect(s.params.sweeps_m).toBeDefined();
    const req = buildRequest(s, [], {}).request;
    expect(req.vessel).toMatchObject({ bhp: 150 });
    expect(typeof req.door === 'object' && req.door !== null).toBe(true);
    expect((req.net as { id: string }).id).toMatch(/_s1\.\d\d$/);
  });
});
