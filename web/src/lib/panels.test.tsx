import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import type { NetSpec, Panel } from '../api/client';
import { PanelTable } from '../components/PanelEditor';
import netStd from '../test/fixtures/net_std.json';
import {
  applyPanelEdits,
  countEdits,
  editErrors,
  editedSpec,
  validateField,
  type PanelEdits,
} from './panels';

const spec = netStd as unknown as NetSpec;
const panelA = spec.panels[0] as Panel & { meshes_a: number; meshes_b: number };

describe('validateField', () => {
  it('mallas enteras y no negativas', () => {
    expect(validateField('meshes_top', '57')).toEqual({ ok: true, value: 57 });
    expect(validateField('meshes_top', '5,5')).toMatchObject({ ok: false, error: /entero/ });
    expect(validateField('meshes_top', '-1')).toMatchObject({ ok: false });
    expect(validateField('meshes_depth', '0')).toMatchObject({ ok: false });
  });
  it('malleros e hilos positivos, U1 en (0, 1]', () => {
    expect(validateField('mesh_mm', '0')).toMatchObject({ ok: false, error: /mayor que 0/ });
    expect(validateField('twine_diameter_mm', '1,2')).toEqual({ ok: true, value: 1.2 });
    expect(validateField('hanging_ratio', '1,2')).toMatchObject({ ok: false });
    expect(validateField('count', '')).toMatchObject({ ok: false });
  });
});

describe('applyPanelEdits / editedSpec', () => {
  it('actualiza meshes_a/meshes_b en espejo (bordes T1/T2 del Excel)', () => {
    // panel A: top=3, bottom=57, a=57, b=3
    const p = applyPanelEdits(panelA, { meshes_bottom: '60' }) as Panel & Record<string, unknown>;
    expect(p.meshes_bottom).toBe(60);
    expect(p.meshes_a).toBe(60);
    expect(p.meshes_b).toBe(3);
  });
  it('sin cambios efectivos → null; con cambios → NetSpec nueva', () => {
    expect(editedSpec(spec, {})).toBeNull();
    expect(editedSpec(spec, { A: { mesh_mm: '80' } })).toBeNull();
    const out = editedSpec(spec, { C: { meshes_depth: '140' } })!;
    expect(out.panels.find((p) => p.id === 'C')!.meshes_depth).toBe(140);
    expect(spec.panels.find((p) => p.id === 'C')!.meshes_depth).toBe(120);
    expect(countEdits(spec, { C: { meshes_depth: '140' }, A: { mesh_mm: '80' } })).toBe(1);
  });
  it('reporta errores por panel y campo', () => {
    expect(editErrors({ A: { meshes_top: 'x' } })).toEqual({ 'A.meshes_top': 'Ingrese un número' });
  });
});

function Harness() {
  const [edits, setEdits] = useState<PanelEdits>({});
  return <PanelTable spec={spec} edits={edits} setEdits={(fn) => setEdits(fn)} />;
}

describe('<PanelTable>', () => {
  it('marca celdas editadas e inválidas', async () => {
    render(<Harness />);
    const row = screen.getByRole('row', { name: /^C/ });
    const depth = within(row).getByLabelText('Mallas de alto (N) del panel C');
    await userEvent.clear(depth);
    await userEvent.type(depth, '140');
    expect(depth.closest('td')).toHaveClass('edited');
    expect(screen.getByText(/1 celda editada/)).toBeInTheDocument();

    await userEvent.clear(depth);
    await userEvent.type(depth, '14,5');
    expect(depth).toHaveAttribute('aria-invalid', 'true');
    expect(depth).toHaveAccessibleDescription('Debe ser un número entero');

    await userEvent.clear(depth);
    await userEvent.type(depth, '120');
    expect(depth.closest('td')).not.toHaveClass('edited');
    expect(screen.getByText(/Sin cambios/)).toBeInTheDocument();
  });
});
