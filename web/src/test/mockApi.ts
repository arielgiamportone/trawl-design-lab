import { vi } from 'vitest';
import { APP_CONTRACT } from '../lib/connection';
import design from './fixtures/design.json';
import designExcel from './fixtures/design_excel.json';
import doors from './fixtures/doors.json';
import errata from './fixtures/errata.json';
import explore from './fixtures/explore.json';
import fouling from './fixtures/fouling.json';
import haul from './fixtures/haul.json';
import layout from './fixtures/layout.json';
import netMod from './fixtures/net_mod.json';
import netStd from './fixtures/net_std.json';
import nets from './fixtures/nets.json';
import optimize from './fixtures/optimize.json';
import params from './fixtures/params.json';
import seabeds from './fixtures/seabeds.json';
import calibrate from './fixtures/calibrate.json';
import selectivity from './fixtures/selectivity.json';
import sensorLog from './fixtures/sensor_log.csv?raw';
import sensorsParse from './fixtures/sensors_parse.json';
import simulate from './fixtures/simulate.json';
import species from './fixtures/species.json';
import uncertainty from './fixtures/uncertainty.json';
import vessels from './fixtures/vessels.json';
import bom from './fixtures/bom.json';
import componentKinds from './fixtures/component_kinds.json';
import componentsWire from './fixtures/components_wire.json';
import optimizeComponents from './fixtures/optimize_components.json';
import batchParse from './fixtures/batch_parse.json';
import batchRun from './fixtures/batch_run.json';
import construction from './fixtures/construction.json';
import economics from './fixtures/economics.json';
import economicsCompare from './fixtures/economics_compare.json';
import teachingExercise from './fixtures/teaching_exercise.json';
import teachingExercises from './fixtures/teaching_exercises.json';
import teachingGrade from './fixtures/teaching_grade.json';
import teachingLab from './fixtures/teaching_lab.json';
import teachingLabCheck from './fixtures/teaching_lab_check.json';
import teachingLabs from './fixtures/teaching_labs.json';

export const fixtures = {
  design,
  designExcel,
  doors,
  errata,
  explore,
  fouling,
  haul,
  layout,
  netMod,
  netStd,
  nets,
  optimize,
  params,
  seabeds,
  calibrate,
  selectivity,
  sensorsParse,
  simulate,
  species,
  uncertainty,
  vessels,
  bom,
  componentKinds,
  componentsWire,
  optimizeComponents,
  batchParse,
  batchRun,
  construction,
  economics,
  economicsCompare,
  teachingExercise,
  teachingExercises,
  teachingGrade,
  teachingLab,
  teachingLabCheck,
  teachingLabs,
};

export interface Call {
  url: string;
  method: string;
  body: unknown;
}

export const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

/** Reemplaza ``fetch`` por un doble que responde como la API con los fixtures grabados. */
export function mockApi(
  overrides: {
    design?: (body: Record<string, unknown>) => Response;
    contract?: string | null;
    /** Rutas del aula (``/classroom/...``); sin esto, el aula está deshabilitada. */
    classroom?: (path: string, method: string, body: unknown) => Response | undefined;
  } = {},
) {
  const calls: Call[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? 'GET';
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ url, method, body });
    const path = new URL(url, 'http://x').pathname.replace(/^\/api/, '');
    if (path === '/health')
      return json({
        status: 'ok',
        version: '0.1.0',
        contract: overrides.contract === undefined ? APP_CONTRACT : overrides.contract,
      });
    if (path === '/catalog/nets') return json(nets);
    if (path === '/catalog/nets/fao_a3_standard') return json(netStd);
    if (path === '/catalog/nets/fao_a3_modified') return json(netMod);
    if (path.startsWith('/catalog/nets/')) return json({ detail: 'red desconocida' }, 404);
    if (path === '/catalog/vessels') return json(vessels);
    if (path === '/catalog/doors') return json(doors);
    if (path === '/params') return json(params);
    if (path === '/catalog/seabeds') return json(seabeds);
    if (path === '/simulate/haul') return json(haul);
    if (path === '/simulate/explore') return json(explore);
    if (path === '/catalog/fouling') return json(fouling);
    if (path === '/catalog/species') return json(species);
    if (path === '/simulate/selectivity') return json(selectivity);
    if (path === '/simulate/uncertainty') return json(uncertainty);
    if (path === '/simulate/calibrate') return json(calibrate);
    if (path === '/sensors/parse') return json(sensorsParse);
    if (path === '/sensors/example')
      return new Response(sensorLog, { headers: { 'Content-Type': 'text/csv' } });
    if (path === '/errata') return json(errata);
    if (path === '/catalog/components') return json(componentKinds);
    if (path === '/catalog/components/wire') return json(componentsWire);
    if (path.startsWith('/catalog/components/wire/')) {
      const id = decodeURIComponent(path.split('/').pop() ?? '');
      const item = componentsWire.find((w) => w.id === id);
      return item ? json({ ...item, issues: [], generic: null }) : json({ detail: 'x' }, 404);
    }
    if (path.startsWith('/catalog/components/')) return json([]);
    if (path === '/components/check') {
      const b = body as Record<string, unknown>;
      const ok = typeof b.diameter_mm === 'number';
      return json({
        ok,
        item: ok ? { ...b, status: 'user' } : null,
        issues: ok
          ? []
          : [
              {
                level: 'error',
                code: 'schema',
                message: 'diameter_mm: Field required',
                panels: [],
              },
            ],
        generic: null,
      });
    }
    if (path === '/teaching/exercises') return json(teachingExercises);
    if (path.startsWith('/teaching/exercises/')) return json(teachingExercise);
    if (path === '/teaching/grade') return json(teachingGrade);
    if (path === '/teaching/labs') return json(teachingLabs);
    if (path === '/teaching/labs/check') return json(teachingLabCheck);
    if (path.startsWith('/teaching/labs/')) return json(teachingLab);
    if (path.startsWith('/classroom/')) {
      const r = overrides.classroom?.(path.slice('/classroom'.length), method, body);
      if (r) return r;
      if (path === '/classroom/status')
        return json({ enabled: false, detail: 'El aula no está habilitada en este servidor.' });
      return json({ detail: 'El aula no está habilitada en este servidor.' }, 503);
    }
    if (path === '/design/bom') return json(bom);
    if (path === '/design/construction') return json(construction);
    if (path === '/economics') return json(economics);
    if (path === '/economics/compare') return json(economicsCompare);
    if (path === '/design/construction/export')
      return new Response('%PDF-fake', { headers: { 'Content-Type': 'application/pdf' } });
    if (path === '/batch/parse') return json(batchParse);
    if (path === '/batch/run') return json(batchRun);
    if (path === '/batch/export' || path === '/batch/template') {
      return new Response('PK-fake', {
        headers: {
          'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        },
      });
    }
    if (path === '/optimize/components') return json(optimizeComponents);
    if (path === '/design') {
      if (overrides.design) return overrides.design(body as Record<string, unknown>);
      return json((body as { compat?: string }).compat === 'excel' ? designExcel : design);
    }
    if (path === '/design/layout') return json(layout);
    if (path === '/optimize') return json(optimize);
    if (path === '/optimize/scaled-net') {
      const b = body as { net: unknown; s: number };
      const base = b.net === 'fao_a3_modified' ? netMod : netStd;
      return json({ ...base, id: `${base.id}_s${b.s.toFixed(2)}` });
    }
    if (path === '/simulate') return json(simulate);
    if (path === '/design/plan') {
      return new Response('<svg xmlns="http://www.w3.org/2000/svg"><title>plano</title></svg>', {
        headers: { 'Content-Type': 'image/svg+xml' },
      });
    }
    return json({ detail: 'Not Found' }, 404);
  });
  vi.stubGlobal('fetch', fn);
  return { fn, calls };
}
