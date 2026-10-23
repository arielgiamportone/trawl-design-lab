/** Grabación de la animación del canvas de WebGL como video WebM (MediaRecorder). */

export function canRecord(canvas: HTMLCanvasElement | null): canvas is HTMLCanvasElement {
  return (
    !!canvas &&
    typeof MediaRecorder !== 'undefined' &&
    typeof (canvas as { captureStream?: unknown }).captureStream === 'function'
  );
}

/**
 * Recorre la línea de tiempo de 0 a ``n`` en ``n · segmentMs`` milisegundos llamando a ``setT`` en
 * cada cuadro, mientras graba el canvas; devuelve el video.
 */
export async function recordTimeline(
  canvas: HTMLCanvasElement,
  n: number,
  setT: (t: number) => void,
  segmentMs = 1200,
): Promise<Blob> {
  const stream = canvas.captureStream(30);
  const type = MediaRecorder.isTypeSupported('video/webm;codecs=vp9')
    ? 'video/webm;codecs=vp9'
    : 'video/webm';
  const rec = new MediaRecorder(stream, { mimeType: type });
  const chunks: Blob[] = [];
  rec.ondataavailable = (e) => {
    if (e.data.size) chunks.push(e.data);
  };
  const stopped = new Promise<void>((resolve) => {
    rec.onstop = () => resolve();
  });
  rec.start();
  const total = Math.max(1, n) * segmentMs;
  const start = performance.now();
  await new Promise<void>((resolve) => {
    const tick = (now: number) => {
      const t = Math.min(n, ((now - start) / total) * n);
      setT(t);
      if (t < n) requestAnimationFrame(tick);
      else resolve();
    };
    requestAnimationFrame(tick);
  });
  await new Promise((res) => setTimeout(res, 300));
  rec.stop();
  await stopped;
  return new Blob(chunks, { type: 'video/webm' });
}
