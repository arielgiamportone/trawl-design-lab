import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { api } from '../../api/client';
import { useT } from '../../i18n';
import {
  chapterLabel,
  classroom,
  fmtDate,
  levelLabel,
  pct,
  type Assignment,
  type Course,
  type ItemIn,
} from '../../lib/classroom';
import { downloadBlob } from '../../lib/download';
import { fmtNum, parseNumber } from '../../lib/format';

/** El aula del docente: cursos, alumnos, tareas, notas y revisión de entregas. */
export function TeacherView({ courses, admin }: { courses: Course[]; admin: boolean }) {
  const T = useT().classroom.teacher;
  const [courseId, setCourseId] = useState<number | null>(courses[0]?.id ?? null);
  const course = courses.find((c) => c.id === courseId) ?? null;
  return (
    <div className="aula-teacher" data-testid="teacher-view">
      <div className="aula-courses">
        {courses.map((c) => (
          <button
            key={c.id}
            type="button"
            className="aula-course"
            aria-pressed={c.id === courseId}
            onClick={() => setCourseId(c.id)}
          >
            <strong>{c.name}</strong>
            <span>
              {c.term} · {T.students(c.students)}
              {c.archived ? T.archived : ''}
            </span>
          </button>
        ))}
        <NewCourse onCreated={setCourseId} />
      </div>
      {course && <CoursePanel key={course.id} course={course} />}
      {admin && <Invites />}
    </div>
  );
}

function errText(err: unknown): string {
  return err instanceof Error ? err.message : String(err);
}

function NewCourse({ onCreated }: { onCreated: (id: number) => void }) {
  const T = useT().classroom.teacher;
  const qc = useQueryClient();
  const [name, setName] = useState('');
  const [term, setTerm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const send = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const c = await classroom.createCourse(name, term);
      setName('');
      setTerm('');
      await qc.invalidateQueries({ queryKey: ['aula'] });
      onCreated(c.id);
    } catch (err) {
      setError(errText(err));
    }
  };
  return (
    <form className="aula-join" onSubmit={send}>
      <label htmlFor="aula-new-course">{T.newCourse}</label>
      <input
        id="aula-new-course"
        placeholder={T.namePlaceholder}
        value={name}
        onChange={(e) => setName(e.target.value)}
      />
      <div className="calc-row">
        <input
          aria-label={T.term}
          placeholder={T.termPlaceholder}
          value={term}
          onChange={(e) => setTerm(e.target.value)}
        />
        <button type="submit" className="btn small" disabled={!name.trim()}>
          {T.create}
        </button>
      </div>
      {error && <p className="alert error">{error}</p>}
    </form>
  );
}

function CoursePanel({ course }: { course: Course }) {
  const T = useT().classroom.teacher;
  const qc = useQueryClient();
  const [view, setView] = useState<'tareas' | 'alumnos'>('tareas');
  const regen = async () => {
    await classroom.updateCourse(course.id, { new_code: true });
    await qc.invalidateQueries({ queryKey: ['aula'] });
  };
  return (
    <section className="card card-pad aula-course-panel" aria-label={T.courseLabel(course.name)}>
      <h3 className="section-title">
        {course.name}
        <span className="aula-code" data-testid="course-code">
          {T.codeForStudents}
          <strong>{course.code}</strong>{' '}
          <button type="button" className="btn ghost small" onClick={() => void regen()}>
            {T.changeCode}
          </button>
        </span>
      </h3>
      <div className="segmented" role="group" aria-label={T.courseSection}>
        <button type="button" aria-pressed={view === 'tareas'} onClick={() => setView('tareas')}>
          {T.assignments}
        </button>
        <button type="button" aria-pressed={view === 'alumnos'} onClick={() => setView('alumnos')}>
          {T.studentsTab(course.students)}
        </button>
      </div>
      {view === 'tareas' ? <Assignments courseId={course.id} /> : <Students courseId={course.id} />}
    </section>
  );
}

function Students({ courseId }: { courseId: number }) {
  const T = useT().classroom.teacher;
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ['aula', 'students', courseId],
    queryFn: () => classroom.students(courseId),
  });
  const [msg, setMsg] = useState<string | null>(null);
  const reset = async (id: number, name: string) => {
    const pw = window.prompt(T.newPassword(name));
    if (!pw) return;
    try {
      await classroom.resetPassword(courseId, id, pw);
      setMsg(T.passwordChanged(name));
    } catch (err) {
      setMsg(errText(err));
    }
  };
  const remove = async (id: number, name: string) => {
    if (!window.confirm(T.confirmRemove(name))) return;
    await classroom.removeStudent(courseId, id);
    await qc.invalidateQueries({ queryKey: ['aula'] });
  };
  if (q.error) return <p className="alert error">{q.error.message}</p>;
  if (!q.data) return <p className="empty">{T.loading}</p>;
  if (!q.data.length) return <p className="empty">{T.noStudents}</p>;
  return (
    <>
      <table className="data">
        <thead>
          <tr>
            <th>{T.name}</th>
            <th>{T.username}</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {q.data.map((u) => (
            <tr key={u.id}>
              <td>{u.display_name}</td>
              <td>{u.username}</td>
              <td>
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={() => void reset(u.id, u.display_name)}
                >
                  {T.resetPassword}
                </button>
                <button
                  type="button"
                  className="btn ghost small"
                  onClick={() => void remove(u.id, u.display_name)}
                >
                  {T.remove}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {msg && <p className="alert info">{msg}</p>}
    </>
  );
}

function Assignments({ courseId }: { courseId: number }) {
  const T = useT().classroom.teacher;
  const q = useQuery({
    queryKey: ['aula', 'assignments', courseId],
    queryFn: () => classroom.assignments(courseId),
  });
  const [editing, setEditing] = useState(false);
  const [open, setOpen] = useState<number | null>(null);
  if (q.error) return <p className="alert error">{q.error.message}</p>;
  const current = q.data?.find((a) => a.id === open) ?? null;
  return (
    <div className="aula-assignments">
      {!editing && !current && (
        <>
          <ul className="aula-list" aria-label={T.courseAssignments}>
            {(q.data ?? []).map((a) => (
              <li key={a.id}>
                <button type="button" className="aula-row" onClick={() => setOpen(a.id)}>
                  <span className="aula-row-title">{a.title}</span>
                  <span className="badge">{T.items(a.items.length)}</span>
                  <span className="aula-row-sub">
                    {a.opens_at ? T.opens(fmtDate(a.opens_at)) : ''}
                    {a.due_at ? T.closes(fmtDate(a.due_at)) : T.noDue}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="btn primary" onClick={() => setEditing(true)}>
            {T.newAssignment}
          </button>
        </>
      )}
      {editing && <AssignmentEditor courseId={courseId} onDone={() => setEditing(false)} />}
      {current && <GradesView a={current} onBack={() => setOpen(null)} />}
    </div>
  );
}

function AssignmentEditor({ courseId, onDone }: { courseId: number; onDone: () => void }) {
  const T = useT().classroom.teacher.editor;
  const qc = useQueryClient();
  const exercises = useQuery({
    queryKey: ['teaching', 'exercises'],
    queryFn: ({ signal }) => api.exercises(signal),
    staleTime: Infinity,
  });
  const labs = useQuery({
    queryKey: ['teaching', 'labs'],
    queryFn: ({ signal }) => api.labs(signal),
    staleTime: Infinity,
  });
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [items, setItems] = useState<ItemIn[]>([]);
  const [due, setDue] = useState('');
  const [attempts, setAttempts] = useState(3);
  const [feedback, setFeedback] = useState<'immediate' | 'after_due'>('immediate');
  const [chapter, setChapter] = useState('');
  const [error, setError] = useState<string | null>(null);
  const chapters = useMemo(
    () => [...new Set((exercises.data ?? []).map((e) => e.chapter))].sort(),
    [exercises.data],
  );
  const has = (kind: string, ref: string) => items.some((i) => i.kind === kind && i.ref === ref);
  const toggle = (kind: 'exercise' | 'lab', ref: string) =>
    setItems(
      has(kind, ref)
        ? items.filter((i) => !(i.kind === kind && i.ref === ref))
        : [...items, { kind, ref, points: 1 }],
    );
  const send = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await classroom.createAssignment(courseId, {
        title,
        description,
        items,
        due_at: due ? new Date(due).toISOString() : null,
        max_attempts: attempts,
        feedback,
        per_student_data: true,
      });
      await qc.invalidateQueries({ queryKey: ['aula', 'assignments', courseId] });
      onDone();
    } catch (err) {
      setError(errText(err));
    }
  };
  return (
    <form className="aula-editor" onSubmit={send} data-testid="assignment-editor">
      <div className="field">
        <label htmlFor="aula-a-title">{T.title}</label>
        <input
          id="aula-a-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
      </div>
      <div className="field">
        <label htmlFor="aula-a-desc">{T.description}</label>
        <textarea
          id="aula-a-desc"
          rows={2}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
      </div>
      <div className="aula-filters">
        <div className="field">
          <label htmlFor="aula-a-due">{T.due}</label>
          <input
            id="aula-a-due"
            type="datetime-local"
            value={due}
            onChange={(e) => setDue(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="aula-a-att">{T.attempts}</label>
          <input
            id="aula-a-att"
            type="number"
            min={1}
            max={20}
            value={attempts}
            onChange={(e) => setAttempts(Number(e.target.value))}
          />
        </div>
        <div className="field">
          <label htmlFor="aula-a-fb">{T.feedback}</label>
          <select
            id="aula-a-fb"
            value={feedback}
            onChange={(e) => setFeedback(e.target.value as 'immediate' | 'after_due')}
          >
            <option value="immediate">{T.immediate}</option>
            <option value="after_due">{T.afterDue}</option>
          </select>
        </div>
      </div>
      <p className="help">{T.chosen(items.length)}</p>
      <div className="field">
        <label htmlFor="aula-a-ch">{T.chapter}</label>
        <select id="aula-a-ch" value={chapter} onChange={(e) => setChapter(e.target.value)}>
          <option value="">{T.all}</option>
          {chapters.map((c) => (
            <option key={c} value={c}>
              {chapterLabel(c)}
            </option>
          ))}
        </select>
      </div>
      <fieldset className="aula-pick">
        <legend>{T.exercises}</legend>
        {(exercises.data ?? [])
          .filter((e) => !chapter || e.chapter === chapter)
          .map((e) => (
            <label key={e.id} className="check-row">
              <input
                type="checkbox"
                checked={has('exercise', e.id)}
                onChange={() => toggle('exercise', e.id)}
              />
              {e.title} <span className="badge">{levelLabel(e.level)}</span>
            </label>
          ))}
      </fieldset>
      <fieldset className="aula-pick">
        <legend>{T.labs}</legend>
        {(labs.data ?? [])
          .filter((l) => !chapter || l.chapter === chapter)
          .map((l) => (
            <label key={l.id} className="check-row">
              <input
                type="checkbox"
                checked={has('lab', l.id)}
                onChange={() => toggle('lab', l.id)}
              />
              {l.title} <span className="badge accent">{T.steps(l.steps)}</span>
            </label>
          ))}
      </fieldset>
      <div className="calc-row">
        <button type="submit" className="btn primary" disabled={!title.trim() || !items.length}>
          {T.create}
        </button>
        <button type="button" className="btn ghost" onClick={onDone}>
          {T.cancel}
        </button>
      </div>
      {error && <p className="alert error">{error}</p>}
    </form>
  );
}

function GradesView({ a, onBack }: { a: Assignment; onBack: () => void }) {
  const T = useT().classroom.teacher.grades;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['aula', 'grades', a.id], queryFn: () => classroom.grades(a.id) });
  const [review, setReview] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const download = async (fn: () => Promise<Blob>, name: string) => {
    setError(null);
    try {
      downloadBlob(await fn(), name);
    } catch (err) {
      setError(errText(err));
    }
  };
  const remove = async () => {
    if (!window.confirm(T.confirmDelete(a.title))) return;
    await classroom.deleteAssignment(a.id);
    await qc.invalidateQueries({ queryKey: ['aula', 'assignments', a.course_id] });
    onBack();
  };
  const g = q.data;
  return (
    <div className="aula-grades" data-testid="grades">
      <button type="button" className="btn ghost small" onClick={onBack}>
        {T.back}
      </button>
      <h4>{a.title}</h4>
      <div className="calc-row">
        <button
          type="button"
          className="btn small"
          onClick={() =>
            void download(() => classroom.gradesExport(a.id, 'xlsx'), T.excelFile(a.id))
          }
        >
          {T.excel}
        </button>
        <button
          type="button"
          className="btn small"
          onClick={() =>
            void download(
              () => classroom.sheet(a.id, { format: 'pdf', key: false, allStudents: true }),
              T.sheetsFile(a.id),
            )
          }
        >
          {T.sheets}
        </button>
        <button
          type="button"
          className="btn small"
          onClick={() =>
            void download(
              () => classroom.sheet(a.id, { format: 'pdf', key: true, allStudents: true }),
              T.keyFile(a.id),
            )
          }
        >
          {T.key}
        </button>
        <button type="button" className="btn ghost small" onClick={() => void remove()}>
          {T.delete}
        </button>
      </div>
      {(q.error || error) && <p className="alert error">{q.error?.message ?? error}</p>}
      {g && (
        <div className="table-scroll">
          <table className="data">
            <thead>
              <tr>
                <th>{T.student}</th>
                {g.assignment.items.map((it, i) => (
                  <th key={i} className="num" title={it.title}>
                    {i + 1}. {it.kind === 'lab' ? T.lab : T.exercise}
                  </th>
                ))}
                <th className="num">
                  {T.points(fmtNum(g.total_points, { maximumFractionDigits: 2 }))}
                </th>
              </tr>
            </thead>
            <tbody>
              {g.rows.map((r) => (
                <tr key={r.student.id}>
                  <th scope="row">{r.student.display_name}</th>
                  {r.cells.map((c) => (
                    <td key={c.item} className="num">
                      {c.submission_id ? (
                        <button
                          type="button"
                          className={`btn ghost small${c.needs_review ? ' aula-review' : ''}`}
                          title={c.needs_review ? T.needsReview : T.view}
                          onClick={() => setReview(c.submission_id)}
                        >
                          {pct(c.score)}
                          {c.needs_review ? ' ✎' : ''}
                        </button>
                      ) : (
                        '—'
                      )}
                    </td>
                  ))}
                  <td className="num">{fmtNum(r.points, { maximumFractionDigits: 2 })}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!g.rows.length && <p className="empty">{T.noStudents}</p>}
        </div>
      )}
      {review !== null && (
        <Review
          id={review}
          onClose={() => {
            setReview(null);
            void qc.invalidateQueries({ queryKey: ['aula', 'grades', a.id] });
          }}
        />
      )}
    </div>
  );
}

interface Answer {
  key?: string;
  id?: string;
  ok: boolean | null;
  given?: string | null;
  expected_text?: string | null;
  message: string;
}

function Review({ id, onClose }: { id: number; onClose: () => void }) {
  // Diálogo de revisión: toma el foco al abrirse, se cierra con Esc y devuelve el foco al botón
  // que lo abrió.
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    box.current?.focus();
    return () => opener?.focus();
  }, []);
  const T = useT().classroom.teacher.review;
  const q = useQuery({
    queryKey: ['aula', 'submission', id],
    queryFn: () => classroom.submission(id),
  });
  const [score, setScore] = useState<string>('');
  const [comment, setComment] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const s = q.data;
  const save = async () => {
    setError(null);
    try {
      const n = score.trim() === '' ? null : parseNumber(score);
      const v = n === null ? null : n / 100;
      await classroom.review(id, v, comment ?? s?.comment ?? '');
      onClose();
    } catch (err) {
      setError(errText(err));
    }
  };
  const result = (s?.result ?? {}) as {
    answers?: Answer[];
    steps?: Record<string, { done: boolean; questions: Answer[] }>;
  };
  return (
    <div
      ref={box}
      className="card card-pad aula-review-box"
      role="dialog"
      aria-label={T.label}
      tabIndex={-1}
      onKeyDown={(e) => {
        if (e.key === 'Escape') onClose();
      }}
    >
      {q.error && <p className="alert error">{q.error.message}</p>}
      {s && (
        <>
          <h4>
            {s.student?.display_name} · {s.item_info.title} · {T.attempt(s.attempt)}
          </h4>
          <p className="help">{T.auto(pct(s.auto_score), fmtDate(s.created_at))}</p>
          {result.answers && (
            <ul className="lab-checks">
              {result.answers.map((x) => (
                <li key={x.key} className={x.ok ? 'ok' : 'bad'}>
                  {x.ok ? '✓' : '✗'} {x.key}: {x.given ?? '—'} {T.expected(x.expected_text ?? '')}
                </li>
              ))}
            </ul>
          )}
          {result.steps &&
            Object.entries(result.steps).map(([step, v]) => (
              <div key={step} className="aula-step">
                <strong>
                  {v.done ? '✓' : '✗'} {T.step(step)}
                </strong>
                <ul className="lab-checks">
                  {v.questions.map((x) => (
                    <li key={x.id} className={x.ok === null ? '' : x.ok ? 'ok' : 'bad'}>
                      {x.ok === null ? '✎' : x.ok ? '✓' : '✗'} {x.id}: {x.given ?? '—'}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          <div className="aula-filters">
            <div className="field">
              <label htmlFor="aula-rev-score">{T.score}</label>
              <input
                id="aula-rev-score"
                inputMode="decimal"
                placeholder={
                  s.teacher_score != null ? String(Math.round(s.teacher_score * 100)) : ''
                }
                value={score}
                onChange={(e) => setScore(e.target.value)}
              />
            </div>
          </div>
          <div className="field">
            <label htmlFor="aula-rev-comment">{T.comment}</label>
            <textarea
              id="aula-rev-comment"
              rows={2}
              value={comment ?? s.comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
          <div className="calc-row">
            <button type="button" className="btn primary" onClick={() => void save()}>
              {T.save}
            </button>
            <button type="button" className="btn ghost" onClick={onClose}>
              {T.close}
            </button>
          </div>
          {error && <p className="alert error">{error}</p>}
        </>
      )}
    </div>
  );
}

function Invites() {
  const T = useT().classroom.teacher.invites;
  const qc = useQueryClient();
  const q = useQuery({ queryKey: ['aula', 'invites'], queryFn: () => classroom.invites() });
  const [error, setError] = useState<string | null>(null);
  const create = async () => {
    setError(null);
    try {
      await classroom.createInvites(1, 30);
      await qc.invalidateQueries({ queryKey: ['aula', 'invites'] });
    } catch (err) {
      setError(errText(err));
    }
  };
  return (
    <section className="card card-pad" aria-label={T.title}>
      <h3 className="section-title">
        {T.title}
        <button type="button" className="btn small" onClick={() => void create()}>
          {T.create}
        </button>
      </h3>
      <ul className="aula-invites">
        {(q.data ?? []).map((i) => (
          <li key={i.code}>
            <code>{i.code}</code>{' '}
            {i.used_by ? T.usedBy(i.used_by) : T.expires(fmtDate(i.expires_at))}
          </li>
        ))}
      </ul>
      {error && <p className="alert error">{error}</p>}
    </section>
  );
}
