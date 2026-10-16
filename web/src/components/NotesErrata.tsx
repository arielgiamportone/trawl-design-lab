import { errataStatus, type ErrataStatus } from '../lib/errata';
import { useCase } from '../state/useCase';

const TONE: Record<ErrataStatus, string> = {
  corregida: 'good',
  reproducida: 'warn',
  documentada: 'accent',
};

export function NotesErrata() {
  const { design, catalogs, state } = useCase();
  const d = design.data;
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
          Notas del cálculo
        </h2>
        {d ? (
          d.notes.length ? (
            <ul className="notes" style={{ marginTop: 8 }}>
              {d.notes.map((n, i) => (
                <li key={i}>{n}</li>
              ))}
            </ul>
          ) : (
            <p className="help">El motor no dejó notas para este caso.</p>
          )
        ) : (
          <p className="help">Sin resultados todavía.</p>
        )}
      </section>
      <section aria-labelledby="erratas-title">
        <h2 className="section-title" id="erratas-title">
          Erratas del libro Excel original
        </h2>
        <p className="section-sub" style={{ marginBottom: 8 }}>
          Modo actual: <strong>{compat === 'excel' ? 'reproducir Excel' : 'corregido'}</strong> ·{' '}
          {counts.corregida} corregidas · {counts.reproducida} reproducidas · {counts.documentada}{' '}
          documentadas.
        </p>
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th scope="col">Errata</th>
                <th scope="col">Hoja · celda</th>
                <th scope="col">En este caso</th>
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
                    <span className={`badge ${TONE[e.status]}`}>{e.status}</span>
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
