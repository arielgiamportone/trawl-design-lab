import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('catalogo'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
});

test('catálogo FAO: filtrar, ver la procedencia y usar una red de pareja', async ({ page }) => {
  test.setTimeout(120_000);
  await page.goto('/');
  const catalog = page.getByTestId('catalog');
  await expect(catalog).toBeVisible();
  // Los borradores no se muestran por defecto.
  await expect(catalog.locator('tr[data-net="scharfe_harstad_1436x200"]')).toHaveCount(0);
  await catalog.getByRole('combobox', { name: 'Aparejo' }).selectOption('pair');
  const row = catalog.locator('tr[data-net="bobp_wp13_pair_ho80"]');
  await expect(row).toBeVisible();
  await expect(catalog.locator('tr[data-net="fao_a3_standard"]')).toHaveCount(0);
  await row.getByRole('button').click();

  const prov = page.getByTestId('provenance');
  await expect(prov.locator('tr[data-path="panels.F.meshes_depth"]')).toContainText('Transcripto');
  await page.getByRole('button', { name: 'Supuesto', exact: true }).click();
  await expect(prov.locator('tr[data-path="panels.F.meshes_depth"]')).toHaveCount(0);
  await expect(page.getByTestId('net-issues')).toContainText('corte');

  await page.getByRole('button', { name: 'Usar esta red' }).click();
  await expect(page.getByRole('button', { name: 'Es la red del caso' })).toBeVisible();
  await expect(page.getByLabel('Red', { exact: true })).toHaveValue('bobp_wp13_pair_ho80');
  await expect(page.getByLabel('Buque', { exact: true })).toHaveValue('');
  // El caso del catálogo: pareja sin portones, buque de la potencia de diseño.
  await page.getByRole('tab', { name: /Notas y erratas/ }).click();
  await expect(page.getByText(/pair_trawl: arrastre de pareja sin portones/)).toBeVisible({
    timeout: 60_000,
  });
  await expect(page.getByText(/catalog: buque genérico de 31.5 hp/)).toBeVisible();
});
