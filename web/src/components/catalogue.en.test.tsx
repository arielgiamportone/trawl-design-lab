/**
 * Catálogo, componentes, lotes, construcción y economía en inglés y en unidades imperiales
 * (Fase 18.3). Se montan los componentes sueltos con los proveedores del caso y la API simulada;
 * los textos de los fixtures (datos y notas del motor) están en español porque se grabaron así,
 * por eso el control de palabras en español mira sólo los textos propios de la interfaz.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactElement } from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../i18n';
import { bomCsv, type Bom } from '../lib/components';
import { forgetAll } from '../lib/memo';
import { fmtU, setUnits } from '../lib/units';
import { CaseProvider } from '../state/CaseProvider';
import { ConnectionProvider } from '../state/ConnectionProvider';
import { fixtures, mockApi } from '../test/mockApi';
import { Batch } from './Batch';
import { Catalog } from './Catalog';
import { Components } from './Components';
import { Construction } from './construction/Construction';
import { Economics } from './economics/Economics';

const SLOW = 20_000;

/** Palabras de la interfaz en español que no deben aparecer en inglés. */
const SPANISH =
  /\b(Calcular|Descargar|Precio|Combustible|Guardar|Abrir|Cerrar|Cargando|Usar|Todas|Todos|Buscar|Moneda|Costo|Margen|Paso|Hecho|Cabo|Lima|Burlón|Portón|Tipo|Fuente|del|las|los|una|para|por|con)\b/;

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

/**
 * Textos propios de la interfaz: títulos, encabezados, botones, rótulos (sólo su texto directo,
 * sin las opciones de datos) y atributos de accesibilidad de controles y tablas.
 */
function uiText(root: HTMLElement): string {
  const own = (el: Element) =>
    Array.from(el.childNodes)
      .filter((n) => n.nodeType === Node.TEXT_NODE)
      .map((n) => n.textContent ?? '')
      .join(' ');
  const parts: string[] = [];
  root
    .querySelectorAll(
      'th, button:not(.link-button), h3, h4, legend, summary span, .kpi-label, .section-sub, label, figcaption',
    )
    .forEach((el) => parts.push(own(el)));
  root
    .querySelectorAll(
      'select, table, progress, [role="group"], [role="search"], input[type="search"]',
    )
    .forEach((el) => {
      parts.push(el.getAttribute('aria-label') ?? '', el.getAttribute('placeholder') ?? '');
    });
  return parts.join(' | ');
}

beforeEach(() => {
  localStorage.clear();
  forgetAll();
  setLang('en');
});
afterEach(() => vi.unstubAllGlobals());

describe('catalogue and components in English', () => {
  it(
    'net catalogue: filters, table and validator in English',
    async () => {
      mockApi();
      renderIn(<Catalog />);
      const tab = await screen.findByTestId('catalog', {}, { timeout: 5000 });
      expect(await within(tab).findByRole('table', { name: 'Catalogue nets' })).toBeInTheDocument();
      expect(within(tab).getByRole('option', { name: 'All families' })).toBeInTheDocument();
      expect(
        await within(tab).findByRole(
          'heading',
          { name: 'Consistency validator' },
          { timeout: 3000 },
        ),
      ).toBeInTheDocument();
      expect(within(tab).getByText('Show drafts')).toBeInTheDocument();
      expect(uiText(tab)).not.toMatch(SPANISH);
    },
    SLOW,
  );

  it(
    'component catalogue, bill of materials and contributions in English',
    async () => {
      mockApi();
      renderIn(<Components />);
      const tab = await screen.findByTestId('components', {}, { timeout: 5000 });
      const table = await within(tab).findByRole('table', {
        name: 'Components: Steel wire rope',
      });
      await waitFor(() => expect(within(table).getAllByRole('row').length).toBeGreaterThan(5));
      expect(
        within(table).getByRole('columnheader', { name: 'Weight [kg/m]' }),
      ).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Use in the case' })).toBeInTheDocument();
      expect(uiText(tab)).not.toMatch(SPANISH);

      await userEvent.click(screen.getByRole('button', { name: 'Bill of materials' }));
      expect(await screen.findByTestId('bom-total-USD', {}, { timeout: 3000 })).toHaveTextContent(
        '900',
      );
      expect(screen.getAllByText('no price').length).toBeGreaterThan(0);
      expect(screen.getByRole('row', { name: /Indicative total/ })).toBeInTheDocument();
      expect(uiText(tab)).not.toMatch(SPANISH);

      await userEvent.click(screen.getByRole('button', { name: 'Contribute' }));
      const form = screen.getByTestId('contribute');
      expect(within(form).getByLabelText('Diameter [mm]')).toBeInTheDocument();
      expect(within(form).getByRole('button', { name: 'Validate' })).toBeInTheDocument();
      expect(uiText(tab)).not.toMatch(SPANISH);
    },
    SLOW,
  );

  it('the bill-of-materials CSV has English headers, commas and imperial quantities', () => {
    setUnits('imperial');
    const csv = bomCsv(fixtures.bom as Bom);
    const [head, first] = csv.split('\n');
    expect(head).toBe('Item,Component,Quantity,Unit,Unit price,Currency,Cost,Note');
    expect(csv).toContain('no price');
    // 33,482 kg de paño → 73,815 lb
    expect(first).toContain(',73.815');
    expect(first).toContain(',lb,');
  });
});

describe('batches, construction and economics in English', () => {
  it(
    'batch tab in English',
    async () => {
      mockApi();
      renderIn(<Batch />);
      const tab = await screen.findByTestId('batch', {}, { timeout: 5000 });
      expect(within(tab).getByRole('button', { name: 'Vessel fleet' })).toBeInTheDocument();
      expect(within(tab).getByRole('button', { name: 'Compute the batch' })).toBeDisabled();
      const file = new File(['nombre;potencia\nDon Pedro;60\n'], 'flota.csv', { type: 'text/csv' });
      await userEvent.upload(within(tab).getByLabelText('Batch spreadsheet'), file);
      const preview = await screen.findByTestId('fleet-preview', {}, { timeout: 3000 });
      expect(within(preview).getByRole('columnheader', { name: 'Power [hp]' })).toBeInTheDocument();
      await userEvent.click(screen.getByRole('button', { name: 'Compute the batch' }));
      const results = await screen.findByTestId('batch-results', {}, { timeout: 3000 });
      expect(within(results).getAllByText('feasible').length).toBeGreaterThan(0);
      expect(
        within(results).getByRole('columnheader', { name: 'Headrope [m]' }),
      ).toBeInTheDocument();
      expect(
        within(results).getAllByRole('button', { name: 'Open this case' }).length,
      ).toBeGreaterThan(0);
      expect(uiText(tab)).not.toMatch(SPANISH);
    },
    SLOW,
  );

  it(
    'construction guide in English and imperial units (ft, lb)',
    async () => {
      setUnits('imperial');
      mockApi();
      renderIn(<Construction />);
      const tab = await screen.findByTestId('construction', {}, { timeout: 5000 });
      const summary = await screen.findByTestId('guide-summary', {}, { timeout: 5000 });
      expect(summary).toHaveTextContent('Netting to purchase');
      expect(summary).toHaveTextContent(/lb/);
      expect(screen.getByRole('columnheader', { name: 'Weight [lb]' })).toBeInTheDocument();
      expect(screen.getByRole('columnheader', { name: 'Mesh size [mm (in)]' })).toBeInTheDocument();
      expect(uiText(tab)).not.toMatch(SPANISH);
      await userEvent.click(screen.getByRole('button', { name: 'Ropes and wires' }));
      const cuts = await screen.findByTestId('rope-cuts');
      expect(within(cuts).getByRole('columnheader', { name: 'Finished [ft]' })).toBeInTheDocument();
      const rope = fixtures.construction.ropes[0]!;
      const row = cuts.querySelector(`[data-rope="${rope.key}"]`) as HTMLElement;
      // 28,698 m → 94,15 ft
      expect(row).toHaveTextContent(fmtU(rope.length_m, 'm', { digits: 2, unit: false }));
      expect(row).toHaveTextContent('94.15');
      expect(screen.getByLabelText('Eye allowance')).toHaveValue('1.64');
      expect(uiText(tab)).not.toMatch(SPANISH);
    },
    SLOW,
  );

  it(
    'economics in English: a diesel price entered per gallon reaches the API per litre',
    async () => {
      setUnits('imperial');
      const { calls } = mockApi();
      renderIn(<Economics />);
      const tab = await screen.findByTestId('economics', {}, { timeout: 5000 });
      const summary = await screen.findByTestId('eco-summary', {}, { timeout: 5000 });
      expect(summary).toHaveTextContent('Best-margin speed');
      expect(summary).toHaveTextContent('Cost per lb');
      const units = Array.from(tab.querySelectorAll('.unit')).map((u) => u.textContent);
      expect(units).toContain(' [USD per gal]');
      expect(units).toContain(' [lb/h]');
      expect(screen.getByRole('columnheader', { name: 'Fuel [gal]' })).toBeInTheDocument();
      expect(uiText(tab)).not.toMatch(SPANISH);
      await userEvent.type(screen.getByLabelText('Diesel price'), '3.785411784');
      await waitFor(() =>
        expect(
          calls.some((c) => {
            const p = (c.body as { economics?: { fuel_price_l?: number } } | undefined)?.economics
              ?.fuel_price_l;
            return (
              new URL(c.url, 'http://x').pathname.endsWith('/economics') &&
              p !== undefined &&
              Math.abs(p - 1) < 1e-9
            );
          }),
        ).toBe(true),
      );
      // El campo conserva lo escrito (en $/gal) aunque se guarde por litro.
      expect(screen.getByLabelText('Diesel price')).toHaveValue('3.785411784');
      const saved = JSON.parse(localStorage.getItem('trawl-design-lab:economics')!);
      expect(Number(saved.values.fuel_price_l)).toBeCloseTo(1, 9);
    },
    SLOW,
  );
});
