/// <reference types="vitest/config" />
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Huella de las rutas de la API con la que se compiló la app (igual que
// trawlkit.api.contract.fingerprint): /health la informa y la app avisa si difiere.
const METHODS = ['get', 'post', 'put', 'patch', 'delete'];
function apiContract(): string {
  const doc = JSON.parse(readFileSync(new URL('./openapi.json', import.meta.url), 'utf8')) as {
    paths: Record<string, Record<string, unknown>>;
  };
  const routes = Object.entries(doc.paths)
    .flatMap(([path, item]) =>
      Object.keys(item)
        .filter((m) => METHODS.includes(m))
        .map((m) => `${m.toUpperCase()} ${path}`),
    )
    .sort();
  return createHash('sha256').update(routes.join('\n')).digest('hex').slice(0, 12);
}

const apiTarget = process.env.TRAWLKIT_API_TARGET ?? 'http://127.0.0.1:8000';
const proxy = {
  '/api': {
    target: apiTarget,
    changeOrigin: true,
    rewrite: (path: string) => path.replace(/^\/api/, ''),
  },
};

// Ruta pública de la app: '/' en desarrollo; '/trawl-design-lab/app/' en GitHub Pages (docs.yml).
const base = (process.env.VITE_BASE ?? '/').replace(/\/?$/, '/');

export default defineConfig({
  base,
  define: { __API_CONTRACT__: JSON.stringify(apiContract()) },
  plugins: [react()],
  server: { proxy },
  preview: { proxy },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          // React aparte (cambia poco y se cachea); Recharts queda en el chunk diferido de Gráficos.
          if (/node_modules\/(react|react-dom|scheduler)\//.test(id)) return 'react';
          return undefined;
        },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
});
