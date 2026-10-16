import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import type { ParamInfo } from '../api/client';
import { ParamField } from '../components/ParamsForm';
import params from '../test/fixtures/params.json';
import { buildParams, defaultText, paramMeta, parseParam } from './params';

const metas = (params as ParamInfo[]).map(paramMeta);
const meta = (n: string) => metas.find((m) => m.name === n)!;

describe('paramMeta', () => {
  it('clasifica los tipos de /params', () => {
    expect(meta('sweeps_m')).toMatchObject({ kind: 'float', nullable: false });
    expect(meta('depth_m')).toMatchObject({ kind: 'float', nullable: true });
    expect(meta('float_count')).toMatchObject({ kind: 'int', nullable: true });
    expect(meta('speeds_kn')).toMatchObject({ kind: 'tuple', tupleLen: null });
    expect(meta('nomura_nhp')).toMatchObject({ kind: 'tuple', tupleLen: 2 });
    expect(meta('ft_propeller').kind).toBe('enum');
    expect(meta('headrope_rope').kind).toBe('string');
  });
  it('placeholder con el valor por defecto', () => {
    expect(defaultText(meta('sweeps_m'))).toBe('25');
    expect(defaultText(meta('spread_per_m'))).toBe('2,65');
    expect(defaultText(meta('depth_m'))).toBe('automático');
    expect(defaultText(meta('nomura_nhp'))).toBe('150; 180');
  });
});

describe('parseParam / buildParams', () => {
  it('acepta coma decimal y listas con ;', () => {
    expect(parseParam(meta('sweeps_m'), '27,5')).toEqual({ ok: true, value: 27.5 });
    expect(parseParam(meta('speeds_kn'), '1; 1,5; 2')).toEqual({ ok: true, value: [1, 1.5, 2] });
  });
  it('valida enteros y largo de tuplas', () => {
    expect(parseParam(meta('float_count'), '12,5')).toMatchObject({ ok: false });
    expect(parseParam(meta('nomura_nhp'), '150')).toMatchObject({ ok: false });
    expect(parseParam(meta('sweeps_m'), 'abc')).toMatchObject({ ok: false });
  });
  it('vacío = valor por defecto (no se envía)', () => {
    const { params: p, errors } = buildParams(metas, {
      sweeps_m: '',
      dan_leno_m: '0,7',
      float_count: 'x',
    });
    expect(p).toEqual({ dan_leno_m: 0.7 });
    expect(errors).toHaveProperty('float_count');
  });
});

describe('<ParamField>', () => {
  it('muestra la celda del Excel como ayuda y el defecto como placeholder', () => {
    render(
      <ParamField
        meta={meta('sweeps_m')}
        idBase="p"
        value=""
        onChange={() => {}}
        onReset={() => {}}
      />,
    );
    const input = screen.getByLabelText('Patentes [m]');
    expect(input).toHaveAttribute('placeholder', '25');
    expect(input).toHaveAccessibleDescription(/Dim!F65/);
    expect(screen.getByRole('button', { name: /Restablecer Patentes/ })).toBeDisabled();
  });
  it('propaga cambios, errores y reset', async () => {
    const onChange = vi.fn();
    const onReset = vi.fn();
    render(
      <ParamField
        meta={meta('sweeps_m')}
        idBase="p"
        value="x"
        error="Ingrese un número"
        onChange={onChange}
        onReset={onReset}
      />,
    );
    const input = screen.getByLabelText('Patentes [m]');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription(/Ingrese un número/);
    await userEvent.type(input, '1');
    expect(onChange).toHaveBeenLastCalledWith('x1');
    await userEvent.click(screen.getByRole('button', { name: /Restablecer Patentes/ }));
    expect(onReset).toHaveBeenCalled();
  });
});
