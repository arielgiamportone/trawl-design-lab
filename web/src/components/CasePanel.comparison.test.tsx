import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { setLang } from '../i18n';
import { MODE_KEY } from '../lib/mode';
import { TAB_KEY } from '../lib/tabs';
import nets from '../test/fixtures/nets.json';
import { json, mockApi } from '../test/mockApi';

/** Catálogo con dos langostineras de tangones además de la A-3. */
const CATALOG = [
  ...nets,
  { id: 'tangonera_a', name: 'Langostinera A', rig: 'outrigger' },
  { id: 'tangonera_b', name: 'Langostinera B', rig: 'outrigger' },
];

beforeEach(() => {
  setLang('es');
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
  window.localStorage.setItem(TAB_KEY, JSON.stringify('resumen'));
});
afterEach(() => vi.unstubAllGlobals());

describe('modo experto: red de comparación al cambiar la red (Fase 20.7)', () => {
  it('reemplaza la A-3 modificada por una del mismo aparejo al elegir una langostinera', async () => {
    mockApi();
    const inner = globalThis.fetch;
    vi.stubGlobal('fetch', (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://x').pathname.replace(/^\/api/, '');
      return path === '/catalog/nets' ? Promise.resolve(json(CATALOG)) : inner(input, init);
    });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    const net = (await screen.findByLabelText('Red')) as HTMLSelectElement;
    const mod = screen.getByLabelText('Variante modificada (opcional)') as HTMLSelectElement;
    await waitFor(() => expect(net.querySelector('option[value="tangonera_a"]')).not.toBeNull());
    expect(mod.value).toBe('fao_a3_modified');

    await userEvent.selectOptions(net, 'tangonera_a');
    await waitFor(() => expect(mod.value).toBe('tangonera_b'));

    // De vuelta a la A-3, la langostinera de comparación se reemplaza por la A-3 modificada.
    await userEvent.selectOptions(net, 'fao_a3_standard');
    expect(mod.value).toBe('fao_a3_modified');
    // Si la red principal pasa a ser la de comparación, la comparación se quita.
    await userEvent.selectOptions(net, 'fao_a3_modified');
    expect(mod.value).toBe('');
  });
});
