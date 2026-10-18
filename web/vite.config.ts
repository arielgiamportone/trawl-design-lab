/// <reference types="vitest/config" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

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
