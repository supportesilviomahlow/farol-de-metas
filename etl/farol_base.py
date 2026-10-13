# -*- coding: utf-8 -*-
"""
Parser do Farol de Metas (planilha -> metas da pessoa).

Copiado de R:/2026/01 - Transportes/Dash DR/extrair_metas.py em 10/10/2026. Aqui so as
funcoes de leitura sao usadas (extrair); o main() original fica por compatibilidade.

Le cada arquivo "Farol*/Metas*.xlsx" da pasta, localiza a aba do farol e extrai,
para cada indicador: area, indicador, unidade, peso, atingimento acumulado, LE,
meta/real acumulados e meta/real/atingimento de cada mes. Tambem le a linha
"Atingimento" para o consolidado da pessoa.

Layout esperado (varia de arquivo para arquivo, o parser se adapta pelos rotulos):
  Area | INDICADOR | UNID. | Peso | Ating | Farol de Metas | LE | ACUMULADO(Meta,Real,
  Ating,Parcial) | JAN(Meta,Real,Ating,Parcial) | FEV(...) | ...
  - "Farol de Metas" (a coluna solta, sem sub-rotulo) = o grau do farol em %.
    E a fonte do atingimento acumulado de cada meta - a unica coluna que significa
    a mesma coisa em todos os arquivos.
  - "Ating"   = deveria ser o atingimento PONDERADO (fracao do peso), mas em alguns
    farois foi preenchida com o proprio peso; so usada como fallback.
  - "Parcial" = atingimento em % da meta (0..1 ou 0..100) -> fonte do % de cada mes
  - linha "Atingimento": % consolidado da pessoa (col do Peso = acumulado,
    col LE = tendencia, col Meta de cada mes = % do mes)

Uso:
    set FAROL_BASE=R:/2026/01 - Transportes/
    set FAROL_OUT=R:/2026/01 - Transportes/Dash DR
    set FAROL_ULTIMO_MES=jul          (opcional; default = detectado)
    python extrair_metas.py

Para reler UM farol so (segundos em vez de ~10 min) e mesclar no metas.json
existente, sem tocar nos demais:

    set FAROL_SOMENTE=thais
    python extrair_metas.py
"""
import openpyxl, glob, os, json, re, unicodedata, time

# Versao gravada no cache do etl/extrair.py. Mudar so quando uma correcao do parser afeta a
# leitura de TODOS os farois (forca reler tudo). Correcao que afeta poucos: apagar so o cache deles.
VERSAO_PARSER = "2026-10-13"

BASE = os.environ.get("FAROL_BASE", "R:/2026/01 - Transportes/")
OUT_DIR = os.environ.get("FAROL_OUT", os.path.join(BASE, "Dash DR"))
ULTIMO_MES = os.environ.get("FAROL_ULTIMO_MES", "").strip().lower() or None
SOMENTE = os.environ.get("FAROL_SOMENTE", "").strip().lower() or None

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
MES_LABEL = {"jan": "Jan", "fev": "Fev", "mar": "Mar", "abr": "Abr",
             "mai": "Mai", "jun": "Jun", "jul": "Jul", "ago": "Ago",
             "set": "Set", "out": "Out", "nov": "Nov", "dez": "Dez"}
MES_FULL = {
    "jan": ["jan", "janeiro"], "fev": ["fev", "fevereiro"],
    "mar": ["mar", "marc", "marco"], "abr": ["abr", "abril"],
    "mai": ["mai", "maio"], "jun": ["jun", "junho"],
    "jul": ["jul", "julho"], "ago": ["ago", "agosto"],
    "set": ["set", "setembro"], "out": ["out", "outubro"],
    "nov": ["nov", "novembro"], "dez": ["dez", "dezembro"],
}

# Reportes diretos do diretor (mesma lista do dashboard consolidado)
DIRETOS = ["laihara", "matheus", "tales", "lucas", "franco"]
DIRETOR = ["eduardo"]

HINT = ("farol", "metas", "gerencial", "resumo", "ficha")
MAX_ROWS, MAX_COLS = 80, 170
VAZIO = ("", "-", "--", "tba", "tbd", "n/a", "na", "#div/0!", "#n/d",
         "#valor!", "#ref!", "#nome?", "#num!")
UNID_OK = ("%", "r$", "un", "und", "qtd", "dia", "hora", "h", "pts", "pto",
           "nps", "nota", "#", "kg", "km", "m3", "ton", "cx", "$", "&")


def norm(s):
    if s is None:
        return ""
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().lower()


def mes_de(t):
    for m, vs in MES_FULL.items():
        if any(t == v or t.startswith(v) for v in vs):
            return m
    return None


def num(v):
    """Converte para float; None para '-', 'TBA', '> 87%', erro de formula."""
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    bruto = str(v)
    s = bruto.strip().replace("%", "").replace("R$", "").replace(">", "").replace("<", "").strip()
    if norm(s) in VAZIO:
        return None
    if re.match(r"^-?\d{1,3}(\.\d{3})+(,\d+)?$", s):        # 1.234,56
        s = s.replace(".", "").replace(",", ".")
    else:
        s = s.replace(",", ".")
    try:
        x = float(s)
    except ValueError:
        return None
    # texto tipo "> 87%" vem como 87; celulas numericas ja chegam como 0.87
    return x / 100.0 if "%" in bruto else x


def frac(v):
    """Atingimento em fracao 0..1+ (aceita 80 ou 0.8)."""
    x = num(v)
    if x is None:
        return None
    if x > 2.0:
        x = x / 100.0
    if x < 0 or x > 3:
        return None
    return round(x, 4)


def nome_do_arquivo(fname):
    n = re.sub(r"\.xlsx$", "", os.path.basename(fname), flags=re.I)
    n = re.sub(r"(?i)farol de metas\s*-?\s*", "", n)
    n = re.sub(r"(?i)^farol\s*", "", n)
    n = re.sub(r"(?i)^metas\s*-?\s*", "", n)
    n = re.sub(r"(?i)\bcoordenador[ae]?\b\s*", "", n)
    n = re.sub(r"(?i)\bcoord\.?(?=\s|_|$)\s*", "", n)
    n = re.sub(r"(?i)\btracking final\b", "", n)
    n = re.sub(r"(?i)\bescopo\b", "", n)
    n = n.replace("_", " ")
    # remove tokens finais que sao so numeros/pontuacao (versoes: "- 4", "026", "2026")
    for _ in range(4):
        novo = re.sub(r"[\s\-.]*\b\d{1,4}\b[\s\-.]*$", "", n).strip(" .-")
        if novo == n:
            break
        n = novo
    n = re.sub(r"\s+", " ", n).strip(" .-")
    return " ".join(w if w.isupper() else w.capitalize() for w in n.split()) \
        or os.path.basename(fname)


def grid(ws):
    out = []
    for row in ws.iter_rows(min_row=1, max_row=MAX_ROWS, max_col=MAX_COLS, values_only=True):
        out.append(list(row))
    return out


def bloco(sub, c0, c1):
    """Sub-colunas Meta/Real/Ating/Parcial dentro de [c0, c1)."""
    blk = {}
    for c in range(c0, min(c1, MAX_COLS)):
        t = sub.get(c, "")
        if t in ("meta", "real", "ating", "parcial") and t not in blk:
            blk[t] = c
    return blk


def mapear(g, hdr):
    """Mapeia colunas pelo cabecalho (linha hdr) + sub-cabecalho (hdr+1)."""
    hr, ic = hdr
    if hr + 1 >= len(g):
        return None
    lab = {c: norm(v) for c, v in enumerate(g[hr]) if norm(v)}
    sub = {c: norm(v) for c, v in enumerate(g[hr + 1]) if norm(v)}

    m = {"hr": hr, "ind": ic, "sub_row": hr + 1}
    for c in sorted(lab):
        t = lab[c]
        if t == "area" and "area" not in m:
            m["area"] = c
        elif t.startswith("unid") and "unid" not in m:
            m["unid"] = c
        elif t == "peso" and "peso" not in m:
            m["peso"] = c
        elif t == "ating" and "ating" not in m:
            m["ating"] = c
        elif t == "le" and "le" not in m:
            m["le"] = c
        elif t in ("acumulado", "acum", "ytd", "acumulado ano") and "acum" not in m:
            m["acum"] = c

    marcos = sorted([(c, mes_de(t)) for c, t in lab.items() if mes_de(t)])
    # Vale o ROTULO, nao a ordem dos blocos (12/10/2026). Nos farois do Leo Resende, Maraiza,
    # Weberson e Rodolfo, quem preenche reaproveita um bloco e troca o rotulo para o mes que
    # esta lancando (ex.: o 2o bloco escrito "AGO" com os numeros de agosto); o bloco com o nome
    # original do mes fica com #REF!. Com rotulo repetido, o setdefault abaixo fica com o
    # PRIMEIRO, que e o reaproveitado. Em 10/10 tentei mapear pela ordem e isso jogava agosto
    # em fevereiro - nao refazer.
    limites = [c for c, _ in marcos] + [MAX_COLS]
    m["meses"] = {}
    for i, (c0, mes) in enumerate(marcos):
        blk = bloco(sub, c0, limites[i + 1])
        if blk:
            m["meses"].setdefault(mes, blk)

    primeiro_mes = marcos[0][0] if marcos else MAX_COLS
    m["acum_blk"] = bloco(sub, m["acum"], min(m["acum"] + 6, primeiro_mes)) if "acum" in m else {}

    # A coluna "Farol de Metas" SEM sub-rotulo (e antes do primeiro mes) e o grau
    # do farol acumulado em %. O mesmo rotulo reaparece dentro dos blocos mensais e
    # no bloco YTD, mas la sempre com sub-rotulo (Ating/Parcial) - esses nao servem.
    for c in sorted(lab):
        # "Farol " (so a palavra, com espaco no fim) no farol do Leonardo Bortoletto (13/10/2026)
        if c < primeiro_mes and lab[c] in ("farol de metas", "farol") and c not in sub:
            m["farol"] = c
            break

    if "peso" not in m or not m["meses"]:
        return None
    return m


def linha_atingimento(g, hr):
    for r in range(hr + 1, len(g)):
        if any(norm(v) == "atingimento" for v in g[r][:18]):
            return r
    return None


def achar_aba(wb):
    """Escolhe a aba com a melhor estrutura de farol (nao a primeira que casa)."""
    ordem = [s for s in wb.sheetnames if any(h in norm(s) for h in HINT)]
    ordem += [s for s in wb.sheetnames if s not in ordem]
    melhor = None
    for sh in ordem[:8]:
        try:
            g = grid(wb[sh])
        except Exception:
            continue
        hdr = None
        for r, row in enumerate(g):
            for c, v in enumerate(row[:18]):
                if norm(v) == "indicador":
                    hdr = (r, c)
                    break
            if hdr:
                break
        if not hdr:
            continue
        m = mapear(g, hdr)
        if not m:
            continue
        arow = linha_atingimento(g, m["hr"])
        score = (len(m["meses"]) + (3 if arow is not None else 0)
                 + (2 if m["acum_blk"] else 0) + (1 if "le" in m else 0))
        if melhor is None or score > melhor[0]:
            melhor = (score, sh, g, m, arow)
        if score >= 18:
            break
    if melhor is None:
        return None, None, None, None
    return melhor[1], melhor[2], melhor[3], melhor[4]


def extrair(path):
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sh, g, m, arow = achar_aba(wb)
        if not m:
            return {"nome": nome_do_arquivo(path), "metas": [],
                    "erro": "estrutura de farol nao reconhecida",
                    "abas": wb.sheetnames[:8]}

        fim = arow if arow is not None else min(m["hr"] + 30, len(g))

        def cel(r, c):
            return g[r][c] if (c is not None and 0 <= c < len(g[r])) else None

        def pct_do_bloco(r, blk, peso):
            """% da meta: usa Parcial; senao Ating/Peso."""
            if "parcial" in blk:
                v = frac(cel(r, blk["parcial"]))
                if v is not None:
                    return v
            if "ating" in blk and peso:
                v = num(cel(r, blk["ating"]))
                if v is not None:
                    return round(min(v / peso, 3), 4)
            return None

        def pct_acumulado(r, peso):
            """% acumulado da meta, em ordem de confiabilidade.

            1. coluna "Farol de Metas" -> o grau do farol, ja em %. E a unica que
               significa a mesma coisa em todos os arquivos.
            2. "Parcial" do bloco ACUMULADO/YTD (tambem ja em %).
            3. "Ating" do cabecalho / Peso. Cuidado: em alguns farois (Bruno,
               Ivanaldo) essa coluna foi preenchida com o proprio peso, o que daria
               100% em tudo - por isso e descartada quando Ating == Peso.
            4. "Ating" do bloco ACUMULADO / Peso.
            """
            if "farol" in m:
                v = frac(cel(r, m["farol"]))
                if v is not None:
                    return v
            if "parcial" in m["acum_blk"]:
                v = frac(cel(r, m["acum_blk"]["parcial"]))
                if v is not None:
                    return v
            if "ating" in m and peso:
                v = num(cel(r, m["ating"]))
                if v is not None and abs(v - peso) > 1e-9:
                    return round(min(v / peso, 3), 4)
            return pct_do_bloco(r, m["acum_blk"], peso)

        area_atual, metas = "", []
        for r in range(m["sub_row"] + 1, fim):
            a = cel(r, m.get("area"))
            if a and str(a).strip():
                area_atual = str(a).strip()
            ind = cel(r, m["ind"])
            if not ind or not str(ind).strip():
                continue
            if norm(ind) in ("indicador", "atingimento", "total", "area"):
                continue

            peso = num(cel(r, m.get("peso")))
            unid = cel(r, m.get("unid"))
            unid = "" if (unid is None or isinstance(unid, (int, float))) else str(unid).strip()
            if unid and (norm(unid) in VAZIO
                         or (norm(unid) not in UNID_OK and len(unid) > 6)):
                unid = ""

            ating_pct = pct_acumulado(r, peso)

            reg = {
                "area": area_atual,
                "indicador": re.sub(r"\s+", " ", str(ind).strip()),
                "unid": unid,
                "peso": round(peso, 4) if peso is not None else None,
                "ating": ating_pct,
                "le": frac(cel(r, m.get("le"))),
                "meta_acum": num(cel(r, m["acum_blk"].get("meta"))),
                "real_acum": num(cel(r, m["acum_blk"].get("real"))),
                "meses": {},
            }
            for mes, blk in m["meses"].items():
                d = {}
                for k in ("meta", "real"):
                    v = num(cel(r, blk.get(k)))
                    if v is not None:
                        d[k] = v
                v = pct_do_bloco(r, blk, peso)
                if v is not None:
                    d["ating"] = v
                if d:
                    reg["meses"][mes] = d
            if reg["peso"] is None and not reg["meses"]:
                continue
            metas.append(reg)

        # linha "Atingimento": acumulado na col do Peso, LE na col LE, mes na col Meta.
        # Em alguns arquivos o rotulo fica uma linha abaixo dos numeros -> escolhe a
        # linha vizinha com mais meses preenchidos.
        tot = {"acum": None, "le": None, "meses": {}}
        if arow is not None:
            drow, melhor = arow, -1
            for r in (arow, arow - 1, arow + 1):
                if r < 0 or r >= len(g):
                    continue
                n = sum(1 for blk in m["meses"].values()
                        if frac(cel(r, blk.get("meta"))) is not None)
                if n > melhor:
                    melhor, drow = n, r

            c0 = m.get("peso", 0)
            c1 = max(list(m["acum_blk"].values()) + [m.get("le") or c0, c0])
            for c in range(c0, c1 + 1):
                v = frac(cel(drow, c))
                if v is not None:
                    tot["acum"] = v
                    tot["_c_acum"] = c
                    break
            for c in (m.get("le"), (m.get("le") or 0) - 1, (m.get("le") or 0) + 1):
                if c is None or c == tot.get("_c_acum"):
                    continue
                v = frac(cel(drow, c))
                if v is not None:
                    tot["le"] = v
                    break
            tot.pop("_c_acum", None)
            for mes, blk in m["meses"].items():
                v = frac(cel(drow, blk.get("meta")))
                if v is None:
                    v = frac(cel(drow, blk.get("ating")))
                if v is not None:
                    tot["meses"][mes] = v

        rec = {"nome": nome_do_arquivo(path), "aba": sh, "metas": metas, "total": tot}
        rec["conf"] = conferir(rec)
        return rec
    finally:
        wb.close()


def conferir(rec):
    """As metas tem de reconstituir o valor da linha 'Atingimento' do farol.

    Alguns farois consolidam por media ponderada pelo peso, outros por media
    simples dos graus - aceita qualquer uma das duas. Se nenhuma fecha, ou a
    coluna lida esta errada, ou o proprio farol esta inconsistente; nesse caso
    o dashboard sinaliza em vez de mascarar.
    """
    pond, xs = 0.0, []
    for mt in rec["metas"]:
        if mt["ating"] is None:
            continue
        xs.append(mt["ating"])
        if mt["peso"]:
            pond += mt["ating"] * mt["peso"]
    simples = sum(xs) / len(xs) if xs else None
    alvo = (rec.get("total") or {}).get("acum")
    conf = {"soma": round(pond, 4),
            "media": round(simples, 4) if simples is not None else None,
            "acum": alvo, "ok": None, "criterio": None}
    if alvo is None or not xs:
        return conf
    if abs(pond - alvo) <= 0.02:
        conf["ok"], conf["criterio"] = True, "ponderada"
    elif simples is not None and abs(simples - alvo) <= 0.02:
        conf["ok"], conf["criterio"] = True, "media simples"
    else:
        conf["ok"] = False
    return conf


def detectar_ultimo_mes(pessoas):
    """Ultimo mes fechado = mes anterior ao corrente, recuando se nao houver apuracao.

    Os farois ja tem meta lancada para o ano inteiro, entao os meses futuros
    aparecem preenchidos; por isso o corte e pelo calendario, nao pelos dados.
    """
    cont = {mes: sum(1 for p in pessoas
                     if (p.get("total") or {}).get("meses", {}).get(mes) is not None)
            for mes in MESES}
    i = max(time.localtime().tm_mon - 2, 0)          # mes anterior, base 0
    while i > 0 and cont[MESES[i]] == 0:
        i -= 1
    return MESES[i], cont


def main():
    files = [f for f in glob.glob(os.path.join(BASE, "*.xlsx"))
             if not os.path.basename(f).startswith("~$")
             and "consolidado" not in norm(f) and "pia de" not in norm(f)]
    if SOMENTE:
        files = [f for f in files if SOMENTE in norm(os.path.basename(f))]
        if not files:
            raise SystemExit("FAROL_SOMENTE=%r nao casou com nenhum arquivo" % SOMENTE)
        print("modo parcial: %d arquivo(s) -> %s"
              % (len(files), ", ".join(os.path.basename(f) for f in files)), flush=True)
    pessoas = []
    for f in sorted(files):
        t0 = time.time()
        print("lendo %s (%.0fMB)..." % (os.path.basename(f), os.path.getsize(f) / 1048576), flush=True)
        try:
            rec = extrair(f)
        except Exception as e:
            rec = {"nome": nome_do_arquivo(f), "metas": [], "erro": "%s: %s" % (type(e).__name__, e)}
        rec["arquivo"] = os.path.basename(f)
        primeiro = norm(rec["nome"]).split()[0] if norm(rec["nome"]) else ""
        rec["grupo"] = ("Diretor" if primeiro in DIRETOR
                        else "Diretos" if primeiro in DIRETOS else "Indiretos")
        pessoas.append(rec)
        t = rec.get("total") or {}
        c = rec.get("conf") or {}
        print("  -> %d metas | aba=%s | acum=%s le=%s | confere=%s (%s) | %s (%.0fs)"
              % (len(rec["metas"]), rec.get("aba"), t.get("acum"), t.get("le"),
                 c.get("ok"), c.get("criterio") or ("soma %s med %s" % (c.get("soma"), c.get("media"))), rec.get("erro", "ok"), time.time() - t0), flush=True)

    os.makedirs(OUT_DIR, exist_ok=True)
    outp = os.path.join(OUT_DIR, "metas.json")

    # Modo parcial: mescla os relidos no metas.json existente, preservando o resto
    antigo = None
    if SOMENTE and os.path.exists(outp):
        with open(outp, encoding="utf-8") as fh:
            antigo = json.load(fh)
        relidos = {p["nome"] for p in pessoas}
        mantidos = [p for p in antigo["pessoas"] if p["nome"] not in relidos]
        print("mesclando: %d relido(s) + %d preservado(s)" % (len(pessoas), len(mantidos)))
        pessoas = pessoas + mantidos

    auto, cont = detectar_ultimo_mes(pessoas)
    ultimo = ULTIMO_MES if ULTIMO_MES in MESES else (antigo or {}).get("ultimoMes") or auto
    if ultimo not in MESES:
        ultimo = auto
    meses = MESES[:MESES.index(ultimo) + 1]

    # descarta meses posteriores ao ultimo fechado
    for p in pessoas:
        for mt in p["metas"]:
            mt["meses"] = {k: v for k, v in mt["meses"].items() if k in meses}
        if p.get("total"):
            p["total"]["meses"] = {k: v for k, v in p["total"]["meses"].items() if k in meses}

    data = {"gerado": time.strftime("%d/%m/%Y %H:%M"), "meses": meses,
            "mesLabel": MES_LABEL, "ultimoMes": ultimo, "pessoas": pessoas}
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    print("\n=== RESUMO ===")
    print("apuracao por mes: %s" % cont)
    print("ultimo mes fechado: %s%s" % (ultimo, " (forcado)" if ULTIMO_MES else " (detectado)"))
    for p in pessoas:
        t = p.get("total") or {}
        c = p.get("conf") or {}
        alerta = ""
        if c.get("ok") is False:
            alerta = "<< nao fecha: soma %.3f vs Atingimento %.3f" % (c["soma"], c["acum"])
        print("%-22s %-10s metas=%2d  acum=%-6s le=%-6s %s%s"
              % (p["nome"][:22], p["grupo"], len(p["metas"]), t.get("acum"), t.get("le"),
                 "ERRO: " + p["erro"] if p.get("erro") else "", alerta))
    print("total de metas: %d" % sum(len(p["metas"]) for p in pessoas))
    ruins = [p["nome"] for p in pessoas if (p.get("conf") or {}).get("ok") is False]
    print("farois que nao reconciliam: %s" % (", ".join(ruins) or "nenhum"))
    print("gravado: %s" % outp)


if __name__ == "__main__":
    main()
