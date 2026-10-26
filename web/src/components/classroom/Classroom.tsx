import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useT } from '../../i18n';
import { classroom, useSession } from '../../lib/classroom';
import { loadJson, saveJson } from '../../lib/storage';
import { Login } from './Login';
import { Practice } from './Practice';
import { StudentView } from './StudentView';
import { TeacherView } from './TeacherView';

type View = 'practica' | 'aula';
const VIEW_KEY = 'trawl-design-lab:aula-view';

/**
 * Modo «Aula UTN» (Fase 17): práctica libre con el banco de ejercicios y los laboratorios (sin
 * cuenta, también sin conexión) y el aula del curso (alumnos y docentes, en línea).
 */
export function Classroom() {
  const T = useT().classroom;
  const session = useSession();
  const [view, setViewState] = useState<View>(() => loadJson<View>(VIEW_KEY) ?? 'practica');
  const setView = (v: View) => {
    setViewState(v);
    saveJson(VIEW_KEY, v);
  };
  return (
    <div className="aula" data-testid="aula">
      <div className="aula-top">
        <h2 className="section-title">{T.shell.title}</h2>
        <div className="segmented" role="group" aria-label={T.shell.sectionLabel}>
          <button
            type="button"
            aria-pressed={view === 'practica'}
            onClick={() => setView('practica')}
          >
            {T.shell.practice}
          </button>
          <button type="button" aria-pressed={view === 'aula'} onClick={() => setView('aula')}>
            {session ? T.shell.myCourses : T.shell.coursesLogin}
          </button>
        </div>
        {session && (
          <span className="aula-who">
            {`${session.user.display_name} (${T.roles[session.user.role] ?? session.user.role})`}
            <button
              type="button"
              className="btn ghost small"
              onClick={() => void classroom.logout()}
            >
              {T.shell.logout}
            </button>
          </span>
        )}
      </div>
      {view === 'practica' ? <Practice /> : <ClassArea />}
    </div>
  );
}

function ClassArea() {
  const T = useT().classroom;
  const session = useSession();
  const status = useQuery({
    queryKey: ['aula', 'status'],
    queryFn: () => classroom.status(),
    staleTime: 60_000,
    retry: false,
  });
  const me = useQuery({
    queryKey: ['aula', 'me', session?.token],
    queryFn: () => classroom.me(),
    enabled: !!session && status.data?.enabled === true,
    retry: false,
  });
  if (status.error)
    return (
      <p className="alert warn" role="status">
        {T.shell.needsApi}
        {status.error.message}
      </p>
    );
  if (!status.data) return <p className="empty">{T.shell.checking}</p>;
  if (!status.data.enabled)
    return (
      <p className="alert info" role="status">
        {status.data.detail}
      </p>
    );
  if (!session) return <Login />;
  if (me.error) {
    return (
      <div>
        <p className="alert error" role="alert">
          {me.error.message}
        </p>
        <button type="button" className="btn" onClick={() => void classroom.logout()}>
          {T.shell.loginAgain}
        </button>
      </div>
    );
  }
  if (!me.data) return <p className="empty">{T.shell.loading}</p>;
  const courses = me.data.courses;
  return me.data.role === 'student' ? (
    <StudentView courses={courses} />
  ) : (
    <TeacherView courses={courses} admin={me.data.role === 'admin'} />
  );
}
