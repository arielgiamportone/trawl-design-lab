import { expect, test, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { E2E_ADMIN } from '../playwright.config';

// Capturas de README y docs/web.md. Cada prueba deja un PNG en docs/screenshots/.
const OUT = 'docs/screenshots';
const API = `http://127.0.0.1:${process.env.E2E_API_PORT ?? 8000}/classroom`;

async function start(
  page: Page,
  opts: { mode: 'expert' | 'simple' | 'aula'; tab?: string; dark?: boolean },
) {
  await page.addInitScript((o) => {
    if (!sessionStorage.getItem('shot-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify(o.mode));
      if (o.tab) localStorage.setItem('trawl-design-lab:tab', JSON.stringify(o.tab));
      localStorage.setItem('trawl-design-lab:theme', JSON.stringify(o.dark ? 'dark' : 'light'));
      sessionStorage.setItem('shot-init', '1');
    }
  }, opts);
  await page.goto('/');
  await expect(page.getByRole('status').filter({ hasText: /conectada|teléfono/ })).toBeVisible({
    timeout: 60_000,
  });
}

// Sin `focus` la captura muestra el inicio de la página; con `focus`, ese elemento arriba.
async function shot(page: Page, name: string, focus?: Locator) {
  if (focus) await focus.evaluate((el) => el.scrollIntoView({ block: 'start' }));
  else await page.evaluate(() => window.scrollTo(0, 0));
  await page.waitForTimeout(600);
  await page.screenshot({ path: `${OUT}/${name}.png` });
}

test.describe('escritorio', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('modo guiado: diagnóstico', async ({ page }) => {
    await start(page, { mode: 'simple' });
    await page.getByRole('radio', { name: /180 BHP/ }).check();
    await page.getByRole('button', { name: 'Siguiente →' }).click();
    await page.getByRole('button', { name: 'Siguiente →' }).click();
    await page.getByRole('slider', { name: /Velocidad de arrastre/ }).fill('2');
    await page.getByRole('button', { name: 'Ver resultado →' }).click();
    await expect(page.locator('[data-check="pull"]')).toHaveClass(/ok|warn|crit/);
    await shot(page, 'guiado-diagnostico');
  });

  test('experto: resumen y KPI', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'resumen' });
    await expect(page.locator('tr[data-key="horizontal_opening_m"]')).toBeVisible();
    await shot(page, 'escritorio-claro-caso');
  });

  test('gráficos en tema oscuro', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'graficos', dark: true });
    await expect(page.locator('.recharts-surface').first()).toBeVisible({ timeout: 30_000 });
    await shot(page, 'escritorio-oscuro-graficos');
  });

  test('diseño interactivo', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'diseno' });
    await page.waitForTimeout(2500);
    await shot(page, 'escritorio-diseno-interactivo');
  });

  test('optimizar', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'optimizar' });
    await page.getByRole('button', { name: 'Optimizar', exact: true }).click();
    await expect(page.getByTestId('opt-best')).toBeVisible({ timeout: 60_000 });
    await expect(page.locator('[data-chart="opt-pareto"] svg.recharts-surface')).toBeVisible();
    await shot(page, 'escritorio-claro-optimizar', page.getByTestId('opt-best'));
  });

  test('simulación 3D', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'simulacion' });
    await page.getByRole('button', { name: 'Simular' }).click();
    await expect(page.getByTestId('net3d-canvas')).toBeVisible({ timeout: 90_000 });
    await page.waitForTimeout(2500);
    await shot(page, 'escritorio-simulacion-3d', page.locator('h3', { hasText: 'Vista 3D' }));
  });

  test('selectividad', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'simulacion' });
    await page.getByRole('button', { name: 'Mallas y selectividad' }).click();
    await page.getByRole('checkbox', { name: 'Bacalao' }).check();
    await page.getByRole('combobox', { name: 'Resolución' }).selectOption('2');
    await page.getByRole('button', { name: 'Calcular selectividad' }).click();
    await expect(page.getByTestId('selectivity-table')).toBeVisible({ timeout: 120_000 });
    await shot(page, 'escritorio-selectividad');
  });

  test('catálogo FAO', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'catalogo' });
    await page.locator('tr[data-net="fao_wb_bt2p_60hp"]').getByRole('button').click();
    await expect(page.getByTestId('provenance')).toBeVisible({ timeout: 30_000 });
    await shot(page, 'escritorio-catalogo-fao', page.locator('tr[data-net="bobp_wp20_ho"]'));
  });

  test('componentes: lista de materiales', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'componentes' });
    await page.getByRole('button', { name: 'Lista de materiales' }).click();
    await expect(page.getByTestId('bom').locator('tr[data-line="warps"]')).toBeVisible({
      timeout: 30_000,
    });
    await shot(page, 'escritorio-componentes');
  });

  test('construcción: armado paso a paso', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'construccion' });
    await expect(page.getByTestId('cut-sheet')).toBeVisible({ timeout: 30_000 });
    await page.getByLabel('Paño A cortado').check();
    await page.getByLabel('Paño B cortado').check();
    await page.getByRole('button', { name: 'Armado paso a paso' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await expect(page.getByTestId('join-map')).toBeVisible();
    await shot(page, 'escritorio-construccion', page.getByTestId('guide-summary'));
  });

  test('economía de la marea', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'economia' });
    const eco = page.getByTestId('economics');
    await expect(eco.getByTestId('eco-summary')).toBeVisible({ timeout: 30_000 });
    const fill: [string, string][] = [
      ['Captura por hora de arrastre', '150'],
      ['Precio en playa', '1000'],
      ['Precio del gasoil', '1200'],
      ['Precio del lubricante', '6000'],
      ['Parte de la tripulación', '40'],
      ['Hielo, víveres, carnada y puerto', '150000'],
      ['Permisos, seguro y fijos', '6000000'],
    ];
    await eco.getByLabel('Moneda', { exact: true }).fill('ARS');
    for (const [label, value] of fill) await eco.getByLabel(label).fill(value);
    await eco.getByLabel('Costo de la red y el aparejo', { exact: true }).fill('3000000');
    await expect(eco.getByTestId('eco-summary')).not.toContainText('Faltan datos');
    await eco.locator('details.accordion summary').first().click();
    await page.waitForTimeout(800);
    await shot(page, 'escritorio-economia', eco.getByTestId('eco-summary'));
  });

  test('lotes y flota', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'lotes' });
    const fleet =
      'nombre;potencia [hp];eslora [m];profundidad [m]\n' +
      'Don Pedro;45;10;25\nCostero;60;11;30\nLa Gaviota;110;14;50\n' +
      'Bolichero;150;17;60\nAltura;250;22;90\n';
    await page.getByLabel('Planilla del lote').setInputFiles({
      name: 'flota.csv',
      mimeType: 'text/csv',
      buffer: Buffer.from(fleet, 'utf-8'),
    });
    await page.getByLabel('Red a proyectar').selectOption('fao_wb_bt2p_60hp');
    await page.getByRole('button', { name: 'Calcular el lote' }).click();
    await expect(page.getByTestId('batch-results').locator('tbody tr')).toHaveCount(5, {
      timeout: 180_000,
    });
    await shot(page, 'escritorio-lotes', page.getByLabel('Red a proyectar'));
  });
});

/** Curso de muestra para la captura del docente: una tarea y tres alumnos con entregas. */
async function sampleCourse(request: APIRequestContext): Promise<string> {
  const post = async (path: string, data: unknown, token?: string) => {
    const r = await request.post(`${API}${path}`, {
      data,
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    expect(r.ok(), await r.text()).toBe(true);
    return (await r.json()) as Record<string, unknown>;
  };
  const admin = (await post('/auth/login', E2E_ADMIN)).token as string;
  const course = await post(
    '/courses',
    { name: 'Tecnología de Artes de Pesca', term: '2026-2C' },
    admin,
  );
  const a = await post(
    `/courses/${String(course.id)}/assignments`,
    {
      title: 'TP 1: potencia y resistencia',
      // Datos del libro para todos: así la captura muestra notas variadas y legibles.
      per_student_data: false,
      items: [
        { kind: 'exercise', ref: 'potencia.fridman_tiro' },
        { kind: 'exercise', ref: 'resistencia.aberdeen' },
        { kind: 'lab', ref: 'lab.buque_y_velocidad', points: 2 },
      ],
    },
    admin,
  );
  const students = [
    ['Legajo 31.204', ['1185', '1592']],
    ['Legajo 31.377', ['1185', '900']],
    ['Legajo 31.512', ['1000', '']],
  ] as const;
  for (const [i, [name, answers]] of students.entries()) {
    const s = await post('/auth/register', {
      username: `alumno-captura-${Date.now()}-${i}`,
      password: 'alumno-123',
      display_name: name,
      course_code: course.code,
    });
    const tok = s.token as string;
    await post(
      `/assignments/${String(a.id)}/items/0/submit`,
      { answers: { ft_kgf: answers[0] } },
      tok,
    );
    if (answers[1])
      await post(
        `/assignments/${String(a.id)}/items/1/submit`,
        { answers: { rn_kgf: answers[1] } },
        tok,
      );
  }
  return admin;
}

test.describe('aula', () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test('aula: planilla del docente', async ({ page, request }) => {
    await sampleCourse(request);
    await start(page, { mode: 'aula' });
    await page.getByRole('button', { name: /Cursos \(ingresar\)/ }).click();
    await page.getByLabel('Usuario').fill(E2E_ADMIN.username);
    await page.getByLabel('Contraseña').fill(E2E_ADMIN.password);
    await page.getByRole('button', { name: 'Ingresar', exact: true }).last().click();
    await page
      .getByRole('button', { name: /Tecnología de Artes de Pesca/ })
      .last()
      .click();
    await page
      .getByRole('button', { name: /TP 1: potencia/ })
      .last()
      .click();
    await expect(page.getByTestId('grades').getByRole('row')).toHaveCount(4);
    await shot(page, 'escritorio-aula-docente');
  });

  test('aula: laboratorio sobre la app', async ({ page }) => {
    await start(page, { mode: 'aula' });
    await page
      .locator('.aula-lab')
      .filter({ hasText: 'El paño y la resistencia' })
      .getByRole('button', { name: 'Empezar' })
      .click();
    const panel = page.getByTestId('lab-panel');
    await expect(panel).toContainText('Paso 1 de 3');
    await expect(page.getByText('2,27').first()).toBeVisible({ timeout: 60_000 });
    await panel.getByLabel(/Superficie sólida/).fill('38,75');
    await panel.getByLabel(/Resistencia de la red a 3 kn/).fill('1592');
    await panel.getByRole('button', { name: 'Comprobar con mi caso' }).click();
    await expect(panel).toContainText('Paso cumplido.', { timeout: 30_000 });
    await shot(page, 'escritorio-aula-laboratorio');
  });
});

test.describe('teléfono', () => {
  test.use({ viewport: { width: 390, height: 844 }, deviceScaleFactor: 2, isMobile: true });

  test('plano en el teléfono', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'plano' });
    await expect(page.getByTestId('plan-image')).toBeVisible();
    await page.waitForTimeout(2000);
    await shot(page, 'movil-plano', page.getByRole('tablist').first());
  });

  test('guía para el taller en el teléfono', async ({ page }) => {
    await start(page, { mode: 'expert', tab: 'construccion' });
    await expect(page.getByTestId('cut-sheet')).toBeVisible({ timeout: 30_000 });
    await page.getByRole('button', { name: 'Armado paso a paso' }).click();
    await page.getByRole('button', { name: 'Hecho, siguiente →' }).click();
    await expect(page.getByTestId('join-map')).toBeVisible();
    await shot(page, 'movil-guia-taller', page.getByTestId('assembly'));
  });

  test('ejercicio del aula en el teléfono', async ({ page }) => {
    await start(page, { mode: 'aula' });
    await page.getByRole('button', { name: /Tiro disponible de Fridman/ }).click();
    await page.getByRole('button', { name: 'Datos del libro' }).click();
    const ex = page.getByTestId('exercise');
    await ex.getByLabel(/Tiro disponible/).fill('1185');
    await ex.getByRole('button', { name: 'Corregir' }).click();
    await expect(ex.getByTestId('grade')).toContainText('100 %');
    await shot(page, 'movil-aula-ejercicio', ex);
  });

  test('sin conexión: motor del teléfono', async ({ page, context }) => {
    await start(page, { mode: 'simple' });
    await page.evaluate(async () => {
      await navigator.serviceWorker.ready;
    });
    await page.reload();
    const panel = page.getByTestId('offline-panel');
    await panel.locator('summary').click();
    await panel.getByRole('button', { name: 'Preparar uso sin conexión' }).click();
    await expect(panel.getByText(/Motor guardado/)).toBeVisible({ timeout: 240_000 });
    await context.setOffline(true);
    await page.reload();
    await expect(page.getByRole('status').filter({ hasText: 'motor del teléfono' })).toBeVisible({
      timeout: 120_000,
    });
    await page.getByRole('radio', { name: /150 BHP/ }).check();
    await shot(page, 'movil-sin-conexion');
    await context.setOffline(false);
  });
});
