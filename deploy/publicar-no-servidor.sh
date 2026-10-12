#!/usr/bin/env bash
# Publica o Farol de Metas no 173, porta 3007. Rode da RAIZ do projeto:
#   bash deploy/publicar-no-servidor.sh             # codigo (e os dados, se o servidor nao tiver)
#   bash deploy/publicar-no-servidor.sh --so-dados  # so o data/farol.json, POR CIMA do servidor
#
# Mesmo padrao do PGP: uma pasta por app em $HOME, node do ~/.local, watchdog no cron
# silenciado por ~/farol-metas/.deploy enquanto a publicacao roda, backup antes,
# verificacao pela rede depois e rollback impresso.
#
# O QUE VAI:
#   web/.output/   o servidor Nitro ja com o front (npm run build); nao precisa de npm no 173
#   etl/           o extrator (referencia; quem roda e o agente no computador do Silvio)
#   deploy/run.sh  o script de subida
#   data/farol.json  SO na primeira publicacao (ou com --so-dados). Depois disso o servidor e a
#                    fonte de verdade: o botao Atualizar regrava o arquivo la, e publicar codigo
#                    nao pode voltar o ranking para a versao desta maquina.
#
# O QUE NAO VAI, NUNCA:
#   nada de credencial: o botao Atualizar so deixa um pedido no servidor, e quem le os Excel e o
#   agente no computador do Silvio (etl/agente_atualizacao.py), com o acesso dele.
#
# set -e FORA de proposito: ssh que mata processo remoto ou sobe daemon detached retorna 255
# mesmo tendo funcionado. A verificacao que vale e o HTTP no final.
set -uo pipefail

HOST=192.168.102.173
BASE=farol-metas
PORT=3007
STAMP=$(date +%Y%m%d-%H%M%S)
SO_DADOS=0
for a in "$@"; do [ "$a" = "--so-dados" ] && SO_DADOS=1; done

[ -f etl/extrair.py ] || { echo "Rode da raiz do projeto (nao achei etl/extrair.py)."; exit 1; }
[ -f data/farol.json ] || { echo "Faltou data/farol.json. Rode: python etl/extrair.py"; exit 1; }

echo "==> [1/7] Conferindo o farol.json"
node -e "const d=require('./data/farol.json'); if(!d.pessoas||d.pessoas.length<10) throw new Error('farol.json com poucas pessoas'); console.log('    '+d.pessoas.length+' liderancas, lido em '+d.gerado)" || exit 1

echo "==> [2/7] Preparando a pasta no servidor"
ssh "$HOST" "mkdir -p ~/$BASE/{data,backups}"
cp_dados() {
  ssh "$HOST" "cd ~/$BASE && [ -f data/farol.json ] && cp data/farol.json backups/farol-$STAMP.json; true"
  gzip -c data/farol.json | ssh "$HOST" "gunzip -c > ~/$BASE/data/farol.json.novo && mv -f ~/$BASE/data/farol.json.novo ~/$BASE/data/farol.json && ls -lh ~/$BASE/data/farol.json"
}

if [ "$SO_DADOS" = "1" ]; then
  echo "==> [3/7] So dados: o servidor rele o arquivo sozinho (sem reiniciar)"
  cp_dados
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://$HOST:$PORT/api/farol")
  echo "    /api/farol devolve HTTP $code"
  exit 0
fi

echo "==> [3/7] Build local"
(cd web && npm run build >/dev/null 2>&1) || { echo "FALHOU o build. Rode: cd web && npm run build"; exit 1; }
[ -f web/.output/server/index.mjs ] || { echo "Build sem .output/server/index.mjs"; exit 1; }
echo "    ok"

ssh "$HOST" "touch ~/$BASE/.deploy"
trap 'ssh "$HOST" "rm -f ~/$BASE/.deploy" >/dev/null 2>&1 || true' EXIT

echo "==> [4/7] Backup e envio do codigo e dos dados"
ssh "$HOST" "cd ~/$BASE && if [ -d .output ]; then tar czf backups/output-$STAMP.tgz .output && echo '    .output anterior em backups/output-$STAMP.tgz'; fi"
tar czf - -C web .output | ssh "$HOST" "cd ~/$BASE && rm -rf .output && tar xzf -"
tar czf - --exclude='__pycache__' etl | ssh "$HOST" "cd ~/$BASE && rm -rf etl && tar xzf -"
cat deploy/run.sh | ssh "$HOST" "cat > ~/$BASE/run.sh && chmod +x ~/$BASE/run.sh"
if ssh "$HOST" "[ -f ~/$BASE/data/farol.json ]"; then
  echo "    data/farol.json: o do servidor fica (use --so-dados para mandar o desta maquina)"
else
  echo "    data/farol.json: primeira vez - enviando o desta maquina"
  cp_dados
fi

echo "==> [5/7] Watchdog no cron"
ssh "$HOST" "
  TMP=\$(mktemp)
  crontab -l 2>/dev/null | grep -v '$BASE/run.sh' > \$TMP || true
  {
    echo '@reboot        \$HOME/$BASE/run.sh >> \$HOME/$BASE/app.log 2>&1'
    echo '*/2 * * * *    [ -f \$HOME/$BASE/.deploy ] || pgrep -f \"$BASE/.output/server/inde[x].mjs\" >/dev/null || \$HOME/$BASE/run.sh >> \$HOME/$BASE/app.log 2>&1'
  } >> \$TMP
  crontab \$TMP && rm -f \$TMP
  crontab -l | grep $BASE || true"

echo "==> [6/7] Parando o processo antigo (ssh isolado)"
ssh "$HOST" "pkill -u \$(id -u) -f '$BASE/.output/server/inde[x].mjs' 2>/dev/null
  for i in \$(seq 1 30); do ss -tlnH 2>/dev/null | grep -q ':$PORT ' || break; sleep 0.5; done" || true
livre=$(ssh "$HOST" "ss -tlnH 2>/dev/null | grep -c ':$PORT ' || true" 2>/dev/null | tr -d '[:space:]')
if [ "${livre:-1}" != "0" ]; then
  echo "FALHOU: a porta $PORT continua ocupada. Veja: ssh $HOST \"ss -tlnp | grep ':$PORT '\""
  exit 1
fi

echo "==> [7/7] Subindo (ssh isolado, detached)"
ssh "$HOST" "setsid --fork bash -c '\"\$HOME/$BASE/run.sh\" >> \"\$HOME/$BASE/app.log\" 2>&1 </dev/null' </dev/null >/dev/null 2>&1" || true

ok=0
for i in $(seq 1 12); do
  sleep 2
  code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 5 "http://$HOST:$PORT/saude") || code=000
  if [ "$code" = "200" ]; then ok=1; break; fi
  echo "    ...subindo (HTTP $code) $i/12"
done
if [ "$ok" != "1" ]; then
  echo "FALHOU. Ultimas linhas do log:"
  ssh "$HOST" "tail -30 ~/$BASE/app.log"
  echo "Rollback: ssh $HOST \"cd ~/$BASE && rm -rf .output && tar xzf backups/output-$STAMP.tgz && ./run.sh\""
  exit 1
fi
idade=$(ssh "$HOST" "ps -o etimes= -p \$(pgrep -u \$(id -u) -f '$BASE/.output/server/inde[x].mjs' | head -1) 2>/dev/null | tr -d ' '" 2>/dev/null)
if [ -n "$idade" ] && [ "$idade" -gt 300 ]; then
  echo "FALHOU: quem responde na $PORT tem $idade s de vida - e o processo ANTIGO."
  exit 1
fi
echo
echo "==> Concluido: http://$HOST:$PORT/  (processo com ${idade:-?} s de vida)"
echo "    Log: ssh $HOST 'tail -f ~/$BASE/app.log'"
