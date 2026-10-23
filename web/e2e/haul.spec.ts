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

test('lance progresivo con captura y fondo contra la API real', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: 'Lance progresivo (captura y fondo)' }).click();
  const seabed = page.getByRole('combobox', { name: /Fondo/ });
  await expect(seabed.locator('option')).toHaveCount(5);
  await seabed.selectOption('rock');
  await expect(page.getByText(/μ tren 0,8 · μ portón 0,7/)).toBeVisible();
  await page.getByRole('spinbutton', { name: /Captura final/ }).fill('900');
  await page.getByText('Rápida (3)').click();
  await page.getByRole('button', { name: 'Simular lance' }).click();

  const summary = page.getByTestId('haul-summary');
  await expect(summary).toBeVisible({ timeout: 90_000 });
  await expect(summary).toContainText('la separación de portones baja');
  await expect(summary).toContainText('el tiro en el buque sube');
  await expect(page.locator('[data-chart="haul-dp"] .recharts-line')).toHaveCount(1);
  await page.getByText('Ver tabla del lance').click();
  await expect(page.getByRole('row')).toHaveCount(5); // encabezado + 4 pasos
  const canvas = page.getByTestId('net3d-canvas');
  await expect(canvas).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: 'Contacto con el fondo' }).click();
  await expect(page.getByText('Paño apoyado en el fondo')).toBeVisible();
});

test('modo guiado: tipo de fondo suma el roce a la demanda', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('trawl-design-lab:mode', '"simple"'));
  await page.goto('/');
  await page.getByRole('button', { name: 'Siguiente →' }).click();
  await page.getByRole('button', { name: 'Siguiente →' }).click();
  await page.getByRole('combobox', { name: /Tipo de fondo/ }).selectOption('gravel');
  await page.getByRole('spinbutton', { name: /Captura esperada/ }).fill('800');
  await page.getByRole('button', { name: 'Ver resultado →' }).click();
  const pull = page.locator('[data-check="pull"]');
  await pull.getByText('¿Por qué?').click();
  await expect(pull).toContainText('de roce con el fondo');
});
