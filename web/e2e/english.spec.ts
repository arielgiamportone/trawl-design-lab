import { expect, test, type Page } from '@playwright/test';

/** Palabras de la interfaz en español que no deben aparecer con la app en inglés. */
const SPANISH =
  /\b(Resumen|Siguiente|Velocidad|Resistencia|Profundidad|Buque|Portón|Descargas|Corregir|Ejercicios)\b/;

async function start(page: Page, prefs: Record<string, string>) {
  await page.addInitScript((p) => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      for (const [k, v] of Object.entries(p)) localStorage.setItem(k, JSON.stringify(v));
      sessionStorage.setItem('e2e-init', '1');
    }
  }, prefs);
  await page.goto('/');
}

test('modo guiado en inglés e imperial: la profundidad en pies llega en metros', async ({
  page,
}) => {
  await start(page, {
    'trawl-design-lab:lang:v1': 'en',
    'trawl-design-lab:units:v1': 'imperial',
  });
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
  await expect(page.getByRole('heading', { name: /Step 1 of 4/ })).toBeVisible();
  await page.getByRole('radio', { name: /180 BHP/ }).check();
  await page.getByRole('button', { name: 'Next →' }).click();
  await page.getByRole('button', { name: 'Next →' }).click();
  const sent: { params?: Record<string, unknown> }[] = [];
  page.on('request', (r) => {
    const u = new URL(r.url());
    if (u.pathname.endsWith('/design') && r.method() === 'POST') {
      expect(u.searchParams.get('lang')).toBe('en');
      sent.push(r.postDataJSON() as { params?: Record<string, unknown> });
    }
  });
  await page.getByRole('textbox', { name: /Working depth/ }).fill('200');
  await page.getByRole('button', { name: 'See result →' }).click();
  await expect.poll(() => Number(sent.at(-1)?.params?.depth_m)).toBeCloseTo(60.96, 2);
  await expect(page.locator('[data-check="pull"]')).toHaveClass(/ok|warn|crit/);
  await expect(page.getByRole('main')).not.toContainText(SPANISH);

  await page.getByRole('button', { name: 'See the technical detail (expert mode)' }).click();
  await expect(page.getByRole('tab', { name: 'Summary' })).toBeVisible();
  await expect(page.locator('tr[data-key="working_depth_m"]')).toContainText('200');
  await expect(page.locator('tr[data-key="working_depth_m"]')).toContainText('ft');
  await expect(page.locator('tr[data-key="headrope_m"]')).toContainText('ft');
});

test('el selector de idioma cambia la app y las respuestas del motor', async ({ page }) => {
  await start(page, { 'trawl-design-lab:mode': 'expert' });
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible();
  await page.getByRole('button', { name: 'EN', exact: true }).click();
  await expect(page.getByRole('tab', { name: 'Summary' })).toBeVisible();
  await expect(page.getByRole('tab', { name: 'Resumen' })).toHaveCount(0);
  await page.getByRole('tab', { name: 'Notes and errata' }).click();
  await expect(page.getByRole('main')).not.toContainText(SPANISH);
  await page.getByRole('button', { name: 'ES', exact: true }).click();
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible();
});

test('práctica libre en inglés: enunciado y corrección del motor en inglés', async ({ page }) => {
  test.setTimeout(120_000);
  await start(page, { 'trawl-design-lab:lang:v1': 'en', 'trawl-design-lab:mode': 'aula' });
  await expect(page.getByTestId('practice')).toBeVisible({ timeout: 60_000 });
  await page.getByRole('button', { name: /Design drag \(Aberdeen demersal\)/ }).click();
  await page.getByRole('button', { name: 'Book data' }).click();
  const ex = page.getByTestId('exercise');
  await expect(ex).toContainText('38.75 m²');
  await ex.getByLabel(/Net drag/).fill('1592');
  await ex.getByRole('button', { name: 'Check' }).click();
  await expect(ex.getByTestId('grade')).toContainText('Score 100');
  await expect(ex).not.toContainText(SPANISH);
});
