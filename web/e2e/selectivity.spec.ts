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

test('selectividad rombo vs T90 y zoom por malla contra la API real', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Mallas y selectividad' }).click();
  await page.getByRole('checkbox', { name: 'Bacalao' }).check();
  await page.getByRole('spinbutton', { name: /Mallero del copo/ }).fill('120');
  await page.getByRole('combobox', { name: 'Resolución' }).selectOption('2');
  await page.getByRole('button', { name: 'Calcular selectividad' }).click();

  const table = page.getByTestId('selectivity-table');
  await expect(table).toBeVisible({ timeout: 90_000 });
  await expect(table).toContainText('Rombo 120 mm');
  await expect(table).toContainText('T90 120 mm');
  await expect(table.locator('td[data-species="cod"]').first()).toContainText(/\d+,\d cm/);
  await expect(page.locator('[data-chart="retention"]')).toBeVisible();
  await expect(page.getByTestId('netanim-canvas')).toBeVisible({ timeout: 30_000 });

  // El zoom se abre en la malla más abierta del copo; una talla grande queda retenida.
  const zoom = page.getByTestId('mesh-zoom');
  await expect(zoom).toBeVisible();
  await expect(zoom).toContainText('Ángulo entre hilos');
  const slider = zoom.getByRole('slider');
  await slider.fill(await slider.getAttribute('max').then((v) => v ?? '100'));
  await expect(zoom.getByRole('status')).toContainText('Queda retenido');
  await page.getByRole('button', { name: 'T90 120 mm' }).click();
  await page.getByRole('button', { name: 'Talla que pasa' }).click();
  await expect(page.locator('.net3d-legend')).toContainText('Talla máxima que pasa');
});
