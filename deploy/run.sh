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

# Botao "Atualizar": o extrator roda com o Python do venv do app (openpyxl + smbprotocol),
# criado a mao uma vez em 12/10/2026. O python3 do sistema nao tem pip (PEP 668).
if [ -x "$BASE/venv/bin/python3" ]; then
  export FAROL_PYTHON="$BASE/venv/bin/python3"
fi

# Credencial de leitura da pasta do RMR (FAROL_SMB_USUARIO / FAROL_SMB_SENHA). Colocada a mao no
# servidor, chmod 600. NUNCA vai no deploy nem no git. Sem ela o site funciona, mas o Atualizar
# avisa que falta configurar.
if [ -f "$BASE/.env" ]; then
  set -a; . "$BASE/.env"; set +a
fi

if ss -tlnH 2>/dev/null | grep -q ":$PORT "; then
  echo "[$(date '+%F %T')] porta $PORT ja em uso, nao subo duplicado"
  exit 0
fi

cd "$BASE"
echo "[$(date '+%F %T')] subindo Farol de Metas na porta $PORT"
# CAMINHO ABSOLUTO de proposito (licao do PGP, 09/09/2026): o pkill do deploy e o pgrep do
# watchdog procuram "farol-metas/.output/server/inde[x].mjs" na linha de comando.
exec node "$BASE/.output/server/index.mjs"
