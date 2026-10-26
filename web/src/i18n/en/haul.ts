import type { Messages } from '../es';

export const haul: Messages['haul'] = {
  catchTypes: {
    fish: 'Fish',
    crustacean: 'Crustaceans (squat lobster, shrimp)',
    mixed: 'Mixed with mud or shell',
  },
  summary: {
    doors: (down: boolean, amount: string, pct: string) =>
      `the otter board spread ${down ? 'falls' : 'rises'} ${amount}${pct}`,
    pull: (up: boolean, amount: string, pct: string) =>
      `the pull at the vessel ${up ? 'rises' : 'falls'} ${amount}${pct}`,
    ah: (down: boolean, amount: string) =>
      `the horizontal opening ${down ? 'falls' : 'rises'} ${amount}`,
    pct: (v: string) => ` (${v}%)`,
    and: ' and ',
    sentence: (from: string, to: string, text: string) => `From ${from} to ${to} of catch, ${text}.`,
  },
  intro:
    'Simulates the haul while the catch comes in: the catch «ball» fills the codend, inflates it and slows it down; the otter boards settle into equilibrium (warp to the vessel, lift from their polar and friction with the chosen seabed).',
  formLabel: 'Haul scenario',
  finalCatch: 'Final catch',
  steps: (list: string) => `Steps: ${list}`,
  catchType: 'Catch type',
  seabedType: 'Seabed type',
  mu: (gear: string, door: string) =>
    `μ gear ${gear} · μ otter board ${door} (estimates, with range)`,
  coupled: 'Coupled otter boards (spread from equilibrium)',
  run: 'Simulate haul',
  running: (s: string) => `Simulating the haul… (≈ ${s} s)`,
  done: (n: number, s: string) => `${n} steps in ${s} s.`,
  unconverged: 'Some step did not fully converge: treat those values with caution.',
  animate: '▶ Animate this haul in the explorer',
  charts: {
    dp: 'Otter board spread',
    pull: 'Pull at the vessel',
    ah: 'Horizontal opening',
    av: 'Vertical opening',
  },
  chartTip: (catchKg: string) => `${catchKg} of catch`,
  chartAria: (title: string) => `${title} by catch`,
  showTable: 'Show haul table',
  tableCaption: 'Progressive haul',
  cols: {
    catchKg: 'Catch',
    doorSpread: 'DS',
    ah: 'AH',
    av: 'AV',
    pull: 'Pull',
    netDrag: 'Net',
    catchDrag: 'Catch',
    friction: 'Friction',
    catchLength: 'Catch length',
    codendDiameter: 'Ø codend',
  },
  shape3dRegion: '3D shape of the haul',
  shape3d: '3D shape',
  step3d: 'Haul step in 3D',
  refs: "Catch model: O'Neill and O'Donoghue (1997); reference trends: Priour and de la Prada (2015). Seabed friction by seabed type is an estimate with a range (TO BE VERIFIED). See chapter 22 of the book.",
  empty:
    'Choose the final catch and the seabed and press «Simulate haul». Each step takes a few seconds.',
};
