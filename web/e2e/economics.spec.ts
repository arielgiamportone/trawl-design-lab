import { expect, test } from '@playwright/test';

test('economía: datos de la marea, mejor velocidad y comparación', async ({ page }) => {
  test.setTimeout(120_000);
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('economia'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
  await page.goto('/');
  const eco = page.getByTestId('economics');
  await expect(eco.getByTestId('eco-summary')).toContainText('Faltan datos', { timeout: 60_000 });
  await eco.getByLabel('Moneda', { exact: true }).fill('ARS');
  await eco.getByLabel('Captura por hora de arrastre').fill('150');
  await eco.getByLabel('Precio en playa').fill('1000');
  await eco.getByLabel('Precio del gasoil').fill('1200');
  await eco.getByLabel('Precio del lubricante').fill('6000');
  await eco.getByLabel('Parte de la tripulación').fill('40');
  await eco.getByLabel('Costo de la red y el aparejo', { exact: true }).fill('3000000');
  await eco.getByLabel('Hielo, víveres, carnada y puerto').fill('150000');
  await eco.getByLabel('Permisos, seguro y fijos').fill('6000000');
  const summary = eco.getByTestId('eco-summary');
  await expect(summary).not.toContainText('Faltan datos', { timeout: 30_000 });
  await expect(summary).toContainText('Velocidad de mayor margen2 kn');
  await expect(eco.getByTestId('eco-breakdown')).toContainText('Combustible');
  await expect(eco.locator('tr.row-best')).toHaveCount(1);

  // Los datos quedan guardados.
  await page.reload();
  await expect(page.getByTestId('eco-summary')).not.toContainText('Faltan datos', {
    timeout: 60_000,
  });

  await page.getByRole('button', { name: 'Comparar redes' }).click();
  const box = page.getByTestId('eco-compare');
  await box.getByLabel('Red a comparar').selectOption('fao_wb_bt2p_60hp');
  await box.getByLabel('Costo de la red nueva').fill('2000000');
  await box.getByRole('button', { name: 'Calcular' }).click();
  const table = box.getByRole('table', { name: 'Comparación económica' });
  await expect(table.locator('tbody tr')).toHaveCount(2, { timeout: 60_000 });
  await expect(table.locator('tr[data-compare="fao_wb_bt2p_60hp"]')).toContainText('ARS');
});

test('modo guiado: «¿Cuánto deja la marea?» abre la economía', async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      sessionStorage.setItem('e2e-init', '1');
    }
  });
  await page.goto('/');
  for (let i = 0; i < 3; i++) {
    await page.getByRole('button', { name: /Siguiente →|Ver resultado →/ }).click();
  }
  await page.getByRole('button', { name: '¿Cuánto deja la marea? Economía' }).click();
  await expect(page.getByTestId('economics')).toBeVisible({ timeout: 60_000 });
});
