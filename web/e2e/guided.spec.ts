import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      sessionStorage.setItem('e2e-init', '1');
    }
  });
});

test('flujo guiado completo contra la API real', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Paso 1 de 4: Buque' })).toBeVisible();
  await page.getByRole('radio', { name: /180 BHP/ }).check();
  await page.getByRole('button', { name: 'Siguiente →' }).click();
  await expect(page.getByRole('radio', { name: /estándar, bolsa 40 mm/ })).toBeChecked();
  await page.getByRole('button', { name: 'Siguiente →' }).click();
  await page.getByRole('slider', { name: /Velocidad de arrastre/ }).fill('1.8');
  await page.getByRole('textbox', { name: /Profundidad de trabajo/ }).fill('60');
  await page.getByRole('button', { name: 'Ver resultado →' }).click();

  const pull = page.locator('[data-check="pull"]');
  await expect(pull).toHaveClass(/ok|warn/);
  await expect(page.locator('[data-check="max_speed"] .check-value')).toContainText('kn');
  await expect(page.locator('[data-check="swept"] .check-value')).toContainText('mil m²/h');
  await pull.getByText('¿Por qué?').click();
  await expect(pull.getByText(/A 1,8 kn el buque puede tirar/)).toBeVisible();

  // El mismo caso sigue en el modo experto.
  await page.getByRole('button', { name: 'Ver el detalle técnico (modo experto)' }).click();
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible();
  await expect(page.getByLabel('Buque', { exact: true })).toHaveValue('fao_a3_180hp');
  await expect(page.locator('tr[data-key="working_depth_m"] td.num')).toHaveText('60');
});

test('cambio de modo, deshacer y proyecto exportado', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('radio', { name: /180 BHP/ }).check();
  await page.getByRole('button', { name: /Deshacer/ }).click();
  await expect(page.getByRole('radio', { name: /150 BHP/ })).toBeChecked();
  await page.getByRole('button', { name: /Rehacer/ }).click();
  await expect(page.getByRole('radio', { name: /180 BHP/ })).toBeChecked();

  await page.locator('.project-menu > summary').click();
  await page.getByLabel('Nombre del proyecto').fill('Beagle 180');
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Exportar archivo' }).click();
  const file = await download;
  expect(file.suggestedFilename()).toBe('beagle-180.trawl.json');
  const saved = JSON.parse(readFileSync((await file.path()) as string, 'utf8'));
  expect(saved).toMatchObject({
    format: 'trawl-design-lab/project',
    case: { vessel: 'fao_a3_180hp' },
  });

  await page.getByRole('button', { name: 'Experto' }).click();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Experto' })).toHaveAttribute(
    'aria-pressed',
    'true',
  );
  await expect(page.getByLabel('Buque', { exact: true })).toHaveValue('fao_a3_180hp');
});
