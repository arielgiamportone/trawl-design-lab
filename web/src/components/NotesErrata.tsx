import { useT } from '../i18n';
import { errataStatus, errataStatusLabel, type ErrataStatus } from '../lib/errata';
import { useCase } from '../state/useCase';

const TONE: Record<ErrataStatus, string> = {
  corregida: 'good',
  reproducida: 'warn',
  documentada: 'accent',
};

export function NotesErrata() {
  const { design, catalogs, state } = useCase();
  const d = design.data;
  const T = useT().expert.notes;
  const compat = d?.case.compat ?? state.compat;
  const counts = { corregida: 0, reproducida: 0, documentada: 0 };
  const rows = catalogs.errata.map((e) => {
    const s = errataStatus(e.key, compat);
    counts[s.status] += 1;
    return { ...e, ...s };
  });

  return (
    <div className="row-gap">
      <section aria-labelledby="notas-title">
        <h2 className="section-title" id="notas-title">
          {T.title}
        </h2>
        {d ? (
          d.notes.length ? (
            <ul className="notes" style={{ marginTop: 8 }}>
              {d.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          ) : (
            <p className="help">{T.none}</p>
          )
        ) : (
          <p className="help">{T.noResults}</p>
        )}
      </section>
      <section aria-labelledby="erratas-title">
        <h2 className="section-title" id="erratas-title">
          {T.errataTitle}
        </h2>
        <p className="section-sub" style={{ marginBottom: 8 }}>
          {T.mode} <strong>{compat === 'excel' ? T.modeExcel : T.modeCorrected}</strong> ·{' '}
          {T.counts(counts.corregida, counts.reproducida, counts.documentada)}
        </p>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">{T.errata}</th>
                <th scope="col">{T.sheetCell}</th>
                <th scope="col">{T.inThisCase}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.key} data-errata={e.key}>
                  <td>
                    {e.description}
                    <div className="mono help">{e.key}</div>
                  </td>
                  <td>
                    {e.sheet}
                    <div className="mono help">{e.cell}</div>
                  </td>
                  <td>
                    <span className={`badge ${TONE[e.status]}`}>{errataStatusLabel(e.status)}</span>
                    <div className="help">{e.note}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
