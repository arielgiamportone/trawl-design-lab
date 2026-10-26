/** Proyectos: guardar/abrir casos con nombre (en el navegador) y exportar/importar archivos. */
import { msg } from '../i18n';
import { sanitizeCase, type CaseState } from '../state/model';
import { loadJson, saveJson } from './storage';

export const PROJECT_FORMAT = 'trawl-design-lab/project';
export const PROJECTS_KEY = 'trawl-design-lab:projects:v1';
export const MAX_PROJECTS = 30;

export interface ProjectFile {
  format: typeof PROJECT_FORMAT;
  version: 1;
  name: string;
  savedAt: string;
  case: CaseState;
}

export function toProjectFile(name: string, state: CaseState, now = new Date()): ProjectFile {
  return {
    format: PROJECT_FORMAT,
    version: 1,
    name: name.trim() || msg().state.projects.untitled,
    savedAt: now.toISOString(),
    case: state,
  };
}

export type ParsedProject = { ok: true; project: ProjectFile } | { ok: false; error: string };

/** Lee un archivo de proyecto; el caso se normaliza (tolera campos viejos o faltantes). */
export function parseProjectFile(text: string): ParsedProject {
  let raw: unknown;
  try {
    raw = JSON.parse(text);
  } catch {
    return { ok: false, error: msg().state.projects.notJson };
  }
  const r = raw as Partial<ProjectFile> | null;
  if (!r || typeof r !== 'object' || r.format !== PROJECT_FORMAT) {
    return { ok: false, error: msg().state.projects.notProject };
  }
  if (r.version !== 1) {
    return { ok: false, error: msg().state.projects.badVersion(String(r.version)) };
  }
  return {
    ok: true,
    project: {
      format: PROJECT_FORMAT,
      version: 1,
      name: typeof r.name === 'string' && r.name.trim() ? r.name : msg().state.projects.imported,
      savedAt: typeof r.savedAt === 'string' ? r.savedAt : new Date(0).toISOString(),
      case: sanitizeCase(r.case),
    },
  };
}

/** Nombre de archivo seguro: «Red Beagle 2026» → ``red-beagle-2026.trawl.json``. */
export function projectFileName(name: string): string {
  const slug = name
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
  return `${slug || msg().state.projects.slug}.trawl.json`;
}

/** Proyectos guardados en este navegador, del más reciente al más viejo. */
export function listProjects(): ProjectFile[] {
  const raw = loadJson<unknown[]>(PROJECTS_KEY);
  if (!Array.isArray(raw)) return [];
  const out: ProjectFile[] = [];
  for (const item of raw) {
    const p = parseProjectFile(JSON.stringify(item));
    if (p.ok) out.push(p.project);
  }
  return out.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
}

/** Guarda (o reemplaza, por nombre) un proyecto y devuelve la lista actualizada. */
export function saveProject(project: ProjectFile): ProjectFile[] {
  const rest = listProjects().filter((p) => p.name !== project.name);
  const next = [project, ...rest].slice(0, MAX_PROJECTS);
  saveJson(PROJECTS_KEY, next);
  return next;
}

export function deleteProject(name: string): ProjectFile[] {
  const next = listProjects().filter((p) => p.name !== name);
  saveJson(PROJECTS_KEY, next);
  return next;
}
