import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { api, type PlanView, type Variant } from '../api/client';
import { useT } from '../i18n';
import { downloadBlob } from '../lib/download';
import { useCase } from '../state/useCase';
import { ZoomStage } from './ZoomStage';

export function PlanViewer() {
  const { committed, state } = useCase();
  const [view, setView] = useState<PlanView>('sheet');
  const T = useT();
  const P = T.expert.plan;
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
    const name = P.fileName(state.net, variant, view === 'sheet');
    downloadBlob(new Blob([plan.data], { type: 'image/svg+xml' }), name);
  };

  return (
    <div>
      <div className="plan-toolbar">
        <div className="segmented" role="group" aria-label={P.viewLabel}>
          <button type="button" aria-pressed={view === 'sheet'} onClick={() => setView('sheet')}>
            {P.sheet}
          </button>
          <button type="button" aria-pressed={view === 'scale'} onClick={() => setView('scale')}>
            {P.scale}
          </button>
        </div>
        {committed?.net_modified && (
          <div className="segmented" role="group" aria-label={P.variantLabel}>
            <button
              type="button"
              aria-pressed={variant === 'std'}
              onClick={() => setVariant('std')}
            >
              {T.labels.variantsTitle.std}
            </button>
            <button
              type="button"
              aria-pressed={variant === 'mod'}
              onClick={() => setVariant('mod')}
            >
              {T.labels.variantsTitle.mod}
            </button>
          </div>
        )}
        <span style={{ flex: 1 }} />
        <button type="button" className="btn small" onClick={download} disabled={!plan.data}>
          {P.downloadSvg}
        </button>
      </div>
      {plan.isError && (
        <div className="alert error" role="alert">
          {P.error} {plan.error.message}
        </div>
      )}
      <ZoomStage
        key={`${view}-${variant}`}
        svg={plan.data}
        fetching={plan.isFetching}
        alt={P.alt(view === 'sheet' ? P.sheetLower : P.scaleLower, T.labels.variants[variant])}
        label={P.stageLabel}
        testId="plan-image"
        placeholder={<p className="empty">{plan.isFetching ? P.generating : P.none}</p>}
      />
      <p className="help" style={{ marginTop: 8 }}>
        {P.help}
      </p>
    </div>
  );
}
