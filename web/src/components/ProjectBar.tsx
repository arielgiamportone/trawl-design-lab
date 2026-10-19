import { useEffect, useId, useRef, useState, type ChangeEvent } from 'react';
import { downloadBlob } from '../lib/download';
import {
  deleteProject,
  listProjects,
  parseProjectFile,
  projectFileName,
  saveProject,
  toProjectFile,
  type ProjectFile,
} from '../lib/projects';
import { useCase } from '../state/useCase';

function isEditable(el: EventTarget | null): boolean {
  const t = el as HTMLElement | null;
  if (!t) return false;
  return t.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName);
}

/** Barra de proyecto: deshacer/rehacer, guardar/abrir en el navegador, exportar/importar. */
export function ProjectBar() {
  const { state, replace, reset, undo, redo, canUndo, canRedo } = useCase();
  const [projects, setProjects] = useState<ProjectFile[]>(listProjects);
  const [name, setName] = useState('');
  const [message, setMessage] = useState<{ tone: 'good' | 'crit'; text: string } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const ids = useId();

  // Atajos: Ctrl/Cmd+Z deshace, Ctrl/Cmd+Shift+Z o Ctrl+Y rehace (fuera de campos de texto,
  // donde rige el deshacer propio del navegador).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (!(e.ctrlKey || e.metaKey) || isEditable(e.target)) return;
      const k = e.key.toLowerCase();
      if (k === 'z' && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if ((k === 'z' && e.shiftKey) || k === 'y') {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [undo, redo]);

  const save = () => {
    const n = name.trim();
    if (!n) {
      setMessage({ tone: 'crit', text: 'Escriba un nombre para el proyecto.' });
      return;
    }
    setProjects(saveProject(toProjectFile(n, state)));
    setMessage({ tone: 'good', text: `Guardado «${n}» en este navegador.` });
  };
  const open = (p: ProjectFile) => {
    replace(p.case);
    setName(p.name);
    setMessage({ tone: 'good', text: `Abierto «${p.name}».` });
  };
  const exportFile = () => {
    const p = toProjectFile(name || 'proyecto', state);
    downloadBlob(
      new Blob([JSON.stringify(p, null, 2)], { type: 'application/json' }),
      projectFileName(p.name),
    );
  };
  const importFile = async (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    e.target.value = '';
    if (!file) return;
    const parsed = parseProjectFile(await file.text());
    if (!parsed.ok) {
      setMessage({ tone: 'crit', text: parsed.error });
      return;
    }
    open(parsed.project);
  };

  return (
    <div className="project-bar" role="toolbar" aria-label="Proyecto">
      <button
        type="button"
        className="btn small ghost"
        onClick={undo}
        disabled={!canUndo}
        title="Deshacer (Ctrl+Z)"
      >
        ↶ Deshacer
      </button>
      <button
        type="button"
        className="btn small ghost"
        onClick={redo}
        disabled={!canRedo}
        title="Rehacer (Ctrl+Shift+Z)"
      >
        ↷ Rehacer
      </button>
      <details className="project-menu">
        <summary className="btn small">Proyectos</summary>
        <div className="project-pop card card-pad">
          <label htmlFor={`${ids}-name`} className="label">
            Nombre del proyecto
          </label>
          <div className="param-row">
            <input
              id={`${ids}-name`}
              type="text"
              value={name}
              placeholder="p. ej. Red Beagle 180 HP"
              onChange={(e) => setName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && save()}
            />
            <button type="button" className="btn small primary" onClick={save}>
              Guardar
            </button>
          </div>
          {message && (
            <p className={`project-msg ${message.tone}`} role="status">
              {message.text}
            </p>
          )}
          <div className="project-actions">
            <button type="button" className="btn small" onClick={exportFile}>
              Exportar archivo
            </button>
            <button type="button" className="btn small" onClick={() => fileRef.current?.click()}>
              Importar archivo
            </button>
            <button type="button" className="btn small ghost" onClick={reset}>
              Caso nuevo
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".json,application/json"
              hidden
              aria-label="Archivo de proyecto"
              onChange={(e) => void importFile(e)}
            />
          </div>
          <h3 className="project-list-title">Guardados en este navegador</h3>
          {projects.length === 0 ? (
            <p className="help">Todavía no hay proyectos guardados.</p>
          ) : (
            <ul className="project-list">
              {projects.map((p) => (
                <li key={p.name}>
                  <span className="project-name">
                    {p.name}
                    <span className="help">
                      {new Date(p.savedAt).toLocaleString('es-AR', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      })}
                    </span>
                  </span>
                  <button type="button" className="btn small" onClick={() => open(p)}>
                    Abrir
                  </button>
                  <button
                    type="button"
                    className="btn small ghost"
                    aria-label={`Eliminar ${p.name}`}
                    onClick={() => setProjects(deleteProject(p.name))}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </details>
    </div>
  );
}
