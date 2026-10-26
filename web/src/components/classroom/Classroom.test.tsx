import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { App } from '../../App';
import { chapterLabel, fmtDate, pct, SESSION_KEY } from '../../lib/classroom';
import { LAB_KEY, caseFromStart, labSubmission, type ActiveLab } from '../../lib/lab';
import { forgetAll } from '../../lib/memo';
import { MODE_KEY } from '../../lib/mode';
import { json, mockApi } from '../../test/mockApi';

const SLOW = 20_000;

function renderApp() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <App />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  localStorage.clear();
  forgetAll();
  window.localStorage.setItem(MODE_KEY, JSON.stringify('aula'));
});
afterEach(() => vi.unstubAllGlobals());

describe('lib/classroom y lib/lab', () => {
  it('etiquetas, fechas y porcentajes', () => {
    expect(chapterLabel('20_optimizacion')).toBe('20 · Optimización');
    expect(chapterLabel('99_otra_cosa')).toBe('99 · Otra cosa');
    expect(pct(0.5)).toBe('50 %');
    expect(pct(null)).toBe('—');
    expect(fmtDate(null)).toBe('—');
    expect(fmtDate('2026-10-26T12:00:00')).toMatch(/26\/10\/2?0?26/);
  });

  it('caso de partida y pasos para entregar', () => {
    const c = caseFromStart({
      net: 'fao_a3_standard',
      vessel: 'fao_a3_180hp',
      params: { depth_m: 80 },
    });
    expect(c.vessel).toBe('fao_a3_180hp');
    expect(c.netModified).toBeNull();
    expect(c.params).toEqual({ depth_m: '80' });
    const lab: ActiveLab = {
      labId: 'lab.x',
      source: { kind: 'practice' },
      step: 0,
      startedAt: '',
      steps: { a: { answers: { q: '1' }, design: { net: 'n' } as never }, b: { answers: {} } },
    };
    expect(Object.keys(labSubmission(lab))).toEqual(['a']);
  });
});

describe('Aula UTN', () => {
  it(
    'práctica libre: abre un ejercicio, corrige y muestra la explicación',
    async () => {
      const { calls } = mockApi();
      renderApp();
      const practice = await screen.findByTestId('practice', {}, { timeout: 5000 });
      await userEvent.click(
        await within(practice).findByRole('button', { name: /Resistencia de diseño/ }),
      );
      const ex = await screen.findByTestId('exercise', {}, { timeout: 5000 });
      expect(ex).toHaveTextContent('superficie sólida de 38,75 m²');
      await userEvent.type(within(ex).getByLabelText(/Resistencia de la red/), '1592');
      await userEvent.click(within(ex).getByRole('button', { name: 'Corregir' }));
      const grade = await screen.findByTestId('grade');
      expect(grade).toHaveTextContent('Puntaje 100 %');
      expect(grade).toHaveTextContent('R_N = 38,75');
      const sent = calls.find((c) => c.url.endsWith('/teaching/grade'));
      expect(sent?.body).toMatchObject({ id: 'resistencia.aberdeen', answers: { rn_kgf: '1592' } });
    },
    SLOW,
  );

  it(
    'empezar un laboratorio abre el modo experto con el panel y comprueba el paso',
    async () => {
      const { calls } = mockApi();
      renderApp();
      await screen.findByTestId('practice', {}, { timeout: 5000 });
      const row = (await screen.findByText('Más potencia, más velocidad')).closest('li')!;
      await userEvent.click(within(row).getByRole('button', { name: 'Empezar' }));
      const panel = await screen.findByTestId('lab-panel', {}, { timeout: 5000 });
      expect(JSON.parse(localStorage.getItem(MODE_KEY)!)).toBe('expert');
      expect(panel).toHaveTextContent('Paso 1 de 2');
      await screen.findByText('2,27', {}, { timeout: 5000 });
      await userEvent.type(within(panel).getByLabelText(/Velocidad máxima/), '2,27');
      const check = within(panel).getByRole('button', { name: 'Comprobar con mi caso' });
      await waitFor(() => expect(check).toBeEnabled(), { timeout: 5000 });
      await userEvent.click(check);
      await within(panel).findByText('Paso cumplido.');
      const sent = calls.find((c) => c.url.endsWith('/teaching/labs/check'));
      expect(sent?.body).toMatchObject({ lab_id: 'lab.buque_y_velocidad', step_id: 'base' });
      const saved = JSON.parse(localStorage.getItem(LAB_KEY)!) as ActiveLab;
      expect(saved.steps.base?.result?.done).toBe(true);
      await userEvent.click(within(panel).getByRole('button', { name: 'Salir' }));
      expect(localStorage.getItem(LAB_KEY)).toBeNull();
    },
    SLOW,
  );

  it(
    'sin base de datos, los cursos avisan que el aula no está habilitada',
    async () => {
      mockApi();
      renderApp();
      await userEvent.click(await screen.findByRole('button', { name: /Cursos \(ingresar\)/ }));
      expect(await screen.findByText(/no está habilitada/)).toBeInTheDocument();
    },
    SLOW,
  );

  it(
    'ingreso y vista del alumno con una tarea',
    async () => {
      const course = {
        id: 1,
        name: 'TAP',
        term: '2026',
        archived: false,
        students: 1,
        teachers: ['Prof.'],
        role: 'student',
        code: null,
      };
      const user = { id: 3, username: 'alumno1', display_name: 'Legajo 1', role: 'student' };
      const { calls } = mockApi({
        classroom: (path, method) => {
          if (path === '/status') return json({ enabled: true, detail: 'ok' });
          if (path === '/auth/login') return json({ token: 'tok', user });
          if (path === '/me') return json({ ...user, courses: [course] });
          if (path === '/courses/1/assignments')
            return json([
              {
                id: 7,
                course_id: 1,
                title: 'TP 1',
                description: '',
                items: [
                  { kind: 'exercise', ref: 'resistencia.aberdeen', points: 1, title: 'Aberdeen' },
                ],
                opens_at: null,
                due_at: null,
                max_attempts: 3,
                feedback: 'immediate',
                per_student_data: true,
                open: true,
                closed: false,
                progress: { items: 1, submitted: 0 },
              },
            ]);
          if (path === '/assignments/7' && method === 'GET')
            return json({
              id: 7,
              course_id: 1,
              title: 'TP 1',
              description: 'Resolver en clase',
              items: [],
              opens_at: null,
              due_at: null,
              max_attempts: 3,
              feedback: 'immediate',
              per_student_data: true,
              open: true,
              closed: false,
              item_list: [
                {
                  index: 0,
                  kind: 'exercise',
                  ref: 'resistencia.aberdeen',
                  points: 1,
                  title: 'Aberdeen',
                  attempts_used: 0,
                  attempts_left: 3,
                  submissions: [],
                  exercise: {
                    id: 'resistencia.aberdeen',
                    seed: null,
                    chapter: '14_resistencia',
                    topic: 't',
                    level: 'basico',
                    title: 'Resistencia de diseño (Aberdeen demersal)',
                    statement: 'Datos propios.',
                    data: [],
                    answers: [
                      {
                        key: 'rn_kgf',
                        label: 'Resistencia de la red',
                        unit: 'kgf',
                        kind: 'number',
                        options: null,
                      },
                    ],
                    hints: [],
                    refs: [],
                  },
                },
              ],
            });
          if (path === '/assignments/7/items/0/submit')
            return json({
              id: 1,
              item: 0,
              attempt: 1,
              created_at: '2026-10-26T12:00:00',
              score: 0,
              teacher_score: null,
              comment: '',
              message: '',
              result: {
                answers: [
                  {
                    key: 'rn_kgf',
                    ok: false,
                    given: '1',
                    expected: null,
                    expected_text: null,
                    message: 'fuera de la tolerancia',
                  },
                ],
              },
            });
          return undefined;
        },
      });
      renderApp();
      await userEvent.click(await screen.findByRole('button', { name: /Cursos \(ingresar\)/ }));
      await userEvent.type(await screen.findByLabelText('Usuario'), 'alumno1');
      await userEvent.type(screen.getByLabelText('Contraseña'), 'alumno-123');
      await userEvent.click(screen.getAllByRole('button', { name: 'Ingresar' }).at(-1)!);
      await screen.findByTestId('student-view', {}, { timeout: 5000 });
      expect(JSON.parse(localStorage.getItem(SESSION_KEY)!).token).toBe('tok');
      await userEvent.click(await screen.findByRole('button', { name: /TP 1/ }));
      const ex = await screen.findByTestId('exercise', {}, { timeout: 5000 });
      expect(ex).toHaveTextContent('Datos propios.');
      await userEvent.type(within(ex).getByLabelText(/Resistencia de la red/), '1');
      await userEvent.click(within(ex).getByRole('button', { name: 'Entregar' }));
      expect(await within(ex).findByText(/fuera de la tolerancia/)).toBeInTheDocument();
      const sub = calls.find((c) => c.url.endsWith('/classroom/assignments/7/items/0/submit'));
      expect(sub?.body).toEqual({ answers: { rn_kgf: '1' } });
      const auth = (vi
        .mocked(fetch)
        .mock.calls.find((c) => String(c[0]).endsWith('/classroom/me'))?.[1]?.headers ??
        {}) as Record<string, string>;
      expect(auth.Authorization).toBe('Bearer tok');
    },
    SLOW,
  );
});
