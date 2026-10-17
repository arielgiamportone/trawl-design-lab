import { expect, test } from '@playwright/test';
import { readFileSync } from 'node:fs';

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    // cada prueba arranca del caso por defecto
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      sessionStorage.setItem('e2e-init', '1');
    }
  });
});

async function waitForResults(page: import('@playwright/test').Page) {
  await expect(page.locator('[data-kpi="max_speed_kn"] .kpi-value')).not.toHaveText('—');
  await expect(page.locator('.kpis.stale')).toHaveCount(0);
}

test('calcula el caso por defecto y muestra los KPI', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveTitle(/trawl-design-lab/);
  await waitForResults(page);
  await expect(page.locator('[data-kpi="vertical_opening_m"] .kpi-value')).toContainText('1,98');
  await expect(page.locator('[data-kpi="max_speed_kn"] .kpi-value')).toContainText('2,27');
  await expect(page.locator('[data-kpi="warp_selected"]')).toContainText('Cumple la rotura');
  await expect(page.getByRole('row', { name: /Lima 28,698 m/ })).toBeVisible();
  await expect(page.getByText('API conectada')).toBeVisible();
});

test('gráficos y plano SVG', async ({ page }) => {
  await page.goto('/');
  await waitForResults(page);
  await page.getByRole('tab', { name: 'Gráficos' }).click();
  await expect(page.locator('[data-chart="tiro"] svg.recharts-surface')).toBeVisible();
  await expect(page.locator('[data-chart="rn"] .recharts-line')).toHaveCount(13);
  await page.getByRole('tab', { name: 'Plano' }).click();
  const img = page.getByTestId('plan-image');
  await expect(img).toBeVisible();
  await expect(img).toHaveAttribute('src', /^data:image\/svg\+xml/);
  const ok = await img.evaluate((el: HTMLImageElement) =>
    el.decode().then(() => el.naturalWidth > 0),
  );
  expect(ok).toBe(true);
  await page.getByRole('button', { name: 'Escala real' }).click();
  await expect(img).toHaveAttribute('alt', /escala real/);
  const download = page.waitForEvent('download');
  await page.getByRole('button', { name: 'Descargar SVG' }).click();
  expect((await download).suggestedFilename()).toMatch(/\.svg$/);
});

test('editar una malla de panel cambia el resumen', async ({ page }) => {
  await page.goto('/');
  await waitForResults(page);
  const lima = page.locator('tr[data-key="headrope_m"] td.num');
  await expect(lima).toHaveText('28,698');
  await page.getByRole('tab', { name: 'Editor de paneles' }).click();
  const cell = page.getByLabel('Mallas de alto (N) del panel C');
  await cell.fill('140');
  await expect(cell.locator('xpath=..')).toHaveClass(/edited/);
  await expect(page.locator('[data-kpi="solid_surface_m2"] .kpi-value')).not.toContainText('38,75');
  await page.getByRole('tab', { name: 'Resumen' }).click();
  await expect(lima).not.toHaveText('28,698');
  // persistencia
  await page.reload();
  await waitForResults(page);
  await expect(page.locator('tr[data-key="headrope_m"] td.num')).not.toHaveText('28,698');
  await expect(page.getByText(/1 celda editada/)).toBeVisible();
  // restablecer
  await page.getByRole('tab', { name: 'Editor de paneles' }).click();
  await page.getByRole('button', { name: 'Restablecer red' }).click();
  await page.getByRole('tab', { name: 'Resumen' }).click();
  await expect(page.locator('tr[data-key="headrope_m"] td.num')).toHaveText('28,698');
});

test('comparar A fijado con B en vivo', async ({ page }) => {
  await page.goto('/');
  await waitForResults(page);
  await page.getByRole('tab', { name: 'Comparar' }).click();
  await page.getByRole('button', { name: /Fijar el resultado actual/ }).click();
  await page.getByText('Reproducir Excel', { exact: true }).click();
  await expect(page.locator('[data-kpi="warp_selected"]')).toContainText('No cumple la rotura');
  const table = page.getByTestId('compare-table');
  await expect(table.locator('tr[data-key="compat"]')).toBeVisible();
  await expect(table.locator('tr.diff-sig').first()).toBeVisible();
});

test('descarga el informe XLSX', async ({ page }) => {
  await page.goto('/');
  await waitForResults(page);
  await page.getByRole('tab', { name: 'Descargas' }).click();
  const download = page.waitForEvent('download');
  await page.locator('[data-download="xlsx"]').click();
  const d = await download;
  expect(d.suggestedFilename()).toMatch(/\.xlsx$/);
  const path = await d.path();
  const bytes = readFileSync(path);
  expect(bytes.subarray(0, 2).toString()).toBe('PK'); // zip (OOXML)
  expect(bytes.length).toBeGreaterThan(5000);
});

test('parámetro inválido muestra error y bloquea Calcular', async ({ page }) => {
  await page.goto('/');
  await waitForResults(page);
  await page.getByText('Parámetros avanzados').click();
  const input = page.getByLabel('Patentes [m]', { exact: true });
  await input.fill('abc');
  await expect(page.getByText('Ingrese un número')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Calcular' })).toBeDisabled();
  await input.fill('30');
  await expect(page.locator('tr[data-key="sweeps_m"] td.num')).toHaveText('30');
});

test('optimizar el caso por defecto da un mejor diseño factible y se puede aplicar', async ({
  page,
}) => {
  await page.goto('/');
  await waitForResults(page);
  await page.getByRole('tab', { name: 'Optimizar' }).click();
  await page.getByRole('button', { name: 'Optimizar', exact: true }).click();
  const best = page.getByTestId('opt-best');
  await expect(best).toBeVisible({ timeout: 60_000 });
  await expect(best.getByText('Factible', { exact: true })).toBeVisible();
  await expect(page.getByTestId('opt-constraints').getByText('OK')).toHaveCount(5);
  await expect(
    page.locator('[data-testid="opt-heatmap"] rect[data-feasible="true"]').first(),
  ).toBeVisible();
  await expect(page.locator('[data-chart="opt-pareto"] svg.recharts-surface')).toBeVisible();
  await best.getByRole('button', { name: 'Usar este diseño' }).click();
  await expect(page.getByTestId('scaled-net')).toContainText('Red escalada s =');
  await expect(page.getByRole('tab', { name: 'Resumen' })).toHaveAttribute('aria-selected', 'true');
  await waitForResults(page);
  await expect(page.locator('tr[data-key="headrope_m"] td.num')).not.toHaveText('28,698');
  await page.getByRole('button', { name: 'Volver a la red del catálogo' }).click();
  await expect(page.locator('tr[data-key="headrope_m"] td.num')).toHaveText('28,698');
});

test('simular 3 kn en resolución rápida muestra tres proyecciones', async ({ page }) => {
  await page.goto('/');
  await waitForResults(page);
  await page.getByRole('tab', { name: 'Simulación' }).click();
  await expect(page.getByRole('button', { name: '3,0' })).toHaveAttribute('aria-pressed', 'true');
  await page.getByText('Rápida (3)').click();
  await page.getByRole('button', { name: 'Simular' }).click();
  const svgs = page.getByTestId('sim-svg');
  await expect(svgs).toHaveCount(3, { timeout: 60_000 });
  for (const img of await svgs.all()) {
    await expect(img).toHaveAttribute('src', /^data:image\/svg\+xml/);
    expect(
      await img.evaluate((el: HTMLImageElement) => el.decode().then(() => el.naturalWidth > 0)),
    ).toBe(true);
  }
  const table = page.getByTestId('sim-table');
  await expect(table.locator('tr[data-row="3-drag_kgf"]')).toContainText('1.331,3');
  await expect(page.getByText(/Sobre la resistencia/)).toBeVisible();
});
