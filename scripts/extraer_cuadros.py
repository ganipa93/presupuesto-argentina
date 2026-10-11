#!/usr/bin/env python3
"""Convierte el PDF del proyecto en un documento navegable para /cuadros.

Para cada página genera:
  - cuadros/img/pNNN.webp   imagen fiel de la página (lo que vale es esto)
  - cuadros/paginas/pNNN.json  texto de la página y, si es un cuadro, la tabla
                               extraída automáticamente (para descargar en CSV)
  - cuadros/indice.json     sección, título y si tiene cuadro, de cada página
  - cuadros/texto.json      texto de todas las páginas, para el buscador

Necesita pdftoppm (poppler), pdfplumber y Pillow. Solo hace falta correrlo
cuando cambia el PDF:
    python3 scripts/extraer_cuadros.py fuentes/proyecto-presupuesto-2027.pdf
"""
import json, pathlib, re, subprocess, sys, tempfile
import pdfplumber
from PIL import Image

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DPI = 130

SECCIONES = [
    (1, 5, 'Portada y nota de elevación'),
    (6, 21, '1. Prioridades de la política presupuestaria'),
    (22, 34, '2. Contexto macroeconómico y supuestos'),
    (35, 39, '3. Ejecución 2026 al mes de julio'),
    (40, 51, '4.1 y 4.2 Recursos tributarios y gastos tributarios'),
    (52, 57, '4.3 Financiamiento y deuda'),
    (58, 62, '4.4 Inversión pública'),
    (63, 73, '4.5 Relación con las provincias'),
    (74, 83, '4.6 Marco fiscal de mediano plazo'),
    (84, 102, '5. Presupuesto de la Administración Nacional 2027'),
    (103, 130, '6. Fondos fiduciarios, otros entes y empresas públicas'),
    (131, 137, '7. Sector Público Nacional consolidado'),
    (138, 162, 'Proyecto de ley (articulado)'),
    (163, 207, 'Planillas anexas al articulado'),
    (208, 221, 'Título II: Administración central'),
    (222, 240, 'Título III: Organismos descentralizados'),
    (241, 249, 'Título III: Instituciones de la seguridad social'),
]

RUIDO = re.compile(r'^(IF-\d{4}|INLEG-|Página \d+ de \d+|República Argentina - Poder|Año de la|Hoja adicional)', re.I)
GENERICOS = {'PRESUPUESTO 2027', 'CAPÍTULO I', 'CAPITULO I', 'TÍTULO II', 'TÍTULO III', 'EN MILLONES DE PESOS', '(EN MILLONES DE PESOS)'}
NUM = re.compile(r'^\(?-?\$?\d{1,3}(?:\.\d{3})*(?:,\d+)?%?\)?$|^\(?-?\d+(?:,\d+)?%?\)?$')


def seccion(n):
    return next((s for a, b, s in SECCIONES if a <= n <= b), 'Otros')


def es_num(t):
    return bool(NUM.match(t)) or t in ('-', '--', '---')


def oracion(t):
    t = t.lower()
    m = re.search(r'[a-záéíóúñ]', t)
    return t[:m.start()] + t[m.start()].upper() + t[m.start() + 1:] if m else t


def titulo_de(texto, previo):
    lineas = [re.sub(r'\s{2,}', ' ', l.strip()) for l in texto.split('\n') if l.strip()]
    lineas = [l for l in lineas if not RUIDO.match(l)]
    cand = []
    for l in lineas[:14]:
        lim = re.sub(r'(Planilla N?º?\s*\d*|Anexa al Art(ículo)?\.? ?\d+º?(\s*\(Cont\.\))?|CAP[IÍ]TULO [IVX]+)', '', l, flags=re.I).strip()
        if not lim or lim.upper() in GENERICOS:
            continue
        if re.match(r'^\d+(\.\d+)*\.?\s+\S', lim) and not re.search(r'\d{1,3}(\.\d{3})+', lim):
            cand.append(lim); break
        if lim.isupper() and 8 <= len(lim) <= 120 and not re.search(r'\d{1,3}(\.\d{3})+,', lim):
            cand.append(lim)
            if len(cand) == 2:
                break
    if cand:
        return ' · '.join(dict.fromkeys(oracion(c) if c.isupper() else c for c in cand))
    return previo


def tabla(page):
    """Tabla aproximada: concepto + columnas numéricas alineadas a la derecha."""
    words = [w for w in page.extract_words() if not RUIDO.match(w['text'])]
    filas = []
    for w in sorted(words, key=lambda w: (round(w['top']), w['x0'])):
        if filas and abs(filas[-1][0] - w['top']) <= 3:
            filas[-1][1].append(w)
        else:
            filas.append([w['top'], [w]])
    con_num = [f for f in filas if sum(es_num(w['text']) for w in f[1]) >= 2]
    if len(con_num) < 4:
        return None
    xs = sorted(w['x1'] for f in con_num for w in f[1] if es_num(w['text']))
    cols = []
    for x in xs:
        if cols and x - cols[-1][-1] <= 10:
            cols[-1].append(x)
        else:
            cols.append([x])
    cols = [sum(c) / len(c) for c in cols if len(c) >= max(3, len(con_num) * 0.25)]
    if len(cols) < 2:
        return None
    izq = min(w['x0'] for f in con_num for w in f[1] if es_num(w['text']))
    primer = con_num[0][0]
    out = []
    for top, ws in filas:
        if top < primer - 1:
            continue
        ws.sort(key=lambda w: w['x0'])
        concepto = ' '.join(w['text'] for w in ws if w['x1'] < izq - 3 or not es_num(w['text']))
        vals = [''] * len(cols)
        for w in ws:
            if es_num(w['text']) and w['x1'] >= izq - 3:
                i = min(range(len(cols)), key=lambda k: abs(cols[k] - w['x1']))
                if abs(cols[i] - w['x1']) > 14:
                    return None  # número que no cae en ninguna columna: tabla poco confiable
                vals[i] = (vals[i] + ' ' + w['text']).strip()
        if concepto or any(vals):
            out.append([concepto] + vals)
    datos = [r for r in out if any(r[1:])]
    llenas = sum(1 for r in datos if r[0] and sum(1 for v in r[1:] if v) >= len(cols) * 0.5)
    if not datos or llenas / len(datos) < 0.7 or any(' ' in v for r in datos for v in r[1:]):
        return None
    return out


def corregir(indice, textos):
    """Títulos que en realidad son encabezados de columnas heredan el de la página anterior,
    y toda página con muchas cifras o de las planillas cuenta como cuadro."""
    malo = re.compile(r'^(concepto|\d{4}\b|v ?a ?riaci|transporte|belgrano|militares|argentinas)', re.I)
    previo = ''
    for x in indice:
        if malo.match(x['t']) or len(re.sub(r'[^A-Za-zÁÉÍÓÚáéíóúñÑ]', '', x['t'])) < 6:
            x['t'] = (previo + ' (continuación)') if previo and not previo.endswith('(continuación)') else previo
        previo = x['t']
        nums = len(re.findall(r'\d{1,3}(?:\.\d{3})+', textos[x['p']]))
        if x['p'] >= 163 or nums >= 12:
            x['c'] = True


def main():
    pdf = pathlib.Path(sys.argv[1])
    base = RAIZ / 'cuadros'
    (base / 'img').mkdir(parents=True, exist_ok=True)
    (base / 'paginas').mkdir(parents=True, exist_ok=True)
    indice, textos, previo = [], {}, ''
    with pdfplumber.open(pdf) as doc, tempfile.TemporaryDirectory() as tmp:
        total = len(doc.pages)
        for n, page in enumerate(doc.pages, 1):
            texto = page.extract_text(layout=True) or ''
            limpio = '\n'.join(l.rstrip() for l in texto.split('\n') if not RUIDO.match(l.strip()))
            limpio = re.sub(r'\n{3,}', '\n\n', limpio).strip('\n')
            if not limpio.strip():
                continue
            titulo = titulo_de(limpio, previo) or seccion(n)
            previo = titulo
            t = tabla(page)
            nums = len(re.findall(r'\d{1,3}(?:\.\d{3})+(?:,\d+)?', limpio))
            es_cuadro = t is not None or nums >= 25
            subprocess.run(['pdftoppm', '-f', str(n), '-l', str(n), '-r', str(DPI), '-gray', '-png', str(pdf), f'{tmp}/p'], check=True)
            png = next(pathlib.Path(tmp).glob('p*.png'))
            im = Image.open(png)
            im.save(base / 'img' / f'p{n:03d}.webp', 'WEBP', quality=70, method=6)
            png.unlink()
            (base / 'paginas' / f'p{n:03d}.json').write_text(json.dumps({'pagina': n, 'titulo': titulo, 'texto': limpio, 'tabla': t}, ensure_ascii=False), encoding='utf-8')
            indice.append({'p': n, 's': seccion(n), 't': titulo, 'c': es_cuadro, 'w': im.width, 'h': im.height})
            textos[n] = re.sub(r'\s+', ' ', limpio)
            print(f'{n}/{total}', 'cuadro' if es_cuadro else 'texto', 'tabla' if t else '', titulo[:70])
    corregir(indice, textos)
    manuales = json.loads((RAIZ / 'scripts' / 'titulos_cuadros.json').read_text(encoding='utf-8'))
    for x in indice:
        x['t'] = manuales.get(str(x['p']), x['t'])
    (base / 'indice.json').write_text(json.dumps(indice, ensure_ascii=False), encoding='utf-8')
    (base / 'texto.json').write_text(json.dumps(textos, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main()
