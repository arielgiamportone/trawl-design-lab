import type { Messages } from '../es';

export const sim3d: Messages['sim3d'] = {
  views: { iso: 'Perspective', plan: 'Plan', profile: 'Profile', front: 'Front' },
  viewsLabel: '3D view',
  colorLabel: 'Netting colour',
  tension: 'Tension',
  contact: 'Seabed contact',
  png: 'Download PNG',
  pngName: (v: string) => `net-3d-${v}kn.png`,
  canvasAria: (v: string, ah: string, av: string) =>
    `3D shape of the net at ${v} kn: horizontal opening ${ah} and vertical ${av}; colour = twine tension.`,
  noWebgl: 'This browser has no WebGL: use the plan, profile and front projections below.',
  stageAria: '3D viewer: drag to rotate, wheel to zoom, arrow keys to pan.',
  twineTension: (unit: string) => `Twine tension [${unit}]`,
  onSeabed: 'Netting resting on the seabed',
  contactShare: (pct: string) => `${pct}% of the netting`,
  legend:
    'Solid line: headrope and footrope · dashed: bridles, sweeps and warps · dots: floats · grid: seabed.',
  noWebglAnim: 'This browser has no WebGL: the 3D animation is not available.',
  animStageAria: 'Animated 3D viewer: drag to rotate, wheel to zoom, arrow keys to pan.',
  openingLegend: 'Mesh opening (area / mesh opened square)',
  valuePerTriangle: 'Value per triangle',
  fouled: 'Fouled netting (stronger = higher level)',
  pickHint: 'Click on the netting to see its meshes up close (mesh zoom).',
  animLegend:
    'Plates: otter boards · red arrows: warp pull at the vessel (length ∝ tension) · dots: floats · grid: seabed.',
};
