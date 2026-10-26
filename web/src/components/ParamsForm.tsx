import { useId, useMemo, useState } from 'react';
import { useT } from '../i18n';
import { checkRange, HELP } from '../lib/help';
import { defaultText, paramLabel, parseParam, useUnitText, type ParamMeta } from '../lib/params';
import { useCase } from '../state/useCase';
import { HelpTip } from './HelpTip';

export function ParamsForm() {
  const { state, update, catalogs, errors } = useCase();
  const [filter, setFilter] = useState('');
  const ids = useId();
  const T = useT().expert.params;
  const metas = catalogs.params;
  const changed = Object.entries(state.params).filter(([, v]) => v.trim() !== '').length;
  const nErr = Object.keys(errors).filter((k) => k.startsWith('param.')).length;

  const shown = useMemo(() => {
    const f = filter.trim().toLowerCase();
    if (!f) return metas;
    return metas.filter(
      (m) =>
        m.name.toLowerCase().includes(f) ||
        paramLabel(m.name).toLowerCase().includes(f) ||
        m.comment.toLowerCase().includes(f),
    );
  }, [metas, filter]);

  const set = (name: string, value: string) =>
    update((s) => ({ ...s, params: { ...s.params, [name]: value } }));
  const resetOne = (name: string) =>
    update((s) => {
      const next = { ...s.params };
      delete next[name];
      return { ...s, params: next };
    });

  return (
    <details className="accordion" open={nErr > 0 ? true : undefined}>
      <summary>
        <span>{T.title}</span>
        <span style={{ display: 'inline-flex', gap: 6 }}>
          {nErr > 0 && <span className="badge crit">{T.withError(nErr)}</span>}
          {changed > 0 && <span className="badge accent">{T.changed(changed)}</span>}
        </span>
      </summary>
      <div className="accordion-body">
        <p className="help" style={{ marginBottom: 8 }}>
          {T.intro}
        </p>
        <div className="param-row" style={{ marginBottom: 6 }}>
          <input
            type="search"
            placeholder={T.searchPlaceholder}
            aria-label={T.searchLabel}
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          {changed > 0 && (
            <button type="button" className="btn small" onClick={() => update({ params: {} })}>
              {T.resetAll}
            </button>
          )}
        </div>
        {metas.length === 0 && <p className="help">{T.loading}</p>}
        {shown.map((m) => (
          <ParamField
            key={m.name}
            meta={m}
            idBase={`${ids}-${m.name}`}
            value={state.params[m.name] ?? ''}
            error={errors[`param.${m.name}`]}
            onChange={(v) => set(m.name, v)}
            onReset={() => resetOne(m.name)}
          />
        ))}
      </div>
    </details>
  );
}

interface FieldProps {
  meta: ParamMeta;
  idBase: string;
  value: string;
  error?: string;
  onChange: (v: string) => void;
  onReset: () => void;
}

export function ParamField({ meta, idBase, value, error, onChange, onReset }: FieldProps) {
  const T = useT().expert.params;
  const [text, setText] = useUnitText(value, meta.unit ?? '', onChange);
  const parsed = parseParam(meta, value);
  const isChanged = value.trim() !== '' && parsed?.ok === true;
  const range = parsed?.ok ? checkRange(meta.name, parsed.value) : { ok: true as const };
  const warnId = `${idBase}-warn`;
  const helpId = `${idBase}-help`;
  const errId = `${idBase}-err`;
  const describedBy =
    [meta.comment ? helpId : '', error ? errId : '', range.ok ? '' : warnId]
      .filter(Boolean)
      .join(' ') || undefined;
  return (
    <div className={`param${isChanged ? ' changed' : ''}`} data-param={meta.name}>
      <div className="param-head">
        <label htmlFor={idBase}>{paramLabel(meta.name)}</label>
        {HELP[meta.name] && <HelpTip topic={meta.name} label={paramLabel(meta.name)} />}
      </div>
      <div className="param-row">
        {meta.kind === 'enum' || meta.kind === 'bool' ? (
          <select
            id={idBase}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            aria-describedby={describedBy}
          >
            <option value="">{T.byDefault(defaultText(meta))}</option>
            {meta.options?.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : (
          <input
            id={idBase}
            type="text"
            inputMode={meta.kind === 'string' || meta.kind === 'strlist' ? 'text' : 'decimal'}
            autoComplete="off"
            spellCheck={false}
            placeholder={defaultText(meta)}
            value={text}
            aria-invalid={error ? true : undefined}
            aria-describedby={describedBy}
            onChange={(e) => setText(e.target.value)}
          />
        )}
        <button
          type="button"
          className="btn small ghost"
          onClick={onReset}
          disabled={value === ''}
          aria-label={T.resetOne(paramLabel(meta.name))}
          title={T.resetTitle}
        >
          ↺
        </button>
      </div>
      {error && (
        <p className="field-error" id={errId}>
          {error}
        </p>
      )}
      {!error && !range.ok && (
        <p className="field-warn" id={warnId}>
          {range.message}
        </p>
      )}
      {meta.comment && (
        <p className="help cell-ref" id={helpId}>
          {meta.comment}
        </p>
      )}
    </div>
  );
}
