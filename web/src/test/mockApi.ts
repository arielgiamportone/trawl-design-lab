import { vi } from 'vitest';
import { APP_CONTRACT } from '../lib/connection';
import design from './fixtures/design.json';
import designExcel from './fixtures/design_excel.json';
import doors from './fixtures/doors.json';
import errata from './fixtures/errata.json';
import haul from './fixtures/haul.json';
import layout from './fixtures/layout.json';
import netMod from './fixtures/net_mod.json';
import netStd from './fixtures/net_std.json';
import nets from './fixtures/nets.json';
import optimize from './fixtures/optimize.json';
import params from './fixtures/params.json';
import seabeds from './fixtures/seabeds.json';
import simulate from './fixtures/simulate.json';
import vessels from './fixtures/vessels.json';

export const fixtures = {
  design,
  designExcel,
  doors,
  errata,
  haul,
  layout,
  netMod,
  netStd,
  nets,
  optimize,
  params,
  seabeds,
  simulate,
  vessels,
};

export interface Call {
  url: string;
  method: string;
  body: unknown;
}

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { 'Content-Type': 'application/json' } });

/** Reemplaza ``fetch`` por un doble que responde como la API con los fixtures grabados. */
export function mockApi(
  overrides: {
    design?: (body: Record<string, unknown>) => Response;
    contract?: string | null;
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
    if (path === '/errata') return json(errata);
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
