import { useId, useRef, type KeyboardEvent, type ReactNode } from 'react';

export interface TabDef {
  id: string;
  label: ReactNode;
}

interface Props {
  tabs: TabDef[];
  active: string;
  onChange: (id: string) => void;
  label: string;
  children: ReactNode;
}

/** Pestañas accesibles (patrón WAI-ARIA con activación automática y flechas). */
export function Tabs({ tabs, active, onChange, label, children }: Props) {
  const base = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const idx = Math.max(
    0,
    tabs.findIndex((t) => t.id === active),
  );

  const onKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    let next = -1;
    if (e.key === 'ArrowRight') next = (idx + 1) % tabs.length;
    else if (e.key === 'ArrowLeft') next = (idx - 1 + tabs.length) % tabs.length;
    else if (e.key === 'Home') next = 0;
    else if (e.key === 'End') next = tabs.length - 1;
    if (next < 0) return;
    e.preventDefault();
    const t = tabs[next];
    if (!t) return;
    onChange(t.id);
    refs.current[next]?.focus();
  };

  return (
    <>
      <div className="tablist" role="tablist" aria-label={label}>
        {tabs.map((t, i) => (
          <button
            key={t.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            id={`${base}-tab-${t.id}`}
            role="tab"
            type="button"
            className="tab"
            aria-selected={t.id === active}
            aria-controls={`${base}-panel`}
            tabIndex={t.id === active ? 0 : -1}
            onClick={() => onChange(t.id)}
            onKeyDown={onKey}
            data-tab={t.id}
          >
            {t.label}
          </button>
        ))}
      </div>
      <div
        className="tabpanel"
        role="tabpanel"
        id={`${base}-panel`}
        aria-labelledby={`${base}-tab-${active}`}
        tabIndex={0}
      >
        {children}
      </div>
    </>
  );
}
