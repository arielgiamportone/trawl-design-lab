import type { Messages } from '../es';

export const interactive: Messages['interactive'] = {
  title: 'Interactive design',
  sub: 'Tap a panel and drag its handles (depth and edges) or use the arrow keys; the case is recomputed on release. Ctrl+Z undoes.',
  outline: 'Original outline',
  loading: 'Loading the plan…',
  edited: (n: number) =>
    n === 0
      ? 'No changes from the base net.'
      : `${n} ${n === 1 ? 'value' : 'values'} edited (panels highlighted). The dashed line is the original net.`,
  stretched:
    'The plan is drawn at stretched mesh: width = meshes × mesh size; depth = N × mesh size.',
  canvasLabel:
    'Editable net plan. Tab moves through the panels; Enter selects; arrow keys adjust meshes (Shift ×10); +/− zoom; 0 full view; Esc deselects.',
  planeTitle: (plane: string) => `${plane.charAt(0).toUpperCase()}${plane.slice(1)} plane`,
  sides: { left: 'left', right: 'right', center: 'centre' },
  panelLabel: (
    id: string,
    where: string,
    top: number,
    bottom: number,
    depth: number,
    mesh: string,
  ) => `Panel ${id} (${where}): ${top} → ${bottom} meshes, N ${depth}, mesh size ${mesh}`,
  dragHandle: (handle: string, id: string) => `Drag the ${handle} of panel ${id}`,
  dragTipHead: (id: string, handle: string) => `Panel ${id} · ${handle}:`,
  dragTipTail: (before: number) => `meshes (before ${before}) · Esc cancels`,
  zoomIn: 'Zoom in',
  zoomOut: 'Zoom out',
  fullView: 'Full view',
  inspector: {
    panel: (id: string) => `Panel ${id}`,
    close: 'Close the panel',
    plane: (plane: string) => `${plane} plane`,
    minus: (field: string) => `Subtract 1 from ${field}`,
    plus: (field: string) => `Add 1 to ${field}`,
    orientation: 'Mesh orientation',
    squareHelp: 'In square mesh, meshes count squares whose side is one bar (mesh size / 2).',
    reset: 'Reset this panel',
  },
  impact: {
    calculating: 'Calculating…',
    label: 'Impact of the changes',
    at: (speed: string) => ` at ${speed} kn`,
    noChange: 'no change',
    baseNet: 'base net',
  },
};
