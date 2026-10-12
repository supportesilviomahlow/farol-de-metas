// Telas Mês e YTD, das duas seções: Ranking de lideranças (slide 33, com multiplicador) e
// Ranking diretoria (slide 36). A troca entre elas é pelo menu lateral.
import { useMemo, useState } from 'react';
import { BotaoExportar, FaixaTitulo, ReguaMultiplicador, SeletorEscuro, TabelaDiretoria, TabelaRanking } from '../components/Ranking.jsx';
import { exportarPptx } from '../lib/exportarPptx.js';
import { MES_NOME, REGRA_PADRAO, montarRanking } from '../lib/ranking.js';

export function useAbertos() {
  const [abertos, setAbertos] = useState(() => new Set());
  const alternar = (id) => setAbertos((s) => {
    const novo = new Set(s);
    if (novo.has(id)) novo.delete(id); else novo.add(id);
    return novo;
  });
  return [abertos, alternar];
}

export function opcoesMes(dados) {
  return dados.meses.map((m) => ({
    valor: m,
    rotulo: MES_NOME[m] + (dados.parciais.includes(m) ? ' (parcial)' : ''),
  }));
}

export const media = (lista) => (lista.length ? lista.reduce((s, x) => s + x.pct, 0) / lista.length : null);

/** Pessoas da seção: farol.json antigo (sem `grupo`) conta tudo como lideranças. */
export const pessoasDo = (dados, grupo) => dados.pessoas.filter((p) => (p.grupo || 'liderancas') === grupo);

export default function Ranking({ dados, tipo, grupo }) {
  const [mes, setMes] = useState(dados.mesPadrao);
  const [abertos, alternar] = useAbertos();
  const base = tipo === 'ytd' ? 'ytd' : mes;
  const pessoas = useMemo(() => pessoasDo(dados, grupo), [dados, grupo]);
  const { lista, comFarol } = useMemo(() => montarRanking(pessoas, base), [pessoas, base]);
  const ultimo = dados.meses[dados.meses.length - 1];
  const diretoria = grupo === 'diretoria';
  const geral = media(comFarol);

  const quem = `${lista.length} ${diretoria ? 'diretores' : 'lideranças'}`;
  const subtitulo = tipo === 'ytd'
    ? `${diretoria ? 'Ranking diretoria · ' : ''}Acumulado jan–${ultimo} ${dados.ano} · ${quem}`
    : `${diretoria ? 'Ranking diretoria · ' : ''}${quem}${dados.parciais.includes(mes) ? ' · apuração ainda em andamento nas planilhas' : ''}`;

  return (
    <>
      <FaixaTitulo titulo={tipo === 'ytd' ? 'YTD' : MES_NOME[mes]} subtitulo={subtitulo} geral={geral}>
        {tipo === 'mes' && <SeletorEscuro rotulo="Mês" valor={mes} aoMudar={setMes} opcoes={opcoesMes(dados)} />}
        <BotaoExportar aoExportar={() => exportarPptx({ grupo, base, geral, lista })} />
      </FaixaTitulo>
      {!diretoria && <ReguaMultiplicador regra={REGRA_PADRAO} />}
      <div className="px-6 pb-8 pt-4">
        {diretoria
          ? <TabelaDiretoria lista={lista} base={base} abertos={abertos} alternar={alternar} />
          : <TabelaRanking lista={lista} regra={REGRA_PADRAO} base={base} abertos={abertos} alternar={alternar} />}
      </div>
    </>
  );
}
