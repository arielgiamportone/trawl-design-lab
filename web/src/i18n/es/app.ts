/** Cabecera, modos, pie y saltos de la app. */
export const app = {
  title: 'Diseño de redes de arrastre',
  modesLabel: 'Modo de la interfaz',
  modes: {
    simple: { label: 'Guiado', title: 'Asistente paso a paso con diagnóstico en lenguaje llano' },
    expert: { label: 'Experto', title: 'Todos los parámetros, pestañas y herramientas' },
    aula: {
      label: 'Aula UTN',
      title: 'Ejercicios con corrección, laboratorios guiados, cursos y entregas',
    },
  },
  docs: 'Documentación',
  outdated: (base: string) =>
    `${base}: la API es de otra versión que la app; algunas funciones pueden dar error hasta que se redespliegue`,
  themeLabel: 'Tema de color',
  themes: { auto: 'Auto', light: 'Claro', dark: 'Oscuro' },
  skip: {
    simple: 'Saltar al asistente',
    aula: 'Saltar al aula',
    expert: 'Saltar a resultados',
  },
  main: { simple: 'Diseño guiado', aula: 'Aula UTN', expert: 'Resultados' },
  footer:
    'trawl-design-lab · motor trawlkit · resultados orientativos: verifique con el plano y el informe antes de construir.',
  footerUtn: 'Hecho en la UTN · Ingeniería Pesquera',
};
