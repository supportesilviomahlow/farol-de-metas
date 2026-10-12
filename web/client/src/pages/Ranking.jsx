// Telas Mês e YTD: o ranking oficial, lido dos faróis. A troca entre as duas é pelo menu lateral.
import { useMemo, useState } from 'react';
import { FaixaTitulo, ReguaMultiplicador, SeletorEscuro, TabelaRanking } from '../components/Ranking.jsx';
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

export default function Ranking({ dados, tipo }) {
  const [mes, setMes] = useState(dados.mesPadrao);
  const [abertos, alternar] = useAbertos();
  const base = tipo === 'ytd' ? 'ytd' : mes;
  const { lista, comFarol } = useMemo(() => montarRanking(dados.pessoas, base), [dados, base]);
  const ultimo = dados.meses[dados.meses.length - 1];

  const subtitulo = tipo === 'ytd'
    ? `Acumulado jan–${ultimo} ${dados.ano} · ${lista.length} lideranças`
    : `${lista.length} lideranças${dados.parciais.includes(mes) ? ' · apuração ainda em andamento nas planilhas' : ''}`;

  return (
    <>
      <FaixaTitulo titulo={tipo === 'ytd' ? 'YTD' : MES_NOME[mes]} subtitulo={subtitulo} geral={media(comFarol)}>
        {tipo === 'mes' && <SeletorEscuro rotulo="Mês" valor={mes} aoMudar={setMes} opcoes={opcoesMes(dados)} />}
      </FaixaTitulo>
      <ReguaMultiplicador regra={REGRA_PADRAO} />
      <div className="px-6 pb-8 pt-4">
        <TabelaRanking lista={lista} regra={REGRA_PADRAO} base={base} abertos={abertos} alternar={alternar} />
      </div>
    </>
  );
}
