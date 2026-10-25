import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { MODE_KEY } from '../../lib/mode';
import { PROJECTS_KEY } from '../../lib/projects';
import { mockApi } from '../../test/mockApi';

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

afterEach(() => vi.unstubAllGlobals());

const next = () => userEvent.click(screen.getByRole('button', { name: /Siguiente|Ver resultado/ }));

describe('modo guiado', () => {
  it('es el modo por defecto y recorre los cuatro pasos hasta el diagnóstico', async () => {
    const { calls } = mockApi();
    renderApp();
    expect(screen.getByRole('button', { name: 'Guiado' })).toHaveAttribute('aria-pressed', 'true');
    expect(screen.getByRole('heading', { name: 'Paso 1 de 4: Buque' })).toBeInTheDocument();

    // Paso 1: buque de 180 BHP y hélice de paso variable con tobera
    await userEvent.click(await screen.findByRole('radio', { name: /180 BHP/ }));
    await userEvent.click(screen.getByRole('radio', { name: /Paso variable con tobera/ }));
    await next();

    // Paso 2: red y portones
    expect(screen.getByRole('heading', { name: 'Paso 2 de 4: Red' })).toHaveFocus();
    expect(screen.getByRole('radio', { name: /estándar, bolsa 40 mm/ })).toBeChecked();
    expect(screen.getByRole('checkbox', { name: /Comparar con otra red/ })).toBeChecked();
    await next();

    // Paso 3: velocidad y profundidad
    const speed = screen.getByRole('slider', { name: /Velocidad de arrastre/ });
    fireEvent.change(speed, { target: { value: '1.5' } });
    expect(screen.getByText('1,5 kn')).toBeInTheDocument();
    const depth = screen.getByRole('textbox', { name: /Profundidad de trabajo/ });
    await userEvent.type(depth, '2000');
    expect(await screen.findByText(/Fuera del rango habitual/)).toBeInTheDocument();
    await userEvent.clear(depth);
    await userEvent.type(depth, '60');
    await userEvent.selectOptions(
      screen.getByRole('combobox', { name: 'Región del puerto' }),
      'latam',
    );
    await userEvent.click(screen.getByRole('checkbox', { name: /Sólo componentes genéricos/ }));
    await next();

    // Paso 4: diagnóstico
    expect(screen.getByRole('heading', { name: 'Paso 4 de 4: Resultado' })).toBeInTheDocument();
    const pull = await screen.findByText('¿Le alcanza la potencia?', {}, { timeout: 3000 });
    expect(pull.closest('[data-check]')).toHaveClass('ok');
    expect(screen.getByText('El diseño es viable a la velocidad elegida.')).toBeInTheDocument();
    const swept = screen.getByText('Área barrida por hora').closest('li') as HTMLElement;
    await userEvent.click(within(swept).getByText('¿Por qué?'));
    expect(within(swept).getByText(/distancia recorrida en una hora a 1,5 kn/)).toBeVisible();

    await waitFor(() => {
      const last = calls.filter((c) => c.url.endsWith('/design')).at(-1);
      expect(last?.body).toMatchObject({
        vessel: 'fao_a3_180hp',
        params: {
          ft_propeller: 'variable_pitch_nozzle',
          depth_m: 60,
          component_region: 'latam',
          generic_only: true,
        },
      });
    });
  });

  it('ofrece bajar a la velocidad máxima viable cuando no se alcanza', async () => {
    mockApi();
    renderApp();
    await screen.findByRole('radio', { name: /150 BHP/ });
    await next();
    await next();
    fireEvent.change(screen.getByRole('slider'), { target: { value: '3' } });
    await next();
    const banner = await screen.findByText(/no funciona así/, {}, { timeout: 3000 });
    expect(banner.closest('[data-overall]')).toHaveAttribute('data-overall', 'crit');
    await userEvent.click(screen.getByRole('button', { name: 'Probar a 2,2 kn (máxima viable)' }));
    expect(await screen.findByText(/viable, pero con poco margen/)).toBeInTheDocument();
  });

  it('pasa al modo experto con el mismo caso y lo recuerda', async () => {
    mockApi();
    renderApp();
    await userEvent.click(await screen.findByRole('radio', { name: /180 BHP/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Experto' }));
    expect(screen.getByRole('tab', { name: 'Resumen' })).toBeInTheDocument();
    expect(screen.getByLabelText('Buque')).toHaveValue('fao_a3_180hp');
    expect(JSON.parse(window.localStorage.getItem(MODE_KEY) as string)).toBe('expert');
  });

  it('deshace y rehace cambios del caso (botones y Ctrl+Z)', async () => {
    mockApi();
    renderApp();
    const r180 = await screen.findByRole('radio', { name: /180 BHP/ });
    const undo = screen.getByRole('button', { name: /Deshacer/ });
    expect(undo).toBeDisabled();
    await userEvent.click(r180);
    expect(r180).toBeChecked();
    await userEvent.click(undo);
    expect(screen.getByRole('radio', { name: /150 BHP/ })).toBeChecked();
    await userEvent.click(screen.getByRole('button', { name: /Rehacer/ }));
    expect(r180).toBeChecked();
    (document.activeElement as HTMLElement | null)?.blur();
    fireEvent.keyDown(window, { key: 'z', ctrlKey: true });
    expect(screen.getByRole('radio', { name: /150 BHP/ })).toBeChecked();
  });

  it('guarda, abre e importa proyectos', async () => {
    mockApi();
    renderApp();
    await userEvent.click(await screen.findByRole('radio', { name: /180 BHP/ }));
    await userEvent.click(screen.getByText('Proyectos'));
    await userEvent.type(screen.getByLabelText('Nombre del proyecto'), 'Beagle 180{Enter}');
    expect(screen.getByText('Guardado «Beagle 180» en este navegador.')).toBeInTheDocument();
    expect(JSON.parse(window.localStorage.getItem(PROJECTS_KEY) as string)).toHaveLength(1);

    await userEvent.click(screen.getByRole('radio', { name: /150 BHP/ }));
    await userEvent.click(screen.getByRole('button', { name: 'Abrir' }));
    expect(screen.getByRole('radio', { name: /180 BHP/ })).toBeChecked();

    const bad = new File(['{"x":1}'], 'otro.json', { type: 'application/json' });
    await userEvent.upload(screen.getByLabelText('Archivo de proyecto'), bad);
    expect(await screen.findByText('No es un proyecto de trawl-design-lab.')).toBeInTheDocument();
  });
});
