// Shell da aplicação.
//
// Portado do AppShell da Central de Fretes (que veio do Margem Por Cliente V2) para manter as
// ferramentas Supporte idênticas: mesmas medidas, mesmo logotipo e a mesma chave de tema no
// localStorage ("supporte-theme"). Sem login: tirei o bloco do usuário e o "Sair".
import { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Calendar, CalendarRange, Moon, SlidersHorizontal, Sun } from 'lucide-react';
import BotaoAtualizar from './BotaoAtualizar.jsx';

const CHAVE_TEMA = 'supporte-theme';

function lerTema() {
  if (typeof window === 'undefined') return 'light';
  try {
    const salvo = localStorage.getItem(CHAVE_TEMA);
    if (salvo === 'dark' || salvo === 'light') return salvo;
  } catch {}
  return document.documentElement.classList.contains('dark') ? 'dark' : 'light';
}

const ITENS_RANKING = [
  { para: '/mes', rotulo: 'Mês', Icone: Calendar },
  { para: '/ytd', rotulo: 'Year to date', Icone: CalendarRange },
];
const ITENS_CENARIOS = [
  { para: '/simulador', rotulo: 'Simulador', Icone: SlidersHorizontal },
];

function ItemMenu({ item, ativo }) {
  const { Icone } = item;
  return (
    <Link
      to={item.para}
      className={`flex items-center gap-2.5 rounded-md px-3 py-2 text-[13px] transition-all ${
        ativo
          ? 'bg-sidebar-primary text-sidebar-primary-foreground shadow-sm'
          : 'text-sidebar-foreground/88 hover:bg-sidebar-accent/80 hover:text-white'
      }`}
    >
      <Icone className="h-3.5 w-3.5" />
      <span className="font-medium">{item.rotulo}</span>
    </Link>
  );
}

function Secao({ titulo }) {
  return (
    <div className="px-3 pb-1 pt-3 text-[10px] uppercase tracking-[0.2em] text-sidebar-foreground/45">{titulo}</div>
  );
}

export default function AppShell({ gerado, aoAtualizar, children }) {
  const { pathname } = useLocation();
  const [tema, setTema] = useState(lerTema);

  useEffect(() => {
    const raiz = document.documentElement;
    raiz.classList.toggle('dark', tema === 'dark');
    raiz.dataset.theme = tema;
    try { localStorage.setItem(CHAVE_TEMA, tema); } catch {}
  }, [tema]);

  // O tema acompanha a troca feita em outra aba (ou em outra ferramenta Supporte).
  useEffect(() => {
    const aoMudar = (e) => {
      if (e.key === CHAVE_TEMA && (e.newValue === 'dark' || e.newValue === 'light')) setTema(e.newValue);
    };
    window.addEventListener('storage', aoMudar);
    return () => window.removeEventListener('storage', aoMudar);
  }, []);

  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="flex min-h-screen items-start">
        <aside className="sticky top-0 flex h-screen w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground shadow-[8px_0_30px_rgba(15,23,42,0.08)]">
          <div className="border-b border-sidebar-border px-4 py-5">
            <img src="/supporte-wordmark.png" alt="Supporte" className="h-9 w-auto max-w-[200px] object-contain" />
            <div className="mt-2 text-[10px] uppercase tracking-[0.28em] text-sidebar-foreground/50">Farol de Metas</div>
          </div>
          <nav className="flex-1 overflow-y-auto px-3 py-4">
            <div className="flex flex-col gap-1">
              <Secao titulo="Ranking de lideranças" />
              {ITENS_RANKING.map((i) => <ItemMenu key={i.para} item={i} ativo={pathname === i.para} />)}
              <Secao titulo="Cenários" />
              {ITENS_CENARIOS.map((i) => <ItemMenu key={i.para} item={i} ativo={pathname === i.para} />)}
            </div>
          </nav>
          <div className="flex flex-col gap-2 border-t border-sidebar-border px-3 py-3">
            <BotaoAtualizar aoConcluir={aoAtualizar} />
            {gerado && <div className="px-1 text-[11px] text-sidebar-foreground/55">Faróis lidos em {gerado}</div>}
            <button
              type="button"
              onClick={() => setTema((t) => (t === 'dark' ? 'light' : 'dark'))}
              className="flex w-full items-center justify-between rounded-md border border-sidebar-border bg-sidebar-accent/40 px-3 py-2 text-[13px] text-sidebar-foreground transition hover:bg-sidebar-accent"
            >
              <span className="flex items-center gap-2">
                {tema === 'dark' ? <Sun className="h-3.5 w-3.5" /> : <Moon className="h-3.5 w-3.5" />}
                <span className="font-medium">{tema === 'dark' ? 'Modo claro' : 'Modo escuro'}</span>
              </span>
              <span className="text-[11px] text-sidebar-foreground/55">{tema === 'dark' ? 'Dark' : 'Light'}</span>
            </button>
          </div>
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
