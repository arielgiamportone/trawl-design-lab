import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { setLang } from '../i18n';
import type { ParamInfo } from '../api/client';
import { MODE_KEY } from '../lib/mode';
import { paramMeta } from '../lib/params';
import { TAB_KEY } from '../lib/tabs';
import { setUnits } from '../lib/units';
import params from '../test/fixtures/params.json';
import { mockApi } from '../test/mockApi';
import { ParamField } from './ParamsForm';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
  window.localStorage.setItem(TAB_KEY, JSON.stringify('resumen'));
});
afterEach(() => vi.unstubAllGlobals());

/** Palabras del español que no deben aparecer en los resultados en inglés. */
const SPANISH =
  /\b(Resumen|Guardar|Descargar|Velocidad|Resistencia|Abrir|Cerrar|Magnitud|Valor|Unidad|Lima|Burlón|Portón|Cable|Aparejo|Abertura|Superficie|Calculando|del|las|los|que|con|para)\b/;

const TABS = [
  'Summary',
  'Charts',
  'Interactive design',
  'Panel editor',
  'Plan',
  'Compare',
  'Optimize',
  'Simulation',
  'Downloads',
  'FAO catalogue',
  'Components',
  'Construction',
  'Economics',
  'Batches and fleet',
  'Notes and errata',
];

describe('expert mode in English', () => {
  it('shows the tabs, KPIs, summary and comparison in English', async () => {
    setLang('en');
    mockApi();
    renderApp();
    const tabs = await screen.findAllByRole('tab');
    expect(tabs.map((t) => t.textContent?.trim().replace(/\s*\d+$/, ''))).toEqual(TABS);
    const summary = await screen.findByTestId('summary', {}, { timeout: 3000 });
    await waitFor(() => expect(within(summary).getByText('Headrope')).toBeInTheDocument());
    expect(within(summary).getAllByText('Quantity').length).toBeGreaterThan(0);
    expect(within(summary).getByText('Standard RN at 3.5 kn')).toBeInTheDocument();
    expect(within(summary).getByText('28.698')).toBeInTheDocument();
    const kpis = screen.getByRole('region', { name: 'Key indicators' });
    expect(within(kpis).getByText('Vertical opening')).toBeInTheDocument();
    expect(kpis.textContent).not.toMatch(SPANISH);
    expect(summary.textContent).not.toMatch(SPANISH);
    expect(screen.getByRole('heading', { name: /Design case/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Calculate' })).toBeInTheDocument();
    expect(screen.getByText('Advanced parameters')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('tab', { name: /Compare/ }));
    const pin = await screen.findByRole('button', { name: /Pin the current result as A/ });
    await userEvent.click(pin);
    expect(
      (await screen.findAllByText('A (pinned)', {}, { timeout: 3000 })).length,
    ).toBeGreaterThan(0);
    const table = screen.getByTestId('compare-table');
    expect(within(table).getByText('Quantity')).toBeInTheDocument();

    await userEvent.click(screen.getByRole('tab', { name: 'Downloads' }));
    expect(screen.getByRole('button', { name: 'Download .pdf' })).toBeInTheDocument();
    const results = screen.getByRole('region', { name: 'Results detail' });
    expect(results.textContent).not.toMatch(SPANISH);
  });

  it('shows lengths in feet and forces in lbf in imperial units', async () => {
    setLang('en');
    setUnits('imperial');
    mockApi();
    renderApp();
    const summary = await screen.findByTestId('summary', {}, { timeout: 3000 });
    // Lima de 28,698 m = 94,154 ft
    const headrope = await within(summary).findByText('Headrope');
    const row = headrope.closest('tr') as HTMLElement;
    expect(row.textContent).toContain('94.154');
    expect(row.textContent).toContain('ft');
    const kpis = screen.getByRole('region', { name: 'Key indicators' });
    expect(kpis.textContent).toContain('lbf');
    await userEvent.click(screen.getByRole('tab', { name: 'Charts' }));
    expect(
      await screen.findByRole('columnheader', { name: 'Standard drag [lbf]' }, { timeout: 3000 }),
    ).toBeInTheDocument();
  });

  it('enters an advanced parameter in feet and stores it in metres', async () => {
    setLang('en');
    setUnits('imperial');
    const meta = paramMeta((params as ParamInfo[]).find((p) => p.name === 'sweeps_m')!);
    const onChange = vi.fn();
    function Harness() {
      const [value, setValue] = useState('');
      return (
        <ParamField
          meta={meta}
          idBase="p"
          value={value}
          onChange={(v) => {
            onChange(v);
            setValue(v);
          }}
          onReset={() => setValue('')}
        />
      );
    }
    render(<Harness />);
    const input = screen.getByLabelText('Sweeps [ft]');
    expect(input).toHaveAttribute('placeholder', '82.021');
    expect(
      screen.getByRole('button', { name: 'Reset Sweeps [ft] to the default value' }),
    ).toBeDisabled();
    await userEvent.type(input, '100');
    expect(onChange).toHaveBeenLastCalledWith('30.48');
    expect(input).toHaveValue('100');
  });
});
