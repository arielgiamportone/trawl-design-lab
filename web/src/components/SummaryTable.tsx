import { useT, type Messages } from '../i18n';
import { fmt } from '../lib/format';
import { label } from '../lib/labels';
import { fmtU, unitLabel } from '../lib/units';
import { useCase } from '../state/useCase';

type GroupKey = keyof Messages['expert']['summary']['groups'];

const GROUPS: { title: GroupKey; match: (k: string) => boolean }[] = [
  { title: 'case', match: (k) => ['net_id', 'vessel_id', 'door_id', 'compat'].includes(k) },
  {
    title: 'net',
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
    title: 'drag',
    match: (k) =>
      k.startsWith('rn_std_') ||
      k.startsWith('rob_') ||
      k.startsWith('net_total_') ||
      k.startsWith('total_drag_') ||
      k === 'max_speed_kn',
  },
  {
    title: 'rigging',
    match: (k) =>
      [
        'dan_leno_m',
        'sweeps_m',
        'crowfoot_m',
        'crowfoot_extension_m',
        'upper_bridle_m',
        'lower_bridle_m',
        'rig',
        'n_nets',
        'net_spread_m',
        'door_spread_total_m',
        'swept_width_m',
        'beam_length_m',
        'boom_tip_offset_m',
        'nets_gap_m',
        'clump_weight_kg',
      ].includes(k),
  },
  {
    title: 'flotation',
    match: (k) =>
      [
        'flotation_total_kgf',
        'float_count',
        'float_diameter_mm',
        'ballast_min_kg',
        'ballast_max_kg',
      ].includes(k),
  },
  { title: 'warp', match: (k) => k.startsWith('warp_') },
];

export function SummaryTable() {
  const { design } = useCase();
  const d = design.data;
  const T = useT();
  const S = T.expert.summary;
  if (!d) return <p className="empty">{design.isFetching ? S.calculating : S.noResults}</p>;
  const keys = Object.keys(d.summary);
  const used = new Set<string>();
  const groups = GROUPS.map((g) => {
    const ks = keys.filter((k) => !used.has(k) && g.match(k));
    ks.forEach((k) => used.add(k));
    return { title: S.groups[g.title], keys: ks };
  });
  const rest = keys.filter((k) => !used.has(k));
  if (rest.length) groups.push({ title: S.groups.other, keys: rest });

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
                    <th scope="col">{S.quantity}</th>
                    <th scope="col" className="num">
                      {S.value}
                    </th>
                    <th scope="col">{S.unit}</th>
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
                              ? T.labels.compatExcel
                              : T.labels.compatCorrected
                            : typeof v === 'number'
                              ? fmtU(v, unit, { unit: false })
                              : fmt(v)}
                        </td>
                        <td className="unit">{unit ? unitLabel(unit) : ''}</td>
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
