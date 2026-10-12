# Farol de Metas

Ranking das lideranças da Supporte pelo Farol de Metas, no formato do slide 33 do Call Nacional, com o multiplicador do abono ao lado de cada nome. Tem três telas: **Mês**, **Year to date** e **Simulador**. Clicando numa liderança, aparecem as metas dela com o peso e o farol de cada uma.

- **Responsável:** Controladoria, Silvio Teixeira
- **Endereço:** http://192.168.102.173:3007/ (rede interna, sem login, só para consumo interno)

## Regras

| O quê | Como |
|---|---|
| % da liderança | Linha "Atingimento" do farol de cada pessoa. No YTD, é a coluna do Peso; no mês, a coluna Meta daquele mês. |
| Desempate | Superação da meta de maior peso: real ÷ meta, ou meta ÷ real quando menor é melhor (custo, pacote, turnover). Tem teto de 150%. Se duas metas empatam no maior peso, vale a média delas. Persistindo o empate, decide a superação média ponderada de todas as metas. |
| Multiplicador | 1º ao 4º: 1,5x. 5º ao 8º: 1,2x. 4 últimos: 0,25x. Demais: 1,0x. |
| Quem entra | As lideranças do slide 33, listadas em `etl/liderancas.json`. Quem não tem farol na pasta continua na lista, marcado "sem farol de metas", e vai para o fim do ranking, o que conta para o multiplicador. No mês, vale o mesmo para quem não lançou aquele mês. |
| Mês padrão | O último mês em que a maioria já lançou o real. Os meses ainda em apuração aparecem como "(parcial)". |

**Por que o desempate mudou em relação ao slide.** O slide usava real ÷ meta sem teto e sem olhar o sentido da meta. Isso passava de 1000% quando a meta era pequena perto do realizado e punia quem ia bem em meta de custo.

**Conferência.** Cada atualização grava `data/conferencia-desempate.md`. O arquivo traz, para cada liderança, a meta de maior peso com a meta, o real, o sentido e a superação usados no desempate, para conferir contra o Excel.

## Como atualizar os dados

Os dados saem das planilhas em `\\192.168.102.161\rmr\2026`.

**Pelo site.** O botão **Atualizar**, no menu lateral, deixa um pedido no servidor. Quem lê os Excel é o **computador do Silvio**, com o acesso dele à pasta.

- No computador do Silvio, a tarefa "Farol de Metas - Atualizar" do Agendador do Windows roda `etl/agente_atualizacao.py` a cada minuto, sem janela.
- O agente vê o pedido, roda o extrator e manda o andamento e o `farol.json` novo para o 173 por ssh, com a chave que já existe. Não há senha em lugar nenhum.
- O botão mostra o andamento ("Lendo faróis 12/44").
- Se o computador estiver desligado ou fora da rede, o site avisa, e a atualização roda quando ele voltar.
- Só são relidos os Excel que mudaram, graças ao cache em `data/.cache`. Sem mudança, termina em segundos.
- Para instalar ou remover a tarefa: `powershell -ExecutionPolicy Bypass -File deploygente-instalar.ps1` (com `-Remover` para tirar).
- Log do agente: `data/agente.log`.

**Por linha de comando** (alternativa):

```bash
python etl/extrair.py                              # grava data/farol.json
bash deploy/publicar-no-servidor.sh --so-dados     # manda o farol.json por cima do servidor
```

Nos dois casos, o extrator avisa no fim quais faróis têm problema, por exemplo quando as metas não fecham com a linha "Atingimento".

## Stack técnica

Porte pequeno: só leitura, sem banco e sem login.

- **Front:** React 19, Vite 7, Tailwind 4, React Router 7 e `lucide-react`. O menu lateral e os tokens visuais vieram da Central de Fretes.
- **Servidor:** Nitro 2. Serve o build do React e o `GET /api/farol`, que lê o `data/farol.json`. Quando o arquivo muda, o servidor relê sozinho. No 173, o botão Atualizar só registra o pedido (`FAROL_MODO_ATUALIZAR=agente`). Em desenvolvimento, roda o extrator direto.
- **ETL:** Python. `etl/farol_base.py` é o parser que já existia em `01 - Transportes/Dash DR`. `etl/extrair.py` aplica as regras acima.

### Fluxos e endpoints

| Método | Rota | O que faz |
|---|---|---|
| GET | `/api/farol` | Devolve o ranking pronto: pessoas, % do YTD e de cada mês, desempates e metas. |
| POST | `/api/atualizar` | Pede a releitura dos faróis. No 173, deixa o pedido para o agente; uma rodada por vez. |
| GET | `/api/atualizar` | Andamento da releitura (lidos/total, ok ou erro). |
| GET | `/saude` | Usado pelo deploy para confirmar que o app subiu. |
| GET | `/mes`, `/ytd`, `/simulador` | Telas do React. O servidor devolve o `index.html`. |

## Como rodar localmente

```bash
python etl/extrair.py          # gera data/farol.json
cd web && npm install && npm run dev
```

Depois, abra http://localhost:5173. O Nitro roda na 3010 e o Vite faz proxy de `/api` para ele.

## Publicação

```bash
bash deploy/publicar-no-servidor.sh
```

O script segue o mesmo padrão do PGP:

- Faz o build local e envia o `web/.output`, o `etl/` e o `run.sh` via `tar | ssh` para `~/farol-metas` no 173.
- O `data/farol.json` só é enviado na primeira vez. Depois disso, quem atualiza é o botão.
- Faz backup antes de trocar qualquer coisa.
- Mantém um watchdog no cron a cada 2 minutos.
- Confere pela rede que o processo novo subiu.

## LGPD

O app mostra o desempenho e o multiplicador de abono por nome. Sem login, qualquer pessoa da rede que chegue ao 173 consegue ver.

- **Escolha atual:** ficou assim por decisão do responsável, para consumo interno.
- **Se o acesso precisar ser restrito:** o caminho é o Login Único (SSO, skill `supplog-sso`).
- **Dados coletados:** só o necessário para o ranking (minimização). São o nome, o % e o farol por meta. Os valores de meta e real ficam só no relatório de conferência.
- **Git:** o `data/` não vai para o Git, nem o esboço e o PowerPoint de referência.

## Pendências conhecidas

1. **Faróis do Francis, do Lucas Bueno e do Rodolfo:** não têm o bloco "ACUMULADO" com meta e real. O desempate do YTD usa a média da superação dos meses.
2. **Faróis do Leo Resende, da Maraíza, do Weberson e do Rodolfo:** quem preenche reaproveita um bloco de mês e troca o rótulo para o mês que está lançando. Os outros meses ficam com `#REF!`.
   - O leitor usa o primeiro bloco com o rótulo do mês.
   - Mês sem meta e real numéricos conta como "não lançado": a pessoa aparece como sem farol naquele mês.
   - Não mapear os meses pela ordem dos blocos: isso jogava agosto em fevereiro.
3. **Faróis da Elyana e do Túlio:** as metas não fecham com a linha "Atingimento" da própria planilha.
4. **Farol do Ivanaldo:** lançado só até julho.
