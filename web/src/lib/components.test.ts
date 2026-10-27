import { describe, expect, it } from 'vitest';
import bom from '../test/fixtures/bom.json';
import wires from '../test/fixtures/components_wire.json';
import { DEFAULT_CASE, sanitizeCase, buildRequest } from '../state/model';
import {
  applyAssembly,
  applyComponent,
  bomCsv,
  cellText,
  contributionId,
  draftComponent,
  filterComponents,
  inCase,
  issueUrl,
  columns,
  COMPONENT_KINDS,
  mergePrices,
  priceKey,
  priceLines,
  sanitizePrices,
  sanitizeContributions,
  type Bom,
  type Component,
  DEFAULT_COMPONENT_FILTERS,
} from './components';

const items = wires as Component[];

describe('grilletes y lista de precios (Fase 19.2)', () => {
  it('el grillete es un tipo del catálogo con sus columnas', () => {
    expect(COMPONENT_KINDS).toContain('shackle');
    expect(columns('shackle').map((c) => c.field)).toEqual([
      'size',
      'wll_t',
      'breaking_load_t',
      'pin_diameter_mm',
      'weight_kg',
    ]);
  });
  it('importar precios pisa las mismas claves y descarta los inválidos', () => {
    const p = { value: 1, currency: 'USD', unit: 'm' as const, date: '2026-10', source: 'a' };
    const merged = mergePrices({ warps: p, doors: { ...p, unit: 'unit' } }, {
      warps: { ...p, value: 2 },
      malo: { ...p, unit: 'ton' },
    } as never);
    expect(merged.warps!.value).toBe(2);
    expect(merged.doors!.unit).toBe('unit');
    expect(merged).not.toHaveProperty('malo');
    expect(sanitizePrices([1, 2])).toEqual({});
  });
  it('arma las líneas de la plantilla de precios desde la lista de materiales', () => {
    const lines = priceLines(bom as Bom);
    expect(lines.length).toBe((bom as Bom).lines.length);
    expect(lines.every((l) => l.key && l.unit)).toBe(true);
    expect(priceLines(undefined)).toEqual([]);
  });
});

describe('catálogo de componentes', () => {
  it('filtra por genérico, marca y texto', () => {
    const generic = filterComponents(items, { ...DEFAULT_COMPONENT_FILTERS, genericOnly: true });
    expect(generic.length).toBeGreaterThan(0);
    expect(generic.every((w) => !w.brand)).toBe(true);
    const text = filterComponents(items, { ...DEFAULT_COMPONENT_FILTERS, text: '6x19' });
    expect(text.length).toBeGreaterThan(0);
    expect(filterComponents(items, { ...DEFAULT_COMPONENT_FILTERS, brand: 'Nadie' })).toEqual([]);
  });
  it('formatea celdas con coma decimal y rangos', () => {
    const w = { ...items[0]!, weight_kg_per_m: 0.484 } as Component;
    expect(cellText(w, 'weight_kg_per_m')).toBe('0,484');
    expect(cellText({ ...w, hp_range: [50, 75] } as Component, 'hp_range')).toBe('50–75');
    expect(cellText(w, 'no_such')).toBe('—');
  });
});

describe('aplicar al caso', () => {
  const wire = items[0]!;
  it('cable, boya y cabo van a sus parámetros; el portón a door', () => {
    const s = applyComponent(DEFAULT_CASE, wire);
    expect(s.params.warp_id).toBe(wire.id);
    expect(inCase(s, wire)).toBe(true);
    const f = applyComponent(
      { ...DEFAULT_CASE, params: { float_count: '12' } },
      { id: 'float_pl_200mm_6', kind: 'float', name: 'b' },
    );
    expect(f.params).toEqual({ float_id: 'float_pl_200mm_6' });
    const r = applyComponent(
      DEFAULT_CASE,
      { id: 'pp_12', kind: 'rope', name: 'c' },
      'footrope_rope',
    );
    expect(r.params.footrope_rope).toBe('pp_12');
    expect(applyComponent(DEFAULT_CASE, { id: 'd1', kind: 'door', name: 'p' }).door).toBe('d1');
  });
  it('un armado fija sus componentes y conserva el portón del plano', () => {
    const a = {
      components: { door: 'plan_1.3x0.65', warp: 'w', float: 'f', twine: null },
      float_count: 4,
    };
    const s = applyAssembly({ ...DEFAULT_CASE, params: { twine_id: 'old' } }, a, 'plan_1.3x0.65');
    expect(s.door).toBeNull();
    expect(s.params).toEqual({ warp_id: 'w', float_id: 'f', float_count: '4' });
    expect(
      applyAssembly(DEFAULT_CASE, { ...a, components: { ...a.components, door: 'x' } }).door,
    ).toBe('x');
  });
});

describe('lista de materiales', () => {
  it('CSV con «;», coma decimal y «sin precio»', () => {
    const csv = bomCsv(bom as Bom);
    const lines = csv.trim().split('\n');
    expect(lines[0]).toBe('Ítem;Componente;Cantidad;Unidad;Precio unitario;Moneda;Costo;Nota');
    expect(csv).toContain('sin precio');
    expect(lines.at(-1)).toMatch(/^Total;;;;;USD;900/);
    expect(priceKey({ key: 'doors', label: '', quantity: 2, unit: 'unit' })).toBe('doors');
  });
});

describe('aportes', () => {
  it('arma el aporte con coma decimal, id y superficie del portón', () => {
    const d = draftComponent('door', { name: 'Portón de Juan', length_m: '1,2', height_m: '0,6' });
    expect(d).toMatchObject({ id: 'user_door_porton_de_juan', status: 'user', length_m: 1.2 });
    expect(d.area_m2).toBe(0.72);
    expect(contributionId('wire', '¡¡')).toBe('user_wire_aporte');
  });
  it('los aportes viajan con el caso y se envían sólo si se habilitan', () => {
    const c = { id: 'user_wire_x', kind: 'wire', name: 'x', status: 'published' };
    expect(sanitizeContributions([c, { id: 1 }, null])).toEqual([{ ...c, status: 'user' }]);
    const state = sanitizeCase({ contributions: [c], useContributions: false });
    expect(buildRequest(state, [], {}).request.components).toBeUndefined();
    const on = { ...state, useContributions: true };
    expect(buildRequest(on, [], {}).request.components).toHaveLength(1);
  });
  it('enlace al issue con la plantilla y el JSON', () => {
    const url = new URL(issueUrl({ id: 'user_wire_x', kind: 'wire', name: 'Cable X' }));
    expect(url.pathname).toMatch(/\/issues\/new$/);
    expect(url.searchParams.get('template')).toBe('componente.yml');
    expect(url.searchParams.get('datos')).toContain('"user_wire_x"');
  });
});
