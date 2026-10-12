# -*- coding: utf-8 -*-
"""
Le os farois das liderancas do slide 33 e grava data/farol.json, que o app serve.

    python etl/extrair.py

Roda de dois jeitos:
  - nesta maquina (Windows), lendo a pasta da rede direto pelo caminho UNC;
  - no servidor 173 (Linux), pelo botao "Atualizar" do site. La a pasta e lida por SMB com a
    biblioteca smbprotocol, usando FAROL_SMB_USUARIO e FAROL_SMB_SENHA do ~/farol-metas/.env
    (colocado a mao no servidor, chmod 600 - nunca vai no deploy nem no git).

Leva ~10 min: cada farol tem 6-10 MB e o do Tulio, 43 MB.

Variaveis de ambiente (opcionais):
    FAROL_BASE        pasta do RMR             (default \\\\192.168.102.161\\rmr\\2026)
    FAROL_SAIDA       arquivo gerado           (default data/farol.json, na raiz do projeto)
    FAROL_ULTIMO_MES  ultimo mes fechado       (default: mes anterior ao corrente)
    FAROL_SMB_USUARIO / FAROL_SMB_SENHA        liga a leitura por SMB (servidor Linux)

Saida no console (o servidor usa para mostrar o progresso no botao):
    total N           antes de comecar
    ok | sem-farol | erro  <arquivo>   uma linha por farol

Regras (combinadas com o Silvio em 10/10/2026):
  - % da pessoa = linha "Atingimento" do farol (YTD na coluna do Peso; mes na coluna Meta do mes).
  - Desempate = superacao da meta de MAIOR PESO (real/meta; meta/real quando menor e melhor),
    com teto de 150%. Empate de peso -> media das metas empatadas. Meta qualitativa no topo
    -> desce para a de maior peso que tenha meta e real. Persistindo o empate, decide a
    superacao media ponderada de todas as metas ("desempate2").
    O criterio antigo do slide (real/meta sem teto e sem direcao) dava 1055% para o Erick
    (Eficiencia Tributaria 12,7 mi contra 1,2 mi) e punia quem ia bem em meta de custo.
  - Lideranca do slide sem farol na pasta continua na lista, marcada "sem farol de metas", e
    vai para o fim do ranking (pedido do Silvio, 12/10/2026).

A cada rodada tambem grava data/conferencia-desempate.md: a meta de maior peso de cada um, com
meta, real, sentido e superacao - para conferir o desempate contra o Excel.
"""
import contextlib, json, os, shutil, sys, tempfile, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import farol_base as fb  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("FAROL_BASE", r"\\192.168.102.161\rmr\2026")
SAIDA = os.environ.get("FAROL_SAIDA", os.path.join(RAIZ, "data", "farol.json"))
CONFERENCIA = os.path.join(os.path.dirname(SAIDA), "conferencia-desempate.md")
MESES = fb.MESES
TETO = 1.5
MENOR_MELHOR = ("custo", "pacote", "turnover", "absente", "incidente", "acidente",
                "ocorr", "despesa", "perda", "avaria", "dias", "prazo", "inadimpl")


# ------------------------------------------------------------------ fonte dos arquivos
class Fonte:
    """Pasta do RMR: caminho local/UNC (Windows) ou SMB direto (Linux, sem montar nada)."""

    def __init__(self, base):
        self.base = base
        self.smb = None
        usuario = os.environ.get("FAROL_SMB_USUARIO")
        if usuario:
            import smbclient  # pip install smbprotocol (venv do servidor)
            servidor = base.strip("\\/").replace("/", "\\").split("\\")[0]
            smbclient.register_session(servidor, username=usuario,
                                       password=os.environ.get("FAROL_SMB_SENHA", ""))
            self.smb = smbclient

    def caminho(self, rel):
        if self.smb:
            return "\\\\" + self.base.strip("\\/").replace("/", "\\") + "\\" + rel.replace("/", "\\")
        return os.path.join(self.base, *rel.split("/"))

    def existe(self, rel):
        c = self.caminho(rel)
        return self.smb.path.isfile(c) if self.smb else os.path.isfile(c)

    @contextlib.contextmanager
    def local(self, rel):
        """Caminho local para o openpyxl. Pelo SMB, copia para um temporario e apaga depois."""
        if not self.smb:
            yield self.caminho(rel)
            return
        fd, tmp = tempfile.mkstemp(suffix=".xlsx")
        try:
            with os.fdopen(fd, "wb") as dst, self.smb.open_file(self.caminho(rel), mode="rb") as src:
                shutil.copyfileobj(src, dst, 1024 * 1024)
            yield tmp
        finally:
            os.remove(tmp)


# ------------------------------------------------------------------ regras
def ultimo_mes():
    forcado = os.environ.get("FAROL_ULTIMO_MES", "").strip().lower()
    if forcado in MESES:
        return forcado
    return MESES[max(time.localtime().tm_mon - 2, 0)]


def direcao(mt):
    """+1 maior e melhor, -1 menor e melhor. Os meses dizem: real abaixo da meta com farol
    cheio => menor e melhor. Sem evidencia, vale o nome do indicador."""
    votos = 0
    for d in mt["meses"].values():
        m, r, a = d.get("meta"), d.get("real"), d.get("ating")
        if m is None or r is None or a is None or m == r:
            continue
        cheio = a >= 0.999
        votos += (-1 if cheio else 1) if r < m else (1 if cheio else -1)
    if votos:
        return 1 if votos > 0 else -1
    return -1 if any(k in fb.norm(mt["indicador"]) for k in MENOR_MELHOR) else 1


def superacao(meta, real, sentido):
    if meta in (None, 0) or real is None:
        return None
    if meta < 0 or real < 0:  # custo lancado com sinal negativo em alguns farois
        meta, real = abs(meta), abs(real)
    if sentido < 0:
        if not real:
            return None
        x = meta / real
    else:
        x = real / meta
    return round(min(max(x, 0.0), TETO), 4)


def sup_meta(mt, chave, meses):
    """(superacao, meta, real, origem) de uma meta na chave ('acum' ou um mes). No acumulado,
    farol sem bloco ACUMULADO (Francis, Lucas Bueno, Rodolfo) usa a media dos meses."""
    if chave != "acum":
        d = mt["meses"].get(chave, {})
        return superacao(d.get("meta"), d.get("real"), mt["sentido"]), d.get("meta"), d.get("real"), chave
    x = superacao(mt.get("meta_acum"), mt.get("real_acum"), mt["sentido"])
    if x is not None:
        return x, mt.get("meta_acum"), mt.get("real_acum"), "acumulado"
    xs = [superacao(d.get("meta"), d.get("real"), mt["sentido"])
          for m, d in mt["meses"].items() if m in meses]
    xs = [v for v in xs if v is not None]
    if not xs:
        return None, None, None, None
    return round(sum(xs) / len(xs), 4), None, None, "media de %d meses" % len(xs)


def desempates(metas, chave, meses):
    """(desempate, desempate2, metas usadas no desempate)."""
    quant = []
    for mt in metas:
        if not mt.get("peso"):
            continue
        x, m, r, origem = sup_meta(mt, chave, meses)
        if x is not None:
            quant.append((mt, x, m, r, origem))
    if not quant:
        return None, None, []
    pmax = max(q[0]["peso"] for q in quant)
    topo = [q for q in quant if abs(q[0]["peso"] - pmax) < 1e-9]
    soma_peso = sum(q[0]["peso"] for q in quant)
    pond = sum(q[0]["peso"] * q[1] for q in quant) / soma_peso
    return round(sum(q[1] for q in topo) / len(topo), 4), round(pond, 4), topo


# ------------------------------------------------------------------ conferencia
def fmt(v):
    if v is None:
        return "-"
    if abs(v) <= 2 and not float(v).is_integer():
        return ("%.2f%%" % (v * 100)).replace(".", ",")
    return ("{:,.0f}".format(v)).replace(",", ".")


def gravar_conferencia(linhas, gerado):
    out = ["# Conferencia do desempate (YTD)", "",
           "Gerado em %s. Superacao = real / meta (ou meta / real quando menor e melhor), teto de 150%%." % gerado,
           "Empate no maior peso: vale a media. Sem bloco ACUMULADO no farol: media dos meses.", "",
           "| Lideranca | % YTD | Meta de maior peso | Peso | Meta | Real | Sentido | Superacao | Origem | Desempate |",
           "|---|---|---|---|---|---|---|---|---|---|"]
    out += linhas
    tmp = CONFERENCIA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    os.replace(tmp, CONFERENCIA)


# ------------------------------------------------------------------ principal
def main():
    lista = json.load(open(os.path.join(RAIZ, "etl", "liderancas.json"), encoding="utf-8"))
    lista.pop("_comentario", None)
    ult = ultimo_mes()
    meses = MESES[:MESES.index(ult) + 1]
    try:
        fonte = Fonte(BASE)
        acessivel = fonte.smb.path.isdir(fonte.caminho("")) if fonte.smb else os.path.isdir(BASE)
    except Exception as e:  # credencial errada, servidor fora
        acessivel, motivo = False, str(e)
    else:
        motivo = "pasta nao encontrada"
        if os.name != "nt" and not fonte.smb:
            motivo = "falta configurar FAROL_SMB_USUARIO e FAROL_SMB_SENHA no .env do servidor"
    if not acessivel:
        # Sem isto cada farol esperava o tempo limite da rede: 44 x ~20 s para dizer que caiu.
        print("FALHOU: nao consegui abrir a pasta dos farois (%s): %s" % (BASE, motivo), flush=True)
        sys.exit(2)
    pessoas, problemas, conferencia = [], [], []
    print("total %d" % len(lista), flush=True)

    def sem_farol(nomes, motivo):
        for nome in nomes:
            pessoas.append({"id": fb.norm(nome).replace(" ", "-"), "nome": nome, "semFarol": True,
                            "ytd": None, "mes": {}, "desempate": {}, "desempate2": {}, "metas": []})
            conferencia.append("| %s | - | sem farol de metas (%s) | | | | | | | |" % (nome, motivo))

    for rel, nomes in lista.items():
        t0 = time.time()
        try:
            if not fonte.existe(rel):
                sem_farol(nomes, "arquivo nao esta na pasta")
                problemas.append("%s: nao esta na pasta - %s fica(m) sem farol" % (rel, ", ".join(nomes)))
                print("sem-farol %s" % rel, flush=True)
                continue
            with fonte.local(rel) as caminho:
                rec = fb.extrair(caminho)
        except Exception as e:  # farol aberto, corrompido, rede caiu...
            sem_farol(nomes, "erro ao ler")
            problemas.append("%s: %s" % (rel, e))
            print("erro %s: %s" % (rel, e), flush=True)
            continue
        if rec.get("erro") or not rec["metas"]:
            sem_farol(nomes, rec.get("erro") or "nenhuma meta encontrada")
            problemas.append("%s: %s" % (rel, rec.get("erro") or "nenhuma meta encontrada"))
            print("sem-farol %s" % rel, flush=True)
            continue
        if (rec.get("conf") or {}).get("ok") is False:
            problemas.append("%s: as metas nao fecham com a linha Atingimento" % rel)
        for mt in rec["metas"]:
            mt["sentido"] = direcao(mt)
        tot = rec.get("total") or {}

        desemp, desemp2 = {}, {}
        for chave in ["acum"] + meses:
            desemp[chave], desemp2[chave], topo = desempates(rec["metas"], chave, meses)
            if chave == "acum":
                topo_ytd = topo

        for nome in nomes:
            pessoas.append({
                "id": fb.norm(nome).replace(" ", "-"),
                "nome": nome,
                "ytd": tot.get("acum"),
                "mes": {m: v for m, v in (tot.get("meses") or {}).items() if m in meses},
                "desempate": desemp,
                "desempate2": desemp2,
                "metas": [{
                    "indicador": mt["indicador"],
                    "peso": mt["peso"],
                    "ytd": mt["ating"],
                    "mes": {m: d["ating"] for m, d in mt["meses"].items()
                            if m in meses and d.get("ating") is not None},
                } for mt in rec["metas"]],
            })
            if not topo_ytd:
                conferencia.append("| %s | %s | nenhuma meta com meta e real | | | | | | | - |" % (nome, fmt(tot.get("acum"))))
            for mt, x, m, r, origem in topo_ytd:
                conferencia.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    nome, fmt(tot.get("acum")), mt["indicador"], fmt(mt["peso"]), fmt(m), fmt(r),
                    "menor e melhor" if mt["sentido"] < 0 else "maior e melhor",
                    fmt(x), origem, fmt(desemp["acum"])))
        print("ok %s ytd=%s (%.0fs)" % (rel, tot.get("acum"), time.time() - t0), flush=True)

    # Mes padrao = o ultimo em que a maioria ja lancou o real da meta de maior peso. Em
    # 10/10/2026 setembro ainda estava pela metade (muita gente com 0% e real zerado).
    def completo(m):
        return sum(1 for p in pessoas if p["desempate"].get(m)) >= 0.7 * len(pessoas)
    padrao = next((m for m in reversed(meses) if completo(m)), ult)

    gerado = time.strftime("%d/%m/%Y %H:%M")
    dados = {
        "gerado": gerado,
        "ano": int(os.environ.get("FAROL_ANO", time.localtime().tm_year)),
        "meses": meses,
        "mesPadrao": padrao,
        "parciais": meses[meses.index(padrao) + 1:],
        "pessoas": pessoas,
    }
    lidos = sum(1 for p in pessoas if not p.get("semFarol"))
    if lidos < len(pessoas) / 2:
        # rede fora, credencial errada...: nao troca um ranking bom por um vazio
        print("FALHOU: so %d de %d farois lidos - data/farol.json mantido como estava" % (lidos, len(pessoas)))
        for p in problemas[:10]:
            print("  - " + p)
        sys.exit(2)

    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    tmp = SAIDA + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(dados, fh, ensure_ascii=False)
    os.replace(tmp, SAIDA)  # o servidor nunca le um arquivo pela metade
    gravar_conferencia(conferencia, gerado)

    print("\n%d liderancas (%d com farol) | meses ate %s | mes padrao %s" % (len(pessoas), lidos, ult, padrao))
    if problemas:
        print("Atencao:")
        for p in problemas:
            print("  - " + p)
    print("gravado: " + SAIDA)


if __name__ == "__main__":
    main()
