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
import contextlib, hashlib, json, os, shutil, sys, tempfile, time

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

    def assinatura(self, rel):
        """(data de modificacao, tamanho) - muda quando alguem salva o farol."""
        st = (self.smb.stat if self.smb else os.stat)(self.caminho(rel))
        return [int(st.st_mtime), int(st.st_size)]

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


CACHE = os.path.join(os.path.dirname(SAIDA), ".cache")


def ler_com_cache(fonte, rel):
    """Leitura bruta do farol (fb.extrair), guardada por arquivo. So rele quem mudou desde a
    ultima vez: com os 44 farois na rede, reler tudo leva ~25 min pela VPN; sem mudancas, o
    Atualizar termina em segundos. FAROL_SEM_CACHE=1 forca reler tudo."""
    assinatura = fonte.assinatura(rel)
    arq = os.path.join(CACHE, hashlib.sha1(rel.encode("utf-8")).hexdigest() + ".json")
    if os.environ.get("FAROL_SEM_CACHE") != "1" and os.path.exists(arq):
        try:
            with open(arq, encoding="utf-8") as fh:
                guardado = json.load(fh)
            if guardado.get("assinatura") == assinatura and guardado.get("versao") == fb_versao():
                return guardado["rec"]
        except (OSError, ValueError):
            pass
    with fonte.local(rel) as caminho:
        rec = fb.extrair(caminho)
    os.makedirs(CACHE, exist_ok=True)
    with open(arq + ".tmp", "w", encoding="utf-8") as fh:
        json.dump({"assinatura": assinatura, "versao": fb_versao(), "rec": rec}, fh, ensure_ascii=False)
    os.replace(arq + ".tmp", arq)
    return rec


def fb_versao():
    """Muda quando o parser muda - invalida o cache sozinho depois de um deploy."""
    with open(fb.__file__, "rb") as fh:
        return hashlib.sha1(fh.read()).hexdigest()[:12]


# ------------------------------------------------------------------ regras
def ultimo_mes():
    forcado = os.environ.get("FAROL_ULTIMO_MES", "").strip().lower()
    if forcado in MESES:
        return forcado
    return MESES[max(time.localtime().tm_mon - 2, 0)]


def canonico(m, r):
    """Custo lancado com sinal negativo (meta E real < 0, ex.: OpEx TI do Leo Resende) vira
    magnitude positiva. Sentido e superacao sao sempre calculados sobre esses valores."""
    if m is not None and r is not None and m < 0 and r < 0:
        return -m, -r
    return m, r


def direcao(mt):
    """+1 maior e melhor, -1 menor e melhor.

    Evidencia: real abaixo da meta com farol cheio => menor e melhor. O ACUMULADO (meta/real
    acumulados + farol acumulado) vale 2 votos e cada mes 1: no farol do Romario o farol do mes
    diz 100% com real 62% contra meta 80% (e ate com real zerado), mas o acumulado diz 0% - o
    mensal daquela planilha nao e confiavel (12/10/2026). Mes com real zerado nao vota (e
    lancamento pendente, nao resultado). Sem evidencia, vale o nome do indicador."""
    def voto(m, r, a):
        m, r = canonico(m, r)
        if m is None or r is None or a is None or m == r or r == 0:
            return 0
        cheio = a >= 0.999
        return (-1 if cheio else 1) if r < m else (1 if cheio else -1)

    votos = sum(voto(d.get("meta"), d.get("real"), d.get("ating")) for d in mt["meses"].values())
    votos += 2 * voto(mt.get("meta_acum"), mt.get("real_acum"), mt.get("ating"))
    if votos:
        return 1 if votos > 0 else -1
    return -1 if any(k in fb.norm(mt["indicador"]) for k in MENOR_MELHOR) else 1


def superacao(meta, real, sentido):
    """Quanto o real superou a meta (1 = bateu a meta), com teto de 150%.

    Mesmo sinal: razao, como nos proprios farois (real/meta; meta/real se menor e melhor).
    Sinais diferentes ou real zerado: 1 + desvio relativo a meta. Ex.: margem do Bruno Fonseca
    com meta -23,2% e real +10,6% - a razao dava 45% (punia quem foi muito melhor que a meta)."""
    meta, real = canonico(meta, real)
    if meta in (None, 0) or real is None:
        return None
    if meta > 0 and real > 0:
        x = real / meta if sentido > 0 else meta / real
    else:
        x = 1 + sentido * (real - meta) / abs(meta)
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
    if abs(v) <= 2:
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
    # Dois rankings: liderancas (slide 33) e diretoria (slides 30 e 36).
    entradas = []  # (arquivo, [(nome, area)], grupo)
    lid = json.load(open(os.path.join(RAIZ, "etl", "liderancas.json"), encoding="utf-8"))
    lid.pop("_comentario", None)
    entradas += [(rel, [(n, None) for n in nomes], "liderancas") for rel, nomes in lid.items()]
    dire = json.load(open(os.path.join(RAIZ, "etl", "diretoria.json"), encoding="utf-8"))
    dire.pop("_comentario", None)
    entradas += [(rel, [(d["nome"], d["area"])], "diretoria") for rel, d in dire.items()]
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
    print("total %d" % len(entradas), flush=True)

    def sem_farol(nomes, motivo):
        for nome, area in nomes:
            pessoas.append({"id": fb.norm(nome).replace(" ", "-"), "nome": nome, "grupo": grupo, "area": area,
                            "semFarol": True, "ytd": None, "mes": {}, "desempate": {}, "desempate2": {}, "metas": []})
            conferencia.append("| %s | - | sem farol de metas (%s) | | | | | | | |" % (nome, motivo))

    for rel, nomes, grupo in entradas:
        t0 = time.time()
        try:
            if not fonte.existe(rel):
                sem_farol(nomes, "arquivo nao esta na pasta")
                problemas.append("%s: nao esta na pasta - %s fica(m) sem farol" % (rel, ", ".join(n for n, _ in nomes)))
                print("sem-farol %s" % rel, flush=True)
                continue
            rec = ler_com_cache(fonte, rel)
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
        # Mes so conta como lancado se alguma meta tem meta E real numericos nele. Nos farois que
        # reaproveitam um bloco para o mes corrente (Leo Resende, Maraiza, Weberson), os outros
        # meses ficam com #REF! e a linha Atingimento da 0% - isso e "nao lancou", nao 0%.
        def lancado(m):
            return any(isinstance(mt["meses"].get(m, {}).get("meta"), float)
                       and isinstance(mt["meses"].get(m, {}).get("real"), float) for mt in rec["metas"])
        tot["meses"] = {m: v for m, v in (tot.get("meses") or {}).items() if lancado(m)}

        desemp, desemp2 = {}, {}
        for chave in ["acum"] + meses:
            desemp[chave], desemp2[chave], topo = desempates(rec["metas"], chave, meses)
            if chave == "acum":
                topo_ytd = topo

        for nome, area in nomes:
            pessoas.append({
                "id": fb.norm(nome).replace(" ", "-"),
                "nome": nome,
                "grupo": grupo,
                "area": area,
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
        lids = [p for p in pessoas if p["grupo"] == "liderancas"]
        return sum(1 for p in lids if p["desempate"].get(m)) >= 0.7 * len(lids)
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
