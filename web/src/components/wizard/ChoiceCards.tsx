import type { ReactNode } from 'react';

export interface Choice {
  value: string;
  title: ReactNode;
  detail?: ReactNode;
}

interface Props {
  name: string;
  legend: ReactNode;
  choices: Choice[];
  value: string;
  onChange: (value: string) => void;
}

/** Grupo de opciones como tarjetas (radio nativo: teclado y lectores de pantalla). */
export function ChoiceCards({ name, legend, choices, value, onChange }: Props) {
  return (
    <fieldset className="choices">
      <legend>{legend}</legend>
      <div className="choice-grid">
        {choices.map((c) => (
          <label key={c.value} className="choice">
            <input
              type="radio"
              name={name}
              value={c.value}
              checked={value === c.value}
              onChange={() => onChange(c.value)}
            />
            <span className="choice-title">{c.title}</span>
            {c.detail && <span className="choice-detail">{c.detail}</span>}
          </label>
        ))}
      </div>
    </fieldset>
  );
}
