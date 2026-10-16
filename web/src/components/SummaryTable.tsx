import { fmt } from '../lib/format';
import { label } from '../lib/labels';
import { useCase } from '../state/useCase';

const GROUPS: { title: string; match: (k: string) => boolean }[] = [
  { title: 'Caso', match: (k) => ['net_id', 'vessel_id', 'door_id', 'compat'].includes(k) },
  {
    title: 'Red',
    match: (k) =>
      [
        'headrope_m',
        'footrope_m',
        'cut_angle_deg',
        'filtration_index',
        'solid_surface_m2',
        'working_surface_m2',
        'net_weight_kg',
        'vertical_opening_m',
        'horizontal_opening_m',
        'working_depth_m',
      ].includes(k),
  },
  {
    title: 'Resistencia y velocidad',
    match: (k) => k.startsWith('rn_std_') || k.startsWith('rob_') || k === 'max_speed_kn',
  },
  {
    title: 'Aparejo',
    match: (k) =>
      [
        'dan_leno_m',
        'sweeps_m',
        'crowfoot_m',
        'crowfoot_extension_m',
        'upper_bridle_m',
        'lower_bridle_m',
      ].includes(k),
  },
  {
    title: 'Flotación y lastre',
    match: (k) =>
      [
        'flotation_total_kgf',
        'float_count',
        'float_diameter_mm',
        'ballast_min_kg',
        'ballast_max_kg',
      ].includes(k),
  },
  { title: 'Cable de remolque', match: (k) => k.startsWith('warp_') },
];

export function SummaryTable() {
  const { design } = useCase();
  const d = design.data;
  if (!d)
    return <p className="empty">{design.isFetching ? 'Calculando…' : 'Sin resultados todavía.'}</p>;
  const keys = Object.keys(d.summary);
  const used = new Set<string>();
  const groups = GROUPS.map((g) => {
    const ks = keys.filter((k) => !used.has(k) && g.match(k));
    ks.forEach((k) => used.add(k));
    return { title: g.title, keys: ks };
  });
  const rest = keys.filter((k) => !used.has(k));
  if (rest.length) groups.push({ title: 'Otros', keys: rest });

  return (
    <div className={`summary-grid${design.isFetching ? ' stale' : ''}`} data-testid="summary">
      {groups
        .filter((g) => g.keys.length)
        .map((g) => (
          <div key={g.title}>
            <h3 className="group-title">{g.title}</h3>
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th scope="col">Magnitud</th>
                    <th scope="col" className="num">
                      Valor
                    </th>
                    <th scope="col">Unidad</th>
                  </tr>
                </thead>
                <tbody>
                  {g.keys.map((k) => {
                    const [name, unit] = label(k);
                    const v = d.summary[k];
                    return (
                      <tr key={k} data-key={k}>
                        <th scope="row" style={{ fontWeight: 500 }}>
                          {name}
                        </th>
                        <td className={typeof v === 'string' ? 'num wrap' : 'num'}>
                          {k === 'compat'
                            ? v === 'excel'
                              ? 'Reproducir Excel'
                              : 'Corregido'
                            : fmt(v)}
                        </td>
                        <td className="unit">{unit}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))}
    </div>
  );
}
