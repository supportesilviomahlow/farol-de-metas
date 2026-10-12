// Botão "Atualizar": relê os faróis na pasta do RMR e regrava o data/farol.json. O /api/farol
// relê o arquivo sozinho quando ele muda.
//
// Dois modos (FAROL_MODO_ATUALIZAR):
//   "local"  - o próprio servidor roda o etl/extrair.py (desenvolvimento, nesta máquina).
//   "agente" - no 173 (decisão do Silvio, 12/10/2026: "usa minha máquina"). O 173 não tem
//              credencial da pasta do RMR, então o botão só deixa um PEDIDO em data/. O agente
//              que roda no computador do Silvio (etl/agente_atualizacao.py, agendado a cada
//              minuto) vê o pedido, lê os Excel com o acesso dele, manda o andamento linha a
//              linha para data/atualizacao.log e, no fim, o farol.json novo.
import { spawn } from 'node:child_process';
import { existsSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import path from 'node:path';

export const ARQUIVO_DADOS = process.env.FAROL_DADOS || path.resolve(process.cwd(), '../data/farol.json');

const MODO = process.env.FAROL_MODO_ATUALIZAR || 'local';
const PASTA = path.dirname(ARQUIVO_DADOS);
const PEDIDO = path.join(PASTA, 'pedido-atualizacao.json');
const LOG = path.join(PASTA, 'atualizacao.log');
const VIVO = path.join(PASTA, 'agente.vivo');      // o agente toca a cada minuto
const AGENTE_SUMIU_MS = 3 * 60 * 1000;
const LOG_PARADO_MS = 5 * 60 * 1000;               // o farol do Túlio (43 MB) leva ~1 min

const idadeMs = (arq) => { try { return Date.now() - statSync(arq).mtimeMs; } catch { return null; } };

/** Conta o andamento a partir das linhas do extrator ("total N", "ok ...", "FIM ok"...). */
function lerLog(linhas) {
  const st = { total: 0, lidos: 0, fim: null, falha: null };
  for (const l of linhas) {
    const t = l.match(/^total (\d+)/);
    if (t) st.total = Number(t[1]);
    if (/^(ok|sem-farol|erro) /.test(l)) st.lidos += 1;
    if (/FALHOU/.test(l)) st.falha = l;
    const f = l.match(/^FIM (ok|erro)\s*(.*)$/);
    if (f) st.fim = { ok: f[1] === 'ok', motivo: f[2] };
  }
  return st;
}

// ------------------------------------------------------------------ modo agente
function statusAgente() {
  const idadePedido = idadeMs(PEDIDO);
  const idadeLog = idadeMs(LOG);
  const idadeVivo = idadeMs(VIVO);
  const agenteLigado = idadeVivo != null && idadeVivo < AGENTE_SUMIU_MS;
  const base = { modo: 'agente', agenteLigado, total: 0, lidos: 0, ok: null, fim: null };

  // Pedido mais novo que o último log: ninguém pegou ainda.
  if (idadePedido != null && (idadeLog == null || idadePedido < idadeLog)) {
    return {
      ...base, rodando: true,
      mensagem: agenteLigado
        ? 'Aguardando o computador do Silvio começar…'
        : 'O computador do Silvio está desligado ou fora da rede. A atualização roda assim que ele ligar.',
    };
  }
  if (idadeLog == null) return { ...base, rodando: false, mensagem: '' };

  const linhas = readFileSync(LOG, 'utf8').split(/\r?\n/).filter(Boolean);
  const st = lerLog(linhas);
  const fim = new Date(statSync(LOG).mtimeMs).toISOString();
  if (st.fim) {
    return {
      ...base, rodando: false, total: st.total, lidos: st.lidos, ok: st.fim.ok, fim,
      mensagem: st.fim.ok ? 'Faróis atualizados.' : (st.falha || st.fim.motivo || 'A atualização falhou.'),
    };
  }
  if (idadeLog > LOG_PARADO_MS) {
    return { ...base, rodando: false, ok: false, fim, mensagem: 'A atualização parou no meio (o computador desligou ou saiu da rede). Clique de novo.' };
  }
  return {
    ...base, rodando: true, total: st.total, lidos: st.lidos,
    mensagem: st.total ? `Lendo faróis ${st.lidos}/${st.total}` : 'Começando a leitura dos faróis…',
  };
}

function iniciarAgente() {
  const st = statusAgente();
  if (st.rodando) return { iniciou: false, ...st };
  writeFileSync(PEDIDO, JSON.stringify({ pedido: new Date().toISOString() }));
  return { iniciou: true, ...statusAgente() };
}

// ------------------------------------------------------------------ modo local
const PYTHON = process.env.FAROL_PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const LIMITE_MS = 30 * 60 * 1000;
const local = { rodando: false, fim: null, ok: null, mensagem: '', log: [] };

function acharEtl() {
  return [
    process.env.FAROL_ETL,
    path.resolve(process.cwd(), 'etl/extrair.py'),
    path.resolve(process.cwd(), '../etl/extrair.py'),
  ].filter(Boolean).find((c) => existsSync(c));
}

function statusLocal() {
  const st = lerLog(local.log);
  return {
    modo: 'local', rodando: local.rodando, total: st.total, lidos: st.lidos, ok: local.ok, fim: local.fim,
    mensagem: local.rodando ? (st.total ? `Lendo faróis ${st.lidos}/${st.total}` : 'Começando a leitura dos faróis…') : local.mensagem,
  };
}

function iniciarLocal() {
  if (local.rodando) return { iniciou: false, ...statusLocal() };
  const etl = acharEtl();
  if (!etl) {
    Object.assign(local, { ok: false, fim: new Date().toISOString(), mensagem: 'Não achei o etl/extrair.py.' });
    return { iniciou: false, ...statusLocal() };
  }
  Object.assign(local, { rodando: true, fim: null, ok: null, mensagem: '', log: [] });
  const proc = spawn(PYTHON, [etl], {
    env: { ...process.env, FAROL_SAIDA: ARQUIVO_DADOS, PYTHONIOENCODING: 'utf-8', PYTHONUNBUFFERED: '1' },
    windowsHide: true,
  });
  const relogio = setTimeout(() => proc.kill(), LIMITE_MS);
  let resto = '';
  const aoLer = (pedaco) => {
    const linhas = (resto + pedaco.toString('utf8')).split(/\r?\n/);
    resto = linhas.pop();
    local.log.push(...linhas.filter((l) => l.trim()));
    if (local.log.length > 300) local.log.splice(0, local.log.length - 300);
  };
  proc.stdout.on('data', aoLer);
  proc.stderr.on('data', aoLer);
  const terminar = (ok, mensagem) => {
    clearTimeout(relogio);
    Object.assign(local, { rodando: false, fim: new Date().toISOString(), ok, mensagem });
  };
  proc.on('error', (e) => terminar(false, `Não consegui rodar o Python (${PYTHON}): ${e.message}`));
  proc.on('close', (codigo) => {
    if (codigo === 0) terminar(true, 'Faróis atualizados.');
    else terminar(false, lerLog(local.log).falha || `O extrator terminou com erro (código ${codigo}).`);
  });
  return { iniciou: true, ...statusLocal() };
}

// ------------------------------------------------------------------ interface
export const statusAtualizacao = () => (MODO === 'agente' ? statusAgente() : statusLocal());
export const iniciarAtualizacao = () => (MODO === 'agente' ? iniciarAgente() : iniciarLocal());
