import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api, type PlanView, type Variant } from '../api/client';
import { downloadBlob } from '../lib/download';
import { useCase } from '../state/useCase';
import { ZoomStage } from './ZoomStage';

export function PlanViewer() {
  const { committed, state } = useCase();
  const [view, setView] = useState<PlanView>('sheet');
  const [variantSel, setVariant] = useState<Variant>('std');
  const variant: Variant = committed?.net_modified ? variantSel : 'std';
  const plan = useQuery({
    queryKey: ['plan', view, variant, committed],
    queryFn: ({ signal }) => api.plan(committed!, view, variant, signal),
    enabled: committed !== null,
    staleTime: 5 * 60_000,
    retry: false,
  });

  const download = () => {
    if (!plan.data) return;
    const name = `plano-${state.net}-${variant}-${view === 'sheet' ? 'lamina' : 'escala'}.svg`;
    downloadBlob(new Blob([plan.data], { type: 'image/svg+xml' }), name);
  };

  return (
    <div>
      <div className="plan-toolbar">
        <div className="segmented" role="group" aria-label="Tipo de plano">
          <button type="button" aria-pressed={view === 'sheet'} onClick={() => setView('sheet')}>
            Lámina técnica
          </button>
          <button type="button" aria-pressed={view === 'scale'} onClick={() => setView('scale')}>
            Escala real
          </button>
        </div>
        {committed?.net_modified && (
          <div className="segmented" role="group" aria-label="Variante de red">
            <button
              type="button"
              aria-pressed={variant === 'std'}
              onClick={() => setVariant('std')}
            >
              Estándar
            </button>
            <button
              type="button"
              aria-pressed={variant === 'mod'}
              onClick={() => setVariant('mod')}
            >
              Modificada
            </button>
          </div>
        )}
        <span style={{ flex: 1 }} />
        <button type="button" className="btn small" onClick={download} disabled={!plan.data}>
          Descargar SVG
        </button>
      </div>
      {plan.isError && (
        <div className="alert error" role="alert">
          No se pudo generar el plano: {plan.error.message}
        </div>
      )}
      <ZoomStage
        key={`${view}-${variant}`}
        svg={plan.data}
        fetching={plan.isFetching}
        alt={`Plano de la red (${view === 'sheet' ? 'lámina técnica' : 'escala real'}, ${variant === 'std' ? 'estándar' : 'modificada'})`}
        label="Plano de la red. Arrastre para desplazar, rueda o teclas + y − para acercar, 0 para restablecer."
        testId="plan-image"
        placeholder={
          <p className="empty">{plan.isFetching ? 'Generando plano…' : 'Sin plano todavía.'}</p>
        }
      />
      <p className="help" style={{ marginTop: 8 }}>
        Arrastre para desplazar; rueda del ratón o pellizco para acercar; doble clic o «0» para
        restablecer.
      </p>
    </div>
  );
}
