import { useId, useState, type FormEvent } from 'react';
import { useT } from '../../i18n';
import { classroom } from '../../lib/classroom';

type Mode = 'login' | 'student' | 'teacher';

/** Inicio de sesión y alta (alumno con código de curso, docente con código de invitación). */
export function Login() {
  const T = useT().classroom.login;
  const ids = useId();
  const [mode, setMode] = useState<Mode>('login');
  const [form, setForm] = useState({ username: '', password: '', name: '', code: '' });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof form, v: string) => setForm({ ...form, [k]: v });

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === 'login') await classroom.login(form.username, form.password);
      else
        await classroom.register({
          username: form.username,
          password: form.password,
          display_name: form.name,
          course_code: mode === 'student' ? form.code : null,
          invite_code: mode === 'teacher' ? form.code : null,
        });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="card card-pad aula-login" aria-labelledby={`${ids}-t`}>
      <h3 className="section-title" id={`${ids}-t`}>
        {mode === 'login' ? T.titleLogin : mode === 'student' ? T.titleStudent : T.titleTeacher}
      </h3>
      <div className="segmented" role="group" aria-label={T.modeLabel}>
        {(
          [
            ['login', T.login],
            ['student', T.imStudent],
            ['teacher', T.imTeacher],
          ] as const
        ).map(([m, label]) => (
          <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}>
            {label}
          </button>
        ))}
      </div>
      <form onSubmit={send}>
        <div className="field">
          <label htmlFor={`${ids}-u`}>{T.username}</label>
          <input
            id={`${ids}-u`}
            autoComplete="username"
            value={form.username}
            onChange={(e) => set('username', e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor={`${ids}-p`}>{T.password}</label>
          <input
            id={`${ids}-p`}
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            value={form.password}
            onChange={(e) => set('password', e.target.value)}
            required
            minLength={mode === 'login' ? undefined : 8}
          />
        </div>
        {mode !== 'login' && (
          <>
            <div className="field">
              <label htmlFor={`${ids}-n`}>{T.name}</label>
              <input
                id={`${ids}-n`}
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor={`${ids}-c`}>{mode === 'student' ? T.courseCode : T.inviteCode}</label>
              <input
                id={`${ids}-c`}
                autoComplete="off"
                value={form.code}
                onChange={(e) => set('code', e.target.value)}
                required
              />
            </div>
            <p className="help">{mode === 'student' ? T.helpStudent : T.helpTeacher}</p>
          </>
        )}
        <div className="calc-row">
          <button type="submit" className="btn primary" disabled={busy}>
            {mode === 'login' ? T.login : T.create}
          </button>
        </div>
      </form>
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
    </section>
  );
}
