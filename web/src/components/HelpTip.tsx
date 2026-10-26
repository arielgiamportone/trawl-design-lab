import { useEffect, useId, useRef, useState } from 'react';
import { useT } from '../i18n';
import { chapterUrl } from '../lib/docs';
import { HELP, rangeText } from '../lib/help';
import { unitLabel } from '../lib/units';

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
  const T = useT().expert.helpTip;

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
  const range = rangeText(topic);
  return (
    <span className="helptip" ref={ref}>
      <button
        type="button"
        className="helptip-btn"
        aria-expanded={open}
        aria-controls={id}
        aria-label={T.aria(label)}
        onClick={() => setOpen((o) => !o)}
      >
        ?
      </button>
      {open && (
        <span className="helptip-pop" id={id} role="note">
          {entry.text}
          {(entry.unit || entry.range) && (
            <span className="helptip-meta">
              {entry.unit && T.unit(unitLabel(entry.unit))}
              {range && T.range(range)}
            </span>
          )}
          {url && (
            <a className="helptip-link" href={url} target="_blank" rel="noreferrer">
              {T.read}
            </a>
          )}
        </span>
      )}
    </span>
  );
}
