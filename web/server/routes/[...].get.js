// Fallback das telas: /mes, /ytd e /simulador sao rotas do React Router. Sem isto, recarregar a
// pagina (F5) ou abrir um link direto dava 404 no servidor. Os arquivos estaticos (js, css,
// png) sao servidos antes pelo Nitro e nunca chegam aqui.
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const CANDIDATOS = [
  path.resolve(process.cwd(), '.output/public/index.html'), // producao (run.sh roda da pasta do app)
  path.resolve(process.cwd(), 'client/dist/index.html'),    // nitro dev depois de um build
];
let html = null;

export default defineEventHandler(async (event) => {
  if (event.path.startsWith('/api/')) throw createError({ statusCode: 404, statusMessage: 'Rota de API inexistente' });
  if (!html) {
    for (const c of CANDIDATOS) {
      try { html = await readFile(c, 'utf8'); break; } catch {}
    }
  }
  if (!html) throw createError({ statusCode: 404, statusMessage: 'Front nao gerado: rode npm run build' });
  setHeader(event, 'content-type', 'text/html; charset=utf-8');
  return html;
});
