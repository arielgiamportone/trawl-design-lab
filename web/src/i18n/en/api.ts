import type { Messages } from '../es';

export const api: Messages['api'] = {
  missingRoute:
    'The online API is older than this version of the app and does not have this feature yet. ' +
    'It updates itself a few minutes after each change; if this persists, it has to be redeployed ' +
    '(Render → Manual Deploy → Deploy latest commit).',
  cannotConnect: (base: string, err: string) => `Could not connect to the API (${base}): ${err}`,
  classroomOffline: (base: string, err: string) =>
    `The classroom needs a connection to the API (${base}): ${err}`,
  status: {
    local: 'Offline · on-device engine',
    connecting: 'Connecting…',
    waking: 'Waking up the API (this may take up to a minute)…',
    outdated: 'API out of date',
    ok: 'API connected',
    down: 'API unavailable',
  },
  offline: {
    stages: {
      python: 'Loading the Python interpreter…',
      packages: 'Loading numpy and pydantic…',
      install: 'Installing the trawlkit engine…',
    },
    downloadFailed: (what: string) => `could not download ${what}`,
    notStarted: 'the offline engine has not been started',
    noEngine: 'this version of the app does not include the offline engine',
    searching: 'Looking for the files…',
    lockFailed: (status: number) => `could not read the package list (${status})`,
    downloading: (i: number, n: number) => `Downloading ${i} of ${n}…`,
    fileFailed: (what: string) => `download of ${what} failed`,
    testing: 'Testing a design…',
    testFailed: 'the offline engine could not compute the test case',
  },
  offlinePanel: {
    starting: 'Starting…',
    title: 'Offline use and low data usage',
    ready: 'ready offline',
    local: 'computing on the device',
    intro:
      'Download the calculation engine once (about 15 MB; preferably over wifi). After that, without signal, the design, the simulation, the plans and the HTML report are computed on this device (large simulations ask you to lower the resolution). PDFs, the refinement of the optimization and the classroom courses still need a connection.',
    prepare: 'Prepare offline use',
    saved: (size: string, version: string) =>
      `Engine saved (${size}, trawlkit ${version}). It is used automatically without signal.`,
    where: 'Where to compute',
    server: 'On the server when there is signal',
    phone: 'Always on the device',
    forget: 'Delete the downloaded engine',
    error: 'Could not prepare:',
    lowData: 'Low data usage: no 3D views or simulation (tabs hidden)',
  },
};
