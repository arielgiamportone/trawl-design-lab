import { useId, useState, type FormEvent } from 'react';
import { useT } from '../../i18n';
import { chapterLabel, levelLabel, pct } from '../../lib/classroom';

/** Lo que se muestra de un ejercicio (instancia del banco, sin respuestas). */
export interface ExerciseLike {
  id: string;
  title: string;
  level: string;
  chapter: string;
  statement: string;
  data: { key: string; label: string; text: string; unit: string }[];
  answers: { key: string; label: string; unit: string; kind: string; options?: string[] | null }[];
  hints: string[];
}

/** Corrección que se muestra (práctica o entrega del aula). */
export interface GradeLike {
  score: number | null;
  answers?: {
    key: string;
    ok: boolean;
    given?: string | null;
    expected_text?: string | null;
    message: string;
  }[];
  explanation?: string | null;
  message?: string;
}

interface Props {
  ex: ExerciseLike;
  onSubmit: (answers: Record<string, string>) => Promise<GradeLike>;
  /** Texto del botón (por defecto, «Corregir» en el idioma activo). */
  submitLabel?: string;
  disabled?: boolean;
  /** Nota al pie (intentos, fechas). */
  footer?: React.ReactNode;
  /** Muestra el capítulo del libro. */
  showChapter?: boolean;
}

/** Ejercicio con sus datos, campos de respuesta y corrección por respuesta. */
export function ExerciseCard({
  ex,
  onSubmit,
  submitLabel,
  disabled,
  footer,
  showChapter = true,
}: Props) {
  const T = useT().classroom.exercise;
  const ids = useId();
  const [values, setValues] = useState<Record<string, string>>({});
  const [grade, setGrade] = useState<GradeLike | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [hints, setHints] = useState(0);

  const send = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      setGrade(await onSubmit(values));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  };
  const byKey = new Map((grade?.answers ?? []).map((a) => [a.key, a]));

  return (
    <article className="aula-ex card card-pad" data-testid="exercise" aria-labelledby={`${ids}-t`}>
      <header className="aula-ex-head">
        <h3 id={`${ids}-t`}>{ex.title}</h3>
        <span className="badge">{levelLabel(ex.level)}</span>
        {showChapter && <span className="badge accent">{chapterLabel(ex.chapter)}</span>}
      </header>
      <p className="aula-statement">{ex.statement}</p>
      {ex.data.length > 0 && (
        <table className="data aula-data">
          <caption className="sr-only">{T.dataCaption}</caption>
          <tbody>
            {ex.data.map((d) => (
              <tr key={d.key}>
                <th scope="row">{d.label}</th>
                <td className="num">{d.text}</td>
                <td className="unit">{d.unit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <form onSubmit={send} className="aula-answers">
        {ex.answers.map((a) => {
          const g = byKey.get(a.key);
          const fid = `${ids}-${a.key}`;
          return (
            <div className={`field aula-answer${g ? (g.ok ? ' ok' : ' bad') : ''}`} key={a.key}>
              <label htmlFor={fid}>
                {a.label}
                {a.unit && <span className="unit"> [{a.unit}]</span>}
              </label>
              {a.kind === 'choice' && a.options ? (
                <select
                  id={fid}
                  value={values[a.key] ?? ''}
                  onChange={(e) => setValues({ ...values, [a.key]: e.target.value })}
                >
                  <option value="">{T.choose}</option>
                  {a.options.map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              ) : (
                <input
                  id={fid}
                  inputMode={a.kind === 'number' ? 'decimal' : 'text'}
                  autoComplete="off"
                  value={values[a.key] ?? ''}
                  onChange={(e) => setValues({ ...values, [a.key]: e.target.value })}
                />
              )}
              {g && (
                <span className="aula-mark" role="status">
                  {g.ok ? T.correct : `✗ ${g.message}`}
                  {!g.ok && g.expected_text ? T.expected(g.expected_text, a.unit) : ''}
                </span>
              )}
            </div>
          );
        })}
        <div className="calc-row">
          <button type="submit" className="btn primary" disabled={busy || disabled}>
            {busy ? T.grading : (submitLabel ?? T.submit)}
          </button>
          {ex.hints.length > 0 && hints < ex.hints.length && (
            <button type="button" className="btn ghost" onClick={() => setHints(hints + 1)}>
              {T.hint}
            </button>
          )}
        </div>
      </form>
      {hints > 0 && (
        <ul className="help aula-hints">
          {ex.hints.slice(0, hints).map((h) => (
            <li key={h}>{h}</li>
          ))}
        </ul>
      )}
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
      {grade && (
        <div
          className={`alert ${grade.score === null ? 'info' : grade.score >= 1 ? 'good' : 'warn'}`}
          role="status"
          data-testid="grade"
        >
          <div>
            <strong>
              {grade.score === null ? (grade.message ?? T.received) : T.score(pct(grade.score))}
            </strong>
            {grade.explanation && <p className="aula-expl">{grade.explanation}</p>}
          </div>
        </div>
      )}
      {footer && <div className="help">{footer}</div>}
    </article>
  );
}
