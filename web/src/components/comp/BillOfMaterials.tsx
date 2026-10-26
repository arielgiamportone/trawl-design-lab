import { useQuery } from '@tanstack/react-query';
import { useMemo, useState } from 'react';
import { api } from '../../api/client';
import { useT } from '../../i18n';
import { downloadBlob } from '../../lib/download';
import {
  bomCsv,
  bomQuantity,
  bomUnitLabel,
  loadPrices,
  priceKey,
  priceToCanonical,
  priceToDisplay,
  savePrices,
  type Bom,
  type BomLine,
  type Price,
} from '../../lib/components';
import { fmt, parseNumber, toInput } from '../../lib/format';
import { useCase } from '../../state/useCase';

/**
 * Lista de materiales del caso: qué comprar, cuánto y el costo orientativo, para llevar al
 * proveedor (CSV o impresión/PDF). Los precios que carga el usuario quedan en el navegador.
 */
export function BillOfMaterials() {
  const { committed } = useCase();
  const T = useT().components;
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
    const shown = parseNumber(text);
    // Se escribe por unidad del sistema activo (por lb, por ft); se guarda por kg o por m.
    const value =
      shown === null ? null : Number(priceToCanonical(shown, line.unit).toPrecision(10));
    const next = { ...prices };
    if (value === null || value < 0) delete next[key];
    else
      next[key] = {
        value,
        currency,
        unit: line.unit as Price['unit'],
        date: new Date().toISOString().slice(0, 7),
        source: T.priceSource,
      };
    setPrices(next);
    savePrices(next);
  };

  const bom = q.data;
  return (
    <div className="bom" data-testid="bom">
      <p className="section-sub">{T.bomIntro}</p>
      <div className="catalog-actions no-print">
        <label className="inline-field">
          {T.currency}
          <input
            aria-label={T.currency}
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
              T.csv.file,
            )
          }
        >
          {T.downloadCsv}
        </button>
        <button type="button" className="btn" disabled={!bom} onClick={() => window.print()}>
          {T.print}
        </button>
      </div>
      {!committed && <p className="empty">{T.bomEmpty}</p>}
      {q.error && (
        <p className="alert crit" role="alert">
          {q.error.message}
        </p>
      )}
      {bom && (
        <div className="table-wrap">
          <table className="data" aria-label={T.bomTable}>
            <thead>
              <tr>
                <th scope="col">{T.colItem}</th>
                <th scope="col">{T.colComponent}</th>
                <th scope="col" className="num">
                  {T.colQuantity}
                </th>
                <th scope="col" className="num">
                  {T.colUnitPrice}
                </th>
                <th scope="col" className="num">
                  {T.colCost}
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
                    {fmt(bomQuantity(l))} {bomUnitLabel(l.unit)}
                  </td>
                  <td className="num">
                    <input
                      className="price-input"
                      inputMode="decimal"
                      aria-label={T.priceOf(l.label, bomUnitLabel(l.unit))}
                      defaultValue={priceText(prices[priceKey(l)]?.value, l.unit)}
                      placeholder={
                        l.unit_price != null ? fmt(priceToDisplay(l.unit_price, l.unit)) : '—'
                      }
                      onBlur={(e) => setPrice(l, e.target.value)}
                    />
                  </td>
                  <td className="num">
                    {l.cost != null ? (
                      `${fmt(l.cost)} ${l.currency ?? ''}`
                    ) : (
                      <span className="badge">{T.noPrice}</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              {Object.entries(bom.totals).map(([cur, v]) => (
                <tr key={cur}>
                  <th scope="row" colSpan={4}>
                    {T.total}
                  </th>
                  <td className="num" data-testid={`bom-total-${cur}`}>
                    {fmt(v)} {cur}
                  </td>
                </tr>
              ))}
              {bom.missing_prices > 0 && (
                <tr>
                  <td colSpan={5} className="help">
                    {T.missingLines(bom.missing_prices)}
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

/** Precio guardado (por kg o por m) en el campo, por unidad del sistema activo. */
function priceText(value: number | undefined, unit: string): string | number {
  if (value === undefined) return '';
  const shown = priceToDisplay(value, unit);
  // En métrico, el número tal cual (como siempre); convertido, con 6 cifras significativas.
  return shown === value ? value : toInput(Number(shown.toPrecision(6)));
}
