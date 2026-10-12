// Peças da tela de ranking, no desenho do slide 33 do Call Nacional: faixa escura com o título e
// o "GERAL" em laranja, e a lista em duas colunas (#, Mult., Liderança, %, Desempate).
// Menos é mais (pedido do Silvio): o drilldown mostra só a meta, o peso e o farol.
import { Fragment } from 'react';
import { ArrowDown, ArrowUp, ChevronDown, ChevronsDown, ChevronsUp } from 'lucide-react';
import { cn } from '../lib/cn.js';
import { mult, pct } from '../lib/formato.js';
import { GRAUS, chaveSim, grauMeta } from '../lib/ranking.js';

export function FaixaTitulo({ titulo, subtitulo, geral, children }) {
  return (
    <div className="flex flex-wrap items-center gap-6 border-l-[12px] border-primary bg-faixa px-6 py-4 text-white">
      <div>
        <h1 className="m-0 text-[52px] font-bold leading-none tracking-[0.01em] text-white">{titulo}</h1>
        {subtitulo && <div className="mt-1 text-[13px] text-white/70">{subtitulo}</div>}
      </div>
      <div className="ml-auto flex flex-wrap items-center gap-3">{children}</div>
      <div className="whitespace-nowrap bg-primary px-7 py-3 font-['Titillium_Web'] text-[32px] font-semibold leading-none text-white">
        GERAL&nbsp;&nbsp;{pct(geral, 1)}
      </div>
    </div>
  );
}

export function SeletorEscuro({ valor, aoMudar, opcoes, rotulo }) {
  return (
    <select
      aria-label={rotulo}
      value={valor}
      onChange={(e) => aoMudar(e.target.value)}
      className="rounded-lg border border-white/20 bg-white/10 px-3 py-1.5 text-[13px] text-white focus:border-primary focus:outline-2 focus:outline-primary [&>option]:text-black"
    >
      {opcoes.map((o) => <option key={o.valor} value={o.valor}>{o.rotulo}</option>)}
    </select>
  );
}

export function SeloMult({ m }) {
  const estilo = m === 1.5 ? 'bg-primary text-white'
    : m === 1.2 ? 'bg-realce-forte text-realce-texto'
      : m === 0.25 ? 'bg-chumbo-escuro text-white'
        : 'border border-border text-muted-foreground';
  return (
    <span className={cn('inline-flex min-w-[56px] items-center justify-center gap-0.5 rounded-full px-2 py-0.5 text-[12.5px] font-semibold', estilo)}>
      {m > 1 && <ChevronsUp className="h-3 w-3" aria-hidden />}
      {m < 1 && <ChevronsDown className="h-3 w-3" aria-hidden />}
      {mult(m)}
    </span>
  );
}

export function ReguaMultiplicador({ regra }) {
  const faixa = (m, texto) => (
    <span className="inline-flex items-center gap-2">
      <SeloMult m={m} />
      <b className="text-foreground">{texto}</b>
    </span>
  );
  return (
    <div className="flex flex-wrap items-center gap-4 border-b border-border bg-card px-6 py-3 text-[12.5px]">
      {faixa(1.5, `1º–${regra.q15}º`)}
      {faixa(1.2, `${regra.q15 + 1}º–${regra.q15 + regra.q12}º`)}
      {faixa(1.0, 'demais')}
      {faixa(0.25, `${regra.q025} últimos`)}
    </div>
  );
}

function Medalha({ pos }) {
  const cor = pos === 1 ? 'bg-primary' : pos === 2 ? 'bg-muted-foreground' : 'bg-bronze';
  return (
    <span className={cn('inline-flex h-[22px] w-[22px] items-center justify-center rounded-full text-[12px] font-bold text-white', cor)}>
      {pos}
    </span>
  );
}

function Farol({ g }) {
  if (g == null) return <span className="text-muted-foreground">–</span>;
  const cor = g >= 0.999 ? 'bg-success' : g >= 0.8 ? 'bg-atencao' : 'bg-destructive';
  return (
    <span className="inline-flex items-center gap-1.5 font-semibold">
      <i className={cn('inline-block h-2 w-2 rounded-full', cor)} aria-hidden />
      {pct(g)}
    </span>
  );
}

function DetalheMetas({ pessoa, base, sim, aoSimular }) {
  return (
    <div className="border-l-[3px] border-primary bg-muted/60 py-3 pl-[52px] pr-3">
      <table className="w-full border-collapse border border-border bg-card text-[12.5px]">
        <thead>
          <tr className="text-[11.5px] text-muted-foreground">
            <th className="border-b border-border px-2 py-1.5 text-left font-semibold">Meta</th>
            <th className="w-20 border-b border-border px-2 py-1.5 text-right font-semibold">Peso</th>
            <th className="w-28 border-b border-border px-2 py-1.5 text-right font-semibold">Farol</th>
          </tr>
        </thead>
        <tbody>
          {pessoa.metas.map((meta, i) => {
            const k = chaveSim(pessoa, i, base);
            const original = grauMeta(meta, base);
            const g = sim && k in sim ? sim[k] : original;
            return (
              <tr key={i} className={sim && k in sim ? 'bg-realce' : undefined}>
                <td className="border-b border-border px-2 py-1.5">{meta.indicador}</td>
                <td className="border-b border-border px-2 py-1.5 text-right">{pct(meta.peso)}</td>
                <td className="border-b border-border px-2 py-1.5 text-right">
                  {aoSimular ? (
                    <select
                      aria-label={`Farol de ${meta.indicador}`}
                      value={g ?? ''}
                      onChange={(e) => aoSimular(k, e.target.value === '' ? null : Number(e.target.value), original)}
                      className="rounded-md border border-border bg-card px-1 py-0.5"
                    >
                      {original == null && <option value="">–</option>}
                      {GRAUS.map((x) => <option key={x} value={x}>{pct(x)}</option>)}
                      {g != null && !GRAUS.some((x) => Math.abs(x - g) < 1e-6) && <option value={g}>{pct(g)}</option>}
                    </select>
                  ) : <Farol g={g} />}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function Corte({ texto, baixo }) {
  return (
    <tr>
      <td colSpan={6} className="p-0">
        <div className={cn(
          'border-t-2 px-2 py-1 text-[10.5px] uppercase tracking-[0.14em]',
          baixo ? 'border-muted-foreground bg-muted text-muted-foreground' : 'border-primary bg-realce text-laranja-texto',
        )}>{texto}</div>
      </td>
    </tr>
  );
}

function Coluna({ itens, n, regra, base, abertos, alternar, posOriginal, sim, aoSimular }) {
  const th = 'border-b border-border bg-muted px-2 py-2.5 font-["Titillium_Web"] text-[13px] font-semibold uppercase tracking-[0.14em] text-muted-foreground';
  return (
    <table className="w-full border-collapse border border-border bg-card">
      <thead>
        <tr>
          <th className={cn(th, 'w-11 text-center')}>#</th>
          <th className={cn(th, 'w-20 text-center')}>Mult.</th>
          <th className={cn(th, 'text-left')}>Liderança</th>
          <th className={cn(th, 'w-[72px] text-right')}>%</th>
          <th className={cn(th, 'w-28 text-right')}>Desempate</th>
          <th className={cn(th, 'w-8')} />
        </tr>
      </thead>
      <tbody>
        {itens.map((x) => {
          const aberto = abertos.has(x.pessoa.id);
          const mov = posOriginal ? posOriginal.get(x.pessoa.id) - x.pos : 0;
          const td = 'border-b border-border px-2 py-[7px] text-[15px]';
          return (
            <Fragment key={x.pessoa.id}>
              {x.pos === regra.q15 + 1 && regra.q15 > 0 && <Corte texto="fim da faixa 1,5x" />}
              {x.pos === regra.q15 + regra.q12 + 1 && regra.q12 > 0 && <Corte texto="fim da faixa 1,2x" />}
              {x.pos === n - regra.q025 + 1 && regra.q025 > 0 && <Corte texto="faixa 0,25x" baixo />}
              <tr
                onClick={() => alternar(x.pessoa.id)}
                className={cn('cursor-pointer hover:bg-realce', x.pos % 2 === 0 && 'bg-background/40')}
                aria-expanded={aberto}
              >
                <td className={cn(td, 'text-center text-muted-foreground')}>{x.pos <= 3 ? <Medalha pos={x.pos} /> : x.pos}</td>
                <td className={cn(td, 'text-center')}><SeloMult m={x.mult} /></td>
                <td className={cn(td, 'uppercase tracking-[0.01em]', x.pos <= 3 && 'font-bold')}>
                  {x.pessoa.nome}
                  {x.semFarol && (
                    <span className="ml-2 rounded-full border border-border px-2 py-0.5 text-[10.5px] font-semibold normal-case tracking-normal text-muted-foreground">
                      sem farol de metas
                    </span>
                  )}
                  {mov !== 0 && (
                    <span className={cn('ml-1.5 inline-flex items-center text-[11px] font-semibold normal-case', mov > 0 ? 'text-success' : 'text-destructive')}>
                      {mov > 0 ? <ArrowUp className="h-3 w-3" aria-hidden /> : <ArrowDown className="h-3 w-3" aria-hidden />}
                      {Math.abs(mov)}
                      <span className="sr-only">{mov > 0 ? 'posições acima' : 'posições abaixo'}</span>
                    </span>
                  )}
                </td>
                <td className={cn(td, 'text-right font-bold', x.pct != null && x.pct >= 0.855 && 'text-laranja-texto')}>{pct(x.pct)}</td>
                <td className={cn(td, 'text-right text-muted-foreground')}>{pct(x.des, 1)}</td>
                <td className={cn(td, 'text-muted-foreground')}>
                  <ChevronDown className={cn('h-4 w-4 transition-transform', aberto && 'rotate-180')} aria-hidden />
                </td>
              </tr>
              {aberto && (
                <tr>
                  <td colSpan={6} className="p-0">
                    <DetalheMetas pessoa={x.pessoa} base={base} sim={sim} aoSimular={aoSimular} />
                  </td>
                </tr>
              )}
            </Fragment>
          );
        })}
      </tbody>
    </table>
  );
}

/** Lista em duas colunas, como no slide (a primeira com a metade de cima). */
export function TabelaRanking({ lista, regra, base, abertos, alternar, posOriginal, sim, aoSimular }) {
  const n = lista.length;
  const meio = Math.ceil(n / 2);
  const props = { n, regra, base, abertos, alternar, posOriginal, sim, aoSimular };
  return (
    <div className="grid items-start gap-4 min-[1250px]:grid-cols-2">
      <Coluna itens={lista.slice(0, meio)} {...props} />
      <Coluna itens={lista.slice(meio)} {...props} />
    </div>
  );
}
