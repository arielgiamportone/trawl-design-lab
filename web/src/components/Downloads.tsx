import { useState } from 'react';
import { api, type ReportFormat } from '../api/client';
import { downloadBlob } from '../lib/download';
import { useCase } from '../state/useCase';

const ITEMS: { format: ReportFormat | 'json'; title: string; desc: string }[] = [
  {
    format: 'html',
    title: 'Informe HTML',
    desc: 'Informe completo navegable, con tablas y planos.',
  },
  { format: 'pdf', title: 'Informe PDF', desc: 'El mismo informe listo para imprimir o archivar.' },
  {
    format: 'xlsx',
    title: 'Planilla XLSX',
    desc: 'Todas las tablas en hojas de cálculo, con números editables.',
  },
  {
    format: 'json',
    title: 'Resultado JSON',
    desc: 'Respuesta completa de la API (caso, resumen, notas y etapas).',
  },
];

export function Downloads() {
  const { committed, design, state } = useCase();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const base = `trawl-${state.net}${state.netModified ? '-vs-mod' : ''}-${state.compat}`;

  const run = async (format: ReportFormat | 'json') => {
    setError(null);
    if (format === 'json') {
      if (!design.data) return;
      downloadBlob(
        new Blob([JSON.stringify(design.data, null, 2)], { type: 'application/json' }),
        `${base}.json`,
      );
      return;
    }
    if (!committed) return;
    setBusy(format);
    try {
      const blob = await api.report(committed, format);
      downloadBlob(blob, `${base}.${format}`);
    } catch (e) {
      setError(`No se pudo generar el informe ${format.toUpperCase()}: ${(e as Error).message}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <h2 className="section-title">Descargas</h2>
      <p className="section-sub" style={{ marginBottom: 12 }}>
        Los informes se generan en el servidor con el caso actual (incluidas las ediciones de
        paneles y parámetros).
      </p>
      <div className="downloads">
        {ITEMS.map((it) => (
          <div className="download-card" key={it.format}>
            <h3>{it.title}</h3>
            <p>{it.desc}</p>
            <button
              type="button"
              className="btn"
              onClick={() => void run(it.format)}
              disabled={busy !== null || (it.format === 'json' ? !design.data : !committed)}
              data-download={it.format}
            >
              {busy === it.format ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Generando…
                </>
              ) : (
                `Descargar .${it.format}`
              )}
            </button>
          </div>
        ))}
      </div>
      <div role="status" aria-live="polite">
        {error && <div className="alert error">{error}</div>}
      </div>
    </div>
  );
}
