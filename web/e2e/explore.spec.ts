import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('simulacion'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
});

test('explorador animado por largo de cable contra la API real', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Explorador animado' }).click();
  await page.getByRole('combobox', { name: 'Variable a recorrer' }).selectOption('warp_length_m');
  await page.getByRole('combobox', { name: 'Estados' }).selectOption('3');
  await page.getByRole('combobox', { name: 'Resolución' }).selectOption('2');
  await page.getByRole('button', { name: 'Calcular estados' }).click();

  const dash = page.getByTestId('explore-dashboard');
  await expect(dash).toBeVisible({ timeout: 90_000 });
  const dp = dash.locator('[data-indicator="dp"]');
  await expect(dp).toContainText('igual al primer estado');
  await expect(page.getByTestId('netanim-canvas')).toBeVisible({ timeout: 30_000 });

  // Reproducir lleva la animación hasta el último estado: más cable, portones más abiertos.
  await page.getByRole('button', { name: '▶ Reproducir' }).click();
  await expect(page.locator('.timeline-value')).toContainText('320 m', { timeout: 15_000 });
  await expect(dp).toContainText('+');
  await expect(dp).toHaveClass(/good/);
  await page.getByRole('button', { name: 'Estado anterior' }).click();
  await expect(page.locator('.timeline-value')).toContainText('220 m');
  await page.getByRole('button', { name: 'Ensuciamiento' }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar PNG' }).click();
  expect((await download).suggestedFilename()).toMatch(/^aparejo-warp_length_m-.*\.png$/);
});
