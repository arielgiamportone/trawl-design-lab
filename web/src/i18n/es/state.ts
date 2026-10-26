/** Textos de «state». */
export const state = {
  batchLabel: 'lote',
  corrected: 'corregido',
  outsideProvider: 'useCase debe usarse dentro de <CaseProvider>',
  projects: {
    untitled: 'Proyecto sin nombre',
    notJson: 'El archivo no es JSON válido.',
    notProject: 'No es un proyecto de trawl-design-lab.',
    badVersion: (v: string) => `Versión de proyecto no soportada (${v}).`,
    imported: 'Proyecto importado',
    slug: 'proyecto',
  },
};
