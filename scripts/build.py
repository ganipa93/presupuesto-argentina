#!/usr/bin/env python3
"""Arma el sitio a partir de datos/*.json y src/*.html.

Uso:  python3 scripts/build.py      (después: node scripts/prerender.mjs)
"""
import json, html, pathlib, datetime, shutil, sys, hashlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from paginas import Generador

RAIZ = pathlib.Path(__file__).resolve().parent.parent
SITE = "https://presupuesto-argentina.vercel.app"
REPO = "https://github.com/ganipa93/presupuesto-argentina"
FECHA = "10/10/2026"
FECHA_ISO = "2026-10-10"

DESCRIPCIONES = {
    "ministerios": "Gasto 2026 estimado y 2027 por jurisdicción (millones de $). Proyecto 2027, pág. 93.",
    "funciones": "Gasto por finalidad y función, 2026 estimado y 2027 (millones de $). Proyecto 2027, pág. 94.",
    "caracter_total": "Gasto 2027 por tipo de gasto (millones de $). Proyecto 2027, planilla 5, pág. 168.",
    "caracter_ministerio": "Gasto 2027 por jurisdicción y tipo de gasto (millones de $). Planilla 5, pág. 168.",
    "recursos": "Recaudación nacional 2026 y 2027 por impuesto (millones de $ y % del PBI). Págs. 40-41.",
    "gasto_tributario": "Gasto tributario 2027 (millones de $). Págs. 46-51. El IVA se calcula como 36,3% del total.",
    "cuenta_pib": "Cuenta ahorro-inversión de la Administración Nacional en % del PBI. Pág. 92.",
    "fuentes_2027": "Fuentes de financiamiento 2027 (billones de $). Pág. 90; 'Otras fuentes' es la diferencia con el total.",
    "ejecucion": "Ejecución al 31/07/2026 contra el estimado anual (millones de $). Págs. 35-38.",
    "asap": "Variación real del gasto acumulado enero-agosto 2026. Fuente: ASAP.",
    "supuestos": "Supuestos macroeconómicos de la ley 2026, el 2026 actual y el proyecto 2027, con fuentes externas (INDEC, REM, FMI).",
    "beneficiarios": "Metas físicas 2026 y 2027 y valores vigentes en agosto 2026. Págs. 10 y 96.",
    "ley_vs_proyecto": "Montos fijados en artículos de la Ley 27.798 y del proyecto 2027 (millones de $).",
    "normas": "Artículos del proyecto 2027 con efecto directo en la gente. Págs. 140-160.",
    "veredictos": "Semáforo de cumplimiento 2026 y realismo 2027. Evaluación propia, con el dato que la respalda.",
    "impacto": "Qué cambia el proyecto 2027 para cada grupo de personas. Elaboración propia.",
    "claves": "Las tres conclusiones principales. Elaboración propia.",
    "congreso": "Etapas del Presupuesto 2027 en el Congreso y cambios anunciados, con fuentes.",
    "ejecucion_ministerios": "Ejecución mensual por jurisdicción desde la API de Presupuesto Abierto (actualización automática).",
    "programas": "Cada programa con sus actividades y obras: proyecto 2027, ley, vigente y gastado 2026 por provincia, metas físicas, más universidades, entes y empresas (millones de $). Lo arma scripts/armar_programas.py.",
    "obras_provincias": "Por provincia: obras y actividades 2027 que la nombran y la inversión 2026 (bienes de uso) que el Estado ubica en ella (millones de $).",
    "comparar": "Datos del comparador: cada programa, organismo y provincia con sus montos 2026-2027 y la serie real 2020-2027 en millones de pesos de 2026.",
    "novedades": "Novedades del sitio y actualizaciones de datos (también en /novedades.xml).",
    "referencias": "Población (INDEC), haber mínimo (Res. ANSES 284/2026), reparto de la recaudación (pág. 41) y supuestos de la calculadora de impuestos.",
}

GRANDES = {"programas", "obras_provincias", "comparar"}  # se cargan aparte (fetch), no van dentro de index.html


LOGO = '<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#13294b"/><rect x="7" y="17" width="4" height="8" rx="1" fill="#9cc3ef"/><rect x="14" y="12" width="4" height="13" rx="1" fill="#9cc3ef"/><rect x="21" y="7" width="4" height="18" rx="1" fill="#f2b632"/></svg>'
MENU = [("/", "Inicio"), ("/programas", "Buscar un gasto"), ("/provincias", "Por provincia"), ("/cuadros", "Todos los cuadros"), ("/metodologia", "Metodología")]


# Secciones de la portada: cada una con su dirección, título y descripción para buscadores
SECCIONES = {
    "resumen": {"ruta": "/", "titulo": "Presupuesto 2027 explicado: qué te cambia, en qué se gasta y si se cumple",
                "h1": "Presupuesto 2027: qué te cambia, en qué se gasta y si se cumple",
                "bajada": "El proyecto que el gobierno mandó al Congreso, comparado con la ley 2026 y con lo que de verdad se gastó este año. Con los documentos oficiales, explicado en criollo.",
                "descripcion": "El Presupuesto 2027 de Argentina en lenguaje simple: qué les cambia a jubilados, familias, estudiantes y trabajadores, en qué se gasta, de dónde sale la plata y si se cumple.",
                "compartir": "El Presupuesto 2027 explicado: qué te cambia, en qué se gasta la plata y si se cumple."},
    "que-me-cambia": {"ruta": "/que-me-cambia", "titulo": "¿Qué te cambia el Presupuesto 2027? Jubilados, AUH, estudiantes y más",
                      "h1": "¿Qué te cambia el Presupuesto 2027?",
                      "bajada": "Elegí tu caso y fijate qué dice el proyecto: qué te favorece, qué te perjudica y qué conviene tener en cuenta.",
                      "descripcion": "Qué cambia el Presupuesto 2027 para jubilados, familias con AUH, estudiantes, personas con discapacidad, trabajadores, empleados públicos, provincias y usuarios de luz y gas.",
                      "compartir": "¿Qué te cambia el Presupuesto 2027? Elegí tu caso y fijate."},
    "tus-impuestos": {"ruta": "/impuestos", "titulo": "¿A dónde van tus impuestos? Calculadora del Presupuesto 2027",
                      "h1": "¿A dónde van tus impuestos?",
                      "bajada": "Poné tu sueldo y lo que gastás por mes: te mostramos cuánto pagás en impuestos nacionales y en qué se usa esa plata según el Presupuesto 2027.",
                      "descripcion": "Calculá cuánto pagás por mes en IVA, Ganancias, aportes y monotributo, y en qué se gasta esa plata según el Presupuesto 2027 de Argentina.",
                      "compartir": "¿A dónde van tus impuestos? Calculá cuánto pagás y en qué se gasta según el Presupuesto 2027."},
    "gasto": {"ruta": "/en-que-se-gasta", "titulo": "En qué se gasta el Presupuesto 2027: ministerio por ministerio",
              "h1": "¿En qué se gasta el Presupuesto 2027?",
              "bajada": "Ministerio por ministerio, por función y por tipo de gasto, comparado con 2026.",
              "descripcion": "El gasto del Presupuesto 2027 de Argentina por ministerio, por función (salud, educación, seguridad social, deuda) y por tipo de gasto, comparado con 2026.",
              "compartir": "En qué se gasta el Presupuesto 2027, ministerio por ministerio."},
    "recursos": {"ruta": "/de-donde-sale", "titulo": "De dónde sale la plata del Presupuesto 2027: impuestos, deuda y exenciones",
                 "h1": "¿De dónde sale la plata?",
                 "bajada": "Cuánto recauda cada impuesto, cómo se financia el Estado y cuánto deja de cobrar por exenciones.",
                 "descripcion": "Recaudación 2027 por impuesto (IVA, Ganancias, aportes), financiamiento con deuda y gasto tributario: de dónde sale la plata del Presupuesto 2027.",
                 "compartir": "De dónde sale la plata del Presupuesto 2027: impuestos y deuda."},
    "cumplimiento-2026": {"ruta": "/cumplimiento-2026", "titulo": "¿Se cumplió el Presupuesto 2026? La ley contra lo que pasó",
                          "h1": "¿Se está cumpliendo el Presupuesto 2026?",
                          "bajada": "Lo que decía la Ley 27.798 contra lo que pasó: inflación, dólar, gasto ejecutado por ministerio y semáforo de cumplimiento.",
                          "descripcion": "Presupuesto 2026 de Argentina: lo que preveía la Ley 27.798 contra lo que pasó. Inflación, dólar, crecimiento y gasto ejecutado por ministerio, actualizado cada mes.",
                          "compartir": "¿Se cumplió el Presupuesto 2026? Lo que decía la ley contra lo que pasó."},
    "realismo-2027": {"ruta": "/realismo-2027", "titulo": "¿Es realista el Presupuesto 2027? Semáforo y simulador",
                      "h1": "¿Es realista el Presupuesto 2027?",
                      "bajada": "Qué supuestos son probables y cuáles no, y qué pasa con las cuentas si la inflación o el dólar se desvían.",
                      "descripcion": "Semáforo de los supuestos del Presupuesto 2027 (inflación, dólar, crecimiento, superávit) comparados con el REM y el FMI, y un simulador de desvíos.",
                      "compartir": "¿Es realista el Presupuesto 2027? Semáforo y simulador de inflación y dólar."},
    "congreso": {"ruta": "/congreso", "titulo": "Presupuesto 2027 en el Congreso: fechas, etapas y cambios",
                 "h1": "El Presupuesto 2027 en el Congreso",
                 "bajada": "Etapas del debate, próximas fechas y los cambios que se anunciaron al proyecto.",
                 "descripcion": "Seguimiento del Presupuesto 2027 en el Congreso: comisión de Presupuesto, dictamen, sesiones en Diputados y Senado, y cambios al proyecto.",
                 "compartir": "El Presupuesto 2027 en el Congreso: fechas, etapas y cambios."},
    "ley-vs-proyecto": {"ruta": "/ley-2026-vs-proyecto-2027", "titulo": "Presupuesto 2026 vs. 2027: los montos de la ley, partida por partida",
                        "h1": "Ley 2026 contra proyecto 2027",
                        "bajada": "Cuánto cambian de un año al otro los montos que fijan los artículos de la ley.",
                        "descripcion": "Comparación de los montos fijados en los artículos de la Ley 27.798 de Presupuesto 2026 y del proyecto 2027: fondos, cupos, deuda y transferencias.",
                        "compartir": "Presupuesto 2026 contra 2027, partida por partida."},
    "articulos": {"ruta": "/articulos", "titulo": "Presupuesto 2027: los artículos que más afectan a la gente",
                  "h1": "Los artículos que más te afectan",
                  "bajada": "Lo que dice el proyecto de ley, artículo por artículo, en lenguaje simple.",
                  "descripcion": "Los artículos del Proyecto de Presupuesto 2027 con efecto directo en la gente, explicados en lenguaje simple.",
                  "compartir": "Los artículos del Presupuesto 2027 que más afectan a la gente."},
}
QUIEN = {"jubilados": "los jubilados y pensionados", "familias": "las familias con hijos y la AUH", "estudiantes": "los estudiantes y las universidades",
         "discapacidad": "las personas con discapacidad", "trabajadores": "los trabajadores en relación de dependencia", "estatales": "los empleados públicos nacionales",
         "provincias": "las provincias", "servicios": "las tarifas de luz, gas y transporte", "contribuyentes": "los contribuyentes, las pymes y los productores"}
GRUPOS = [("Para vos", [("resumen", "Resumen"), ("que-me-cambia", "¿Qué me cambia?"), ("tus-impuestos", "Tus impuestos"), ("/programas", "Buscar un gasto")]),
          ("Los números", [("gasto", "En qué se gasta"), ("/comparar", "Comparar"), ("/evolucion", "Qué creció y qué cayó"), ("recursos", "De dónde sale la plata"), ("/provincias", "Por provincia")]),
          ("¿Se cumple?", [("cumplimiento-2026", "2026: ¿se cumplió?"), ("/ejecucion-2026", "Lo que no se está gastando"), ("realismo-2027", "2027: ¿es realista?"), ("congreso", "En el Congreso")]),
          ("La ley", [("ley-vs-proyecto", "2026 vs. 2027"), ("articulos", "Artículos clave"), ("/cuadros", "Todos los cuadros"), ("/glosario", "Glosario")])]


def perfiles_seo(impacto):
    out = {}
    for p in impacto:
        q = QUIEN.get(p["id"], p["perfil"].lower())
        out[p["id"]] = {"titulo": f"Presupuesto 2027 para {q}: qué cambia", "h1": f"¿Qué cambia el Presupuesto 2027 para {q}?",
                        "bajada": "Lo que te favorece, lo que te perjudica y lo que conviene tener en cuenta, según el proyecto y lo que pasó en 2026.",
                        "descripcion": f"Qué dice el Proyecto de Presupuesto 2027 para {q}: montos, cambios y lo que hay que tener en cuenta, explicado en lenguaje simple.",
                        "compartir": f"¿Qué cambia el Presupuesto 2027 para {q}? Fijate acá:"}
    return out


def secnav(actual="resumen"):
    partes = []
    for g, items in GRUPOS:
        partes.append(f'<li class="grupo" aria-hidden="true">{g}</li>')
        for k, t in items:
            if k.startswith("/"):
                partes.append(f'<li><a href="{k}">{t}</a></li>')
            else:
                partes.append(f'<li><a href="{SECCIONES[k]["ruta"]}" data-tab="{k}"' + (' aria-current="page"' if k == actual else "") + f">{t}</a></li>")
    return "<ol>" + "".join(partes) + "</ol>"


def cabecera(actual=""):
    """Cabecera común a todas las páginas."""
    links = "".join(f'<a href="{u}"' + (' aria-current="page"' if u == actual else "") + f">{t}</a>" for u, t in MENU)
    return f'<header class="top"><a class="brand" href="/">{LOGO}<span>Presupuesto Argentina</span></a><nav aria-label="Principal">{links}</nav></header>'


def copiar_js():
    """Copia src/js/*.js a js/ y devuelve su versión (hash) para que el navegador no use una copia vieja."""
    (RAIZ / "js").mkdir(exist_ok=True)
    versiones = {}
    for f in sorted((RAIZ / "src" / "js").glob("*.js")):
        datos = f.read_bytes()
        (RAIZ / "js" / f.name).write_bytes(datos)
        versiones["V_" + f.stem.upper()] = hashlib.sha1(datos).hexdigest()[:10]
    return versiones


def leer_datos():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((RAIZ / "datos").glob("*.json"))}

def reemplazar(texto, valores):
    for k, v in valores.items():
        texto = texto.replace("{{" + k + "}}", v)
    assert "{{" not in texto, "quedó un marcador sin reemplazar"
    return texto

def main():
    datos = leer_datos()
    datos_js = json.dumps({k: v for k, v in datos.items() if k not in GRANDES}, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    jsonld = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "name": "Presupuesto Argentina", "url": SITE + "/", "inLanguage": "es-AR"},
            {"@type": "Dataset", "name": "Presupuesto nacional de Argentina 2026 y proyecto 2027",
             "description": "Gasto por jurisdicción y función, recursos, financiamiento, ejecución 2026 y artículos clave del Proyecto de Ley de Presupuesto 2027, comparados con la Ley 27.798.",
             "url": SITE + "/", "dateModified": FECHA_ISO, "inLanguage": "es-AR", "isAccessibleForFree": True,
             "license": "https://creativecommons.org/licenses/by/4.0/",
             "spatialCoverage": "Argentina", "temporalCoverage": "2026/2027",
             "creator": {"@type": "Organization", "name": "Presupuesto Argentina", "url": SITE + "/"},
             "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": f"{SITE}/datos/{k}.json"} for k in datos]}]}
    comunes = {"SITE": SITE, "REPO": REPO, "FECHA": FECHA, **copiar_js()}
    cab = lambda u: {"CABECERA": cabecera(u)}
    (RAIZ / "index.html").write_text(reemplazar((RAIZ / "src/plantilla.html").read_text(encoding="utf-8"), {
        **comunes, **cab("/"), "SECNAV": secnav(), "SECCIONES_JS": json.dumps(SECCIONES, ensure_ascii=False),
        "PERFILES_JS": json.dumps(perfiles_seo(datos["impacto"]), ensure_ascii=False), "DATA": datos_js, "SITE_JS": json.dumps(SITE),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")}), encoding="utf-8")
    (RAIZ / "metodologia.html").write_text(reemplazar((RAIZ / "src/metodologia.html").read_text(encoding="utf-8"), {**comunes, **cab("/metodologia"), "INFLP": f'{next(r for r in datos["supuestos"] if r["clave"] == "infl_prom")["proyecto2027"]:g}'.replace(".", ",")}), encoding="utf-8")

    # Página índice de datos abiertos
    filas = "\n".join(f'<li><a href="/datos/{k}.json">{k}.json</a> · {html.escape(DESCRIPCIONES.get(k, ""))}</li>' for k in datos)
    (RAIZ / "datos/index.html").write_text(f"""<!doctype html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Datos abiertos · Presupuesto Argentina</title><meta name="description" content="Los datos del sitio Presupuesto Argentina en formato JSON, para descargar y reutilizar.">
<link rel="canonical" href="{SITE}/datos/"><link rel="icon" href="/favicon.svg" type="image/svg+xml"><link rel="stylesheet" href="/estilos.css"></head>
<body><div class="wrap"><div class="top"><a class="brand" href="/">Presupuesto Argentina</a><nav><a href="/">Volver al sitio</a><a href="/metodologia">Metodología y fuentes</a></nav></div>
<main class="prose"><h1>Datos abiertos</h1><p class="sub">Todos los datos del sitio en JSON, uno por tabla. Podés usarlos citando la fuente (licencia CC BY 4.0). Actualizados al {FECHA}. Las páginas citadas son las del PDF del proyecto.</p>
<ul>
{filas}
</ul></main></div></body></html>
""", encoding="utf-8")

    # Explorador de todos los cuadros del PDF (los genera scripts/extraer_cuadros.py)
    ind_path = RAIZ / "cuadros/indice.json"
    if ind_path.exists():
        indice = json.loads(ind_path.read_text(encoding="utf-8"))
        def lista_de(indice, d):
            secciones = {}
            for x in indice:
                secciones.setdefault(x["s"], []).append(x)
            return "\n".join(
                "<details" + (" open" if i == 0 else "") + "><summary>" + html.escape(sec) + f" ({sum(1 for x in xs if x['c'])})</summary><ol>" +
                "".join(f'<li><a href="#{"ley2026-" if d == "2026" else ""}p{x["p"]}" data-doc="{d}" data-p="{x["p"]}"' + ("" if x["c"] else ' class="txt"') +
                        f'><span class="n">p. {x["p"]}</span><span>{html.escape(x["t"])}</span></a></li>' for x in xs) +
                "</ol></details>" for i, (sec, xs) in enumerate(secciones.items()))
        ind26_path = RAIZ / "cuadros/2026/indice.json"
        indice26 = json.loads(ind26_path.read_text(encoding="utf-8")) if ind26_path.exists() else []
        js = lambda v: json.dumps(v, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        (RAIZ / "cuadros.html").write_text(reemplazar((RAIZ / "src/cuadros.html").read_text(encoding="utf-8"), {
            **comunes, **cab("/cuadros"), "SITE_JS": json.dumps(SITE), "N": str(len(indice)), "N26": str(len(indice26)),
            "LISTA": lista_de(indice, "2027"), "LISTA26": lista_de(indice26, "2026"),
            "INDICE": js(indice), "INDICE26": js(indice26)}), encoding="utf-8")

    # Buscador por programa (datos/programas.json, lo arma scripts/armar_programas.py)
    sup = {r["clave"]: r for r in datos["supuestos"]}
    if "programas" in datos:
        (RAIZ / "programas.html").write_text(reemplazar((RAIZ / "src/programas.html").read_text(encoding="utf-8"), {
            **comunes, **cab("/programas"), "SITE_JS": json.dumps(SITE), "NPROG": str(len(datos["programas"]["programas"])),
            "INFL": f'{sup["inflacion"]["proyecto2027"]:g}'.replace(".", ","),
            "INFLP": f'{sup["infl_prom"]["proyecto2027"]:g}'.replace(".", ","),
            "INFLP_JS": f'{sup["infl_prom"]["proyecto2027"]:g}',
            "INFL26": f'{sup["inflacion"]["estimado2026"]:g}'.replace(".", ",")}), encoding="utf-8")

    # Páginas fijas por programa, organismo y provincia
    paginas = []
    if "programas" in datos:
        for d in ("gasto", "provincias"):
            shutil.rmtree(RAIZ / d, ignore_errors=True)
        for f in ("gasto.html", "provincias.html"):
            (RAIZ / f).unlink(missing_ok=True)
        paginas = Generador(RAIZ, SITE, REPO, FECHA, cabecera, datos, sup["infl_prom"]["proyecto2027"], sup["inflacion"]["estimado2026"]).todo()

    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    urls = [v["ruta"] for v in SECCIONES.values()] + [f'/que-me-cambia/{p["id"]}' for p in datos["impacto"]] + ["/programas", "/cuadros", "/metodologia", "/datos/"] + paginas
    (RAIZ / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
        "".join(f"  <url><loc>{SITE}{u}</loc><lastmod>{FECHA_ISO}</lastmod></url>\n" for u in urls) + "</urlset>\n", encoding="utf-8")

    # Imagen para redes: se completa con datos y la renderiza prerender.mjs
    m = datos["ministerios"]
    gasto = sum(r["y2027"] for r in m) / 1e6
    infl = next(r for r in datos["supuestos"] if r["clave"] == "inflacion")["proyecto2027"]
    og = reemplazar((RAIZ / "src/og.html").read_text(encoding="utf-8"), {
        "GASTO": f"${gasto:,.1f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "INFL": f"{infl:g}", "OBRAS": "1.683", "HOST": SITE.replace("https://", "")})
    (RAIZ / "scripts/.og-render.html").write_text(og, encoding="utf-8")
    print("Listo: index.html, metodologia.html, datos/index.html, robots.txt, sitemap.xml")

if __name__ == "__main__":
    main()
