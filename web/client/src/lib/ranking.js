// Regras do ranking (combinadas com o Silvio em 10/10/2026).
//
// Ordem: % do farol (linha "Atingimento" da planilha); empatou, decide o desempate (superação
// da meta de maior peso, já calculada no etl/extrair.py); persistindo, a superação média
// ponderada de todas as metas; por fim, o nome.
// Multiplicador (padrão definido pelo Silvio em 13/10/2026): os 4 primeiros 1,5x, os 4 seguintes
// 1,2x, os 8 últimos 0,25x (deflator) e o resto 1,0x.

export const REGRA_PADRAO = { q15: 4, q12: 4, q025: 8 };

// Graus do farol, conforme o "Guia" das planilhas.
export const GRAUS = [1, 0.9, 0.8, 0.6, 0];

export const MES_NOME = {
  jan: 'Janeiro', fev: 'Fevereiro', mar: 'Março', abr: 'Abril', mai: 'Maio', jun: 'Junho',
  jul: 'Julho', ago: 'Agosto', set: 'Setembro', out: 'Outubro', nov: 'Novembro', dez: 'Dezembro',
};

/** Farol de uma meta na base: 'ytd' ou um mês ('jan'...). */
export function grauMeta(meta, base) {
  return base === 'ytd' ? meta.ytd : meta.mes?.[base] ?? null;
}

/** Chave do simulador para a meta i da pessoa na base. */
export const chaveSim = (pessoa, i, base) => `${pessoa.id}|${i}|${base}`;

/**
 * % da pessoa na base. No simulador, quem teve alguma meta alterada é recalculado do zero:
 * soma de peso x farol de cada meta (peso 20% com farol 90% = 0,18). Meta sem farol conta 0.
 *
 * Antes (até 13/10/2026) partia do % oficial e somava só a diferença da meta alterada - na
 * Elyana, cujo Excel soma 92% com as metas valendo 78%, uma meta para 100% a levava a 100%.
 */
export function pctPessoa(pessoa, base, sim) {
  const oficial = base === 'ytd' ? pessoa.ytd : pessoa.mes?.[base] ?? null;
  if (!sim || !pessoa.metas.some((_, i) => chaveSim(pessoa, i, base) in sim)) return oficial;
  let soma = 0;
  pessoa.metas.forEach((meta, i) => {
    if (!meta.peso) return;
    const k = chaveSim(pessoa, i, base);
    soma += meta.peso * ((k in sim ? sim[k] : grauMeta(meta, base)) ?? 0);
  });
  return soma;
}

export function multiplicador(pos, n, regra) {
  if (pos <= regra.q15) return 1.5;
  if (pos <= regra.q15 + regra.q12) return 1.2;
  if (pos > n - regra.q025) return 0.25;
  return 1.0;
}

/**
 * Monta o ranking. Quem não tem farol (arquivo fora da pasta, ou sem lançamento no mês) vai
 * para o fim, marcado `semFarol`, e conta nas posições e no multiplicador (pedido do Silvio,
 * 12/10/2026: "joga lá para último"). O GERAL considera só quem tem farol.
 */
export function montarRanking(pessoas, base, regra = REGRA_PADRAO, sim = null) {
  const chaveDes = base === 'ytd' ? 'acum' : base;
  const comDado = [];
  const semDado = [];
  for (const p of pessoas) {
    const pct = pctPessoa(p, base, sim);
    if (pct == null) semDado.push({ pessoa: p, pct: null, des: null, des2: null, semFarol: true });
    else comDado.push({ pessoa: p, pct, des: p.desempate?.[chaveDes] ?? null, des2: p.desempate2?.[chaveDes] ?? null });
  }
  // arredonda o % a 4 casas antes de comparar: 0,96 e 0,9600000000000002 são o mesmo farol
  const r4 = (x) => Math.round(x * 1e4);
  comDado.sort((a, b) => (r4(b.pct) - r4(a.pct))
    || ((b.des ?? -1) - (a.des ?? -1))
    || ((b.des2 ?? -1) - (a.des2 ?? -1))
    || a.pessoa.nome.localeCompare(b.pessoa.nome, 'pt-BR'));
  semDado.sort((a, b) => a.pessoa.nome.localeCompare(b.pessoa.nome, 'pt-BR'));
  const lista = [...comDado, ...semDado];
  lista.forEach((x, i) => {
    x.pos = i + 1;
    x.mult = multiplicador(x.pos, lista.length, regra);
  });
  return { lista, comFarol: comDado };
}
