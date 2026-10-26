import AxeBuilder from '@axe-core/playwright';
import { expect, test, type Locator, type Page } from '@playwright/test';

// Accesibilidad (Fase 18.4): axe con WCAG 2.1 A/AA sobre cada modo y pestaña, en tema claro y
// oscuro, en español e inglés. Fallan las violaciones serias o críticas.
const TABS = [
  'resumen',
  'graficos',
  'diseno',
  'paneles',
  'plano',
  'comparar',
  'optimizar',
  'simulacion',
  'descargas',
  'catalogo',
  'componentes',
  'construccion',
  'economia',
  'lotes',
  'notas',
];

async function start(
  page: Page,
  o: { mode: string; tab?: string; theme?: string; lang?: string },
): Promise<void> {
  await page.addInitScript((opts) => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify(opts.mode));
      if (opts.tab) localStorage.setItem('trawl-design-lab:tab', JSON.stringify(opts.tab));
      localStorage.setItem('trawl-design-lab:theme', JSON.stringify(opts.theme ?? 'light'));
      localStorage.setItem('trawl-design-lab:lang:v1', JSON.stringify(opts.lang ?? 'es'));
      sessionStorage.setItem('e2e-init', '1');
    }
  }, o);
  await page.goto('/');
  await expect(page.locator('#resultados')).toBeVisible({ timeout: 60_000 });
  await page.waitForLoadState('networkidle');
}

async function expectAccessible(page: Page): Promise<void> {
  const r = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa'])
    .analyze();
  const bad = r.violations
    .filter((v) => v.impact === 'serious' || v.impact === 'critical')
    .map((v) => `${v.id} (${v.impact}): ${v.nodes.map((n) => n.target.join(' ')).join(', ')}`);
  expect(bad, bad.join('\n')).toEqual([]);
}

for (const lang of ['es', 'en'])
  for (const theme of ['light', 'dark']) {
    test.describe(`${lang} · ${theme}`, () => {
      test('modo guiado y aula', async ({ page }) => {
        await start(page, { mode: 'simple', theme, lang });
        await expectAccessible(page);
        await page.goto('/');
        await page.locator('.mode-switch button').nth(2).click();
        await expect(page.getByTestId('practice')).toBeVisible({ timeout: 60_000 });
        await expectAccessible(page);
      });

      test('modo experto: todas las pestañas', async ({ page }) => {
        test.setTimeout(180_000);
        await start(page, { mode: 'expert', tab: 'resumen', theme, lang });
        const tabs = page.getByRole('tab');
        await expect(tabs).toHaveCount(TABS.length);
        for (let i = 0; i < TABS.length; i++) {
          await tabs.nth(i).click();
          await page.waitForLoadState('networkidle');
          await expectAccessible(page);
        }
      });
    });
  }

test('resultados calculados: simulación, optimización y laboratorio', async ({ page }) => {
  test.setTimeout(240_000);
  await start(page, { mode: 'expert', tab: 'simulacion' });
  await page.getByRole('button', { name: 'Simular' }).click();
  await expect(page.getByTestId('net3d-canvas')).toBeVisible({ timeout: 90_000 });
  await expectAccessible(page);

  await page.getByRole('tab', { name: 'Optimizar' }).click();
  await page.getByRole('button', { name: 'Optimizar', exact: true }).click();
  await expect(page.getByTestId('opt-best')).toBeVisible({ timeout: 60_000 });
  await expectAccessible(page);

  await page.locator('.mode-switch button').nth(2).click();
  await expect(page.getByTestId('practice')).toBeVisible({ timeout: 60_000 });
  await page
    .locator('.aula-lab')
    .filter({ hasText: 'Más potencia' })
    .getByRole('button', { name: 'Empezar' })
    .click();
  await expect(page.getByTestId('lab-panel')).toBeVisible();
  await expectAccessible(page);
});

/** Tab hasta que ``target`` tenga el foco (sin mouse). */
async function tabTo(page: Page, target: Locator, max = 120): Promise<void> {
  for (let i = 0; i < max; i++) {
    if (await target.evaluate((el) => el === document.activeElement)) return;
    await page.keyboard.press('Tab');
  }
  throw new Error(`no se llegó con Tab a ${String(target)}`);
}

test('teclado: el modo guiado completo sin mouse', async ({ page }) => {
  await start(page, { mode: 'simple' });
  await tabTo(page, page.getByRole('radio', { name: /150 BHP/ }));
  await page.keyboard.press('ArrowDown');
  await expect(page.getByRole('radio', { name: /180 BHP/ })).toBeChecked();
  await tabTo(page, page.getByRole('button', { name: 'Siguiente →' }));
  await page.keyboard.press('Enter');
  await tabTo(page, page.getByRole('button', { name: 'Siguiente →' }));
  await page.keyboard.press('Enter');
  const depth = page.getByRole('textbox', { name: /Profundidad de trabajo/ });
  await tabTo(page, depth);
  await page.keyboard.type('60');
  await tabTo(page, page.getByRole('button', { name: 'Ver resultado →' }));
  await page.keyboard.press('Enter');
  const why = page.locator('[data-check="pull"]').getByText('¿Por qué?');
  await tabTo(page, why);
  await page.keyboard.press('Enter');
  await expect(page.locator('[data-check="pull"]')).toContainText(/el buque puede tirar/);
  await tabTo(page, page.getByRole('button', { name: 'Ver el detalle técnico (modo experto)' }));
  await page.keyboard.press('Enter');
  await expect(page.getByRole('tab', { name: 'Resumen' })).toBeVisible();
  // Las pestañas se recorren con las flechas.
  await tabTo(page, page.getByRole('tab', { selected: true }));
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: 'Gráficos' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
});

test('teclado: resolver y corregir un ejercicio sin mouse', async ({ page }) => {
  await start(page, { mode: 'aula' });
  await expect(page.getByTestId('practice')).toBeVisible({ timeout: 60_000 });
  await tabTo(page, page.getByRole('button', { name: /Resistencia de diseño/ }));
  await page.keyboard.press('Enter');
  await tabTo(page, page.getByRole('button', { name: 'Datos del libro' }));
  await page.keyboard.press('Enter');
  const ex = page.getByTestId('exercise');
  await expect(ex).toContainText('38,75 m²');
  await tabTo(page, ex.getByLabel(/Resistencia de la red/));
  await page.keyboard.type('1592');
  await page.keyboard.press('Enter');
  await expect(ex.getByTestId('grade')).toContainText('Puntaje 100 %');
});
