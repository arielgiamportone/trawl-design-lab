import { expect, test, type Page } from '@playwright/test';

const FLEET =
  'nombre;potencia (kW);eslora [m];profundidad [m]\n' +
  'Don Pedro;44;11;30\nLa Gaviota;110;14;50\nEstrella;55;12;40\n';

async function openBatch(page: Page) {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('lotes'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
  await page.goto('/');
  return page.getByTestId('batch');
}

async function uploadFleet(page: Page) {
  const batch = page.getByTestId('batch');
  await batch.getByLabel('Planilla del lote').setInputFiles({
    name: 'flota.csv',
    mimeType: 'text/csv',
    buffer: Buffer.from(FLEET, 'utf-8'),
  });
  await expect(page.getByTestId('fleet-preview').locator('tbody tr')).toHaveCount(3);
  await batch.getByLabel('Red a proyectar').selectOption('fao_wb_bt2p_60hp');
}

test('lote de flota: plantilla, proyección, XLSX y abrir un buque', async ({ page }) => {
  test.setTimeout(180_000);
  const batch = await openBatch(page);
  const tpl = page.waitForEvent('download');
  await batch.getByRole('button', { name: 'Descargar plantilla XLSX' }).click();
  expect((await tpl).suggestedFilename()).toBe('plantilla_flota.xlsx');

  await uploadFleet(page);
  await batch.getByRole('button', { name: 'Calcular el lote' }).click();
  const results = page.getByTestId('batch-results');
  await expect(results.locator('tbody tr')).toHaveCount(3, { timeout: 120_000 });
  await expect(results).toContainText('Don Pedro');

  const xlsx = page.waitForEvent('download');
  await batch.getByRole('button', { name: 'Descargar XLSX' }).click();
  expect((await xlsx).suggestedFilename()).toBe('lote.xlsx');

  await results.locator('tbody tr').nth(1).getByRole('button', { name: 'Abrir este caso' }).click();
  await expect(page.getByTestId('from-batch')).toContainText('La Gaviota');
  await expect(page.getByTestId('scaled-net')).toBeVisible();
});

test('lote de flota sin conexión con el motor del teléfono', async ({ page, context }) => {
  test.setTimeout(300_000);
  await openBatch(page);
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect
    .poll(() => page.evaluate(() => !!navigator.serviceWorker.controller), { timeout: 30_000 })
    .toBe(true);
  const panel = page.getByTestId('offline-panel');
  await panel.locator('summary').click();
  await panel.getByRole('button', { name: 'Preparar uso sin conexión' }).click();
  await expect(panel.getByText(/Motor guardado/)).toBeVisible({ timeout: 240_000 });

  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole('status').filter({ hasText: 'motor del teléfono' })).toBeVisible({
    timeout: 120_000,
  });
  await uploadFleet(page);
  const batch = page.getByTestId('batch');
  await batch.getByLabel('Armar con el catálogo (más lento)').uncheck();
  await batch.getByRole('button', { name: 'Calcular el lote' }).click();
  await expect(page.getByTestId('batch-results').locator('tbody tr')).toHaveCount(3, {
    timeout: 180_000,
  });
  const xlsx = page.waitForEvent('download');
  await batch.getByRole('button', { name: 'Descargar XLSX' }).click();
  expect((await xlsx).suggestedFilename()).toBe('lote.xlsx');
  await context.setOffline(false);
});
