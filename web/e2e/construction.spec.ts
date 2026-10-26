import { expect, test } from '@playwright/test';

test('guía de construcción: hoja de corte, armado paso a paso y descargas', async ({ page }) => {
  test.setTimeout(120_000);
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('construccion'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
  await page.goto('/');
  const guide = page.getByTestId('construction');
  const sheet = guide.getByTestId('cut-sheet');
  await expect(sheet.locator('li[data-piece="A"]')).toContainText('1N2B', { timeout: 60_000 });
  await sheet.getByLabel('Paño A cortado').check();

  await guide.getByRole('button', { name: 'Armado paso a paso' }).click();
  const asm = guide.getByTestId('assembly');
  await expect(asm).toContainText('Paso 1 de 11');
  await expect(asm.getByTestId('join-map').locator('[data-panel="E"][data-on="true"]')).toHaveCount(
    1,
  );
  await asm.getByRole('button', { name: 'Hecho, siguiente →' }).click();
  await expect(asm).toContainText('Paso 2 de 11');

  // Lo tildado sobrevive a la recarga.
  await page.reload();
  await expect(page.getByTestId('guide-summary')).toContainText('10 %', { timeout: 60_000 });

  await page.getByRole('button', { name: 'Montaje en relingas' }).click();
  await expect(page.getByTestId('float-line').locator('circle')).toHaveCount(12);

  const pdf = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Guía en PDF (A4)' }).click();
  expect((await pdf).suggestedFilename()).toBe('guia-fao_a3_standard.pdf');
  const xlsx = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Planilla XLSX' }).click();
  expect((await xlsx).suggestedFilename()).toBe('guia-fao_a3_standard.xlsx');
});

test('modo guiado: «¿Cómo la armo?» abre la guía para el taller', async ({ page }) => {
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
  await page.getByRole('button', { name: '¿Cómo la armo? Guía para el taller' }).click();
  await expect(page.getByTestId('cut-sheet')).toBeVisible({ timeout: 60_000 });
});
