/** Aula UTN (Fase 17): sesión en el navegador y pedidos a ``/classroom`` (sólo en línea). */
import { useSyncExternalStore } from 'react';
import { classroomRequest } from '../api/client';
import type { components } from '../api/schema';
import { loadJson, removeKey, saveJson } from './storage';

type S = components['schemas'];
export type ClassUser = S['UserOut'];
export type ClassSession = S['SessionOut'];
export type Me = S['MeOut'];
export type Course = S['CourseOut'];
export type Invite = S['InviteOut'];
export type Assignment = S['AssignmentOut'];
export type AssignmentIn = S['AssignmentIn'];
export type AssignmentView = S['AssignmentViewOut'];
export type StudentItem = S['StudentItemOut'];
export type StudentSubmission = S['StudentSubmissionOut'];
export type Grades = S['GradesOut'];
export type Submission = S['SubmissionOut'];
export type ItemIn = S['ItemIn'];
export type ClassStatus = S['StatusOut'];

export const SESSION_KEY = 'trawl-design-lab:aula:v1';
const EVENT = 'trawl-design-lab:aula';

/** Sesión guardada (token y usuario) o ``null``. */
export function loadSession(): ClassSession | null {
  const s = loadJson<ClassSession>(SESSION_KEY);
  return s && typeof s.token === 'string' && s.user ? s : null;
}

export function saveSession(s: ClassSession | null): void {
  if (s) saveJson(SESSION_KEY, s);
  else removeKey(SESSION_KEY);
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(cb: () => void): () => void {
  window.addEventListener(EVENT, cb);
  window.addEventListener('storage', cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener('storage', cb);
  };
}

let cachedRaw: string | null = null;
let cached: ClassSession | null = null;
function snapshot(): ClassSession | null {
  let raw: string | null;
  try {
    raw = window.localStorage.getItem(SESSION_KEY);
  } catch {
    raw = null;
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw;
    cached = loadSession();
  }
  return cached;
}

/** Sesión del aula, reactiva a inicio y cierre de sesión (también en otras pestañas). */
export function useSession(): ClassSession | null {
  return useSyncExternalStore(subscribe, snapshot, () => null);
}

async function json<T>(res: Response): Promise<T> {
  return (await res.json()) as T;
}

/** Pedidos al aula con el token de la sesión guardada. */
export const classroom = {
  status: async () => json<ClassStatus>(await classroomRequest('/status', null)),
  async login(username: string, password: string): Promise<ClassSession> {
    const res = await classroomRequest('/auth/login', null, {
      method: 'POST',
      body: { username, password },
    });
    const s = await json<ClassSession>(res);
    saveSession(s);
    return s;
  },
  async register(body: {
    username: string;
    password: string;
    display_name: string;
    course_code?: string | null;
    invite_code?: string | null;
  }): Promise<ClassSession> {
    const res = await classroomRequest('/auth/register', null, { method: 'POST', body });
    const s = await json<ClassSession>(res);
    saveSession(s);
    return s;
  },
  async logout(): Promise<void> {
    const s = loadSession();
    saveSession(null);
    if (s) await classroomRequest('/auth/logout', s.token, { method: 'POST' }).catch(() => {});
  },
  me: async () => json<Me>(await classroomRequest('/me', tok())),
  async changePassword(oldPassword: string, newPassword: string): Promise<void> {
    await classroomRequest('/me/password', tok(), {
      method: 'POST',
      body: { old_password: oldPassword, new_password: newPassword },
    });
  },
  async deleteMe(password: string): Promise<void> {
    await classroomRequest('/me/delete', tok(), { method: 'POST', body: { password } });
    saveSession(null);
  },
  invites: async () => json<Invite[]>(await classroomRequest('/invites', tok())),
  createInvites: async (count: number, days: number) =>
    json<Invite[]>(
      await classroomRequest('/invites', tok(), { method: 'POST', body: { count, days } }),
    ),
  courses: async () => json<Course[]>(await classroomRequest('/courses', tok())),
  createCourse: async (name: string, term: string) =>
    json<Course>(
      await classroomRequest('/courses', tok(), { method: 'POST', body: { name, term } }),
    ),
  joinCourse: async (code: string) =>
    json<Course>(
      await classroomRequest('/courses/join', tok(), { method: 'POST', body: { code } }),
    ),
  updateCourse: async (
    id: number,
    patch: { name?: string; term?: string; archived?: boolean; new_code?: boolean },
  ) =>
    json<Course>(await classroomRequest(`/courses/${id}`, tok(), { method: 'PATCH', body: patch })),
  students: async (courseId: number) =>
    json<ClassUser[]>(await classroomRequest(`/courses/${courseId}/students`, tok())),
  async removeStudent(courseId: number, studentId: number): Promise<void> {
    await classroomRequest(`/courses/${courseId}/students/${studentId}`, tok(), {
      method: 'DELETE',
    });
  },
  async resetPassword(courseId: number, studentId: number, password: string): Promise<void> {
    await classroomRequest(`/courses/${courseId}/students/${studentId}/password`, tok(), {
      method: 'POST',
      body: { password },
    });
  },
  assignments: async (courseId: number) =>
    json<Assignment[]>(await classroomRequest(`/courses/${courseId}/assignments`, tok())),
  createAssignment: async (courseId: number, body: AssignmentIn) =>
    json<Assignment>(
      await classroomRequest(`/courses/${courseId}/assignments`, tok(), { method: 'POST', body }),
    ),
  async deleteAssignment(id: number): Promise<void> {
    await classroomRequest(`/assignments/${id}`, tok(), { method: 'DELETE' });
  },
  assignment: async (id: number) =>
    json<AssignmentView>(await classroomRequest(`/assignments/${id}`, tok())),
  submit: async (
    id: number,
    item: number,
    body: {
      answers?: Record<string, string>;
      steps?: Record<string, { design: unknown; answers: Record<string, string> }>;
    },
  ) =>
    json<StudentSubmission>(
      await classroomRequest(`/assignments/${id}/items/${item}/submit`, tok(), {
        method: 'POST',
        body,
      }),
    ),
  grades: async (id: number) =>
    json<Grades>(await classroomRequest(`/assignments/${id}/grades`, tok())),
  gradesExport: async (id: number, format: 'xlsx' | 'csv') =>
    (await classroomRequest(`/assignments/${id}/grades/export?format=${format}`, tok())).blob(),
  sheet: async (id: number, opts: { format: 'html' | 'pdf'; key: boolean; allStudents: boolean }) =>
    (
      await classroomRequest(
        `/assignments/${id}/sheet?format=${opts.format}&key=${opts.key}&all_students=${opts.allStudents}`,
        tok(),
      )
    ).blob(),
  submission: async (id: number) =>
    json<Submission>(await classroomRequest(`/submissions/${id}`, tok())),
  review: async (id: number, teacherScore: number | null, comment: string) =>
    json<Submission>(
      await classroomRequest(`/submissions/${id}`, tok(), {
        method: 'PATCH',
        body: { teacher_score: teacherScore, comment },
      }),
    ),
};

function tok(): string | null {
  return loadSession()?.token ?? null;
}

export const LEVEL_LABEL: Record<string, string> = {
  basico: 'Básico',
  intermedio: 'Intermedio',
  avanzado: 'Avanzado',
};

const CHAPTERS: Record<string, string> = {
  '10': 'Potencia',
  '11': 'Paños y cortes',
  '12': 'Mecánica de la red',
  '13': 'Dimensiones',
  '14': 'Resistencia',
  '15': 'Portones y aparejo',
  '16': 'Aberturas',
  '17': 'Flotación y lastre',
  '18': 'Cables',
  '19': 'Ventana de velocidad',
  '20': 'Optimización',
  '21': 'Simulación',
  '22': 'Simulación realista',
  '23': 'Mar real',
  '24': 'Malla y selectividad',
  '25': 'Incertidumbre',
  '36': 'Construcción',
  '37': 'Economía',
};

/** Capítulo del libro legible: ``14_resistencia`` → ``14 · Resistencia``. */
export function chapterLabel(chapter: string): string {
  const [num = '', ...rest] = chapter.split('_');
  const text = CHAPTERS[num] ?? rest.join(' ');
  return `${num} · ${text.charAt(0).toUpperCase()}${text.slice(1)}`;
}

/** Fecha y hora local corta (es-AR) de una fecha ISO de la API (UTC sin zona). */
export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(/[zZ]|[+-]\d\d:?\d\d$/.test(iso) ? iso : `${iso}Z`);
  return d.toLocaleString('es-AR', { dateStyle: 'short', timeStyle: 'short' });
}

/** Puntaje 0–1 como porcentaje. */
export function pct(x: number | null | undefined): string {
  return x == null ? '—' : `${Math.round(x * 100)} %`;
}
