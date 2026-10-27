import { describe, expect, it } from 'vitest';
import type { Vessel } from '../api/client';
import { setLang } from '../i18n';
import { buildRequest, DEFAULT_CASE, sanitizeCase } from '../state/model';
import { parseProjectFile, toProjectFile } from './projects';
import {
  EMPTY_MY_VESSEL,
  filterVessels,
  myVesselErrors,
  myVesselFrom,
  myVesselToApi,
  propellerOf,
  sanitizeMyVessel,
} from './vessel';

const MV = { ...EMPTY_MY_VESSEL, bhp: '200', length_m: '12', beam_m: '4', depth_m: '2' };

describe('Mi buque', () => {
  it('arma el tipo de hélice con paso y tobera', () => {
    expect(propellerOf('fixed', false)).toBe('fixed_pitch');
    expect(propellerOf('fixed', true)).toBe('fixed_pitch_nozzle');
    expect(propellerOf('variable', false)).toBe('variable_pitch');
    expect(propellerOf('variable', true)).toBe('variable_pitch_nozzle');
  });

  it('valida campos, rangos y la hélice sin KF de Fridman', () => {
    expect(myVesselErrors(MV)).toEqual({});
    expect(Object.keys(myVesselErrors({ ...MV, bhp: '' }))).toEqual(['bhp']);
    expect(myVesselErrors({ ...MV, beam_m: '15' }).beam_m).toMatch(/manga/);
    expect(myVesselErrors({ ...MV, propeller_diameter_m: '20' }).propeller_diameter_m).toMatch(
      /rango/,
    );
    expect(myVesselErrors({ ...MV, nozzle: true }).propeller).toMatch(/KF de Fridman/);
    expect(myVesselErrors({ ...MV, nozzle: true }, '12')).toEqual({});
    setLang('en');
    expect(myVesselErrors({ ...MV, bhp: 'x' }).bhp).toBe('Not a number.');
    setLang('es');
  });

  it('envía sólo los datos cargados, en métrico', () => {
    const v = myVesselToApi({ ...MV, length_m: '12,5', propeller_diameter_m: '1.2' });
    expect(v).toMatchObject({ id: 'mi_buque', bhp: 200, length_m: 12.5, beam_m: 4 });
    expect(v.propeller_diameter_m).toBe(1.2);
    expect('winch_drum_capacity_m' in v).toBe(false);
    expect(v.name).toBe('Mi buque de 200 hp');
  });

  it('se guarda en el caso y en los proyectos', () => {
    const state = { ...DEFAULT_CASE, myVessel: { ...MV, region: 'latam' }, useMyVessel: true };
    const back = parseProjectFile(JSON.stringify(toProjectFile('x', state)));
    expect(back.ok && back.project.case.myVessel).toEqual(state.myVessel);
    expect(back.ok && back.project.case.useMyVessel).toBe(true);
    expect(sanitizeCase({ useMyVessel: true }).useMyVessel).toBe(false);
    expect(sanitizeMyVessel({ bhp: 3, pitch: 'x' })).toMatchObject({ bhp: '', pitch: 'fixed' });
    const { request, errors } = buildRequest(state, [], {});
    expect(errors).toEqual({});
    expect(request.vessel).toMatchObject({ id: 'mi_buque', region: 'latam' });
    expect(request.params).toMatchObject({ component_region: 'latam' });
    const bad = buildRequest({ ...state, myVessel: { ...MV, bhp: '' } }, [], {});
    expect(bad.errors['vessel.bhp']).toBeTruthy();
    // Sin «usar», va el buque del catálogo.
    expect(buildRequest({ ...state, useMyVessel: false }, [], {}).request.vessel).toBeNull();
  });

  it('parte de un buque del catálogo y filtra por tipo y región', () => {
    const cat = [
      { id: 'a', bhp: 150, length_m: 9, propeller: 'fixed_pitch' },
      { id: 'b', bhp: 900, vessel_type: 'tangonero', region: 'latam' },
      {
        id: 'c',
        bhp: 2100,
        vessel_type: 'investigacion',
        region: 'latam',
        propeller: 'variable_pitch',
      },
    ] as unknown as Vessel[];
    expect(myVesselFrom(cat[2])).toMatchObject({ bhp: '2100', pitch: 'variable', nozzle: false });
    expect(myVesselFrom(cat[0]).length_m).toBe('9');
    expect(filterVessels(cat, 'tangonero', '').map((v) => v.id)).toEqual(['b']);
    expect(filterVessels(cat, 'book', '').map((v) => v.id)).toEqual(['a']);
    expect(filterVessels(cat, '', 'latam').map((v) => v.id)).toEqual(['b', 'c']);
  });
});
