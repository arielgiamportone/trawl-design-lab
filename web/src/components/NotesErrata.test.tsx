import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import type { Erratum } from '../api/client';
import { setLang } from '../i18n';
import { errataStatus, errataStatusLabel } from '../lib/errata';
import { MODE_KEY } from '../lib/mode';
import { TAB_KEY } from '../lib/tabs';
import errata from '../test/fixtures/errata.json';
import { mockApi } from '../test/mockApi';

const ERRATA = errata as Erratum[];

beforeEach(() => {
  setLang('es');
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
  window.localStorage.setItem(TAB_KEY, JSON.stringify('notas'));
});
afterEach(() => vi.unstubAllGlobals());

describe('estado de las erratas (Fase 20.7)', () => {
  it('el estado mostrado es el declarado por la API en cada modo', () => {
    for (const e of ERRATA) {
      expect(errataStatus(e, 'corrected').status).toBe(e.status_corrected);
      expect(errataStatus(e, 'excel').status).toBe(e.status_excel);
    }
    const fridman = ERRATA.find((e) => e.key === 'fridman_dp_warp_saturation')!;
    expect(errataStatus(fridman, 'corrected')).toEqual({
      status: 'documented',
      note: fridman.note,
    });
  });

  it('la pestaña «Notas y erratas» muestra el estado declarado y lo cuenta', async () => {
    mockApi();
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <App />
      </QueryClientProvider>,
    );
    await screen.findByRole('heading', { name: 'Erratas del libro Excel original' });
    const tab = screen.queryByRole('tab', { name: /Notas y erratas/ });
    if (tab) await userEvent.click(tab);
    const n = (s: Erratum['status_corrected']) =>
      ERRATA.filter((e) => e.status_corrected === s).length;
    expect(n('corrected')).toBe(24);
    expect(n('documented')).toBe(2);
    const counts = `${n('corrected')} corregidas · ${n('reproduced')} reproducidas · ${n('documented')} documentadas.`;
    expect(
      await screen.findByText((_, el) => el?.tagName === 'P' && !!el.textContent?.endsWith(counts)),
    ).toBeInTheDocument();
    for (const e of ERRATA) {
      const row = container.querySelector<HTMLElement>(`tr[data-errata="${e.key}"]`)!;
      expect(within(row).getByText(errataStatusLabel(e.status_corrected))).toBeInTheDocument();
    }
    const row = container.querySelector<HTMLElement>(
      'tr[data-errata="fridman_dp_warp_saturation"]',
    )!;
    expect(within(row).getByText('documentada')).toBeInTheDocument();
    expect(within(row).queryByText(/se aplica la fórmula correcta/)).toBeNull();
  });
});
