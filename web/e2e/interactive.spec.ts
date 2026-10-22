import { expect, test } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('expert'));
      localStorage.setItem('trawl-design-lab:tab', JSON.stringify('diseno'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
});

test('arrastrar el alto de un panel recalcula y deshacer lo revierte', async ({ page }) => {
  await page.goto('/');
  const ss = page.locator('[data-kpi="solid_surface_m2"] .kpi-value');
  await expect(ss).toContainText('38,75');
  const panel = page.locator('polygon[data-panel="C"][data-side="right"]');
  await panel.click();
  const depth = page
    .getByTestId('panel-inspector')
    .getByLabel('Mallas de alto (N)', { exact: true });
  await expect(depth).toHaveValue('120');

  await page.setViewportSize({ width: 1280, height: 640 });
  const handle = page.locator('circle[data-panel="C"][data-side="right"][data-handle="depth"]');
  // el plano puede quedar bajo el pliegue: el mouse sólo llega a lo visible
  await handle.scrollIntoViewIfNeeded();
  const box = (await handle.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2, box.y + 50, { steps: 5 });
  await expect(page.getByRole('status').filter({ hasText: 'Esc cancela' })).toBeVisible();
  await page.mouse.up();

  await expect(depth).not.toHaveValue('120');
  expect(Number(await depth.inputValue())).toBeGreaterThan(120);
  await expect(ss).not.toContainText('38,75');
  await expect(page.locator('[data-impact="ss"] .impact-delta')).toContainText('+');
  await expect(page.locator('polygon.nc-base').first()).toBeAttached();

  await page.getByRole('button', { name: /Deshacer/ }).click();
  await expect(depth).toHaveValue('120');
  await expect(ss).toContainText('38,75');
});

test('ajuste por teclado sobre el plano', async ({ page }) => {
  await page.goto('/');
  const panel = page.locator('polygon[data-panel="G"]').first();
  await panel.focus();
  await page.keyboard.press('Enter');
  const bottom = page
    .getByTestId('panel-inspector')
    .getByLabel('Mallas del borde hacia la bolsa', { exact: true });
  await expect(bottom).toHaveValue('162');
  await page.keyboard.press('ArrowRight');
  await expect(bottom).toHaveValue('164');
  await page.keyboard.press('Shift+ArrowRight');
  await expect(bottom).toHaveValue('184');
});

test('vista 3D de la forma simulada', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('tab', { name: 'Simulación' }).click();
  await expect(page.getByRole('checkbox', { name: 'Vista 3D' })).toBeChecked();
  await page.getByRole('button', { name: 'Simular' }).click();
  const canvas = page.getByTestId('net3d-canvas');
  await expect(canvas).toBeVisible({ timeout: 60_000 });
  await expect(canvas).toHaveAttribute('aria-label', /Forma 3D de la red a 3 kn/);
  await page.getByRole('button', { name: 'Planta' }).click();
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar PNG' }).click();
  expect((await download).suggestedFilename()).toMatch(/^red-3d-3kn\.png$/);
});
