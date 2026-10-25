import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { api } from '../../api/client';
import { downloadBlob } from '../../lib/download';
import {
  bomCsv,
  loadPrices,
  priceKey,
  savePrices,
  UNIT_LABEL,
  type Bom,
  type BomLine,
  type Price,
} from '../../lib/components';
import { fmt, parseNumber } from '../../lib/format';
import { useCase } from '../../state/useCase';

/**
 * Lista de materiales del caso: qué comprar, cuánto y el costo orientativo, para llevar al
 * proveedor (CSV o impresión/PDF). Los precios que carga el usuario quedan en el navegador.
 */
export function BillOfMaterials() {
  const { committed } = useCase();
  const [prices, setPrices] = useState<Record<string, Price>>(() => loadPrices());
  const [currency, setCurrency] = useState<string>(
    () => Object.values(loadPrices())[0]?.currency ?? 'USD',
  );
  const body = useMemo(() => (committed ? { ...committed, prices } : null), [committed, prices]);
  const q = useQuery({
    queryKey: ['bom', body],
    queryFn: ({ signal }) => api.bom(body!, signal) as Promise<Bom>,
    enabled: body !== null,
    placeholderData: (prev) => prev,
  });

  const setPrice = (line: BomLine, text: string) => {
    const key = priceKey(line);
    const value = parseNumber(text);
    const next = { ...prices };
    if (value === null || value < 0) delete next[key];
    else
      next[key] = {
        value,
        currency,
        unit: line.unit as Price['unit'],
        date: new Date().toISOString().slice(0, 7),
        source: 'usuario',
      };
    setPrices(next);
    savePrices(next);
  };

  const bom = q.data;
  return (
    <div className="bom" data-testid="bom">
      <p className="section-sub">
        Cantidades del armado calculado. Cargue el precio que le dan en su puerto: queda guardado en
        este navegador y se usa en el armado por costo. Sin precio, la línea dice «sin precio» (no
        se cuenta como cero).
      </p>
      <div className="catalog-actions no-print">
        <label className="inline-field">
          Moneda
          <input
            aria-label="Moneda"
            value={currency}
            maxLength={3}
            size={4}
            onChange={(e) => setCurrency(e.target.value.toUpperCase())}
          />
        </label>
        <button
          type="button"
          className="btn"
          disabled={!bom}
          onClick={() =>
            bom &&
            downloadBlob(
              new Blob([bomCsv(bom)], { type: 'text/csv;charset=utf-8' }),
              'lista_de_materiales.csv',
            )
          }
        >
          Descargar CSV
        </button>
        <button type="button" className="btn" disabled={!bom} onClick={() => window.print()}>
          Imprimir o guardar PDF
        </button>
      </div>
      {!committed && <p className="empty">Complete el caso para ver la lista de materiales.</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {bom && (
        <div className="table-wrap">
          <table className="data" aria-label="Lista de materiales">
            <thead>
              <tr>
                <th scope="col">Ítem</th>
                <th scope="col">Componente</th>
                <th scope="col" className="num">
                  Cantidad
                </th>
                <th scope="col" className="num">
                  Precio unitario
                </th>
                <th scope="col" className="num">
                  Costo
                </th>
              </tr>
            </thead>
            <tbody>
              {bom.lines.map((l) => (
                <tr key={l.key} data-line={l.key}>
                  <td>
                    {l.label}
                    {l.note && <p className="help">{l.note}</p>}
                  </td>
                  <td>{l.component_name ?? l.component_id ?? '—'}</td>
                  <td className="num">
                    {fmt(l.quantity)} {UNIT_LABEL[l.unit] ?? l.unit}
                  </td>
                  <td className="num">
                    <input
                      className="price-input"
                      inputMode="decimal"
                      aria-label={`Precio de ${l.label} por ${UNIT_LABEL[l.unit] ?? l.unit}`}
                      defaultValue={prices[priceKey(l)]?.value ?? ''}
                      placeholder={l.unit_price != null ? fmt(l.unit_price) : '—'}
                      onBlur={(e) => setPrice(l, e.target.value)}
                    />
                  </td>
                  <td className="num">
                    {l.cost != null ? (
                      `${fmt(l.cost)} ${l.currency ?? ''}`
                    ) : (
                      <span className="badge">sin precio</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              {Object.entries(bom.totals).map(([cur, v]) => (
                <tr key={cur}>
                  <th scope="row" colSpan={4}>
                    Total orientativo
                  </th>
                  <td className="num" data-testid={`bom-total-${cur}`}>
                    {fmt(v)} {cur}
                  </td>
                </tr>
              ))}
              {bom.missing_prices > 0 && (
                <tr>
                  <td colSpan={5} className="help">
                    {bom.missing_prices} {bom.missing_prices === 1 ? 'línea' : 'líneas'} sin precio:
                    el total no las incluye.
                  </td>
                </tr>
              )}
            </tfoot>
          </table>
        </div>
      )}
    </div>
  );
}
