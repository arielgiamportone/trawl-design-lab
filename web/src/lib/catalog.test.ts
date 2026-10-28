import { describe, expect, it } from 'vitest';
import type { CatalogItem } from '../api/client';
import {
  comparisonAfterChange,
  comparisonNets,
  DEFAULT_FILTERS,
  filterNets,
  hpLabel,
  hpMatches,
  kindShares,
  pathLabel,
  proposedComparison,
  sources,
} from './catalog';

const item = (p: Partial<CatalogItem>): CatalogItem => ({ id: 'x', ...p }) as CatalogItem;

const NETS: CatalogItem[] = [
  item({ id: 'fao_a3_standard', name: 'FAO A-3 estándar' }),
  item({
    id: 'pair80',
    name: 'Pareja 464 × 80',
    family: 'bottom',
    rig: 'pair',
    vessel_hp: [30, 33],
    status: 'published',
    source: { key: 'bobpwp13', title: 'BOBP/WP/13', url: 'https://x' },
  }),
  item({
    id: 'krill',
    name: 'Krill 1420 × 200',
    family: 'pelagic',
    rig: 'otter',
    vessel_hp: [1000, 1500],
    status: 'published',
    source: { key: 'scharfe1983', title: 'Schärfe 1983', url: 'https://y' },
  }),
  item({
    id: 'harstad',
    name: 'Harstad',
    family: 'pelagic',
    vessel_hp: [1000, 1500],
    status: 'draft',
    source: { key: 'scharfe1983', title: 'Schärfe 1983', url: 'https://y' },
  }),
];

describe('catálogo de redes', () => {
  it('filtra por potencia con ±25 % y deja siempre las redes sin rango', () => {
    expect(hpMatches(NETS[1] as CatalogItem, 40)).toBe(true);
    expect(hpMatches(NETS[1] as CatalogItem, 45)).toBe(false);
    expect(hpMatches(NETS[0] as CatalogItem, 5000)).toBe(true);
    const ids = filterNets(NETS, { ...DEFAULT_FILTERS, hp: 35 }).map((n) => n.id);
    expect(ids).toEqual(['fao_a3_standard', 'pair80']);
  });

  it('oculta los borradores salvo que se pidan', () => {
    expect(filterNets(NETS, DEFAULT_FILTERS).map((n) => n.id)).not.toContain('harstad');
    const all = filterNets(NETS, { ...DEFAULT_FILTERS, drafts: true });
    expect(all.map((n) => n.id)).toContain('harstad');
  });

  it('filtra por familia, aparejo, fuente y texto', () => {
    expect(filterNets(NETS, { ...DEFAULT_FILTERS, rig: 'pair' }).map((n) => n.id)).toEqual([
      'pair80',
    ]);
    expect(filterNets(NETS, { ...DEFAULT_FILTERS, family: 'pelagic' })).toHaveLength(1);
    expect(filterNets(NETS, { ...DEFAULT_FILTERS, source: 'bobpwp13' })).toHaveLength(1);
    expect(filterNets(NETS, { ...DEFAULT_FILTERS, text: 'KRILL' })).toHaveLength(1);
    expect(sources(NETS).map((s) => s.key)).toEqual(['bobpwp13', 'scharfe1983']);
  });

  it('arma etiquetas y la barra de procedencia', () => {
    expect(hpLabel(NETS[1] as CatalogItem)).toBe('30–33 hp');
    expect(hpLabel(NETS[0] as CatalogItem)).toBe('—');
    const shares = kindShares({ transcribed: 6, assumed: 2, derived: 2 });
    expect(shares.map((s) => s.kind)).toEqual(['transcribed', 'derived', 'assumed']);
    expect(shares[0]?.share).toBeCloseTo(0.6);
    expect(pathLabel('panels.C.meshes_top')).toBe('C · mallas de boca');
    expect(pathLabel('headrope.length_m')).toBe('Lima · largo');
    expect(pathLabel('ballast_kg')).toBe('Lastre');
  });
});

describe('red para comparar en el modo guiado (Fase 19.9)', () => {
  // Orden del catálogo de la API: la A-3 primero, después las demás.
  const CAT: CatalogItem[] = [
    item({ id: 'fao_a3_standard' }),
    item({ id: 'fao_a3_modified' }),
    item({ id: 'bobp_pair', rig: 'pair', status: 'published' }),
    item({ id: 'inidep_iat075_tangonera_propuesta', rig: 'outrigger', status: 'draft' }),
    item({ id: 'inidep_ito043_tangonera_empresa', rig: 'outrigger', status: 'published' }),
    item({ id: 'inidep_ito043_tangonera_inidep', rig: 'outrigger', status: 'published' }),
    item({ id: 'seafdec_beam', rig: 'beam', status: 'published' }),
  ];

  it('con una langostinera de tangones propone otra langostinera publicada', () => {
    expect(proposedComparison(CAT, 'inidep_ito043_tangonera_inidep')).toBe(
      'inidep_ito043_tangonera_empresa',
    );
  });

  it('con la A-3 sigue proponiendo la A-3 modificada', () => {
    expect(proposedComparison(CAT, 'fao_a3_standard')).toBe('fao_a3_modified');
  });

  it('sin otra red del mismo aparejo propone la primera del catálogo', () => {
    expect(proposedComparison(CAT, 'seafdec_beam')).toBe('fao_a3_standard');
  });

  it('ordena el desplegable con las del mismo aparejo primero', () => {
    expect(comparisonNets(CAT, 'inidep_ito043_tangonera_inidep').map((n) => n.id)).toEqual([
      'inidep_iat075_tangonera_propuesta',
      'inidep_ito043_tangonera_empresa',
      'fao_a3_standard',
      'fao_a3_modified',
      'bobp_pair',
      'seafdec_beam',
    ]);
  });

  it('al cambiar de red reemplaza la de comparación de otro aparejo', () => {
    const main = 'inidep_ito043_tangonera_inidep';
    expect(comparisonAfterChange(CAT, main, 'fao_a3_modified')).toBe(
      'inidep_ito043_tangonera_empresa',
    );
    // Una del mismo aparejo se conserva, aunque sea borrador; la misma red se quita.
    expect(comparisonAfterChange(CAT, main, 'inidep_iat075_tangonera_propuesta')).toBe(
      'inidep_iat075_tangonera_propuesta',
    );
    expect(comparisonAfterChange(CAT, main, main)).toBeNull();
    expect(comparisonAfterChange(CAT, main, null)).toBeNull();
    // Sin otra del mismo aparejo, la elegida queda.
    expect(comparisonAfterChange(CAT, 'seafdec_beam', 'bobp_pair')).toBe('bobp_pair');
  });
});
