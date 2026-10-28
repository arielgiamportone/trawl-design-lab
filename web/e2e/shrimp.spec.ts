import { expect, test, type Page } from '@playwright/test';

/** Palabras de la interfaz en español que no deben aparecer con la app en inglés. */
const SPANISH =
  /\b(Resumen|Siguiente|Velocidad|Resistencia|Profundidad|Buque|Portón|Descargas|Tangones|tijera|Camaronero|camaronero)\b/;

async function start(page: Page, prefs: Record<string, string> = {}) {
  await page.addInitScript((p) => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      for (const [k, v] of Object.entries(p)) localStorage.setItem(k, JSON.stringify(v));
      sessionStorage.setItem('e2e-init', '1');
    }
  }, prefs);
  await page.goto('/');
}

/**
 * Pasos 1 a 3 del modo guiado con el tangonero argentino (``ar_tangonero_1998``) y la tangonera
 * del INIDEP (``inidep_ito043_tangonera_inidep``; el nombre del plano no se traduce).
 */
async function guidedShrimp(page: Page, next: RegExp, result: RegExp) {
  await page
    .getByRole('radio', { name: /Tangonero típico \(langostino|Typical outrigger shrimp trawler/ })
    .check();
  await page.getByRole('button', { name: next }).click();
  await page
    .getByRole('radio', { name: /Red tangonera de langostino propuesta por el INIDEP/ })
    .check();
  await page.getByRole('button', { name: next }).click();
  await page.getByRole('button', { name: result }).click();
}

// Fase 19.8d: la tangonera con el buque elegido usa el portón de su plano; el resultado muestra
// AH, AV y DP de cada red, el límite de AV de la Res. CFP 7/2018 y la nota del método camaronero.
test('modo guiado: tangonero con la tangonera del INIDEP (AH, AV y método camaronero)', async ({
  page,
}) => {
  await start(page);
  await guidedShrimp(page, /Siguiente →/, /Ver resultado →/);

  const opening = page.locator('[data-check="opening"]');
  await expect(opening).toContainText('Boca de cada red (2 redes)');
  await expect(opening.locator('.check-value')).toHaveText(/^AH \d+,\d m × AV 1,42 m$/);
  // Con el portón del plano (2,86 × 1,43 m) la boca abre ≈ 14 m, no la mitad.
  const ah = Number(
    ((await opening.locator('.check-value').textContent()) ?? '')
      .match(/AH ([\d,]+)/)?.[1]
      ?.replace(',', '.'),
  );
  expect(ah).toBeGreaterThan(12);
  await opening.getByText('¿Por qué?').click();
  await expect(opening).toContainText('Separación de portones de cada red (DP)');
  const cfp = page.locator('[data-check="cfp_av"]');
  await expect(cfp).toHaveClass(/ok/);
  await expect(cfp.locator('.check-value')).toHaveText('AV 1,42 m ≤ 1,5 m');

  await page.getByRole('button', { name: 'Ver el detalle técnico (modo experto)' }).click();
  await expect(page.locator('[data-kpi="vertical_opening_m"]')).toContainText('Límite CFP');
  await expect(page.locator('[data-kpi="horizontal_opening_m"]')).toContainText('DP');
  await expect(page.locator('tr[data-key="opening_method"] td.num')).toHaveText(
    'Camaronero: equilibrio portón–tijera–red',
  );
  await expect(page.locator('tr[data-key="rig"] td.num')).toHaveText('Tangones');
  await expect(page.locator('tr[data-key="door_spread_m"]')).toBeVisible();
  await page.getByRole('tab', { name: 'Notas y erratas' }).click();
  const notes = page.locator('ul.notes');
  await expect(notes).toContainText('shrimp_opening: método camaronero con tijera');
  await expect(notes).toContainText('catalog: portón del plano');
  // Cada nota una sola vez.
  const texts = await notes.locator('li').allInnerTexts();
  expect(new Set(texts).size).toBe(texts.length);
});

// Fase 19.9: con una langostinera de tangones, la comparación propone otra langostinera (no la A-3).
test('modo guiado: la comparación de una tangonera propone otra langostinera', async ({ page }) => {
  await start(page);
  await page.getByRole('radio', { name: /Tangonero típico \(langostino/ }).check();
  await page.getByRole('button', { name: /Siguiente →/ }).click();
  await page
    .getByRole('radio', { name: /Red tangonera de langostino propuesta por el INIDEP/ })
    .check();
  const compare = page.getByRole('checkbox', { name: /Comparar con otra red/ });
  const other = page.getByRole('combobox', { name: 'Red para comparar' });
  // La A-3 modificada que venía marcada se reemplaza por otra red de tangones al cambiar de red.
  if (await compare.isChecked()) {
    await expect(other).toHaveValue(/^inidep_/);
    await compare.uncheck();
  }
  await compare.check();
  await expect(other).toHaveValue(/^inidep_(?!ito043_tangonera_inidep$)/);
  // En el desplegable, primero las langostineras.
  const first = await other.locator('option').first().getAttribute('value');
  expect(first).toMatch(/^inidep_/);
  await page.getByRole('button', { name: /Siguiente →/ }).click();
  await page.getByRole('button', { name: /Ver resultado →/ }).click();
  await expect(page.locator('[data-check="opening"]')).toContainText('Boca de cada red');
});

test('guided mode in English and imperial: the shrimp result has no Spanish', async ({ page }) => {
  await start(page, {
    'trawl-design-lab:lang:v1': 'en',
    'trawl-design-lab:units:v1': 'imperial',
  });
  await guidedShrimp(page, /Next →/, /See result →/);
  const opening = page.locator('[data-check="opening"]');
  await expect(opening).toContainText('Mouth of each net (2 nets)');
  await expect(opening.locator('.check-value')).toHaveText(/^AH [\d.]+ ft × AV 4\.66 ft$/);
  await expect(page.locator('[data-check="cfp_av"] .check-value')).toContainText('≤');
  await expect(page.getByRole('main')).not.toContainText(SPANISH);

  await page.getByRole('button', { name: 'See the technical detail (expert mode)' }).click();
  await expect(page.locator('tr[data-key="opening_method"] td.num')).toHaveText(
    'Shrimp: door–bridle–net balance',
  );
  await expect(page.locator('tr[data-key="door_spread_m"]')).toContainText('ft');
  await expect(page.getByTestId('summary')).not.toContainText(SPANISH);
});
