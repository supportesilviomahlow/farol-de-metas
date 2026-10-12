// Botão "Atualizar": roda o etl/extrair.py, que lê os faróis na pasta do RMR e regrava o
// data/farol.json. O /api/farol relê o arquivo sozinho quando ele muda.
//
// Uma rodada por vez (leva ~10 min). O estado fica em memória: se o servidor reiniciar no meio,
// o pior caso é o botão voltar a ficar livre. O extrator grava o JSON de forma atômica e não
// troca um ranking bom por um vazio quando a rede cai.
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import path from 'node:path';

export const ARQUIVO_DADOS = process.env.FAROL_DADOS || path.resolve(process.cwd(), '../data/farol.json');

const PYTHON = process.env.FAROL_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const LIMITE_MS = 30 * 60 * 1000;

function acharEtl() {
  const candidatos = [
    process.env.FAROL_ETL,
    path.resolve(process.cwd(), 'etl/extrair.py'),    // producao: run.sh roda da pasta do app
    path.resolve(process.cwd(), '../etl/extrair.py'), // nitro dev roda de web/
  ].filter(Boolean);
  return candidatos.find((c) => existsSync(c));
}

const estado = { rodando: false, inicio: null, fim: null, ok: null, total: 0, lidos: 0, mensagem: '', log: [] };

export function statusAtualizacao() {
  const { log, ...resto } = estado;
  return { ...resto, ultimasLinhas: log.slice(-8) };
}

export function iniciarAtualizacao() {
  if (estado.rodando) return { iniciou: false, ...statusAtualizacao() };
  const etl = acharEtl();
  if (!etl) {
    Object.assign(estado, { ok: false, fim: new Date().toISOString(), mensagem: 'Não achei o etl/extrair.py no servidor.' });
    return { iniciou: false, ...statusAtualizacao() };
  }

  Object.assign(estado, {
    rodando: true, inicio: new Date().toISOString(), fim: null, ok: null,
    total: 0, lidos: 0, mensagem: 'Começando a leitura dos faróis…', log: [],
  });

  const proc = spawn(PYTHON, [etl], {
    env: { ...process.env, FAROL_SAIDA: ARQUIVO_DADOS, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' },
    windowsHide: true,
  });
  const relogio = setTimeout(() => proc.kill(), LIMITE_MS);

  let resto = '';
  const aoLer = (pedaco) => {
    const linhas = (resto + pedaco.toString('utf8')).split(/\r?\n/);
    resto = linhas.pop();
    for (const l of linhas) {
      if (!l.trim()) continue;
      estado.log.push(l);
      if (estado.log.length > 200) estado.log.shift();
      const total = l.match(/^total (\d+)/);
      if (total) estado.total = Number(total[1]);
      if (/^(ok|sem-farol|erro) /.test(l)) {
        estado.lidos += 1;
        estado.mensagem = `Lendo faróis ${estado.lidos}/${estado.total}`;
      }
    }
  };
  proc.stdout.on('data', aoLer);
  proc.stderr.on('data', aoLer);

  const terminar = (ok, mensagem) => {
    clearTimeout(relogio);
    Object.assign(estado, { rodando: false, fim: new Date().toISOString(), ok, mensagem });
  };
  proc.on('error', (e) => terminar(false, `Não consegui rodar o Python (${PYTHON}): ${e.message}`));
  proc.on('close', (codigo) => {
    if (codigo === 0) terminar(true, 'Faróis atualizados.');
    else {
      const falha = [...estado.log].reverse().find((l) => /FALHOU|Error|erro /i.test(l));
      terminar(false, falha || `O extrator terminou com erro (código ${codigo}).`);
    }
  });
  return { iniciou: true, ...statusAtualizacao() };
}
