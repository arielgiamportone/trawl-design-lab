/** Escenario del lance (``ScenarioIn``) con los valores por defecto de la API. */
import type { ScenarioIn } from '../api/client';

export const DEFAULT_SCENARIO: ScenarioIn = {
  catch_kg: 0,
  catch_bulk_density: 750,
  catch_body_density: 1070,
  catch_cp: 1,
  seabed: null,
  mu_gear: null,
  mu_door: null,
  coupled_doors: true,
  fouling: null,
  fouling_level: 1,
  current_kn: 0,
  warp_length_m: null,
  haul_hours: 2,
  mesh_bending: null,
  mesh_bending_factor: 1,
  door_cl_factor: 1,
  door_cd_factor: 1,
};

/** Escenario completo a partir de los campos que cambian. */
export function scenarioIn(patch: Partial<ScenarioIn>): ScenarioIn {
  return { ...DEFAULT_SCENARIO, ...patch };
}
