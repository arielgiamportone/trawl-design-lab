import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { setLang } from '../../i18n';
import { setUnits } from '../../lib/units';
import { mockApi, type Call } from '../../test/mockApi';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

/** Palabras del español que no deben quedar en la interfaz en inglés (fuera de los datos). */
const SPANISH =
  /\b(Resumen|Guardar|Descargar|Velocidad|Resistencia|Abrir|Cerrar|Paso|Siguiente|Anterior|Buque|Hélice|Portones|Calculando|Profundidad|Captura|Atención|Problema|Bien|del|las|los|que|con|para|el|la)\b/;

const next = () => userEvent.click(screen.getByRole('button', { name: /Next|See result/ }));

const designCalls = (calls: Call[]) =>
  calls.filter((c) => new URL(c.url, 'http://x').pathname.endsWith('/design'));

describe('guided mode in English', () => {
  it('walks the four steps and shows the diagnosis in English', async () => {
    setLang('en');
    const { calls } = mockApi();
    renderApp();
    expect(screen.getByRole('heading', { name: 'Step 1 of 4: Vessel' })).toBeInTheDocument();
    await userEvent.click(await screen.findByRole('radio', { name: /180 BHP/ }));
    await userEvent.click(
      screen.getByRole('radio', { name: /Controllable pitch with nozzle/ }),
    );
    await next();

    expect(screen.getByRole('heading', { name: 'Step 2 of 4: Net' })).toBeInTheDocument();
    expect(screen.getByRole('checkbox', { name: /Compare with another net/ })).toBeChecked();
    expect(screen.getByRole('combobox', { name: /Otter boards/ })).toBeInTheDocument();
    await next();

    expect(screen.getByRole('heading', { name: 'Step 3 of 4: Operation' })).toBeInTheDocument();
    fireEvent.change(screen.getByRole('slider', { name: /Towing speed/ }), {
      target: { value: '1.5' },
    });
    expect(screen.getByText('1.5 kn')).toBeInTheDocument();
    const depth = screen.getByRole('textbox', { name: /Working depth \[m\]/ });
    await userEvent.type(depth, '2000');
    expect(await screen.findByText(/Outside the usual range \(10–800 m\)/)).toBeInTheDocument();
    await userEvent.clear(depth);
    await next();

    expect(screen.getByRole('heading', { name: 'Step 4 of 4: Result' })).toBeInTheDocument();
    const pull = await screen.findByText('Is there enough power?', {}, { timeout: 3000 });
    expect(pull.closest('[data-check]')).toHaveClass('ok');
    expect(screen.getByText('Yes: 94% to spare')).toBeInTheDocument();
    expect(screen.getByText('2.27 kn')).toBeInTheDocument();
    expect(screen.getByText('The design is feasible at the chosen speed.')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Adjust the net on the plan' })).toBeInTheDocument();
    expect(screen.getAllByText('Why?').length).toBeGreaterThan(0);
    const wizard = document.querySelector('.wizard') as HTMLElement;
    expect(wizard.textContent).not.toMatch(SPANISH);
    // Los pedidos a la API llevan el idioma.
    expect(designCalls(calls).at(-1)?.url).toMatch(/\?lang=en$/);
  });

  it('accepts the depth in feet and sends it to the API in metres', async () => {
    setLang('en');
    setUnits('imperial');
    const { calls } = mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    await next();
    await next();
    const depth = screen.getByRole('textbox', { name: /Working depth \[ft\]/ });
    await userEvent.type(depth, '200');
    // 200 ft = 60,96 m
    await waitFor(
      () => {
        const body = designCalls(calls).at(-1)?.body as { params: Record<string, unknown> };
        expect(body.params.depth_m).toBeCloseTo(60.96, 2);
      },
      { timeout: 3000 },
    );
    // Rango habitual en pies y captura en libras.
    await userEvent.clear(depth);
    await userEvent.type(depth, '5000');
    expect(await screen.findByText(/Outside the usual range \(32\.808–2,624\.7 ft\)/)).toBeInTheDocument();
    expect(screen.getByRole('spinbutton', { name: /Expected catch per haul \[lb\]/ })).toHaveValue(
      1102,
    );
    await next();
    const opening = await screen.findByText('Net mouth', {}, { timeout: 3000 });
    expect(opening.closest('li')?.textContent).toMatch(/ft × .* ft/);
  });
});
