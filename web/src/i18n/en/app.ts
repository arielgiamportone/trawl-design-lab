import type { Messages } from '../es';

export const app: Messages['app'] = {
  title: 'Trawl net design',
  modesLabel: 'Interface mode',
  modes: {
    simple: { label: 'Guided', title: 'Step-by-step assistant with a plain-language diagnosis' },
    expert: { label: 'Expert', title: 'Every parameter, tab and tool' },
    aula: {
      label: 'UTN Classroom',
      title: 'Exercises with grading, guided labs, courses and submissions',
    },
  },
  docs: 'Documentation',
  outdated: (base: string) =>
    `${base}: the API is a different version from the app; some features may fail until it is redeployed`,
  themeLabel: 'Colour theme',
  themes: { auto: 'Auto', light: 'Light', dark: 'Dark' },
  skip: {
    simple: 'Skip to the assistant',
    aula: 'Skip to the classroom',
    expert: 'Skip to results',
  },
  main: { simple: 'Guided design', aula: 'UTN Classroom', expert: 'Results' },
  footer:
    'trawl-design-lab · trawlkit engine · indicative results: check against the plan and the report before building.',
  footerUtn: 'Made at UTN · Fisheries Engineering',
};
