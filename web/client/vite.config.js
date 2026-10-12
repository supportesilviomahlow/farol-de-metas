// Vite - front React do Farol de Metas. Em desenvolvimento, /api vai para o Nitro (3010).
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import tailwind from '@tailwindcss/vite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const raiz = path.dirname(fileURLToPath(import.meta.url));
const SERVIDOR = process.env.FAROL_SERVIDOR || 'http://localhost:3010';

export default defineConfig({
  root: raiz,
  plugins: [react(), tailwind()],
  resolve: { alias: { '@': path.join(raiz, 'src') } },
  server: {
    port: 5173,
    proxy: { '/api': { target: SERVIDOR, changeOrigin: true } },
  },
  build: { outDir: path.join(raiz, 'dist'), emptyOutDir: true },
});
