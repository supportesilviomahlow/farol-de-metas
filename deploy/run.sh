#!/usr/bin/env bash
# Roda NO servidor 173. Sobe o Farol de Metas na porta 3007.
# Mesmo padrao das outras ferramentas: node do ~/.local, log em app.log, e o watchdog do cron
# religa se o processo cair.
set -euo pipefail
export PATH="$HOME/.local/node/bin:$PATH"

BASE="$HOME/farol-metas"
export PORT=3007
export FAROL_DADOS="$BASE/data/farol.json"
export FAROL_ETL="$BASE/etl/extrair.py"
# Atualizar pelo computador do Silvio (etl/agente_atualizacao.py): o botao so deixa um pedido.
export FAROL_MODO_ATUALIZAR=agente


if ss -tlnH 2>/dev/null | grep -q ":$PORT "; then
  echo "[$(date '+%F %T')] porta $PORT ja em uso, nao subo duplicado"
  exit 0
fi

cd "$BASE"
echo "[$(date '+%F %T')] subindo Farol de Metas na porta $PORT"
# CAMINHO ABSOLUTO de proposito (licao do PGP, 09/09/2026): o pkill do deploy e o pgrep do
# watchdog procuram "farol-metas/.output/server/inde[x].mjs" na linha de comando.
exec node "$BASE/.output/server/index.mjs"
