import { useContext } from 'react';
import { msg } from '../i18n';
import { CaseContext, type CaseContextValue } from './context';

export function useCase(): CaseContextValue {
  const v = useContext(CaseContext);
  if (!v) throw new Error(msg().state.outsideProvider);
  return v;
}
