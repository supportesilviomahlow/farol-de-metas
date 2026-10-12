# -*- coding: utf-8 -*-
"""
Agente do botao "Atualizar" - roda no computador do Silvio (decisao dele, 12/10/2026).

O 173 nao tem credencial da pasta do RMR; este computador tem (a sessao do Windows do Silvio).
O Agendador de Tarefas roda este script a cada minuto, sem janela (pythonw):

  1. avisa o 173 que o computador esta ligado e pergunta se ha pedido de atualizacao;
  2. havendo pedido, roda o etl/extrair.py aqui e manda cada linha de andamento para o
     data/atualizacao.log do 173 (o botao mostra "Lendo farois 12/44");
  3. no fim, envia o data/farol.json e a conferencia do desempate, e grava "FIM ok" no log.

Tudo pelo ssh com a chave que ja existe (~/.ssh/config). Nao ha senha em lugar nenhum.
Instalar/remover a tarefa: deploy/agente-instalar.ps1
Log local: data/agente.log
"""
import os, subprocess, sys, time

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = os.environ.get("FAROL_HOST", "192.168.102.173")
REMOTO = "~/farol-metas/data"
TRAVA = os.path.join(RAIZ, "data", "agente.trava")
LOG_LOCAL = os.path.join(RAIZ, "data", "agente.log")
SEM_JANELA = 0x08000000 if os.name == "nt" else 0  # CREATE_NO_WINDOW

_win_ssh = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "OpenSSH", "ssh.exe")
SSH = [_win_ssh if os.path.exists(_win_ssh) else "ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=15", HOST]


def registrar(msg):
    os.makedirs(os.path.dirname(LOG_LOCAL), exist_ok=True)
    with open(LOG_LOCAL, "a", encoding="utf-8") as fh:
        fh.write("%s %s\n" % (time.strftime("%d/%m %H:%M:%S"), msg))


def ssh(cmd, entrada=None):
    r = subprocess.run(SSH + [cmd], input=entrada, capture_output=True, timeout=120,
                       creationflags=SEM_JANELA)
    return r.returncode, r.stdout.decode("utf-8", "replace").strip()


def enviar(local, remoto):
    with open(local, "rb") as fh:
        cod, _ = ssh("cat > %s.novo && mv -f %s.novo %s" % (remoto, remoto, remoto), fh.read())
    return cod == 0


def atualizar():
    # Marca o inicio ANTES de apagar o pedido: o servidor considera "rodando" quando o log e
    # mais novo que o pedido.
    ssh("echo 'inicio %s' > %s/atualizacao.log && rm -f %s/pedido-atualizacao.json"
        % (time.strftime("%d/%m/%Y %H:%M"), REMOTO, REMOTO))
    registrar("pedido recebido - lendo os farois")

    # Uma conexao ssh so, aberta durante a leitura toda, recebendo as linhas do extrator.
    canal = subprocess.Popen(SSH + ["cat >> %s/atualizacao.log" % REMOTO], stdin=subprocess.PIPE,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=SEM_JANELA)
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
    python = sys.executable.replace("pythonw.exe", "python.exe")
    proc = subprocess.Popen([python, os.path.join(RAIZ, "etl", "extrair.py")], cwd=RAIZ, env=env,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, creationflags=SEM_JANELA)
    ultimas = []
    for linha in proc.stdout:
        ultimas = (ultimas + [linha.decode("utf-8", "replace").rstrip()])[-20:]
        try:
            canal.stdin.write(linha)
            canal.stdin.flush()
        except OSError:
            pass  # rede caiu no meio: a leitura continua e o resultado e enviado no fim
    codigo = proc.wait()
    try:
        canal.stdin.close()
        canal.wait(timeout=30)
    except Exception:
        canal.kill()

    if codigo == 0:
        ok = enviar(os.path.join(RAIZ, "data", "farol.json"), REMOTO + "/farol.json")
        conf = os.path.join(RAIZ, "data", "conferencia-desempate.md")
        if ok and os.path.exists(conf):
            enviar(conf, REMOTO + "/conferencia-desempate.md")
        fim = "FIM ok" if ok else "FIM erro nao consegui enviar o farol.json para o servidor"
    else:
        falha = next((l for l in reversed(ultimas) if "FALHOU" in l or "Error" in l), "")
        fim = "FIM erro " + (falha or "o extrator terminou com erro (codigo %d)" % codigo)
    ssh("echo %s >> %s/atualizacao.log" % (sh_aspas(fim), REMOTO))
    registrar(fim)


def sh_aspas(s):
    return "'" + s.replace("'", "'\\''") + "'"


def main():
    # Uma rodada por vez: a leitura completa leva ~25 min e a tarefa dispara a cada minuto.
    if os.path.exists(TRAVA) and time.time() - os.path.getmtime(TRAVA) < 40 * 60:
        return
    cod, saida = ssh("mkdir -p %s && touch %s/agente.vivo && [ -f %s/pedido-atualizacao.json ] && echo PEDIDO || true"
                     % (REMOTO, REMOTO, REMOTO))
    if cod != 0 or "PEDIDO" not in saida:
        return
    os.makedirs(os.path.dirname(TRAVA), exist_ok=True)
    open(TRAVA, "w").close()
    try:
        atualizar()
    except Exception as e:  # nunca deixar o servidor esperando para sempre
        registrar("erro: %r" % e)
        ssh("echo %s >> %s/atualizacao.log" % (sh_aspas("FIM erro no computador do Silvio: %s" % e), REMOTO))
    finally:
        os.remove(TRAVA)


if __name__ == "__main__":
    main()
