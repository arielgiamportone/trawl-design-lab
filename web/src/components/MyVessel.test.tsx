import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../App';
import { setLang } from '../i18n';
import { MODE_KEY } from '../lib/mode';
import { setUnits } from '../lib/units';
import { mockApi, type Call } from '../test/mockApi';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

const designCalls = (calls: Call[]) =>
  calls.filter((c) => new URL(c.url, 'http://x').pathname.endsWith('/design'));
const lastVessel = (calls: Call[]) =>
  (designCalls(calls).at(-1)?.body as { vessel?: unknown } | undefined)?.vessel;

describe('Mi buque (modo guiado, español)', () => {
  it('envía el buque en línea, en métrico, con la hélice y el guinche', async () => {
    const { calls } = mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    await userEvent.click(screen.getByRole('checkbox', { name: 'Usar mi buque' }));
    const form = screen.getByTestId('my-vessel');
    // Parte del buque elegido (150 BHP, 9 × 2,5 × 1,8 m).
    expect(within(form).getByRole('textbox', { name: /Potencia al freno/ })).toHaveValue('150');
    const bhp = within(form).getByRole('textbox', { name: /Potencia al freno/ });
    await userEvent.clear(bhp);
    await userEvent.type(bhp, '210');
    const len = within(form).getByRole('textbox', { name: /Eslora \[m\]/ });
    await userEvent.clear(len);
    await userEvent.type(len, '12,5');
    await userEvent.selectOptions(
      within(form).getByRole('combobox', { name: 'Tipo de hélice' }),
      'variable',
    );
    await userEvent.click(within(form).getByRole('checkbox', { name: /Con tobera/ }));
    await userEvent.type(
      within(form).getByRole('textbox', { name: /Diámetro de la hélice/ }),
      '1,1',
    );
    await userEvent.type(within(form).getByRole('textbox', { name: /Capacidad de cable/ }), '400');
    await userEvent.selectOptions(
      within(form).getByRole('combobox', { name: 'Región del puerto' }),
      'latam',
    );
    await waitFor(
      () =>
        expect(lastVessel(calls)).toMatchObject({
          id: 'mi_buque',
          bhp: 210,
          length_m: 12.5,
          beam_m: 2.5,
          depth_m: 1.8,
          propeller: 'variable_pitch_nozzle',
          nozzle: true,
          propeller_diameter_m: 1.1,
          winch_drum_capacity_m: 400,
          region: 'latam',
        }),
      { timeout: 3000 },
    );
    const body = designCalls(calls).at(-1)?.body as { params: Record<string, unknown> };
    expect(body.params.component_region).toBe('latam');
  });

  it('valida los datos y no calcula con una hélice sin KF de Fridman publicado', async () => {
    const { calls } = mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    await userEvent.click(screen.getByRole('checkbox', { name: 'Usar mi buque' }));
    const form = screen.getByTestId('my-vessel');
    const bhp = within(form).getByRole('textbox', { name: /Potencia al freno/ });
    await userEvent.clear(bhp);
    expect(await within(form).findByText('Dato obligatorio.')).toBeInTheDocument();
    await userEvent.type(bhp, 'abc');
    expect(await within(form).findByText('No es un número.')).toBeInTheDocument();
    await userEvent.clear(bhp);
    await userEvent.type(bhp, '200');
    await userEvent.click(within(form).getByRole('checkbox', { name: /Con tobera/ }));
    expect(await within(form).findByText(/sólo tabula el KF de Fridman/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Siguiente/ })).toBeDisabled();
    const n = designCalls(calls).length;
    await new Promise((r) => setTimeout(r, 600));
    expect(designCalls(calls).length).toBe(n);
    expect(designCalls(calls).some((c) => JSON.stringify(c.body).includes('mi_buque'))).toBe(false);
  });

  it('filtra el catálogo por tipo de buque', async () => {
    mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    expect(screen.getAllByRole('radio', { name: /BHP/ })).toHaveLength(4);
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Tipo de buque' }),
      'tangonero',
    );
    const radios = screen.getAllByRole('radio', { name: /BHP/ });
    expect(radios).toHaveLength(1);
    expect(radios[0]).toHaveAccessibleName(/Tangonero típico/);
    await userEvent.selectOptions(screen.getByRole('combobox', { name: 'Tipo de buque' }), 'book');
    expect(screen.getAllByRole('radio', { name: /BHP/ })).toHaveLength(2);
    expect(screen.getByText('2 de 4 buques')).toBeInTheDocument();
  });
});

describe('My vessel (English, imperial)', () => {
  it('reads feet and sends metres to the API', async () => {
    setLang('en');
    setUnits('imperial');
    const { calls } = mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    await userEvent.click(screen.getByRole('checkbox', { name: 'Use my vessel' }));
    const form = screen.getByTestId('my-vessel');
    // 9 m del buque de partida → 29.528 ft.
    const len = within(form).getByRole('textbox', { name: /Length \[ft\]/ });
    expect(len).toHaveValue('29.5276');
    await userEvent.clear(len);
    await userEvent.type(len, '40');
    const beam = within(form).getByRole('textbox', { name: /Beam \[ft\]/ });
    await userEvent.clear(beam);
    await userEvent.type(beam, '13');
    await userEvent.type(
      within(form).getByRole('textbox', { name: /Propeller diameter \(optional\) \[ft\]/ }),
      '3',
    );
    await userEvent.type(
      within(form).getByRole('textbox', { name: /Warp capacity per drum \(optional\) \[ft\]/ }),
      '1000',
    );
    await waitFor(
      () => {
        const v = lastVessel(calls) as Record<string, number>;
        expect(v.length_m).toBeCloseTo(12.192, 3);
        expect(v.beam_m).toBeCloseTo(3.9624, 3);
        expect(v.propeller_diameter_m).toBeCloseTo(0.9144, 4);
        expect(v.winch_drum_capacity_m).toBeCloseTo(304.8, 2);
        expect(v.bhp).toBe(150);
      },
      { timeout: 3000 },
    );
    expect(designCalls(calls).at(-1)?.url).toMatch(/\?lang=en$/);
    const step = document.querySelector('.wizard') as HTMLElement;
    expect(step.textContent).not.toMatch(/\b(Potencia|Eslora|Manga|Puntal|tobera|Usar)\b/);
  });

  it('shows the form in the expert case panel', async () => {
    setLang('en');
    window.localStorage.setItem(MODE_KEY, JSON.stringify('expert'));
    const { calls } = mockApi();
    renderApp();
    const box = await screen.findByRole('checkbox', { name: 'Use my vessel' });
    await userEvent.click(box);
    const form = screen.getByTestId('my-vessel');
    expect(screen.getByRole('combobox', { name: 'Vessel' })).toBeDisabled();
    const bhp = within(form).getByRole('textbox', { name: /Brake power/ });
    await userEvent.clear(bhp);
    await userEvent.type(bhp, '320');
    await waitFor(() => expect(lastVessel(calls)).toMatchObject({ id: 'mi_buque', bhp: 320 }), {
      timeout: 3000,
    });
  });
});
