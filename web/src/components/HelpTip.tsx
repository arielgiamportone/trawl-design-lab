import { useEffect, useId, useRef, useState } from 'react';
import { chapterUrl } from '../lib/docs';
import { HELP } from '../lib/help';

interface Props {
  /** Clave de ``HELP``. */
  topic: string;
  /** Nombre accesible del dato («Profundidad de trabajo»). */
  label: string;
}

/** Botón «?» con la explicación, unidad, rango habitual y enlace al capítulo del libro. */
export function HelpTip({ topic, label }: Props) {
  const entry = HELP[topic];
  const [open, setOpen] = useState(false);
  const id = useId();
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  if (!entry) return null;
  const url = entry.chapter ? chapterUrl(entry.chapter) : null;
  const f = (n: number) => n.toLocaleString('es-AR');
  return (
    <span className="helptip" ref={ref}>
      <button
        type="button"
        className="helptip-btn"
        aria-expanded={open}
        aria-controls={id}
        aria-label={`Ayuda: ${label}`}
        onClick={() => setOpen((o) => !o)}
      >
        ?
      </button>
      {open && (
        <span className="helptip-pop" id={id} role="note">
          {entry.text}
          {(entry.unit || entry.range) && (
            <span className="helptip-meta">
              {entry.unit && <>Unidad: {entry.unit}. </>}
              {entry.range && (
                <>
                  Rango habitual: {f(entry.range[0])}–{f(entry.range[1])}
                  {entry.unit ? ` ${entry.unit}` : ''}.
                </>
              )}
            </span>
          )}
          {url && (
            <a className="helptip-link" href={url} target="_blank" rel="noreferrer">
              Leer en el libro ↗
            </a>
          )}
        </span>
      )}
    </span>
  );
}
