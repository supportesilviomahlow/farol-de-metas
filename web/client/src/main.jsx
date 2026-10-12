// Ponto de entrada do front. Carrega o ranking uma vez (/api/farol) e monta as três telas.
import { StrictMode, useCallback, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import AppShell from './components/AppShell.jsx';
import Ranking from './pages/Ranking.jsx';
import Simulador from './pages/Simulador.jsx';
import './styles.css';

function Aviso({ titulo, texto }) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center p-8 text-center">
      <div>
        <h1 className="text-lg font-semibold">{titulo}</h1>
        {texto && <p className="mt-2 text-sm text-muted-foreground">{texto}</p>}
      </div>
    </div>
  );
}

function App() {
  const [dados, setDados] = useState(null);
  const [erro, setErro] = useState(null);

  const carregar = useCallback(() => {
    fetch('/api/farol')
      .then(async (r) => {
        if (!r.ok) throw new Error((await r.json().catch(() => ({}))).statusMessage || `HTTP ${r.status}`);
        return r.json();
      })
      .then((d) => { setDados(d); setErro(null); })
      .catch((e) => setErro(e.message));
  }, []);

  useEffect(() => { carregar(); }, [carregar]);

  let conteudo;
  if (erro) conteudo = <Aviso titulo="Não consegui carregar os faróis" texto={erro} />;
  else if (!dados) conteudo = <Aviso titulo="Carregando…" />;
  else {
    conteudo = (
      <Routes>
        <Route path="/mes" element={<Ranking key="mes" dados={dados} tipo="mes" />} />
        <Route path="/ytd" element={<Ranking key="ytd" dados={dados} tipo="ytd" />} />
        <Route path="/simulador" element={<Simulador dados={dados} />} />
        <Route path="*" element={<Navigate to="/ytd" replace />} />
      </Routes>
    );
  }
  return <AppShell gerado={dados?.gerado} aoAtualizar={carregar}>{conteudo}</AppShell>;
}

createRoot(document.getElementById('raiz')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
