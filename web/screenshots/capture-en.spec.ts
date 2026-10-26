import { expect, test, type Page } from '@playwright/test';

// Capturas en inglés (README.en.md): la app con lang=en; el resumen y la economía en imperial.
const OUT = 'docs/screenshots';

async function start(
  page: Page,
  opts: { mode: 'expert' | 'simple' | 'aula'; tab?: string; imperial?: boolean },
) {
  await page.addInitScript((o) => {
    if (!sessionStorage.getItem('shot-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:lang:v1', JSON.stringify('en'));
      localStorage.setItem(
        'trawl-design-lab:units:v1',
        JSON.stringify(o.imperial ? 'imperial' : 'metric'),
      );
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify(o.mode));
      if (o.tab) localStorage.setItem('trawl-design-lab:tab', JSON.stringify(o.tab));
      localStorage.setItem('trawl-design-lab:theme', JSON.stringify('light'));
      sessionStorage.setItem('shot-init', '1');
    }
  }, opts);
  await page.goto('/');
  await expect(page.getByRole('status').filter({ hasText: /connected|device/ })).toBeVisible({
    timeout: 60_000,
  });
}

async function shot(page: Page, name: string) {
  await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}.png` });
}

test.describe('desktop in English', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('guided mode: diagnosis', async ({ page }) => {
    await start(page, { mode: 'simple' });
    await page.getByRole('radio', { name: /180 BHP/ }).check();
    await page.getByRole('button', { name: 'Next →' }).click();
    await page.getByRole('button', { name: 'Next →' }).click();
    await page.getByRole('slider', { name: /Towing speed/ }).fill('2');
    await page.getByRole('button', { name: 'See result →' }).click();
    await expect(page.locator('[data-check="pull"]')).toHaveClass(/ok|warn|crit/);
    await shot(page, 'en-guided-diagnosis');
  });

  test('expert mode: summary in imperial units', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'resumen', imperial: true });
    await expect(page.locator('tr[data-key="headrope_m"]')).toContainText('ft');
    await shot(page, 'en-expert-summary-imperial');
  });

  test('economics in imperial units', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'economia', imperial: true });
    await expect(page.locator('.recharts-surface').first()).toBeVisible({ timeout: 30_000 });
    await shot(page, 'en-economics-imperial');
  });

  test('UTN classroom: free practice', async ({ page }) => {
    await start(page, { mode: 'aula' });
    await page.getByRole('button', { name: /Design drag \(Aberdeen demersal\)/ }).click();
    await page.getByRole('button', { name: 'Book data' }).click();
    await expect(page.getByTestId('exercise')).toContainText('38.75');
    await shot(page, 'en-classroom-practice');
  });
});
