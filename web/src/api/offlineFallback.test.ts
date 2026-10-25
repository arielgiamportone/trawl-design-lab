import { afterEach, describe, expect, it, vi } from 'vitest';

const local = vi.fn(
  async () =>
    new Response(JSON.stringify({ status: 'ok', version: '1.0.0', offline: true }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    }),
);
let prepared = false;
vi.mock('../engine/offline', () => ({
  isPrepared: () => prepared,
  preferLocal: () => false,
  localRequest: (...args: unknown[]) => local(...(args as [])),
}));

const { api, ApiError } = await import('./client');

afterEach(() => {
  vi.unstubAllGlobals();
  local.mockClear();
});

describe('cliente sin red', () => {
  it('sin motor preparado, un fallo de red es un error de conexión', async () => {
    prepared = false;
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api.health()).rejects.toBeInstanceOf(ApiError);
    expect(local).not.toHaveBeenCalled();
  });
  it('con el motor preparado, el pedido lo atiende el teléfono', async () => {
    prepared = true;
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    const h = await api.health();
    expect((h as { offline?: boolean }).offline).toBe(true);
    expect(local).toHaveBeenCalledWith('GET', '/health', null);
  });
});
