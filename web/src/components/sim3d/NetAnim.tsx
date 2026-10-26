import { forwardRef, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { frameIndex, nodesAt, type Frame, type Geometry } from '../../lib/explore';
import { fmt } from '../../lib/format';
import {
  cameraPosition,
  CONTACT_Z,
  RAMP_DARK,
  RAMP_LIGHT,
  rampColor,
  tensionOf,
  tensionRange,
  type CameraView,
} from '../../lib/sim3d';
import { useChartColors, useResolvedTheme } from '../../lib/theme';
import { useT } from '../../i18n';
import { toDisplay, unitLabel } from '../../lib/units';

export type AnimColor = 'tension' | 'contact' | 'fouling' | 'opening' | 'values';
export type AnimScope = 'net' | 'full';

export interface NetAnimHandle {
  /** Canvas de WebGL (para exportar PNG o grabar video). */
  canvas: () => HTMLCanvasElement | null;
  render: () => void;
}

interface Props {
  geometry: Geometry;
  frames: Frame[];
  /** Posición en la línea de tiempo, de 0 a frames.length − 1 (interpola entre estados). */
  t: number;
  color: AnimColor;
  scope: AnimScope;
  label: string;
  /** Valor por triángulo para ``color = 'values'`` (null = sin dato, gris). */
  triValues?: (number | null)[];
  /** Leyenda de ``triValues`` (p. ej. «Talla máxima que pasa [cm]»). */
  valuesLabel?: string;
  /** Clic sobre un triángulo del paño (para el zoom por malla). */
  onPick?: (triangle: number) => void;
  /** Triángulo resaltado. */
  picked?: number | null;
}

/** Fracción abierta de la malla (sen β) interpolada entre dos cuadros. */
function openingAt(a: Frame, b: Frame, k: number, f: number): number {
  const oa = (a as Frame & { opening_deg?: number[] }).opening_deg?.[k];
  const ob = (b as Frame & { opening_deg?: number[] }).opening_deg?.[k] ?? oa;
  if (oa === undefined || ob === undefined) return 0;
  return Math.max(0, Math.sin(((oa + (ob - oa) * f) * Math.PI) / 180));
}

/** Escala de color estable para toda la animación: tensión hasta el p95 de todos los cuadros. */
function globalTensionMax(frames: Frame[]): number {
  const all: number[] = [];
  for (const f of frames) for (const v of f.twine_tension_n) all.push(tensionOf(v));
  return tensionRange(all)[1];
}

function bbox(frames: Frame[], idx: number[] | null) {
  const f0 = frames[0];
  const min = [Infinity, Infinity, Infinity];
  const max = [-Infinity, -Infinity, -Infinity];
  if (!f0) return { center: [0, 0, 0] as [number, number, number], radius: 1 };
  const nodes = idx ?? f0.nodes.map((_, i) => i);
  for (const f of [f0, frames[frames.length - 1] ?? f0]) {
    for (const i of nodes) {
      const p = f.nodes[i];
      if (!p) continue;
      const q = [p[0], p[2], p[1]];
      for (let k = 0; k < 3; k++) {
        min[k] = Math.min(min[k] as number, q[k] as number);
        max[k] = Math.max(max[k] as number, q[k] as number);
      }
    }
  }
  const center = [0, 1, 2].map((k) => ((min[k] as number) + (max[k] as number)) / 2) as [
    number,
    number,
    number,
  ];
  const radius = Math.hypot(...[0, 1, 2].map((k) => (max[k] as number) - (min[k] as number))) / 2;
  return { center, radius: radius || 1 };
}

function hasWebGL(): boolean {
  try {
    const c = document.createElement('canvas');
    return !!(c.getContext('webgl2') ?? c.getContext('webgl'));
  } catch {
    return false;
  }
}

/**
 * Aparejo animado: paño, relingas, bridas, patentes, cables y portones en el estado ``t``
 * (interpolado entre los equilibrios calculados), coloreado por tensión, contacto o ensuciamiento.
 */
export const NetAnim = forwardRef<NetAnimHandle, Props>(function NetAnim(
  { geometry, frames, t, color, scope, label, triValues, valuesLabel, onPick, picked = null },
  ref,
) {
  const theme = useResolvedTheme();
  const colors = useChartColors();
  const T = useT().sim3d;
  const ramp = theme === 'dark' ? RAMP_DARK : RAMP_LIGHT;
  const host = useRef<HTMLDivElement>(null);
  const [noGl] = useState(() => !hasWebGL());
  const tMax = useMemo(() => globalTensionMax(frames), [frames]);
  const vMax = useMemo(() => {
    const vals = (triValues ?? []).filter((v): v is number => v !== null && Number.isFinite(v));
    return vals.length ? Math.max(...vals) : 1;
  }, [triValues]);
  const pickRef = useRef(onPick);
  const pickedRef = useRef(picked);
  useEffect(() => {
    pickRef.current = onPick;
    pickedRef.current = picked;
  });
  // Encuadre «red»: paño y portones (sin los cables, que miden cientos de metros).
  const netNodes = useMemo(
    () => [...new Set([...geometry.triangles.flat(), ...geometry.doors])],
    [geometry],
  );
  const frame = useMemo(
    () => bbox(frames, scope === 'net' ? netNodes : null),
    [frames, scope, netNodes],
  );
  const scene3d = useRef<{
    renderer: THREE.WebGLRenderer;
    update: (t: number) => void;
    render: () => void;
    setView: (v: CameraView) => void;
    dispose: () => void;
  } | null>(null);

  useImperativeHandle(ref, () => ({
    canvas: () => scene3d.current?.renderer.domElement ?? null,
    render: () => scene3d.current?.render(),
  }));

  useEffect(() => {
    const el = host.current;
    if (!el || noGl) return;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, preserveDrawingBuffer: true });
    } catch {
      return;
    }
    const width = el.clientWidth || 640;
    const height = el.clientHeight || 420;
    renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    renderer.setSize(width, height);
    renderer.setClearColor(new THREE.Color(colors.surface));
    el.appendChild(renderer.domElement);
    const canvas = renderer.domElement;
    canvas.setAttribute('role', 'img');
    canvas.setAttribute('aria-label', label);
    canvas.setAttribute('data-testid', 'netanim-canvas');

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(40, width / height, 0.05, frame.radius * 100);
    const tris = geometry.triangles;
    const nTri = tris.length;
    const meshGeo = new THREE.BufferGeometry();
    const pos = new Float32Array(nTri * 9);
    const col = new Float32Array(nTri * 9);
    meshGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    meshGeo.setAttribute('color', new THREE.BufferAttribute(col, 3));
    const mesh = new THREE.Mesh(
      meshGeo,
      new THREE.MeshBasicMaterial({
        vertexColors: true,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.92,
      }),
    );
    scene.add(mesh);

    const kinds = geometry.bar_kind;
    const groups: Record<'ropes' | 'rigging' | 'warps', number[]> = {
      ropes: [],
      rigging: [],
      warps: [],
    };
    kinds.forEach((k, i) => {
      if (k === 'headrope' || k === 'footrope') groups.ropes.push(i);
      else if (k === 'warp') groups.warps.push(i);
      else groups.rigging.push(i);
    });
    const lineObj = (bars: number[], mat: THREE.LineBasicMaterial) => {
      const g = new THREE.BufferGeometry();
      g.setAttribute('position', new THREE.BufferAttribute(new Float32Array(bars.length * 6), 3));
      const obj = new THREE.LineSegments(g, mat);
      scene.add(obj);
      return { obj, bars };
    };
    const lines = [
      lineObj(groups.ropes, new THREE.LineBasicMaterial({ color: colors.text })),
      lineObj(groups.rigging, new THREE.LineBasicMaterial({ color: colors.muted })),
      lineObj(groups.warps, new THREE.LineBasicMaterial({ color: colors.text2 })),
    ];
    const floatGeo = new THREE.BufferGeometry();
    floatGeo.setAttribute(
      'position',
      new THREE.BufferAttribute(new Float32Array(geometry.float_nodes.length * 3), 3),
    );
    scene.add(
      new THREE.Points(
        floatGeo,
        new THREE.PointsMaterial({ color: colors.s2, size: 7, sizeAttenuation: false }),
      ),
    );
    // Portones: placas de 1,9 × 0,95 m orientadas según el cable.
    const doorMeshes = geometry.doors.map(() => {
      const m = new THREE.Mesh(
        new THREE.BoxGeometry(1.9, 0.95, 0.08),
        new THREE.MeshBasicMaterial({ color: colors.s4 }),
      );
      scene.add(m);
      return m;
    });
    // Flechas de tiro en el buque (largo ∝ tensión del cable).
    const arrows = geometry.warps.map(() => {
      const a = new THREE.ArrowHelper(
        new THREE.Vector3(-1, 0, 0),
        new THREE.Vector3(),
        1,
        new THREE.Color(colors.critical).getHex(),
      );
      scene.add(a);
      return a;
    });
    const grid = new THREE.GridHelper(
      frame.radius * 4,
      16,
      new THREE.Color(colors.axis),
      new THREE.Color(colors.grid),
    );
    grid.position.set(frame.center[0], 0, frame.center[2]);
    scene.add(grid);

    let nodeBuf: Float32Array | undefined;
    const P = (k: number): [number, number, number] => {
      const b = nodeBuf as Float32Array;
      return [b[3 * k] as number, b[3 * k + 2] as number, b[3 * k + 1] as number];
    };
    const restColor = rampColor(0, ramp);
    const hit = rampColor(0, [colors.s2, colors.s2]);
    const fouled = rampColor(0, [colors.s3, colors.s3]);
    const mark = rampColor(0, [colors.s4, colors.s4]);
    const none = rampColor(0, [colors.grid, colors.grid]);
    const update = (tt: number) => {
      nodeBuf = nodesAt(frames, tt, nodeBuf);
      const { i, f } = frameIndex(tt, frames.length);
      const a = frames[i] as Frame;
      const b = (frames[i + 1] ?? a) as Frame;
      for (let k = 0; k < nTri; k++) {
        const tri = tris[k] as [number, number, number];
        let c: [number, number, number];
        if (color === 'contact') {
          c = tri.every((n) => (nodeBuf as Float32Array)[3 * n + 2]! <= CONTACT_Z)
            ? hit
            : restColor;
        } else if (color === 'fouling') {
          const fv = (a.fouling_tri[k] ?? 0) * (1 - f) + (b.fouling_tri[k] ?? 0) * f;
          const c0 = rampColor(0, ramp);
          c = [0, 1, 2].map((j) => c0[j]! + (fouled[j]! - c0[j]!) * Math.min(1, fv)) as [
            number,
            number,
            number,
          ];
        } else if (color === 'opening') {
          c = rampColor(openingAt(a, b, k, f), ramp);
        } else if (color === 'values') {
          const v = triValues?.[k];
          c = v === null || v === undefined ? none : rampColor(v / vMax, ramp);
        } else {
          const ta = tensionOf(a.twine_tension_n[k] ?? 0);
          const tb = tensionOf(b.twine_tension_n[k] ?? 0);
          c = rampColor((ta + (tb - ta) * f) / tMax, ramp);
        }
        if (pickedRef.current === k) c = mark;
        for (let j = 0; j < 3; j++) {
          pos.set(P(tri[j] as number), k * 9 + j * 3);
          col.set(c, k * 9 + j * 3);
        }
      }
      meshGeo.attributes.position!.needsUpdate = true;
      meshGeo.attributes.color!.needsUpdate = true;
      for (const { obj, bars } of lines) {
        const arr = (obj.geometry.attributes.position as THREE.BufferAttribute)
          .array as Float32Array;
        bars.forEach((bi, j) => {
          const [n0, n1] = geometry.bars[bi] as [number, number];
          arr.set(P(n0), j * 6);
          arr.set(P(n1), j * 6 + 3);
        });
        obj.geometry.attributes.position!.needsUpdate = true;
        obj.geometry.computeBoundingSphere();
      }
      const fa = floatGeo.attributes.position!.array as Float32Array;
      geometry.float_nodes.forEach((n, j) => fa.set(P(n), j * 3));
      floatGeo.attributes.position!.needsUpdate = true;
      geometry.doors.forEach((d, j) => {
        const m = doorMeshes[j] as THREE.Mesh;
        const p = P(d);
        m.position.set(...p);
        const w = geometry.warps[j];
        const nxt: [number, number, number] =
          w && w[1] !== undefined ? P(w[1]) : [p[0] - 1, p[1], p[2]];
        const yaw = Math.atan2(-(nxt[2] - p[2]), nxt[0] - p[0]);
        // Placa vertical con un ángulo de ataque de ~30° respecto del rumbo, abierta hacia afuera.
        const out = p[2] >= 0 ? 1 : -1;
        m.rotation.set(0, yaw + out * 0.52, 0);
      });
      geometry.warps.forEach((w, j) => {
        const last = w[w.length - 1];
        const prev = w[w.length - 2];
        if (last === undefined || prev === undefined) return;
        const tip = new THREE.Vector3(...P(last));
        const dir = new THREE.Vector3(...P(last)).sub(new THREE.Vector3(...P(prev))).normalize();
        const barIdx = geometry.bars.findIndex(([x0, x1]) => x0 === prev && x1 === last);
        const ta = a.bar_tension_n[barIdx] ?? 0;
        const tb = b.bar_tension_n[barIdx] ?? 0;
        const tension = ta + (tb - ta) * f;
        const len = Math.max(0.5, (tension / 9.80665 / 1000) * frame.radius * 0.6);
        const arrow = arrows[j] as THREE.ArrowHelper;
        arrow.position.copy(tip);
        arrow.setDirection(dir);
        arrow.setLength(len, Math.min(len * 0.3, 3), Math.min(len * 0.15, 1.5));
      });
    };

    // Clic (sin arrastre) sobre el paño: triángulo elegido (faceIndex = índice del triángulo).
    const ray = new THREE.Raycaster();
    let down: [number, number] | null = null;
    const onDown = (e: PointerEvent) => {
      down = [e.clientX, e.clientY];
    };
    const onUp = (e: PointerEvent) => {
      if (!down || !pickRef.current) return;
      const moved = Math.hypot(e.clientX - down[0], e.clientY - down[1]);
      down = null;
      if (moved > 4) return;
      const rect = canvas.getBoundingClientRect();
      const ndc = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1,
      );
      ray.setFromCamera(ndc, camera);
      const hitTri = ray.intersectObject(mesh)[0];
      if (hitTri?.faceIndex !== undefined && hitTri.faceIndex !== null) {
        pickRef.current(hitTri.faceIndex);
      }
    };
    canvas.addEventListener('pointerdown', onDown);
    canvas.addEventListener('pointerup', onUp);
    const controls = new OrbitControls(camera, canvas);
    controls.target.set(...frame.center);
    controls.listenToKeyEvents(el);
    const render = () => renderer.render(scene, camera);
    controls.addEventListener('change', render);
    const setView = (v: CameraView) => {
      camera.position.set(...cameraPosition(v, frame.center, frame.radius));
      controls.target.set(...frame.center);
      controls.update();
      render();
    };
    setView('iso');
    update(0);
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
      update,
      render,
      setView,
      dispose: () => {
        canvas.removeEventListener('pointerdown', onDown);
        canvas.removeEventListener('pointerup', onUp);
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
        canvas.remove();
      },
    };
    return () => {
      scene3d.current?.dispose();
      scene3d.current = null;
    };
    // La escena se rearma al cambiar geometría, cuadros, color, encuadre o tema; ``t`` sólo
    // actualiza los buffers (efecto de abajo).
  }, [geometry, frames, color, frame, colors, ramp, tMax, noGl, label, triValues, vMax]);

  useEffect(() => {
    const s = scene3d.current;
    if (!s) return;
    s.update(t);
    s.render();
  }, [t, geometry, frames, color, frame, colors, picked]);

  if (noGl) {
    return (
      <div className="alert warn" role="note">
        <span>{T.noWebglAnim}</span>
      </div>
    );
  }
  const gradient = `linear-gradient(to right, ${ramp.join(', ')})`;
  return (
    <figure className="net3d" style={{ margin: 0 }}>
      <div className="net3d-tools">
        <div className="segmented" role="group" aria-label={T.viewsLabel}>
          {(['iso', 'plan', 'profile', 'front'] as CameraView[]).map((v) => (
            <button key={v} type="button" onClick={() => scene3d.current?.setView(v)}>
              {T.views[v]}
            </button>
          ))}
        </div>
      </div>
      <div ref={host} className="net3d-stage" tabIndex={0} aria-label={T.animStageAria} />
      <figcaption className="net3d-legend">
        {color === 'tension' ? (
          <>
            <span>{T.twineTension(unitLabel('N'))}</span>
            <span className="net3d-ramp" style={{ background: gradient }} aria-hidden="true" />
            <span className="net3d-ticks">
              <span>0</span>
              <span>≥ {fmt(Math.round(toDisplay(tMax, 'N')))}</span>
            </span>
          </>
        ) : color === 'opening' || color === 'values' ? (
          <>
            <span>
              {color === 'opening' ? T.openingLegend : (valuesLabel ?? T.valuePerTriangle)}
            </span>
            <span className="net3d-ramp" style={{ background: gradient }} aria-hidden="true" />
            <span className="net3d-ticks">
              <span>0</span>
              <span>{color === 'opening' ? '1' : fmt(Math.round(vMax))}</span>
            </span>
          </>
        ) : color === 'contact' ? (
          <span>
            <span className="key-rect" style={{ background: colors.s2 }} aria-hidden="true" />{' '}
            {T.onSeabed}
          </span>
        ) : (
          <span>
            <span className="key-rect" style={{ background: colors.s3 }} aria-hidden="true" />{' '}
            {T.fouled}
          </span>
        )}
        {onPick && (
          <span className="help">{T.pickHint}</span>
        )}
        <span className="help">{T.animLegend}</span>
      </figcaption>
    </figure>
  );
});
