import type { Messages } from '../es';

export const state: Messages['state'] = {
  batchLabel: 'batch',
  corrected: 'corrected',
  outsideProvider: 'useCase must be used inside <CaseProvider>',
  projects: {
    untitled: 'Untitled project',
    notJson: 'The file is not valid JSON.',
    notProject: 'It is not a trawl-design-lab project.',
    badVersion: (v: string) => `Unsupported project version (${v}).`,
    imported: 'Imported project',
    slug: 'project',
  },
};
