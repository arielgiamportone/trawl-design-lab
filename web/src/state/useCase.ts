import { useContext } from 'react';
import { CaseContext, type CaseContextValue } from './context';

export function useCase(): CaseContextValue {
  const v = useContext(CaseContext);
  if (!v) throw new Error('useCase debe usarse dentro de <CaseProvider>');
  return v;
}
