import { useEffect, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { downloadBlob } from '../../lib/download';
import { fmt, fmtFixed } from '../../lib/format';
import {
  buildBuffers,
  cameraPosition,
  RAMP_DARK,
  RAMP_LIGHT,
  contactTriangles,
  type CameraView,
  type ColorMode,
  type SimGeometry,
} from '../../lib/sim3d';
import { useChartColors, useResolvedTheme } from '../../lib/theme';

const VIEWS: { key: CameraView; label: string }[] = [
  { key: 'iso', label: 'Perspectiva' },
  { key: 'plan', label: 'Planta' },
  { key: 'profile', label: 'Perfil' },
  { key: 'front', label: 'Frente' },
];

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') ?? c.getContext('webgl'));
  } catch {
    return false;
  }
}

interface Scene3D {
  renderer: THREE.WebGLRenderer;
  camera: THREE.PerspectiveCamera;
  controls: OrbitControls;
  render: () => void;
  dispose: () => void;
}

/**
 * Forma simulada en 3D: paño coloreado por la tensión del hilo, relingas resaltadas, aparejo y
 * boyas. Órbita con mouse/táctil; flechas giran; vistas estándar y descarga PNG.
 */
export function Net3D({ geometry }: { geometry: SimGeometry }) {
  const theme = useResolvedTheme();
  const colors = useChartColors();
  const ramp = theme === 'dark' ? RAMP_DARK : RAMP_LIGHT;
  const [mode, setMode] = useState<ColorMode>('tension');
  const buffers = useMemo(
    () => buildBuffers(geometry, ramp, mode, colors.s2),
    [geometry, ramp, mode, colors.s2],
  );
  const contactShare = useMemo(() => {
    const t = contactTriangles(geometry);
    return t.length ? t.filter(Boolean).length / t.length : 0;
  }, [geometry]);
  const host = useRef<HTMLDivElement>(null);
  const scene3d = useRef<Scene3D | null>(null);
  const [noGl] = useState(() => !hasWebGL());

  useEffect(() => {
    const el = host.current;
    if (!el || noGl) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    } catch {
      return; // WebGL detectado pero no inicializable: queda el lienzo vacío y las proyecciones
    }
    const width = el.clientWidth || 640;
    const height = el.clientHeight || 420;
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.setSize(width, height);
    renderer.setClearColor(new THREE.Color(colors.surface));
    el.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('role', 'img');
    renderer.domElement.setAttribute(
      'aria-label',
      `Forma 3D de la red a ${fmtFixed(geometry.speed_kn, 1)} kn: abertura horizontal ` +
        `${fmtFixed(geometry.ah_m, 1)} m y vertical ${fmtFixed(geometry.av_m, 2)} m; ` +
        'color = tensión del hilo.',
    );
    renderer.domElement.setAttribute('data-testid', 'net3d-canvas');

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.05, buffers.radius * 80);
    const [cx, cy, cz] = buffers.center;

    const mesh = new THREE.BufferGeometry();
    mesh.setAttribute('position', new THREE.BufferAttribute(buffers.positions, 3));
    mesh.setAttribute('color', new THREE.BufferAttribute(buffers.colors, 3));
    mesh.computeVertexNormals();
    const meshMat = new THREE.MeshBasicMaterial({
      vertexColors: true,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.92,
    });
    scene.add(new THREE.Mesh(mesh, meshMat));
    const wire = new THREE.LineSegments(
      new THREE.WireframeGeometry(mesh),
      new THREE.LineBasicMaterial({ color: colors.grid, transparent: true, opacity: 0.35 }),
    );
    scene.add(wire);

    const lineGeo = (arr: Float32Array) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(arr, 3));
      return g;
    };
    const ropes = new THREE.LineSegments(
      lineGeo(buffers.lines.ropes),
      new THREE.LineBasicMaterial({ color: colors.text }),
    );
    const rigging = new THREE.LineSegments(
      lineGeo(buffers.lines.rigging),
      new THREE.LineDashedMaterial({ color: colors.muted, dashSize: 0.6, gapSize: 0.4 }),
    );
    rigging.computeLineDistances();
    scene.add(ropes, rigging);
    const floats = new THREE.Points(
      lineGeo(buffers.floats),
      new THREE.PointsMaterial({ color: colors.s2, size: 8, sizeAttenuation: false }),
    );
    scene.add(floats);
    // fondo: grilla en z = 0 de la simulación (y = 0 en three.js)
    const grid = new THREE.GridHelper(
      buffers.radius * 4,
      16,
      new THREE.Color(colors.axis),
      new THREE.Color(colors.grid),
    );
    grid.position.set(cx, 0, cz);
    scene.add(grid);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.target.set(cx, cy, cz);
    controls.enableDamping = false;
    controls.listenToKeyEvents(el);
    const render = () => renderer.render(scene, camera);
    controls.addEventListener('change', render);
    camera.position.set(...cameraPosition('iso', buffers.center, buffers.radius));
    camera.lookAt(cx, cy, cz);
    controls.update();
    render();

    const ro =
      typeof ResizeObserver !== 'undefined'
        ? new ResizeObserver(() => {
            const w = el.clientWidth || width;
            const h = el.clientHeight || height;
            renderer.setSize(w, h);
            camera.aspect = w / h;
            camera.updateProjectionMatrix();
            render();
          })
        : null;
    ro?.observe(el);

    scene3d.current = {
      renderer,
      camera,
      controls,
      render,
      dispose: () => {
        ro?.disconnect();
        controls.dispose();
        scene.traverse((o) => {
          const m = o as THREE.Mesh;
          m.geometry?.dispose();
          const mat = m.material as THREE.Material | THREE.Material[] | undefined;
          if (Array.isArray(mat)) mat.forEach((x) => x.dispose());
          else mat?.dispose();
        });
        renderer.dispose();
        renderer.domElement.remove();
      },
    };
    return () => {
      scene3d.current?.dispose();
      scene3d.current = null;
    };
  }, [buffers, colors, geometry, noGl]);

  const setView = (v: CameraView) => {
    const s = scene3d.current;
    if (!s) return;
    s.camera.position.set(...cameraPosition(v, buffers.center, buffers.radius));
    s.controls.target.set(...buffers.center);
    s.controls.update();
    s.render();
  };
  const savePng = () => {
    const s = scene3d.current;
    if (!s) return;
    s.render();
    s.renderer.domElement.toBlob((b) => {
      if (b) downloadBlob(b, `red-3d-${fmtFixed(geometry.speed_kn, 1).replace(',', '_')}kn.png`);
    });
  };

  const gradient = `linear-gradient(to right, ${ramp.join(', ')})`;
  return (
    <figure className="net3d" style={{ margin: 0 }}>
      <div className="net3d-tools">
        <div className="segmented" role="group" aria-label="Vista 3D">
          {VIEWS.map((v) => (
            <button key={v.key} type="button" onClick={() => setView(v.key)}>
              {v.label}
            </button>
          ))}
        </div>
        <div className="segmented" role="group" aria-label="Color del paño">
          <button
            type="button"
            aria-pressed={mode === 'tension'}
            onClick={() => setMode('tension')}
          >
            Tensión
          </button>
          <button
            type="button"
            aria-pressed={mode === 'contact'}
            onClick={() => setMode('contact')}
          >
            Contacto con el fondo
          </button>
        </div>
        <button type="button" className="btn small" onClick={savePng} disabled={noGl}>
          Descargar PNG
        </button>
      </div>
      {noGl ? (
        <div className="alert warn" role="note">
          <span>
            Este navegador no tiene WebGL: use las proyecciones de planta, perfil y frente de abajo.
          </span>
        </div>
      ) : (
        <div
          ref={host}
          className="net3d-stage"
          tabIndex={0}
          aria-label="Visor 3D: arrastre para girar, rueda para acercar, flechas para desplazar."
        />
      )}
      <figcaption className="net3d-legend">
        {mode === 'tension' ? (
          <>
            <span>Tensión del hilo [N]</span>
            <span className="net3d-ramp" style={{ background: gradient }} aria-hidden="true" />
            <span className="net3d-ticks">
              <span>{fmt(Math.round(buffers.range[0]))}</span>
              <span>≥ {fmt(Math.round(buffers.range[1]))}</span>
            </span>
          </>
        ) : (
          <>
            <span>
              <span className="key-rect" style={{ background: colors.s2 }} aria-hidden="true" />{' '}
              Paño apoyado en el fondo
            </span>
            <span className="net3d-contact">{fmtFixed(contactShare * 100, 0)} % del paño</span>
          </>
        )}
        <span className="help">
          Línea llena: lima y burlón · discontinua: bridas, patentes y cables · puntos: boyas ·
          grilla: fondo.
        </span>
      </figcaption>
    </figure>
  );
}
