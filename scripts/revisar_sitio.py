#!/usr/bin/env python3
"""Revisa el sitio armado: links internos rotos, datos estructurados (JSON-LD) inválidos,
títulos y descripciones vacíos. Sale con código 1 si encuentra algún problema."""
import html, json, pathlib, re, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def existe(u):
    u = html.unescape(u).split("#")[0].split("?")[0]
    if u in ("", "/"):
        return True
    p = u.strip("/")
    return (RAIZ / (p + ".html")).exists() or (RAIZ / p / "index.html").exists() or (RAIZ / p).is_file()


def main():
    paginas = [p for p in RAIZ.rglob("*.html") if not any(x in p.parts for x in ("src", "scripts", "node_modules", "fuentes", "embed"))]
    problemas = []
    for f in paginas:
        s = f.read_text(encoding="utf-8")
        nombre = f.relative_to(RAIZ)
        if not re.search(r"<title>[^<]{5,}</title>", s):
            problemas.append(f"{nombre}: sin título")
        if 'name="description"' not in s and nombre.parts[0] not in ("cuadros",):
            problemas.append(f"{nombre}: sin descripción")
        for u in set(re.findall(r'(?:href|src)="(/[^"]*)"', s)):
            if u.startswith("/_vercel/"):
                continue
            if not existe(u):
                problemas.append(f"{nombre}: link roto {u}")
        for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', s, re.S):
            try:
                json.loads(m)
            except ValueError as e:
                problemas.append(f"{nombre}: JSON-LD inválido ({e})")
    print(f"{len(paginas)} páginas revisadas, {len(problemas)} problemas")
    for p in problemas[:50]:
        print(" -", p)
    sys.exit(1 if problemas else 0)


if __name__ == "__main__":
    main()
