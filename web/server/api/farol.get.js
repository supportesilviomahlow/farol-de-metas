// GET /api/farol - o ranking pronto, gerado pelo etl/extrair.py (data/farol.json).
//
// O arquivo mora FORA de web/ para o deploy do codigo nao apagar os dados. Relido so quando
// muda (mtime): o botao Atualizar regrava o arquivo e a proxima consulta ja ve o novo.
import { readFile, stat } from 'node:fs/promises';

let cache = { mtime: 0, dados: null };

export default defineEventHandler(async () => {
  let info;
  try {
    info = await stat(ARQUIVO_DADOS);
  } catch {
    throw createError({ statusCode: 503, statusMessage: 'Ainda sem dados: clique em Atualizar para ler os faróis.' });
  }
  if (info.mtimeMs !== cache.mtime) {
    cache = { mtime: info.mtimeMs, dados: JSON.parse(await readFile(ARQUIVO_DADOS, 'utf8')) };
  }
  return cache.dados;
});
