import { useId, useState, type FormEvent } from 'react';
import { classroom } from '../../lib/classroom';

type Mode = 'login' | 'student' | 'teacher';

/** Inicio de sesión y alta (alumno con código de curso, docente con código de invitación). */
export function Login() {
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
        {mode === 'login'
          ? 'Ingresar al aula'
          : mode === 'student'
            ? 'Crear cuenta de alumno'
            : 'Crear cuenta de docente'}
      </h3>
      <div className="segmented" role="group" aria-label="Ingreso o alta">
        {(
          [
            ['login', 'Ingresar'],
            ['student', 'Soy alumno'],
            ['teacher', 'Soy docente'],
          ] as const
        ).map(([m, label]) => (
          <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}>
            {label}
          </button>
        ))}
      </div>
      <form onSubmit={send}>
        <div className="field">
          <label htmlFor={`${ids}-u`}>Usuario</label>
          <input
            id={`${ids}-u`}
            autoComplete="username"
            value={form.username}
            onChange={(e) => set('username', e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label htmlFor={`${ids}-p`}>Contraseña</label>
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
              <label htmlFor={`${ids}-n`}>Nombre o legajo</label>
              <input
                id={`${ids}-n`}
                value={form.name}
                onChange={(e) => set('name', e.target.value)}
                required
              />
            </div>
            <div className="field">
              <label htmlFor={`${ids}-c`}>
                {mode === 'student' ? 'Código del curso' : 'Código de invitación'}
              </label>
              <input
                id={`${ids}-c`}
                autoComplete="off"
                value={form.code}
                onChange={(e) => set('code', e.target.value)}
                required
              />
            </div>
            <p className="help">
              {mode === 'student'
                ? 'El código se lo da su docente. Usuario: 3 a 40 letras minúsculas, números, punto o guion; la contraseña, de 8 caracteres o más. No se pide correo: si la olvida, su docente le pone una nueva.'
                : 'Las invitaciones para docentes las genera la administración del aula.'}
            </p>
          </>
        )}
        <div className="calc-row">
          <button type="submit" className="btn primary" disabled={busy}>
            {mode === 'login' ? 'Ingresar' : 'Crear cuenta'}
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
