import { useCallback } from 'react';
import { api } from '../../api/client';
import { caseFromStart, startLab, type ActiveLab } from '../../lib/lab';
import { goToMode } from '../../lib/mode';
import { goToTab } from '../../lib/tabs';
import { useCase } from '../../state/useCase';

/** Empieza un laboratorio: carga su caso de partida, lo marca en curso y abre la app. */
export function useBeginLab(): (labId: string, source: ActiveLab['source']) => Promise<void> {
  const { replace } = useCase();
  return useCallback(
    async (labId, source) => {
      const lab = await api.lab(labId);
      replace(caseFromStart(lab.start));
      startLab(labId, source);
      const first = lab.step_list[0];
      if (first?.target.tab) goToTab(first.target.tab);
      goToMode(first?.target.mode === 'simple' ? 'simple' : 'expert');
    },
    [replace],
  );
}
