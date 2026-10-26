import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { api, type ExerciseSummary, type LabSummary } from '../../api/client';
import { useT } from '../../i18n';
import { chapterLabel, levelLabel, levelLabels } from '../../lib/classroom';
import { ExerciseCard } from './ExerciseCard';
import { useBeginLab } from './useBeginLab';

/** Semilla nueva para datos distintos (1 a 2³¹ − 1). */
function newSeed(): number {
  return 1 + Math.floor(Math.random() * 2_000_000_000);
}

/**
 * Práctica libre (sin cuenta y sin conexión): ejercicios del banco con corrección inmediata y
 * laboratorios guiados sobre el caso abierto.
 */
export function Practice() {
  const T = useT().classroom.practice;
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
  const [chapter, setChapter] = useState('');
  const [level, setLevel] = useState('');
  const [open, setOpen] = useState<{ id: string; seed: number } | null>(null);

  const chapters = useMemo(
    () => [...new Set((exercises.data ?? []).map((e) => e.chapter))].sort(),
    [exercises.data],
  );
  const shown = (exercises.data ?? []).filter(
    (e) => (!chapter || e.chapter === chapter) && (!level || e.level === level),
  );

  return (
    <div className="aula-practice" data-testid="practice">
      <p className="section-sub">{T.intro}</p>
      <div className="aula-filters">
        <div className="field">
          <label htmlFor="aula-ch">{T.chapter}</label>
          <select id="aula-ch" value={chapter} onChange={(e) => setChapter(e.target.value)}>
            <option value="">{T.all}</option>
            {chapters.map((c) => (
              <option key={c} value={c}>
                {chapterLabel(c)}
              </option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="aula-lv">{T.level}</label>
          <select id="aula-lv" value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">{T.all}</option>
            {Object.entries(levelLabels()).map(([k, v]) => (
              <option key={k} value={k}>
                {v}
              </option>
            ))}
          </select>
        </div>
      </div>
      {exercises.error && (
        <p className="alert error" role="alert">
          {exercises.error.message}
        </p>
      )}
      {open ? (
        <OpenExercise
          key={`${open.id}:${open.seed}`}
          id={open.id}
          seed={open.seed}
          onNew={() => setOpen({ id: open.id, seed: newSeed() })}
          onBook={() => setOpen({ id: open.id, seed: 0 })}
          onBack={() => setOpen(null)}
        />
      ) : (
        <ExerciseList items={shown} onOpen={(id) => setOpen({ id, seed: newSeed() })} />
      )}
      <h3 className="section-title aula-h">{T.labsTitle}</h3>
      <LabList items={(labs.data ?? []).filter((l) => !chapter || l.chapter === chapter)} />
    </div>
  );
}

function ExerciseList({
  items,
  onOpen,
}: {
  items: ExerciseSummary[];
  onOpen: (id: string) => void;
}) {
  const T = useT().classroom.practice;
  if (!items.length) return <p className="empty">{T.noExercises}</p>;
  return (
    <ul className="aula-list" aria-label={T.exercisesLabel}>
      {items.map((e) => (
        <li key={e.id}>
          <button type="button" className="aula-row" onClick={() => onOpen(e.id)}>
            <span className="aula-row-title">{e.title}</span>
            <span className="badge">{levelLabel(e.level)}</span>
            <span className="aula-row-sub">{chapterLabel(e.chapter)}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

function OpenExercise({
  id,
  seed,
  onNew,
  onBook,
  onBack,
}: {
  id: string;
  seed: number;
  onNew: () => void;
  onBook: () => void;
  onBack: () => void;
}) {
  const T = useT().classroom.practice;
  const q = useQuery({
    queryKey: ['teaching', 'exercise', id, seed],
    queryFn: ({ signal }) => api.exercise(id, seed, signal),
    staleTime: Infinity,
  });
  return (
    <div className="aula-open">
      <div className="calc-row">
        <button type="button" className="btn ghost small" onClick={onBack}>
          {T.allExercises}
        </button>
        <button type="button" className="btn small" onClick={onNew}>
          {T.newData}
        </button>
        <button type="button" className="btn small" onClick={onBook} disabled={seed === 0}>
          {T.bookData}
        </button>
      </div>
      {q.error && (
        <p className="alert error" role="alert">
          {q.error.message}
        </p>
      )}
      {q.data && (
        <ExerciseCard
          ex={q.data}
          onSubmit={(answers) => api.grade(id, seed, answers)}
          footer={seed === 0 ? T.bookSeed : T.seed(seed)}
        />
      )}
    </div>
  );
}

function LabList({ items }: { items: LabSummary[] }) {
  const T = useT().classroom.practice;
  const beginLab = useBeginLab();
  const [error, setError] = useState<string | null>(null);
  const begin = async (id: string) => {
    setError(null);
    try {
      await beginLab(id, { kind: 'practice' });
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  };
  return (
    <>
      <ul className="aula-list" aria-label={T.labsLabel}>
        {items.map((l) => (
          <li key={l.id} className="aula-lab">
            <div>
              <span className="aula-row-title">{l.title}</span>{' '}
              <span className="badge">{levelLabel(l.level)}</span>
              <p className="aula-row-sub">
                {l.summary} {T.steps(l.steps)} · {chapterLabel(l.chapter)}
              </p>
            </div>
            <button type="button" className="btn small" onClick={() => void begin(l.id)}>
              {T.start}
            </button>
          </li>
        ))}
      </ul>
      {error && (
        <p className="alert error" role="alert">
          {error}
        </p>
      )}
    </>
  );
}
