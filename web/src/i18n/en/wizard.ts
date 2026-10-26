import type { Messages } from '../es';

export const wizard: Messages['wizard'] = {
  verdict: {
    pullTitle: 'Is there enough power?',
    pullShort: (v: string) => `No: ${v} short`,
    pullTight: (pct: number) => `Just: ${pct}% to spare`,
    pullYes: (pct: number) => `Yes: ${pct}% to spare`,
    pullWhy: (speed: string, available: string, demand: string) =>
      `At ${speed} the vessel can pull about ${available} and the net with its otter boards and warps needs about ${demand}`,
    pullFriction: (v: string) => ` (including ${v} of seabed friction)`,
    pullWhyCrit:
      'With that shortfall the vessel cannot reach that speed: lower the speed, use a smaller net or a more powerful vessel.',
    pullWhyWarn: 'It is enough, but with little margin for current, hard ground or catch in the codend.',
    pullWhyOk: 'There is margin for current, ground and catch.',
    pullNoData: 'No data at that speed',
    pullNoDataWhy:
      'The chosen speed is outside the computed ones; adjust the list of speeds in expert mode.',
    maxTitle: 'Maximum towing speed',
    maxNone: 'No feasible speed',
    maxNoneWhy: 'At none of the computed speeds does the pull exceed the drag.',
    maxWhy: 'It is the speed at which the available pull equals the total drag',
    maxRange: (from: string, to: string) => `; the gear can be towed between ${from} and ${to}.`,
    maxMod: (v: string) => ` With the modified net: ${v}.`,
    warpTitle: 'Warp',
    warpNone: 'No warp could be selected from the catalogue.',
    warpOk: (v: string) =>
      `Its breaking load (${v}) covers the required one with the safety factor.`,
    warpFail:
      'Its breaking load does not cover the required one with the safety factor: choose a thicker warp.',
    openingTitle: 'Net mouth',
    openingWhy: 'Width between wingtips × height of the mouth, estimated for the net while fishing.',
    sweptTitle: 'Area swept per hour',
    swept: (thousands: string, unit: string) => `${thousands} thousand ${unit}/h`,
    sweptWhy: (width: string, speed: string) =>
      `Mouth width (${width}) × distance covered in one hour at ${speed}. It is an indicator of fishing performance.`,
  },
};
