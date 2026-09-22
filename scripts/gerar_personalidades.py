import csv
import datetime
import io
import json
import os
import re
import unicodedata
import urllib.request

avisos = []

def slugify(text):
    text = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", text)

def lista(v):
    return [x.strip() for x in re.split(r"[,;\n]+", v or "") if x.strip()]

def sim(v):
    return (v or "").strip().lower() in ("sim", "s", "x", "true", "1")

def eh_historico(v):
    val = (v or "").strip().lower()
    return val in ("sim", "s", "x", "true", "1", "historico", "histórico", "historica", "histórica")

def extrair_ano(v):
    m = re.search(r"\b(\d{4})\b", v or "")
    return int(m.group(1)) if m else None

def ler_links(v, onde):
    out = []
    for linha in (v or "").splitlines():
        linha = linha.strip()
        if not linha:
            continue
        if "|" in linha:
            rotulo, _, url = linha.rpartition("|")
            rotulo, url = rotulo.strip(), url.strip()
        else:
            url, rotulo = linha, ""
        if not url.lower().startswith(("http://", "https://")):
            avisos.append(f"{onde}: link sem http(s) ignorado: {linha}")
            continue
        out.append({"texto": rotulo or url, "url": url})
    return out

with urllib.request.urlopen(os.environ["CSV_URL"]) as r:
    texto_csv = r.read().decode("utf-8")

pessoas = []
ids_vistos = set()
ano_atual = datetime.date.today().year

for n, linha in enumerate(csv.DictReader(io.StringIO(texto_csv)), start=2):
    l = {(k or "").strip(): (v or "").strip() for k, v in linha.items()}
    pid = l.get("id", "")
    title = l.get("title", "")
    
    # Ignora linhas em branco
    if not pid and not title:
        continue
    
    # Respeita publicação se a coluna existir
    if l.get("publicar", "").lower() in ("não", "nao", "false", "0"):
        continue

    onde = f"Linha {n} ({title or pid})"

    if not pid:
        pid = slugify(title)
        avisos.append(f"{onde}: id ausente na planilha, gerado automaticamente como '{pid}'")
    else:
        pid = slugify(pid)

    if pid in ids_vistos:
        avisos.append(f"{onde}: id duplicado '{pid}'")
    ids_vistos.add(pid)

    nasc = l.get("nascimento", "")
    falec = l.get("falecimento", "")
    ano_nasc = extrair_ano(nasc)
    ano_falec = extrair_ano(falec)

    idade = None
    if ano_nasc and ano_falec:
        if ano_falec < ano_nasc:
            avisos.append(f"{onde}: ano de falecimento ({ano_falec}) é anterior ao nascimento ({ano_nasc})")
        else:
            idade = ano_falec - ano_nasc
    elif ano_nasc and not ano_falec and not eh_historico(l.get("historico")):
        # Se for contemporâneo e ainda vivo, calcula idade atual aproximada
        idade = ano_atual - ano_nasc

    img = l.get("imagem", "")
    if img and not img.lower().startswith(("http://", "https://")):
        avisos.append(f"{onde}: imagem não começa com http(s)")

    links = ler_links(l.get("link"), onde)

    item = {
        "id": pid,
        "title": title,
        "genero": l.get("genero", ""),
        "origem": l.get("origem", ""),
        "pais": l.get("pais", ""),
        "categoria": l.get("categoria", ""),
        "historico": eh_historico(l.get("historico")),
        "destaque": sim(l.get("destaque")),
        "nascimento": nasc,
        "falecimento": falec,
        "ano_nascimento": ano_nasc,
        "ano_falecimento": ano_falec,
        "idade": idade,
        "resumo": l.get("resumo", ""),
        "descricao": l.get("descricao", ""),
        "imagem": img,
        "tags": lista(l.get("tags")),
        "fonte": l.get("fonte", ""),
        "link": links[0]["url"] if links else "",
        "links": links
    }
    pessoas.append(item)

with open("personalidades.json", "w", encoding="utf-8") as f:
    json.dump(pessoas, f, ensure_ascii=False, indent=2)

for a in avisos:
    print(f"::warning::{a}")
print(f"{len(pessoas)} personalidade(s) gravada(s) em personalidades.json")
