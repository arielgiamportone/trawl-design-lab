import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ENGINE_KEY, READY_KEY } from './config';
import { enginePref, isPrepared, packageFiles, preferLocal, readyInfo } from './offline';

beforeEach(() => localStorage.clear());
afterEach(() => vi.restoreAllMocks());

describe('motor sin conexión', () => {
  it('resuelve los archivos de los paquetes con sus dependencias', () => {
    const lock = {
      packages: {
        numpy: { file_name: 'numpy.whl', depends: [] },
        pydantic: { file_name: 'pydantic.whl', depends: ['pydantic-core', 'typing-extensions'] },
        'pydantic-core': { file_name: 'core.whl', depends: ['typing-extensions'] },
        'typing-extensions': { file_name: 'te.whl' },
      },
    };
    expect(packageFiles(lock, ['numpy', 'Pydantic'])).toEqual([
      'numpy.whl',
      'pydantic.whl',
      'core.whl',
      'te.whl',
    ]);
  });
  it('sólo prefiere el motor local si está preparado y no hay red o se eligió', () => {
    expect(isPrepared()).toBe(false);
    expect(preferLocal()).toBe(false);
    localStorage.setItem(
      READY_KEY,
      JSON.stringify({ version: '1.0.0', pyodide: '0.29.5', at: 'x', bytes: 1 }),
    );
    expect(readyInfo()?.version).toBe('1.0.0');
    expect(preferLocal()).toBe(false);
    localStorage.setItem(ENGINE_KEY, JSON.stringify('local'));
    expect(enginePref()).toBe('local');
    expect(preferLocal()).toBe(true);
    localStorage.setItem(ENGINE_KEY, JSON.stringify('auto'));
    vi.spyOn(navigator, 'onLine', 'get').mockReturnValue(false);
    expect(preferLocal()).toBe(true);
  });
});
