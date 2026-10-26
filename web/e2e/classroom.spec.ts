import { expect, test, type Page } from '@playwright/test';
import { E2E_ADMIN } from '../playwright.config';

async function openAula(page: Page) {
  await page.addInitScript(() => {
    if (!sessionStorage.getItem('e2e-init')) {
      localStorage.clear();
      localStorage.setItem('trawl-design-lab:mode', JSON.stringify('aula'));
      sessionStorage.setItem('e2e-init', '1');
    }
  });
  await page.goto('/');
  await expect(page.getByTestId('practice')).toBeVisible({ timeout: 60_000 });
}

async function login(page: Page, username: string, password: string) {
  await page.getByLabel('Usuario').fill(username);
  await page.getByLabel('Contraseña').fill(password);
  await page.getByRole('button', { name: 'Ingresar', exact: true }).last().click();
}

test('práctica libre: ejercicio con los datos del libro y laboratorio sobre la app', async ({
  page,
}) => {
  test.setTimeout(120_000);
  await openAula(page);
  await page.getByRole('button', { name: /Resistencia de diseño/ }).click();
  await page.getByRole('button', { name: 'Datos del libro' }).click();
  const ex = page.getByTestId('exercise');
  await expect(ex).toContainText('38,75 m²');
  await ex.getByLabel(/Resistencia de la red/).fill('1592');
  await ex.getByRole('button', { name: 'Corregir' }).click();
  await expect(ex.getByTestId('grade')).toContainText('Puntaje 100 %');

  await page.getByRole('button', { name: '← Todos los ejercicios' }).click();
  await page
    .locator('.aula-lab')
    .filter({ hasText: 'Más potencia' })
    .getByRole('button', { name: 'Empezar' })
    .click();
  const panel = page.getByTestId('lab-panel');
  await expect(panel).toContainText('Paso 1 de 2');
  await expect(page.getByRole('tab', { name: 'Gráficos' })).toHaveAttribute(
    'aria-selected',
    'true',
  );
  await panel.getByLabel(/Velocidad máxima/).fill('2,27');
  await panel.getByRole('button', { name: 'Comprobar con mi caso' }).click();
  await expect(panel).toContainText('Paso cumplido.', { timeout: 30_000 });

  // Paso 2: cambiar al buque de 180 HP en el panel del caso y comprobar.
  await panel.getByRole('button', { name: 'Siguiente →' }).click();
  await page.getByLabel('Buque', { exact: true }).selectOption('fao_a3_180hp');
  await panel.getByLabel(/Velocidad máxima con 180 HP/).fill('2,52');
  await panel.getByLabel(/resistencia de la red/i).selectOption('No: la red es la misma');
  const check = panel.getByRole('button', { name: 'Comprobar con mi caso' });
  await expect(check).toBeEnabled({ timeout: 30_000 });
  await check.click();
  await expect(panel).toContainText('Paso cumplido.', { timeout: 30_000 });
  await panel.getByRole('button', { name: 'Terminar' }).click();
  await expect(panel).toContainText('2 de 2 pasos cumplidos');
  await panel.getByRole('button', { name: 'Salir del laboratorio' }).click();
  await expect(panel).toHaveCount(0);
});

test('aula: el docente crea curso y tarea, el alumno entrega y el docente ve la nota', async ({
  page,
}) => {
  test.setTimeout(180_000);
  await openAula(page);
  await page.getByRole('button', { name: /Cursos \(ingresar\)/ }).click();
  await login(page, E2E_ADMIN.username, E2E_ADMIN.password);
  await expect(page.getByTestId('teacher-view')).toBeVisible({ timeout: 30_000 });
  const name = `TAP ${Date.now()}`;
  await page.getByLabel('Curso nuevo').fill(name);
  await page.getByLabel('Cuatrimestre').fill('2026-2C');
  await page.getByRole('button', { name: 'Crear', exact: true }).click();
  const code = (await page.getByTestId('course-code').locator('strong').textContent())!.trim();
  expect(code).toMatch(/^[A-Z0-9]{8}$/);

  await page.getByRole('button', { name: 'Nueva tarea' }).click();
  const editor = page.getByTestId('assignment-editor');
  await editor.getByLabel('Título').fill('TP 1: resistencia');
  await editor.getByLabel('Capítulo').selectOption('14_resistencia');
  await editor.getByLabel(/Resistencia de diseño/).check();
  await editor.getByLabel(/El paño y la resistencia/).check();
  await editor.getByRole('button', { name: 'Crear tarea' }).click();
  await expect(page.getByRole('button', { name: /TP 1: resistencia/ })).toBeVisible();
  await page.getByRole('button', { name: 'Salir' }).click();

  // Alumno nuevo con el código del curso.
  const student = `alumno${Date.now() % 100000}`;
  await page.getByRole('button', { name: 'Soy alumno' }).click();
  await page.getByLabel('Usuario').fill(student);
  await page.getByLabel('Contraseña').fill('alumno-123');
  await page.getByLabel('Nombre o legajo').fill('Legajo 4321');
  await page.getByLabel('Código del curso').fill(code.toLowerCase());
  await page.getByRole('button', { name: 'Crear cuenta' }).click();
  await expect(page.getByTestId('student-view')).toBeVisible({ timeout: 30_000 });
  await page.getByRole('button', { name: /TP 1: resistencia/ }).click();
  const ex = page.getByTestId('exercise').first();
  await ex.getByLabel(/Resistencia de la red/).fill('1');
  await ex.getByRole('button', { name: 'Entregar' }).click();
  await expect(ex.getByTestId('grade')).toContainText('Puntaje 0 %');
  await expect(ex).toContainText('intentos: 1 de 3');
  await expect(page.getByTestId('lab-item')).toContainText('El paño y la resistencia');
  await page.getByRole('button', { name: 'Salir' }).click();

  // El docente ve la planilla con la entrega y descarga las notas.
  await login(page, E2E_ADMIN.username, E2E_ADMIN.password);
  await page.getByRole('button', { name: new RegExp(name) }).click();
  await page.getByRole('button', { name: /TP 1: resistencia/ }).click();
  const grades = page.getByTestId('grades');
  await expect(grades.getByRole('row', { name: /Legajo 4321/ })).toContainText('0 %');
  const download = page.waitForEvent('download');
  await grades.getByRole('button', { name: 'Notas (Excel)' }).click();
  expect((await download).suggestedFilename()).toMatch(/^notas-\d+\.xlsx$/);
});
