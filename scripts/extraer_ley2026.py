#!/usr/bin/env python3
"""Convierte el texto sancionado de la Ley 27.798 (Presupuesto 2026) en páginas navegables para /cuadros.

El PDF es un escaneo firmado (sin texto) y muchas planillas están giradas. Para cada página:
  - detecta la orientación (tesseract OSD) y la endereza,
  - guarda la imagen en cuadros/2026/img/pNNN.webp,
  - reconoce el texto (OCR en castellano) para el buscador: cuadros/2026/paginas/pNNN.json,
y al final escribe cuadros/2026/indice.json y cuadros/2026/texto.json.

El texto del OCR solo sirve para buscar: los números valen en la imagen.
Necesita pdftoppm, tesseract con el idioma "spa" y Pillow.
    python3 scripts/extraer_ley2026.py fuentes/ley-27798-presupuesto-2026.pdf
"""
import json, multiprocessing, pathlib, re, subprocess, sys, tempfile
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
RAIZ = pathlib.Path(__file__).resolve().parent.parent
BASE = RAIZ / "cuadros" / "2026"
ANCHO = 1300  # ancho de la imagen publicada, en píxeles

# (desde, hasta, sección, título) armado mirando el documento
FORZAR = {42: 90}  # páginas donde la detección automática de orientación se equivoca
TITULOS = json.loads((RAIZ / "scripts" / "titulos_ley2026.json").read_text(encoding="utf-8"))


def osd(png):
    r = subprocess.run(["tesseract", png, "-", "--psm", "0"], capture_output=True, text=True)
    rot = re.search(r"Rotate: (\d+)", r.stdout)
    conf = re.search(r"Orientation confidence: ([\d.]+)", r.stdout)
    return (int(rot.group(1)) if rot else 0), (float(conf.group(1)) if conf else 0.0)


def ocr(im, tmp, psm="3"):
    f = f"{tmp}/o.png"
    im.save(f)
    r = subprocess.run(["tesseract", f, "-", "-l", "spa", "--psm", psm], capture_output=True, text=True)
    return r.stdout


def palabras(t):
    return len(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúÑñ]{4,}", t))


def pagina(args):
    pdf, n = args
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-f", str(n), "-l", str(n), "-r", "300", "-gray", "-png", pdf, f"{tmp}/p"], check=True)
        png = str(next(pathlib.Path(tmp).glob("p*.png")))
        rot, conf = osd(png)
        im = Image.open(png).convert("L")
        if n in FORZAR:
            rot = FORZAR[n]
        elif conf < 2:  # orientación dudosa: se queda con la que da más palabras
            opciones = {g: im.rotate(-g, expand=True) for g in (0, 90, 270)}
            textos = {g: ocr(v, tmp, "6") for g, v in opciones.items()}
            rot = max(textos, key=lambda g: palabras(textos[g]))
        im = im.rotate(-rot, expand=True) if rot else im
        texto = ocr(im, tmp)
        chica = im.resize((ANCHO, round(im.height * ANCHO / im.width)), Image.LANCZOS)
        chica.save(BASE / "img" / f"p{n:03d}.webp", "WEBP", quality=72, method=6)
    limpio = re.sub(r"\n{3,}", "\n\n", "\n".join(l.rstrip() for l in texto.split("\n"))).strip()
    (BASE / "paginas" / f"p{n:03d}.json").write_text(json.dumps({"pagina": n, "texto": limpio, "giro": rot}, ensure_ascii=False), encoding="utf-8")
    print(n, "giro", rot, "conf", conf, palabras(limpio), "palabras", flush=True)
    return n, chica.width, chica.height, re.sub(r"\s+", " ", limpio)


def main():
    pdf = sys.argv[1]
    (BASE / "img").mkdir(parents=True, exist_ok=True)
    (BASE / "paginas").mkdir(parents=True, exist_ok=True)
    total = int(re.search(r"Pages:\s+(\d+)", subprocess.run(["pdfinfo", pdf], capture_output=True, text=True).stdout).group(1))
    hechas = {int(p.stem[1:]) for p in (BASE / "paginas").glob("p*.json")} if "--seguir" in sys.argv else set()
    with multiprocessing.Pool(2) as pool:
        for _ in pool.imap_unordered(pagina, [(pdf, n) for n in range(1, total + 1) if n not in hechas]):
            pass
    indice, textos, ultimo_art = [], {}, 1
    for n in range(1, total + 1):
        d = json.loads((BASE / "paginas" / f"p{n:03d}.json").read_text(encoding="utf-8"))
        w, h = Image.open(BASE / "img" / f"p{n:03d}.webp").size
        sec, tit, cuadro = next(((s, t, c) for a, b, s, t, c in TITULOS if a <= n <= b), ("Otros", "", False))
        if not tit:  # páginas del articulado: los artículos que empiezan en la página
            arts = sorted({int(x) for x in re.findall(r"Art[íi1l]culo (\d{1,2})\D{0,4}[.\-–]", d["texto"])})
            if arts:
                tit = f"Artículos {arts[0]} a {arts[-1]}" if len(arts) > 1 else f"Artículo {arts[0]}"
                ultimo_art = arts[-1]
            else:
                tit = f"Artículo {ultimo_art} (continuación)"
        indice.append({"p": n, "s": sec, "t": tit, "c": cuadro, "w": w, "h": h})
        textos[n] = re.sub(r"\s+", " ", d["texto"])
    (BASE / "indice.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    (BASE / "texto.json").write_text(json.dumps(textos, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
