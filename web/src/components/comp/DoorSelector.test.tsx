/**
 * «Elegir portón» (Fase 19.3): pide ``POST /doors/select`` con el caso y los filtros, lista los
 * portones que alcanzan la superficie equivalente y aplica uno al caso; en español y en inglés.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../../i18n';
import { forgetAll } from '../../lib/memo';
import { CaseProvider } from '../../state/CaseProvider';
import { ConnectionProvider } from '../../state/ConnectionProvider';
import { fixtures, mockApi } from '../../test/mockApi';
import { Components } from '../Components';

const SLOW = 20_000;

function renderIn(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ConnectionProvider>
        <CaseProvider>{ui}</CaseProvider>
      </ConnectionProvider>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  forgetAll();
});
afterEach(() => {
  setLang('es');
  vi.unstubAllGlobals();
});

describe('Elegir portón', () => {
  it(
    'lista los candidatos con superficie, peso, tipo y margen, y usa uno en el caso',
    async () => {
      setLang('es');
      const { calls } = mockApi();
      renderIn(<Components />);
      await userEvent.click(await screen.findByRole('button', { name: 'Elegir portón' }));
      const panel = screen.getByTestId('door-selector');
      await userEvent.selectOptions(within(panel).getByLabelText('Tipo de portón'), 'oval');
      const go = within(panel).getByRole('button', { name: 'Elegir portón' });
      await waitFor(() => expect(go).toBeEnabled(), { timeout: 5000 });
      await userEvent.click(go);
      const table = await within(panel).findByRole(
        'table',
        { name: 'Portones que alcanzan la superficie equivalente' },
        { timeout: 3000 },
      );
      const req = calls.find((c) => c.url.endsWith('/doors/select'))?.body as {
        types: string[];
        max_results: number;
      };
      expect(req.types).toEqual(['oval']);
      const rows = within(table).getAllByTestId('door-candidate');
      expect(rows).toHaveLength(fixtures.doorsSelect.candidates.length);
      for (const h of ['Superficie', 'Requerida', 'Margen', 'Peso en aire', 'Patas de gallo']) {
        expect(within(table).getByRole('columnheader', { name: h })).toBeInTheDocument();
      }
      expect(within(table).getAllByText('sin peso publicado').length).toBeGreaterThan(0);
      expect(within(panel).getByTestId('door-required')).toHaveTextContent('1,66');
      const first = within(rows[0]!).getByRole('button', { name: 'Usar este portón' });
      await userEvent.click(first);
      expect(within(rows[0]!).getByRole('button', { name: 'Es el del caso' })).toBeDisabled();
      await waitFor(
        () =>
          expect(
            calls.some(
              (c) =>
                c.url.endsWith('/design') &&
                (c.body as { door?: string }).door === fixtures.doorsSelect.candidates[0]!.id,
            ),
          ).toBe(true),
        { timeout: 3000 },
      );
    },
    SLOW,
  );

  it(
    'en inglés',
    async () => {
      setLang('en');
      mockApi();
      renderIn(<Components />);
      await userEvent.click(await screen.findByRole('button', { name: 'Choose otter boards' }));
      const panel = screen.getByTestId('door-selector');
      expect(within(panel).getByLabelText('Otter board type')).toBeInTheDocument();
      const go = within(panel).getByRole('button', { name: 'Choose otter boards' });
      await waitFor(() => expect(go).toBeEnabled(), { timeout: 5000 });
      await userEvent.click(go);
      const table = await within(panel).findByRole(
        'table',
        { name: 'Otter boards that reach the equivalent area' },
        { timeout: 3000 },
      );
      for (const h of ['Area', 'Required', 'Margin', 'Weight in air', 'Backstrops']) {
        expect(within(table).getByRole('columnheader', { name: h })).toBeInTheDocument();
      }
      expect(
        within(table).getAllByRole('button', { name: 'Use this board' }).length,
      ).toBeGreaterThan(0);
      expect(within(panel).getByText('Rules and sources')).toBeInTheDocument();
    },
    SLOW,
  );
});
