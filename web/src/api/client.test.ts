import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, apiBase, detailMessage } from './client';

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe('apiBase', () => {
  it('usa 127.0.0.1:8000 por defecto', () => {
    vi.stubEnv('VITE_API_URL', '');
    expect(apiBase()).toBe('http://127.0.0.1:8000');
  });
  it('respeta VITE_API_URL sin barra final', () => {
    vi.stubEnv('VITE_API_URL', '/api/');
    expect(apiBase()).toBe('/api');
  });
});

describe('detailMessage', () => {
  it('pasa el texto tal cual', () => {
    expect(detailMessage("red desconocida: 'x'")).toBe("red desconocida: 'x'");
  });
  it('resume errores de validación de FastAPI', () => {
    const msg = detailMessage([
      { loc: ['body', 'net', 'panels', 0, 'mesh_mm'], msg: 'Input should be greater than 0' },
    ]);
    expect(msg).toBe('net.panels.0.mesh_mm: Input should be greater than 0');
  });
});

describe('api', () => {
  it('envía POST /design con JSON', async () => {
    const fetchMock = vi.fn(
      async () => new Response(JSON.stringify({ case: {}, summary: {}, notes: [], result: {} })),
    );
    vi.stubGlobal('fetch', fetchMock);
    vi.stubEnv('VITE_API_URL', 'http://api.test');
    await api.design({ net: 'fao_a3_standard', compat: 'corrected', params: {} });
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe('http://api.test/design');
    expect(init.method).toBe('POST');
    expect(JSON.parse(String(init.body))).toMatchObject({ net: 'fao_a3_standard' });
  });

  it('convierte 422/404 en ApiError con el detail', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        async () =>
          new Response(JSON.stringify({ detail: 'parámetros desconocidos' }), { status: 422 }),
      ),
    );
    await expect(
      api.design({ net: 'fao_a3_standard', compat: 'corrected', params: { foo: 1 } }),
    ).rejects.toMatchObject({
      name: 'ApiError',
      status: 422,
      message: 'parámetros desconocidos',
    });
  });

  it('informa los errores de red', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      }),
    );
    const err = await api.health().catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(0);
    expect((err as ApiError).message).toMatch(/No se pudo conectar/);
  });

  it('pide el plano con view y variant', async () => {
    const fetchMock = vi.fn(async () => new Response('<svg/>'));
    vi.stubGlobal('fetch', fetchMock);
    const svg = await api.plan(
      { net: 'fao_a3_standard', compat: 'corrected', params: {} },
      'scale',
      'mod',
    );
    expect(svg).toBe('<svg/>');
    expect(String((fetchMock.mock.calls[0] as unknown as [string])[0])).toMatch(
      /\/design\/plan\?view=scale&variant=mod$/,
    );
  });
});
