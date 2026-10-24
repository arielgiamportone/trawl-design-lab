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

test('bandas de incertidumbre contra la API real', async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto('/');
  await page.getByRole('button', { name: 'Incertidumbre y calibración' }).click();
  await page.getByRole('combobox', { name: 'Muestras' }).selectOption('6');
  await page.getByRole('button', { name: 'Calcular bandas' }).click();
  const table = page.getByTestId('uncertainty-table');
  await expect(table).toBeVisible({ timeout: 150_000 });
  await expect(table.locator('[data-output="door_spread_m"] td').nth(1)).toContainText(/\d+,\d/);
  await expect(page.getByTestId('tornado')).toBeVisible();
});

test('calibración con el registro de ejemplo contra la API real', async ({ page }) => {
  test.setTimeout(240_000);
  await page.goto('/');
  await page.getByRole('button', { name: 'Incertidumbre y calibración' }).click();
  await page.getByRole('button', { name: 'Calibración con mediciones' }).click();
  await page.getByRole('button', { name: 'Usar el registro de ejemplo' }).click();
  await expect(page.getByTestId('sensor-summary')).toContainText('360 filas', { timeout: 30_000 });
  await page.getByRole('combobox', { name: 'Evaluaciones máximas' }).selectOption('6');
  await page.getByRole('button', { name: 'Calibrar' }).click();
  const params = page.getByTestId('calibration-params');
  await expect(params).toBeVisible({ timeout: 200_000 });
  await expect(params).toContainText(/0,9\d/);
});
