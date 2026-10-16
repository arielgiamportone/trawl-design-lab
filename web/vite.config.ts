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

export default defineConfig({
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
