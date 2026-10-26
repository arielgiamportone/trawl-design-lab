import { expect, test, type Locator, type Page } from '@playwright/test';

// Capturas de README y docs/web.md. Cada prueba deja un PNG en docs/screenshots/.
const OUT = 'docs/screenshots';

async function start(
  page: Page,
  opts: { mode: 'expert' | 'simple'; tab?: string; dark?: boolean },
) {
  await page.addInitScript((o) => {
    if (!sessionStorage.getItem('shot-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify(o.mode));
      if (o.tab) localStorage.setItem('trawl-design-lab:tab', JSON.stringify(o.tab));
      localStorage.setItem('trawl-design-lab:theme', JSON.stringify(o.dark ? 'dark' : 'light'));
      sessionStorage.setItem('shot-init', '1');
    }
  }, opts);
  await page.goto('/');
  await expect(page.getByRole('status').filter({ hasText: /conectada|teléfono/ })).toBeVisible({
    timeout: 60_000,
  });
}

// Sin `focus` la captura muestra el inicio de la página; con `focus`, ese elemento arriba.
async function shot(page: Page, name: string, focus?: Locator) {
  if (focus) await focus.evaluate((el) => el.scrollIntoView({ block: 'start' }));
  else await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}.png` });
}

test.describe('escritorio', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('modo guiado: diagnóstico', async ({ page }) => {
    await start(page, { mode: 'simple' });
    await page.getByRole('radio', { name: /180 BHP/ }).check();
    await page.getByRole('button', { name: 'Siguiente →' }).click();
    await page.getByRole('button', { name: 'Siguiente →' }).click();
    await page.getByRole('slider', { name: /Velocidad de arrastre/ }).fill('2');
    await page.getByRole('button', { name: 'Ver resultado →' }).click();
    await expect(page.locator('[data-check="pull"]')).toHaveClass(/ok|warn|crit/);
    await shot(page, 'guiado-diagnostico');
  });

  test('experto: resumen y KPI', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'resumen' });
    await expect(page.locator('tr[data-key="horizontal_opening_m"]')).toBeVisible();
    await shot(page, 'escritorio-claro-caso');
  });

  test('gráficos en tema oscuro', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'graficos', dark: true });
    await expect(page.locator('.recharts-surface').first()).toBeVisible({ timeout: 30_000 });
    await shot(page, 'escritorio-oscuro-graficos');
  });

  test('diseño interactivo', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'diseno' });
    await page.waitForTimeout(2500);
    await shot(page, 'escritorio-diseno-interactivo');
  });

  test('optimizar', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'optimizar' });
    await page.getByRole('button', { name: 'Optimizar', exact: true }).click();
    await expect(page.getByTestId('opt-best')).toBeVisible({ timeout: 60_000 });
    await expect(page.locator('[data-chart="opt-pareto"] svg.recharts-surface')).toBeVisible();
    await shot(page, 'escritorio-claro-optimizar', page.getByTestId('opt-best'));
  });

  test('simulación 3D', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'simulacion' });
    await page.getByRole('button', { name: 'Simular' }).click();
    await expect(page.getByTestId('net3d-canvas')).toBeVisible({ timeout: 90_000 });
    await page.waitForTimeout(2500);
    await shot(page, 'escritorio-simulacion-3d', page.locator('h3', { hasText: 'Vista 3D' }));
  });

  test('selectividad', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'simulacion' });
    await page.getByRole('button', { name: 'Mallas y selectividad' }).click();
    await page.getByRole('checkbox', { name: 'Bacalao' }).check();
    await page.getByRole('combobox', { name: 'Resolución' }).selectOption('2');
    await page.getByRole('button', { name: 'Calcular selectividad' }).click();
    await expect(page.getByTestId('selectivity-table')).toBeVisible({ timeout: 120_000 });
    await shot(page, 'escritorio-selectividad');
  });

  test('catálogo FAO', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'catalogo' });
    await page.locator('tr[data-net="fao_wb_bt2p_60hp"]').getByRole('button').click();
    await expect(page.getByTestId('provenance')).toBeVisible({ timeout: 30_000 });
    await shot(page, 'escritorio-catalogo-fao', page.locator('tr[data-net="bobp_wp20_ho"]'));
  });

  test('componentes: lista de materiales', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'componentes' });
    await page.getByRole('button', { name: 'Lista de materiales' }).click();
    await expect(page.getByTestId('bom').locator('tr[data-line="warps"]')).toBeVisible({
      timeout: 30_000,
    });
    await shot(page, 'escritorio-componentes');
  });

  test('construcción: armado paso a paso', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'construccion' });
    await expect(page.getByTestId('cut-sheet')).toBeVisible({ timeout: 30_000 });
    await page.getByLabel('Paño A cortado').check();
    await page.getByLabel('Paño B cortado').check();
    await page.getByRole('button', { name: 'Armado paso a paso' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await expect(page.getByTestId('join-map')).toBeVisible();
    await shot(page, 'escritorio-construccion', page.getByTestId('guide-summary'));
  });

  test('economía de la marea', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'economia' });
    const eco = page.getByTestId('economics');
    await expect(eco.getByTestId('eco-summary')).toBeVisible({ timeout: 30_000 });
    const fill: [string, string][] = [
      ['Captura por hora de arrastre', '150'],
      ['Precio en playa', '1000'],
      ['Precio del gasoil', '1200'],
      ['Precio del lubricante', '6000'],
      ['Parte de la tripulación', '40'],
      ['Hielo, víveres, carnada y puerto', '150000'],
      ['Permisos, seguro y fijos', '6000000'],
    ];
    await eco.getByLabel('Moneda', { exact: true }).fill('ARS');
    for (const [label, value] of fill) await eco.getByLabel(label).fill(value);
    await eco.getByLabel('Costo de la red y el aparejo', { exact: true }).fill('3000000');
    await expect(eco.getByTestId('eco-summary')).not.toContainText('Faltan datos');
    await eco.locator('details.accordion summary').first().click();
    await page.waitForTimeout(800);
    await shot(page, 'escritorio-economia', eco.getByTestId('eco-summary'));
  });

  test('lotes y flota', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'lotes' });
    const fleet =
      'nombre;potencia [hp];eslora [m];profundidad [m]\n' +
      'Don Pedro;45;10;25\nCostero;60;11;30\nLa Gaviota;110;14;50\n' +
      'Bolichero;150;17;60\nAltura;250;22;90\n';
    await page.getByLabel('Planilla del lote').setInputFiles({
      name: 'flota.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(fleet, 'utf-8'),
    });
    await page.getByLabel('Red a proyectar').selectOption('fao_wb_bt2p_60hp');
    await page.getByRole('button', { name: 'Calcular el lote' }).click();
    await expect(page.getByTestId('batch-results').locator('tbody tr')).toHaveCount(5, {
      timeout: 180_000,
    });
    await shot(page, 'escritorio-lotes', page.getByLabel('Red a proyectar'));
  });
});

test.describe('teléfono', () => {
  test.use({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });

  test('plano en el teléfono', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'plano' });
    await expect(page.getByTestId('plan-image')).toBeVisible();
    await page.waitForTimeout(2000);
    await shot(page, 'movil-plano', page.getByRole('tablist').first());
  });

  test('guía para el taller en el teléfono', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'construccion' });
    await expect(page.getByTestId('cut-sheet')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: 'Armado paso a paso' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await expect(page.getByTestId('join-map')).toBeVisible();
    await shot(page, 'movil-guia-taller', page.getByTestId('assembly'));
  });

  test('sin conexión: motor del teléfono', async ({ page, context }) => {
    await start(page, { mode: 'simple' });
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
    });
    await page.reload();
    const panel = page.getByTestId('offline-panel');
    await panel.locator('summary').click();
    await panel.getByRole('button', { name: 'Preparar uso sin conexión' }).click();
    await expect(panel.getByText(/Motor guardado/)).toBeVisible({ timeout: 240_000 });
    await context.setOffline(true);
    await page.reload();
    await expect(page.getByRole('status').filter({ hasText: 'motor del teléfono' })).toBeVisible({
      timeout: 120_000,
    });
    await page.getByRole('radio', { name: /150 BHP/ }).check();
    await shot(page, 'movil-sin-conexion');
    await context.setOffline(false);
  });
});
