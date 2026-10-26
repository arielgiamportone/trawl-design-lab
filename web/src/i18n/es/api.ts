/** Textos de «api». */
export const api = {
  missingRoute:
    'La API en línea es anterior a esta versión de la app y todavía no tiene esta función. ' +
    'Se actualiza sola unos minutos después de cada cambio; si persiste, hay que redesplegarla ' +
    '(Render → Manual Deploy → Deploy latest commit).',
  cannotConnect: (base: string, err: string) => `No se pudo conectar con la API (${base}): ${err}`,
  classroomOffline: (base: string, err: string) =>
    `El aula necesita conexión con la API (${base}): ${err}`,
  /** Indicador de conexión (``lib/connection.statusLabel``). */
  status: {
    local: 'Sin conexión · motor del teléfono',
    connecting: 'Conectando…',
    waking: 'Despertando la API (puede tardar hasta un minuto)…',
    outdated: 'API desactualizada',
    ok: 'API conectada',
    down: 'API no disponible',
  },
  /** Motor sin conexión (``engine/offline``). */
  offline: {
    stages: {
      python: 'Cargando el intérprete de Python…',
      packages: 'Cargando numpy y pydantic…',
      install: 'Instalando el motor trawlkit…',
    },
    downloadFailed: (what: string) => `no se pudo descargar ${what}`,
    notStarted: 'el motor sin conexión no está iniciado',
    noEngine: 'esta versión de la app no trae el motor sin conexión',
    searching: 'Buscando los archivos…',
    lockFailed: (status: number) => `no se pudo leer la lista de paquetes (${status})`,
    downloading: (i: number, n: number) => `Descargando ${i} de ${n}…`,
    fileFailed: (what: string) => `falló la descarga de ${what}`,
    testing: 'Probando un diseño…',
    testFailed: 'el motor sin conexión no pudo calcular el caso de prueba',
  },
  offlinePanel: {
    starting: 'Empezando…',
    title: 'Uso sin conexión y bajo consumo de datos',
    ready: 'listo sin conexión',
    local: 'calculando en el teléfono',
    intro:
      'Descargue el motor de cálculo una sola vez (unos 15 MB; mejor con wifi). Después, sin señal, el diseño, la simulación, los planos y el informe HTML se calculan en este teléfono (las simulaciones grandes piden bajar la resolución). Los PDF, el refinamiento de la optimización y los cursos del aula siguen necesitando conexión.',
    prepare: 'Preparar uso sin conexión',
    saved: (size: string, version: string) =>
      `Motor guardado (${size}, trawlkit ${version}). Sin señal se usa solo.`,
    where: 'Dónde calcular',
    server: 'En el servidor si hay señal',
    phone: 'Siempre en el teléfono',
    forget: 'Borrar el motor descargado',
    error: 'No se pudo preparar:',
    lowData: 'Bajo consumo de datos: sin vistas 3D ni simulación (pestañas ocultas)',
  },
};
