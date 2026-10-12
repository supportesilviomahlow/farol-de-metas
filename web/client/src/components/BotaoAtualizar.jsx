// Botão "Atualizar" do menu lateral: manda o servidor reler os faróis na pasta do RMR e, ao
// terminar, recarrega o ranking. Se outra pessoa já disparou, só acompanha o andamento.
import { useCallback, useEffect, useRef, useState } from 'react';
import { CircleAlert, CircleCheck, RefreshCw } from 'lucide-react';
import { cn } from '../lib/cn.js';

export default function BotaoAtualizar({ aoConcluir }) {
  const [st, setSt] = useState(null);
  const [aviso, setAviso] = useState(null);
  const rodava = useRef(false);

  const consultar = useCallback(async () => {
    try {
      const r = await fetch('/api/atualizar');
      if (r.ok) setSt(await r.json());
    } catch {}
  }, []);

  useEffect(() => { consultar(); }, [consultar]);

  // Enquanto roda, consulta a cada 3 s; ao terminar, avisa e recarrega o ranking.
  useEffect(() => {
    if (!st) return undefined;
    if (rodava.current && !st.rodando) {
      setAviso({ ok: st.ok, texto: st.mensagem });
      if (st.ok) aoConcluir?.();
    }
    rodava.current = st.rodando;
    if (!st.rodando) return undefined;
    const t = setTimeout(consultar, 3000);
    return () => clearTimeout(t);
  }, [st, consultar, aoConcluir]);

  const atualizar = async () => {
    setAviso(null);
    try {
      const r = await fetch('/api/atualizar', { method: 'POST' });
      setSt(await r.json());
    } catch (e) {
      setAviso({ ok: false, texto: `Não consegui falar com o servidor: ${e.message}` });
    }
  };

  const rodando = Boolean(st?.rodando);
  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={atualizar}
        disabled={rodando}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-sidebar-primary px-3 py-2 text-[13px] font-semibold text-sidebar-primary-foreground transition hover:brightness-110 disabled:cursor-wait disabled:opacity-80"
      >
        <RefreshCw className={cn('h-3.5 w-3.5', rodando && 'animate-spin')} aria-hidden />
        {rodando ? (st.total ? `Lendo faróis ${st.lidos}/${st.total}` : 'Atualizando…') : 'Atualizar'}
      </button>
      {rodando && st.total > 0 && (
        <div className="h-1 overflow-hidden rounded-full bg-sidebar-accent" aria-hidden>
          <div className="h-full bg-sidebar-primary transition-all" style={{ width: `${(100 * st.lidos) / st.total}%` }} />
        </div>
      )}
      {aviso && (
        <div className={cn('flex items-start gap-1.5 px-1 text-[11px]', aviso.ok ? 'text-sidebar-foreground/70' : 'text-[#f8a878]')}>
          {aviso.ok ? <CircleCheck className="mt-px h-3 w-3 shrink-0" aria-hidden /> : <CircleAlert className="mt-px h-3 w-3 shrink-0" aria-hidden />}
          <span>{aviso.texto}</span>
        </div>
      )}
    </div>
  );
}
