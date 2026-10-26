import type { Messages } from '../es';

export const simulate: Messages['simulate'] = {
  quality: { fast: 'Fast', normal: 'Normal' },
  resolutions: { veryFast: 'Very fast', fast: 'Fast', normal: 'Normal' },
  quantities: {
    ah_m: { label: 'Horizontal opening AH', engine: 'Fridman DPA' },
    av_m: { label: 'Vertical opening AV', engine: 'Fridman AV' },
    drag_kgf: { label: 'Net drag', engine: 'Aberdeen RN' },
  },
  speed: 'Speed',
  resolution: 'Resolution',
  seabed: 'Seabed',
  catchCodend: 'Catch in the codend',
  noSelectivity: '(no selectivity)',
  error: 'Error',
  errorStatus: (status: number) => `Error ${status}`,
  loading3d: 'Loading the 3D viewer…',
  engineRule: 'engine rule',
  engineDemand: 'engine demand',
  yes: 'yes',
  no: 'no',
  title: 'Shape simulation',
  experimental: 'experimental',
  viewsLabel: 'Simulation type',
  views: {
    speeds: 'Speed sweep',
    haul: 'Progressive haul (catch and seabed)',
    explore: 'Animated explorer',
    selectivity: 'Meshes and selectivity',
    uncertainty: 'Uncertainty and calibration',
  },
  projections: { plan: 'Plan', profile: 'Profile', front: 'Front' },
  table: {
    caption: (dynamit: boolean) =>
      `Simulation vs the empirical engine${dynamit ? ' and DynamiT' : ''}`,
    quantity: 'Quantity',
    sim: 'Simulation',
    engine: 'Engine',
    simVsEngine: 'Δ sim/engine',
    simVsDynamit: 'Δ sim/DynamiT',
    engineVsDynamit: 'Δ engine/DynamiT',
    engineNote: (name: string) => ` engine: ${name}`,
  },
  scaledNet: (s: string) => `scaled net s = ${s}`,
  intro: (net: string) =>
    `Finds the equilibrium shape of the net (${net}) towed at each speed: twine netting with Morison drag, headrope and footrope, floats, ballast, bridles, sweeps and seabed contact, with the rigging of the current case.`,
  formLabel: 'Simulation parameters',
  speedsLegend: (max: number, n: number) => `Speeds [kn] (up to ${max}, ${n} selected)`,
  estimate: (s: number) => `≈ ${s} s on the server`,
  view3d: '3D view',
  run: 'Simulate',
  cancel: 'Cancel',
  running: 'Simulating…',
  runningOf: (s: number) => `of ≈ ${s} s`,
  done: (n: number, secs: string, res: string) =>
    `${n} ${n === 1 ? 'speed simulated' : 'speeds simulated'} in ${secs} s (resolution ${res}).`,
  unconverged: (speeds: string) =>
    `The simulation did not fully converge at ${speeds} kn: treat those values with caution.`,
  view3dRegion: '3D view of the simulated shape',
  speed3d: 'Speed of the 3D view',
  projAria: (v: string) => `Projections at ${v} kn`,
  at: (v: string) => `At ${v} kn`,
  projAlt: (view: string, v: string) => `${view} of the simulated net at ${v} kn`,
  projLabel: (view: string, v: string) =>
    `${view} of the net at ${v} kn. Drag to pan, wheel or + and − keys to zoom, 0 to reset.`,
  firstThree: 'Only the first three speeds are drawn.',
  compareTitle: (dynamit: boolean) =>
    `Simulation, empirical engine${dynamit ? ' and DynamiT' : ''}`,
  dragNote: {
    title: 'About the drag.',
    a: 'The simulated drag is only that of the twines (Morison with C',
    b: (cn: string) => ` = ${cn} and C`,
    c: (ct: string) =>
      ` = ${ct}) plus seabed friction: for the FAO A-3 net it is ≈ 50 % below the DynamiT RA between 2 and 4 kn, and the engine's empirical RN (Aberdeen) ≈ 20 % above. The openings, on the other hand, agree: AH within 3 % and AV within 10–20 %. The drag gap points to what the model lacks —knots, vibration and undulation of the netting, hydrodynamic shading between twines and twine coefficients calibrated in uniform flow— and it does not close with C`,
    d: '/C',
    e: ' within the ranges in the literature (see chapter 21 of the book). Use the simulation for the shape and the openings, and the engine for the design drag.',
  },
  empty:
    'Choose up to three speeds and press «Simulate». The fast version takes about one second per speed.',
};
