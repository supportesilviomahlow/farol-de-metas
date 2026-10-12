// Nitro - servidor do Farol de Metas (mesmo modelo da Central de Fretes).
//
// Em desenvolvimento o Vite serve o React na 5173 e faz proxy de /api para a 3010.
// No build, o client vai para client/dist e o Nitro serve esses arquivos como estaticos.
// Nao ha login: e ferramenta de consumo interno (decisao do Silvio, 10/10/2026).
import { defineNitroConfig } from 'nitropack/config';

export default defineNitroConfig({
  srcDir: 'server',
  compatibilityDate: '2026-10-10',
  publicAssets: [{ dir: '../client/dist', maxAge: 60 * 60 }],
  routeRules: {
    '/**': { headers: { 'x-powered-by': 'Farol de Metas' } },
  },
});
