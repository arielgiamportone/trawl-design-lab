import { expect, test } from '@playwright/test';

// Uso sin conexión (Fases 13 y 18): instalar la app, preparar el motor (Pyodide), cortar la red
// y calcular, ver la lista de materiales, cargar un aporte, el plano, el informe y simular, todo
// en el navegador.
test('sin conexión: el motor del teléfono calcula, arma la lista y valida un aporte', async ({
  page,
  context,
}) => {
  test.setTimeout(300_000);
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('resumen'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
  await page.goto('/');
  // El service worker se instala y toma el control (la segunda carga ya pasa por él).
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await expect
    .poll(() => page.evaluate(() => !!navigator.serviceWorker.controller), { timeout: 30_000 })
    .toBe(true);
  await expect(page.getByRole('status').filter({ hasText: 'API conectada' })).toBeVisible();

  const panel = page.getByTestId('offline-panel');
  await panel.locator('summary').click();
  await panel.getByRole('button', { name: 'Preparar uso sin conexión' }).click();
  await expect(panel.getByText(/Motor guardado/)).toBeVisible({ timeout: 240_000 });

  await context.setOffline(true);
  await page.reload();
  await expect(page.getByRole('status').filter({ hasText: 'motor del teléfono' })).toBeVisible({
    timeout: 120_000,
  });
  // El diseño de la A-3 se calcula en el teléfono (mismo resumen que la API).
  await expect(page.getByText('2,27').first()).toBeVisible({ timeout: 120_000 });

  await page.getByRole('tab', { name: 'Componentes' }).click();
  await page.getByRole('button', { name: 'Lista de materiales' }).click();
  const bom = page.getByTestId('bom');
  await expect(bom.locator('tr[data-line="warps"]')).toBeVisible({ timeout: 60_000 });
  await expect(bom.getByText('sin precio').first()).toBeVisible();

  await page.getByRole('button', { name: 'Aportar' }).click();
  const form = page.getByTestId('contribute');
  await form.getByLabel('Nombre (como lo conoce en el puerto)').fill('Cable del muelle');
  await form.getByLabel('Construcción (6x19, 6x24…)').fill('6x19');
  await form.getByLabel('Diámetro [mm]').fill('12');
  await form.getByLabel('Peso [kg/m]').fill('0,5');
  await form.getByLabel('Rotura [t]').fill('6,5');
  await form.getByRole('button', { name: 'Validar' }).click();
  await expect(form.getByText(/coherentes/)).toBeVisible({ timeout: 60_000 });
  await form.getByRole('button', { name: 'Guardar en este navegador' }).click();
  const item = form.locator('li[data-contribution="user_wire_cable_del_muelle"]');
  await expect(item).toContainText('aporte, sin verificar');
  const download = page.waitForEvent('download');
  await item.getByRole('button', { name: 'Exportar' }).click();
  expect((await download).suggestedFilename()).toBe('user_wire_cable_del_muelle.json');

  // La guía de construcción también sale del teléfono (el PDF no: avisa).
  await page.getByRole('tab', { name: 'Construcción' }).click();
  await expect(page.getByTestId('cut-sheet')).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: 'Guía en PDF (A4)' }).click();
  await expect(page.getByTestId('construction').getByRole('alert')).toContainText('conexión');
  const xlsx = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Planilla XLSX' }).click();
  expect((await xlsx).suggestedFilename()).toBe('guia-fao_a3_standard.xlsx');

  // Fase 18: el plano, el informe HTML y la simulación también corren en el teléfono.
  await page.getByRole('tab', { name: 'Plano' }).click();
  await expect(page.getByTestId('plan-image')).toBeVisible({ timeout: 60_000 });
  await page.getByRole('tab', { name: 'Descargas' }).click();
  const report = page.waitForEvent('download');
  await page.locator('button[data-download="html"]').click();
  expect((await report).suggestedFilename()).toMatch(/\.html$/);
  await page.getByRole('tab', { name: 'Simulación' }).click();
  await page.getByText('Rápida (3)').click();
  await page.getByRole('button', { name: 'Simular' }).click();
  await expect(page.getByTestId('sim-svg')).toHaveCount(3, { timeout: 180_000 });
  await context.setOffline(false);
});
