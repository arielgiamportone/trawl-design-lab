import { describe, expect, it } from 'vitest';
import { DEFAULT_CASE } from '../state/model';
import {
  deleteProject,
  listProjects,
  parseProjectFile,
  projectFileName,
  saveProject,
  toProjectFile,
} from './projects';

describe('proyectos', () => {
  it('ida y vuelta por archivo, normalizando el caso', () => {
    const state = { ...DEFAULT_CASE, vessel: 'fao_a3_180hp', targetSpeed: 2.6 };
    const file = toProjectFile('  Beagle 180 ', state, new Date('2026-10-19T10:00:00Z'));
    expect(file.name).toBe('Beagle 180');
    const back = parseProjectFile(JSON.stringify(file));
    expect(back.ok && back.project.case).toEqual(state);
    const old = { ...file, case: { net: 'fao_a3_standard' } };
    const parsed = parseProjectFile(JSON.stringify(old));
    expect(parsed.ok && parsed.project.case.targetSpeed).toBe(DEFAULT_CASE.targetSpeed);
  });

  it('rechaza archivos ajenos con un mensaje claro', () => {
    expect(parseProjectFile('no json')).toEqual({
      ok: false,
      error: 'El archivo no es JSON válido.',
    });
    expect(parseProjectFile('{"a":1}')).toMatchObject({ ok: false });
    const future = { ...toProjectFile('x', DEFAULT_CASE), version: 9 };
    expect(parseProjectFile(JSON.stringify(future))).toMatchObject({
      ok: false,
      error: expect.stringContaining('9'),
    });
  });

  it('guarda por nombre en el navegador (reemplaza, ordena y elimina)', () => {
    saveProject(toProjectFile('A', DEFAULT_CASE, new Date('2026-01-01')));
    saveProject(toProjectFile('B', DEFAULT_CASE, new Date('2026-02-01')));
    saveProject(toProjectFile('A', { ...DEFAULT_CASE, targetSpeed: 3 }, new Date('2026-03-01')));
    const list = listProjects();
    expect(list.map((p) => p.name)).toEqual(['A', 'B']);
    expect(list[0]?.case.targetSpeed).toBe(3);
    expect(deleteProject('A').map((p) => p.name)).toEqual(['B']);
  });

  it('nombre de archivo seguro', () => {
    expect(projectFileName('Red Beagle — 180 HP (versión 2)')).toBe(
      'red-beagle-180-hp-version-2.trawl.json',
    );
    expect(projectFileName('***')).toBe('proyecto.trawl.json');
  });
});
