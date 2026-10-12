// Simulador: o mesmo ranking, mas dá para trocar o farol de cada meta e o tamanho das faixas
// do multiplicador. A seta ao lado do nome mostra quanto a pessoa andou em relação ao oficial.
// Nada é gravado: recarregar a página volta ao oficial.
import { useMemo, useState } from 'react';
import { RotateCcw } from 'lucide-react';
import { BotaoExportar, FaixaTitulo, ReguaMultiplicador, SeletorEscuro, TabelaDiretoria, TabelaRanking } from '../components/Ranking.jsx';
import { exportarPptx } from '../lib/exportarPptx.js';
import { MES_NOME, REGRA_PADRAO, montarRanking } from '../lib/ranking.js';
import { media, opcoesMes, pessoasDo, useAbertos } from './Ranking.jsx';

function CampoFaixa({ rotulo, sufixo, valor, aoMudar }) {
  return (
    <label className="inline-flex items-center gap-1.5">
      {rotulo}
      <input
        type="number"
        min={0}
        value={valor}
        onChange={(e) => aoMudar(Math.max(0, parseInt(e.target.value, 10) || 0))}
        className="w-14 rounded-md border border-border bg-card px-1.5 py-1 focus:border-primary focus:outline-2 focus:outline-primary"
      />
      {sufixo}
    </label>
  );
}

export default function Simulador({ dados, grupo }) {
  const [base, setBase] = useState('ytd');
  const [regra, setRegra] = useState(REGRA_PADRAO);
  const [sim, setSim] = useState({});
  const [abertos, alternar] = useAbertos();

  const diretoria = grupo === 'diretoria';
  const pessoas = useMemo(() => pessoasDo(dados, grupo), [dados, grupo]);
  const { lista, comFarol } = useMemo(() => montarRanking(pessoas, base, regra, sim), [pessoas, base, regra, sim]);
  const posOriginal = useMemo(
    () => new Map(montarRanking(pessoas, base).lista.map((x) => [x.pessoa.id, x.pos])),
    [pessoas, base],
  );
  const geral = media(comFarol);

  const aoSimular = (k, valor, original) => setSim((s) => {
    const novo = { ...s };
    if (valor == null || (original != null && Math.abs(valor - original) < 1e-9)) delete novo[k];
    else novo[k] = valor;
    return novo;
  });

  const opcoesBase = [{ valor: 'ytd', rotulo: 'YTD (acumulado)' }, ...opcoesMes(dados)];
  const alteradas = Object.keys(sim).filter((k) => k.endsWith(`|${base}`)).length;

  return (
    <>
      <FaixaTitulo
        titulo="Simulador"
        subtitulo={`${diretoria ? 'Ranking diretoria · ' : ''}${base === 'ytd' ? 'YTD' : MES_NOME[base]} · ${lista.length} ${diretoria ? 'diretores' : 'lideranças'}${alteradas ? ` · ${alteradas} meta(s) alterada(s)` : ''}`}
        geral={geral}
      >
        <SeletorEscuro rotulo="Base da simulação" valor={base} aoMudar={setBase} opcoes={opcoesBase} />
        <BotaoExportar aoExportar={() => exportarPptx({ grupo, base, geral, lista })} />
      </FaixaTitulo>
      <div className="flex flex-wrap items-center gap-4 border-b border-border bg-realce px-6 py-3 text-[13px]">
        {diretoria ? <b>Abra um diretor e troque o farol das metas</b> : (
          <>
            <b>Multiplicador</b>
            <CampoFaixa rotulo="1,5x para os" sufixo="primeiros" valor={regra.q15} aoMudar={(v) => setRegra((r) => ({ ...r, q15: v }))} />
            <CampoFaixa rotulo="1,2x para os" sufixo="seguintes" valor={regra.q12} aoMudar={(v) => setRegra((r) => ({ ...r, q12: v }))} />
            <CampoFaixa rotulo="0,25x para os" sufixo="últimos" valor={regra.q025} aoMudar={(v) => setRegra((r) => ({ ...r, q025: v }))} />
          </>
        )}
        <button
          type="button"
          onClick={() => { setSim({}); setRegra(REGRA_PADRAO); }}
          className="ml-auto inline-flex items-center gap-1.5 rounded-lg border border-border bg-card px-3 py-1.5 font-semibold hover:border-primary"
        >
          <RotateCcw className="h-3.5 w-3.5" aria-hidden /> Restaurar
        </button>
      </div>
      {!diretoria && <ReguaMultiplicador regra={regra} />}
      <div className="px-6 pb-8 pt-4">
        {diretoria ? (
          <TabelaDiretoria lista={lista} base={base} abertos={abertos} alternar={alternar}
            posOriginal={posOriginal} sim={sim} aoSimular={aoSimular} />
        ) : (
        <TabelaRanking
          lista={lista}
          regra={regra}
          base={base}
          abertos={abertos}
          alternar={alternar}
          posOriginal={posOriginal}
          sim={sim}
          aoSimular={aoSimular}
        />
        )}
      </div>
    </>
  );
}
