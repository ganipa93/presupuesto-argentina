#!/usr/bin/env python3
"""Arma el sitio a partir de datos/*.json y src/*.html.

Uso:  python3 scripts/build.py      (después: node scripts/prerender.mjs)
"""
import json, html, pathlib, datetime

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
    "referencias": "Población (INDEC), haber mínimo (Res. ANSES 284/2026), reparto de la recaudación (pág. 41) y supuestos de la calculadora de impuestos.",
}

def leer_datos():
    return {p.stem: json.loads(p.read_text(encoding="utf-8")) for p in sorted((RAIZ / "datos").glob("*.json"))}

def reemplazar(texto, valores):
    for k, v in valores.items():
        texto = texto.replace("{{" + k + "}}", v)
    assert "{{" not in texto, "quedó un marcador sin reemplazar"
    return texto

def main():
    datos = leer_datos()
    datos_js = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
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
    comunes = {"SITE": SITE, "REPO": REPO, "FECHA": FECHA}
    (RAIZ / "index.html").write_text(reemplazar((RAIZ / "src/plantilla.html").read_text(encoding="utf-8"), {
        **comunes, "DATA": datos_js, "SITE_JS": json.dumps(SITE),
        "JSONLD": json.dumps(jsonld, ensure_ascii=False).replace("</", "<\\/")}), encoding="utf-8")
    (RAIZ / "metodologia.html").write_text(reemplazar((RAIZ / "src/metodologia.html").read_text(encoding="utf-8"), comunes), encoding="utf-8")

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

    (RAIZ / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")
    urls = ["/", "/metodologia", "/datos/"]
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
