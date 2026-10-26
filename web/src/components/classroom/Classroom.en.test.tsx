/**
 * Aula UTN en inglés: la interfaz del aula no deja textos en español. Las respuestas de la API se
 * reemplazan por versiones en inglés (como llegan con ``?lang=en``) para poder buscar palabras
 * españolas en todo el texto visible.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { setLang } from '../../i18n';
import { chapterLabel, fmtDate, levelLabel, pct, SESSION_KEY } from '../../lib/classroom';
import { LAB_KEY, type ActiveLab } from '../../lib/lab';
import { forgetAll } from '../../lib/memo';
import { CaseProvider } from '../../state/CaseProvider';
import { ConnectionProvider } from '../../state/ConnectionProvider';
import teachingLab from '../../test/fixtures/teaching_lab.json';
import { json, mockApi } from '../../test/mockApi';
import { Classroom } from './Classroom';
import { LabPanel } from './LabPanel';

const SLOW = 20_000;
const VIEW_KEY = 'trawl-design-lab:aula-view';

/** Palabras españolas que no deben quedar en la interfaz en inglés. */
const SPANISH = new RegExp(
  '(?<!\\p{L})(Entregar|Entregado|Curso|Cursos|Tarea|Tareas|Alumno|Alumnos|Docente|Ingresar|' +
    'Contraseña|Usuario|Guardar|Cerrar|Capítulo|Nivel|Todos|Empezar|Ejercicios|Laboratorios?|' +
    'Paso|pasos|Corregir|Elegir|Salir|Notas|Puntos|Nueva|Nuevo|Crear|del|las|los|una|con|para)' +
    '(?!\\p{L})',
  'u',
);

function noSpanish(el: HTMLElement) {
  const texts = [
    el.textContent ?? '',
    ...[...el.querySelectorAll('[aria-label],[title],[placeholder]')].map((e) =>
      ['aria-label', 'title', 'placeholder'].map((a) => e.getAttribute(a) ?? '').join(' '),
    ),
  ];
  for (const t of texts) expect(t).not.toMatch(SPANISH);
}

/** Respuestas de la API en inglés (lo que llega con ``?lang=en``). */
const EN: Record<string, unknown> = {
  '/teaching/exercises': [
    {
      id: 'resistencia.aberdeen',
      chapter: '14_resistencia',
      topic: 'drag',
      level: 'basico',
      title: 'Design drag (Aberdeen demersal)',
      answers: 1,
    },
  ],
  '/teaching/labs': [
    {
      id: 'lab.buque_y_velocidad',
      chapter: '19_ventana_velocidad',
      topic: 'window',
      level: 'basico',
      title: 'More power, more speed',
      summary: 'Change the vessel and watch the speed window move.',
      steps: 2,
    },
  ],
  '/teaching/exercises/resistencia.aberdeen': {
    id: 'resistencia.aberdeen',
    seed: 1,
    chapter: '14_resistencia',
    topic: 'drag',
    level: 'basico',
    title: 'Design drag (Aberdeen demersal)',
    statement: 'A net with a solid area of 38.75 m² is towed at 3 kn.',
    data: [{ key: 's', label: 'Solid area', text: '38.75', unit: 'm²' }],
    answers: [{ key: 'rn_kgf', label: 'Net drag', unit: 'kgf', kind: 'number', options: null }],
    hints: ['Use the Aberdeen formula.'],
    refs: [],
  },
  '/teaching/grade': {
    id: 'resistencia.aberdeen',
    seed: 1,
    score: 0,
    answers: [
      {
        key: 'rn_kgf',
        ok: false,
        given: '1',
        expected: 1592,
        expected_text: '1,592',
        error_rel: 0.99,
        message: 'outside the tolerance',
      },
    ],
    explanation: 'R_N = 38.75 × 41.08 = 1,592 kgf.',
  },
  '/teaching/labs/lab.buque_y_velocidad': {
    ...teachingLab,
    title: 'More power, more speed',
    summary: 'Change the vessel.',
    closing: 'Power moves the pull curve.',
    step_list: [
      {
        id: 'base',
        title: 'Top speed with 150 HP',
        instruction: 'In the Charts tab, see where pull and total drag cross.',
        target: { mode: 'expert', tab: 'graficos', hint: null },
        checks: [{ label: '150 HP vessel', fact: 'vessel.bhp', op: '==' }],
        questions: [{ id: 'vmax', kind: 'number', prompt: 'Top speed', unit: 'kn', options: null }],
      },
      {
        id: 'buque',
        title: 'Switch to the 180 HP vessel',
        instruction: 'Pick the 180 HP vessel and recalculate.',
        target: { mode: 'expert', tab: 'graficos', hint: 'Vessel selector in the case panel' },
        checks: [{ label: '180 HP vessel or more', fact: 'vessel.bhp', op: '>=' }],
        questions: [
          {
            id: 'rn',
            kind: 'choice',
            prompt: 'Did the net drag at 3 kn change?',
            unit: '',
            options: ['Yes, it rose', 'Yes, it fell', 'No: the net is the same'],
            option_ids: ['up', 'down', 'same'],
          },
        ],
      },
    ],
  },
};

/** ``mockApi`` con las rutas de enseñanza en inglés. */
function mockEnglish(overrides: Parameters<typeof mockApi>[0] = {}) {
  const r = mockApi(overrides);
  const inner = globalThis.fetch;
  vi.stubGlobal(
    'fetch',
    vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const path = new URL(String(input), 'http://x').pathname.replace(/^\/api/, '');
      if (path in EN) {
        r.calls.push({
          url: String(input),
          method: init?.method ?? 'GET',
          body: init?.body ? JSON.parse(String(init.body)) : undefined,
        });
        return json(EN[path]);
      }
      return inner(input, init);
    }),
  );
  return r;
}

function renderClassroom(ui = <Classroom />) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <ConnectionProvider>
        <CaseProvider>{ui}</CaseProvider>
      </ConnectionProvider>
    </QueryClientProvider>,
  );
}

const course = {
  id: 1,
  name: 'TAP',
  term: '2026',
  archived: false,
  students: 2,
  teachers: ['Prof.'],
  role: 'student',
  code: 'ABC123',
};
const assignment = {
  id: 7,
  course_id: 1,
  title: 'Assignment 1',
  description: '',
  items: [{ kind: 'exercise', ref: 'resistencia.aberdeen', points: 1, title: 'Aberdeen' }],
  opens_at: null,
  due_at: '2026-10-30T12:00:00',
  max_attempts: 3,
  feedback: 'immediate',
  per_student_data: true,
  open: true,
  closed: false,
  progress: { items: 1, submitted: 0 },
};

function signIn(role: 'student' | 'teacher') {
  const user = { id: 3, username: 'u1', display_name: 'Jane', role };
  localStorage.setItem(SESSION_KEY, JSON.stringify({ token: 'tok', user }));
  localStorage.setItem(VIEW_KEY, JSON.stringify('aula'));
  return user;
}

beforeEach(() => {
  localStorage.clear();
  forgetAll();
  setLang('en');
});
afterEach(() => vi.unstubAllGlobals());

describe('lib/classroom in English', () => {
  it('chapters, levels, percentages and dates', () => {
    expect(chapterLabel('14_resistencia')).toBe('14 · Drag');
    expect(chapterLabel('20_optimizacion')).toBe('20 · Optimization');
    expect(chapterLabel('99_otra_cosa')).toBe('99 · Otra cosa');
    expect(levelLabel('intermedio')).toBe('Intermediate');
    expect(pct(0.5)).toBe('50%');
    expect(fmtDate('2026-10-26T12:00:00')).toMatch(/10\/26\/26/);
    setLang('es');
    expect(chapterLabel('14_resistencia')).toBe('14 · Resistencia');
    expect(pct(0.5)).toBe('50 %');
  });
});

describe('UTN Classroom in English', () => {
  it(
    'free practice: lists, opens and grades an exercise',
    async () => {
      const { calls } = mockEnglish();
      renderClassroom();
      const practice = await screen.findByTestId('practice', {}, { timeout: 5000 });
      expect(screen.getByRole('heading', { name: 'UTN Classroom' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Free practice' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Courses (sign in)' })).toBeInTheDocument();
      expect(within(practice).getByLabelText('Chapter')).toBeInTheDocument();
      const lab = (await within(practice).findByText('More power, more speed')).closest('li')!;
      expect(lab).toHaveTextContent('2 steps · 19 · Speed window');
      expect(within(lab).getByRole('button', { name: 'Start' })).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));

      await userEvent.click(within(practice).getByRole('button', { name: /Design drag/ }));
      const ex = await screen.findByTestId('exercise', {}, { timeout: 5000 });
      expect(ex).toHaveTextContent('14 · Drag');
      expect(ex).toHaveTextContent('Basic');
      await userEvent.click(within(ex).getByRole('button', { name: 'Show a hint' }));
      await userEvent.type(within(ex).getByLabelText(/Net drag/), '1');
      await userEvent.click(within(ex).getByRole('button', { name: 'Check' }));
      const grade = await screen.findByTestId('grade');
      expect(grade).toHaveTextContent('Score 0%');
      expect(ex).toHaveTextContent('✗ outside the tolerance · expected 1,592 kgf');
      expect(screen.getByRole('button', { name: '← All exercises' })).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
      expect(
        calls.some((c) => c.url.includes('/teaching/exercises') && /lang=en/.test(c.url)),
      ).toBe(true);
    },
    SLOW,
  );

  it(
    'sign-in and sign-up forms',
    async () => {
      mockEnglish({
        classroom: (path) =>
          path === '/status' ? json({ enabled: true, detail: 'ok' }) : undefined,
      });
      localStorage.setItem(VIEW_KEY, JSON.stringify('aula'));
      renderClassroom();
      expect(
        await screen.findByRole('heading', { name: 'Sign in to the classroom' }, { timeout: 5000 }),
      ).toBeInTheDocument();
      expect(screen.getByLabelText('Username')).toBeInTheDocument();
      expect(screen.getByLabelText('Password')).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
      await userEvent.click(screen.getByRole('button', { name: "I'm a student" }));
      expect(screen.getByRole('heading', { name: 'Create a student account' })).toBeInTheDocument();
      expect(screen.getByLabelText('Course code')).toBeInTheDocument();
      expect(screen.getByLabelText('Name or student ID')).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
      await userEvent.click(screen.getByRole('button', { name: "I'm a teacher" }));
      expect(screen.getByLabelText('Invitation code')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Create account' })).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
    },
    SLOW,
  );

  it(
    'student view: courses, assignments and submission',
    async () => {
      const user = signIn('student');
      mockEnglish({
        classroom: (path, method) => {
          if (path === '/status') return json({ enabled: true, detail: 'ok' });
          if (path === '/me') return json({ ...user, courses: [course] });
          if (path === '/courses/1/assignments') return json([assignment]);
          if (path === '/assignments/7' && method === 'GET')
            return json({
              ...assignment,
              description: 'Solve in class',
              item_list: [
                {
                  index: 0,
                  kind: 'exercise',
                  ref: 'resistencia.aberdeen',
                  points: 1,
                  title: 'Aberdeen',
                  attempts_used: 1,
                  attempts_left: 2,
                  submissions: [
                    {
                      id: 1,
                      item: 0,
                      attempt: 1,
                      created_at: '2026-10-26T12:00:00',
                      score: 0.5,
                      teacher_score: null,
                      comment: 'Check the units',
                      message: '',
                      result: null,
                    },
                  ],
                  exercise: EN['/teaching/exercises/resistencia.aberdeen'],
                },
              ],
            });
          return undefined;
        },
      });
      renderClassroom();
      const view = await screen.findByTestId('student-view', {}, { timeout: 5000 });
      expect(screen.getByText(/Jane \(student\)/)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Sign out' })).toBeInTheDocument();
      expect(within(view).getByLabelText('Join another course')).toBeInTheDocument();
      const row = await within(view).findByRole('button', { name: /Assignment 1/ });
      expect(row).toHaveTextContent('0 of 1 item submitted');
      expect(row).toHaveTextContent(/due 10\/30\/26/);
      noSpanish(screen.getByTestId('aula'));
      await userEvent.click(row);
      const ex = await screen.findByTestId('exercise', {}, { timeout: 5000 });
      expect(within(ex).getByRole('button', { name: 'Submit' })).toBeInTheDocument();
      expect(ex).toHaveTextContent(
        'Item 1 · 1 pt · attempts: 1 of 3 · latest: 50% · comment: “Check the units”',
      );
      expect(screen.getByText(/3 attempts per item\./)).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
    },
    SLOW,
  );

  it(
    'teacher view: course, assignments and gradebook',
    async () => {
      const user = signIn('teacher');
      mockEnglish({
        classroom: (path, method) => {
          if (path === '/status') return json({ enabled: true, detail: 'ok' });
          if (path === '/me') return json({ ...user, courses: [{ ...course, role: 'teacher' }] });
          if (path === '/courses/1/assignments') return json([assignment]);
          if (path === '/assignments/7/grades' && method === 'GET')
            return json({
              assignment,
              total_points: 1,
              rows: [
                {
                  student: { id: 5, username: 's1', display_name: 'Ann', role: 'student' },
                  cells: [
                    { item: 0, attempts: 1, score: 0.5, submission_id: 9, needs_review: true },
                  ],
                  points: 0.5,
                },
              ],
            });
          return undefined;
        },
      });
      renderClassroom();
      const view = await screen.findByTestId('teacher-view', {}, { timeout: 5000 });
      expect(within(view).getByText(/2 students/)).toBeInTheDocument();
      expect(within(view).getByTestId('course-code')).toHaveTextContent(
        'Code for students: ABC123',
      );
      expect(within(view).getByRole('button', { name: 'Students (2)' })).toBeInTheDocument();
      expect(within(view).getByLabelText('New course')).toBeInTheDocument();
      const row = await within(view).findByRole('button', { name: /Assignment 1/ });
      expect(row).toHaveTextContent('1 item');
      noSpanish(screen.getByTestId('aula'));
      await userEvent.click(row);
      const grades = await screen.findByTestId('grades');
      expect(within(grades).getByRole('button', { name: 'Gradebook (Excel)' })).toBeInTheDocument();
      expect(await within(grades).findByText('Points (out of 1)')).toBeInTheDocument();
      expect(within(grades).getByTitle('Has open answers to grade')).toHaveTextContent('50% ✎');
      expect(within(grades).getByText('0.5')).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
      await userEvent.click(within(view).getByRole('button', { name: '← Course assignments' }));
      await userEvent.click(within(view).getByRole('button', { name: 'New assignment' }));
      const editor = await screen.findByTestId('assignment-editor');
      expect(within(editor).getByLabelText('Due date')).toBeInTheDocument();
      expect(
        within(editor).getByRole('option', { name: 'After the due date (exam)' }),
      ).toBeTruthy();
      expect(await within(editor).findByText('2 steps')).toBeInTheDocument();
      noSpanish(screen.getByTestId('aula'));
    },
    SLOW,
  );

  it(
    'lab panel: English labels and choice answers stored by option id',
    async () => {
      mockEnglish();
      const active: ActiveLab = {
        labId: 'lab.buque_y_velocidad',
        source: { kind: 'practice' },
        step: 1,
        steps: {},
        startedAt: '',
      };
      localStorage.setItem(LAB_KEY, JSON.stringify(active));
      renderClassroom(<LabPanel />);
      const panel = await screen.findByTestId('lab-panel', {}, { timeout: 5000 });
      expect(panel).toHaveAttribute('aria-label', 'Guided lab');
      expect(await within(panel).findByText('Step 2 of 2 · 0 completed')).toBeInTheDocument();
      expect(within(panel).getByRole('button', { name: 'Go to “Charts”' })).toBeInTheDocument();
      expect(
        within(panel).getByRole('button', { name: 'Check against my case' }),
      ).toBeInTheDocument();
      expect(within(panel).getByRole('button', { name: 'Finish' })).toBeInTheDocument();
      const select = within(panel).getByLabelText(/Did the net drag/);
      await userEvent.selectOptions(select, 'Yes, it rose');
      const saved = JSON.parse(localStorage.getItem(LAB_KEY)!) as ActiveLab;
      expect(saved.steps.buque?.answers.rn).toBe('up');
      expect(select).toHaveValue('up');
      noSpanish(panel);
    },
    SLOW,
  );
});
