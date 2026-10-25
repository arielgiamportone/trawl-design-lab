/// <reference types="vitest/config" />
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';

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
  plugins: [
    react(),
    // App instalable que funciona sin red (Fase 13): el service worker guarda la app; el motor
    // Pyodide y la wheel de trawlkit se guardan en «trawl-offline-v1» al pulsar «Preparar uso sin
    // conexión» (src/engine/offline.ts) y se sirven desde ahí.
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'trawl-design-lab · Diseño de redes de arrastre',
        short_name: 'Redes de arrastre',
        description: 'Diseño, armado y costo de redes de arrastre, también sin conexión.',
        lang: 'es',
        theme_color: '#1c5cab',
        background_color: '#fcfcfb',
        display: 'standalone',
        start_url: '.',
        scope: '.',
        icons: [
          { src: 'pwa-192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        // three.js (vistas 3D) no se precarga: se guarda al abrir una vista 3D por primera vez.
        globIgnores: ['py/**', 'assets/OrbitControls-*.js'],
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024,
        navigateFallback: 'index.html',
        runtimeCaching: [
          {
            urlPattern: /\/assets\/[^/]+-[A-Za-z0-9_-]{8}\.js$/,
            handler: 'CacheFirst',
            options: { cacheName: 'trawl-assets' },
          },
          {
            urlPattern: /^https:\/\/cdn\.jsdelivr\.net\/pyodide\//,
            handler: 'CacheFirst',
            options: { cacheName: 'trawl-offline-v1' },
          },
          {
            // La wheel lleva el hash del contenido en la ruta: nunca cambia.
            urlPattern: /\/py\/[0-9a-f]{12}\/[^/]+\.whl$/,
            handler: 'CacheFirst',
            options: { cacheName: 'trawl-offline-v1' },
          },
          {
            urlPattern: /\/py\/manifest\.json$/,
            handler: 'NetworkFirst',
            options: { cacheName: 'trawl-offline-v1', networkTimeoutSeconds: 5 },
          },
        ],
      },
    }),
  ],
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
