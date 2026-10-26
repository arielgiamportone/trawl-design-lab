import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { msg, useT } from '../../i18n';
import {
  classroom,
  fmtDate,
  pct,
  type AssignmentView,
  type Course,
  type StudentItem,
} from '../../lib/classroom';
import { ExerciseCard, type ExerciseLike, type GradeLike } from './ExerciseCard';
import { useBeginLab } from './useBeginLab';

/** El aula del alumno: sus cursos, las tareas abiertas y cada ítem para resolver y entregar. */
export function StudentView({ courses }: { courses: Course[] }) {
  const T = useT().classroom.student;
  const [courseId, setCourseId] = useState<number | null>(courses[0]?.id ?? null);
  const [assignmentId, setAssignmentId] = useState<number | null>(null);
  const course = courses.find((c) => c.id === courseId) ?? null;
  return (
    <div className="aula-student" data-testid="student-view">
      <div className="aula-courses">
        {courses.map((c) => (
          <button
            key={c.id}
            type="button"
            className="aula-course"
            aria-pressed={c.id === courseId}
            onClick={() => {
              setCourseId(c.id);
              setAssignmentId(null);
            }}
          >
            <strong>{c.name}</strong>
            <span>
              {c.term} · {c.teachers.join(', ')}
            </span>
          </button>
        ))}
        <JoinCourse />
      </div>
      {course && !assignmentId && (
        <AssignmentList courseId={course.id} onOpen={(id) => setAssignmentId(id)} />
      )}
      {assignmentId && <StudentAssignment id={assignmentId} onBack={() => setAssignmentId(null)} />}
      {!courses.length && <p className="empty">{T.noCourses}</p>}
    </div>
  );
}

function JoinCourse() {
  const T = useT().classroom.student;
  const qc = useQueryClient();
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const send = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await classroom.joinCourse(code);
      setCode('');
      await qc.invalidateQueries({ queryKey: ['aula'] });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };
  return (
    <form className="aula-join" onSubmit={send}>
      <label htmlFor="aula-join">{T.joinLabel}</label>
      <div className="calc-row">
        <input
          id="aula-join"
          placeholder={T.codePlaceholder}
          value={code}
          onChange={(e) => setCode(e.target.value)}
        />
        <button type="submit" className="btn small" disabled={!code.trim()}>
          {T.join}
        </button>
      </div>
      {error && <p className="alert error">{error}</p>}
    </form>
  );
}

function AssignmentList({ courseId, onOpen }: { courseId: number; onOpen: (id: number) => void }) {
  const T = useT().classroom.student;
  const q = useQuery({
    queryKey: ['aula', 'assignments', courseId],
    queryFn: () => classroom.assignments(courseId),
  });
  if (q.error) return <p className="alert error">{q.error.message}</p>;
  if (!q.data) return <p className="empty">{T.loading}</p>;
  if (!q.data.length) return <p className="empty">{T.noAssignments}</p>;
  return (
    <ul className="aula-list" aria-label={T.assignmentsLabel}>
      {q.data.map((a) => (
        <li key={a.id}>
          <button type="button" className="aula-row" onClick={() => onOpen(a.id)}>
            <span className="aula-row-title">{a.title}</span>
            {a.closed ? (
              <span className="badge">{T.closed}</span>
            ) : (
              <span className="badge accent">{T.due(fmtDate(a.due_at))}</span>
            )}
            <span className="aula-row-sub">
              {T.submittedOf(a.progress?.submitted ?? 0, a.items.length)}
            </span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function StudentAssignment({ id, onBack }: { id: number; onBack: () => void }) {
  const T = useT().classroom.student;
  const qc = useQueryClient();
  const q = useQuery({
    queryKey: ['aula', 'assignment', id],
    queryFn: () => classroom.assignment(id),
  });
  const a = q.data;
  return (
    <div className="aula-assignment">
      <button type="button" className="btn ghost small" onClick={onBack}>
        {T.back}
      </button>
      {q.error && <p className="alert error">{q.error.message}</p>}
      {a && (
        <>
          <h3 className="section-title">{a.title}</h3>
          {a.description && <p className="section-sub">{a.description}</p>}
          <p className="help">
            {a.due_at ? T.closes(fmtDate(a.due_at)) : ''}
            {T.attempts(a.max_attempts)}{' '}
            {a.feedback === 'after_due' ? T.feedbackAfterDue : T.feedbackImmediate}
          </p>
          {(a.item_list ?? []).map((it) => (
            <StudentItemView
              key={it.index}
              a={a}
              it={it}
              onDone={() => void qc.invalidateQueries({ queryKey: ['aula', 'assignment', id] })}
            />
          ))}
        </>
      )}
    </div>
  );
}

function lastGrade(it: StudentItem): string {
  const T = msg().classroom.student;
  const last = it.submissions[it.submissions.length - 1];
  if (!last) return T.notSubmitted;
  const score = last.teacher_score ?? last.score;
  return score === null || score === undefined
    ? T.submitted
    : `${pct(score)}${last.teacher_score != null ? T.byTeacher : ''}`;
}

function StudentItemView({
  a,
  it,
  onDone,
}: {
  a: AssignmentView;
  it: StudentItem;
  onDone: () => void;
}) {
  const T = useT().classroom.student;
  const beginLab = useBeginLab();
  const [error, setError] = useState<string | null>(null);
  const closed = a.closed || it.attempts_left <= 0;
  const footer = (
    <>
      {T.footer(it.index + 1, it.points, it.attempts_used, a.max_attempts, lastGrade(it))}
      {it.submissions.some((s) => s.comment) &&
        T.comment(it.submissions.filter((s) => s.comment).pop()?.comment ?? '')}
    </>
  );
  if (it.kind === 'exercise' && it.exercise) {
    return (
      <ExerciseCard
        ex={it.exercise as unknown as ExerciseLike}
        submitLabel={closed ? T.noAttempts : T.submit}
        disabled={closed}
        footer={footer}
        onSubmit={async (answers) => {
          const r = await classroom.submit(a.id, it.index, { answers });
          onDone();
          const res = (r.result ?? null) as GradeLike | null;
          return {
            score: r.score,
            answers: res?.answers,
            explanation: res?.explanation,
            message: r.message,
          };
        }}
      />
    );
  }
  return (
    <article className="aula-ex card card-pad" data-testid="lab-item">
      <header className="aula-ex-head">
        <h3>{it.title}</h3>
        <span className="badge accent">{T.labBadge}</span>
      </header>
      <p className="help">{(it.lab as { summary?: string } | null)?.summary}</p>
      <div className="calc-row">
        <button
          type="button"
          className="btn primary"
          disabled={closed}
          onClick={() =>
            void beginLab(it.ref, {
              kind: 'assignment',
              assignmentId: a.id,
              item: it.index,
            }).catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
          }
        >
          {T.doLab}
        </button>
      </div>
      {error && <p className="alert error">{error}</p>}
      <div className="help">{footer}</div>
    </article>
  );
}
