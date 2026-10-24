"""Páginas fijas, una por programa, organismo y provincia (/gasto/<slug>, /provincias/<slug>),
más sus índices. Las llama build.py. Montos de entrada en millones de pesos."""
import html, json, re, unicodedata
from collections import defaultdict

MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
ESPECIALES = {"Nacional", "Interprovincial", "No Clasificado", "Binacional", "Exterior"}
e = html.escape


def miles(v, dec=0):
    s = f"{v:,.{dec}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def plata(m):
    """Millones de pesos → texto corto en castellano."""
    if m is None:
        return "—"
    a = abs(m)
    if a >= 1e6:
        return f"${miles(m / 1e6, 2)} billones"
    if a >= 1000:
        return f"${miles(m)} millones"
    if a >= 1:
        return f"${miles(m, 1)} millones"
    if a > 0:
        return f"${miles(m * 1e6)}"
    return "$0"


def plata_og(m):
    if m is None:
        return ("—", "")
    if abs(m) >= 1e6:
        return (f"${miles(m / 1e6, 2)}", "billones")
    if abs(m) >= 1:
        return (f"${miles(m)}", "millones")
    return (f"${miles(m * 1e6)}", "pesos")


def dolares(u):
    """Millones de dólares → texto corto («US$ 1.234 millones»)."""
    if u is None:
        return "—"
    a = abs(u)
    if a >= 100:
        return f"US$ {miles(u)} millones"
    if a >= 1:
        return f"US$ {miles(u, 1)} millones"
    return f"US$ {miles(u * 1e6)}"


def dn(m):
    """Monto para una celda de tabla: el texto corto y el valor exacto (millones) para descargar."""
    return plata(m) if m is None else f'<span data-n="{round(m, 1)}">{plata(m)}</span>'


def pct(a, b):
    return f"{miles(a / b * 100)}%" if b else "—"


def fecha(iso):
    a, m, d = (int(x) for x in iso.split("-"))
    return f"{d} de {MESES[m - 1]} de {a}"


def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def tabla(cab, filas, clase=""):
    th = "".join(f'<th scope="col"{" class=\"t\"" if i == 0 else ""}>{e(c)}</th>' for i, c in enumerate(cab))
    cuerpo = "".join("<tr>" + "".join((f'<th scope="row">{c}</th>' if i == 0 else f"<td>{c}</td>") for i, c in enumerate(f)) + "</tr>" for f in filas)
    return f'<div class="tw{(" " + clase) if clase else ""}"><table><thead><tr>{th}</tr></thead><tbody>{cuerpo}</tbody></table></div>'


def stat(k, n, s="", ink=False, barra=None, u=None):
    b = f'<div class="ejbar"><span style="width:{max(0, min(100, barra)):.1f}%"></span></div>' if barra is not None else ""
    us = f'<span class="u">≈ {e(u)}</span>' if u else ""
    return f'<div class="stat{" ink" if ink else ""}"><span class="k">{e(k)}</span><span class="n">{e(n)}</span>{us}{f"<span class=s>{e(s)}</span>" if s else ""}{b}</div>'


class Generador:
    def __init__(self, raiz, site, repo, fecha_sitio, cabecera, datos, infl_prom27, infl26):
        self.raiz, self.site, self.repo, self.fecha_sitio, self.cabecera = raiz, site, repo, fecha_sitio, cabecera
        self.P = datos["programas"]["programas"]
        self.E = datos["programas"]["entes"]
        self.corte = datos["programas"]["corte26"]
        self.infl27, self.infl26 = infl_prom27, infl26
        self.urls, self.og = [], []
        self.v_desc = __import__("hashlib").sha1((raiz / "src" / "js" / "descargas.js").read_bytes()).hexdigest()[:10]
        self.datos = datos
        self.ipc = self.indices_ipc()
        self.HO = datos["programas"].get("historia_org", {})
        self.OB = datos.get("obras_provincias", {})
        self.HT = datos["programas"].get("historia_total", [])
        self.TC = {int(a): v for a, v in datos.get("dolar", {}).get("promedio", {}).items()}

    def usd(self, m, anio):
        """Millones de pesos de un año → texto en dólares al promedio oficial de ese año (o None)."""
        if m is None or anio not in self.TC:
            return None
        return dolares(m / self.TC[anio])

    def usd_hab(self, pesos, anio):
        return f"US$ {miles(pesos / self.TC[anio])}" if anio in self.TC else None

    def nota_usd(self):
        if not self.TC:
            return ""
        return (f'<p class="note">En dólares, al dólar oficial promedio de cada año (BCRA): ${miles(self.TC[2026])} en 2026, con los meses publicados, '
                f'y ${miles(self.TC[2027])} en 2027, según el dólar que proyecta el Ministerio de Economía. <a href="/metodologia#dolares">Cómo se calcula</a>.</p>')

    def indices_ipc(self):
        """IPC promedio de cada año. 2026: meses publicados + el resto interpolado hasta la inflación anual estimada;
        2027: inflación promedio que supone el proyecto."""
        f = json.loads((self.raiz / "fuentes" / "ipc_indec.json").read_text(encoding="utf-8"))
        ipc = {int(k): v for k, v in f["promedio_anual"].items()}
        m26 = [v for k, v in sorted(f["mensual_2025_2026"].items()) if k.startswith("2026")]
        dic25 = f["mensual_2025_2026"]["2025-12"]
        dic26 = dic25 * (1 + self.infl26 / 100)
        faltan = 12 - len(m26)
        if faltan:
            paso = (dic26 / m26[-1]) ** (1 / faltan)
            m26 += [m26[-1] * paso ** (i + 1) for i in range(faltan)]
        ipc[2026] = sum(m26) / 12
        ipc[2027] = ipc[2026] * (1 + self.infl27 / 100)
        self.ipc_meses = len([k for k in f["mensual_2025_2026"] if k.startswith("2026")])
        return ipc

    def real(self, v, anio):
        """Pesos corrientes de un año → pesos de 2026."""
        return v * self.ipc[2026] / self.ipc[anio]

    def serie(self, x):
        """[(año, nominal, tipo)] con lo gastado 2020-2025, lo autorizado 2026 y lo pedido 2027."""
        out = [(a, v, "gastado") for a, v in x.get("h", [])]
        if x.get("v26"):
            out.append((2026, x["v26"], "autorizado"))
        if x.get("a27") is not None:
            out.append((2027, x["a27"], "proyecto"))
        return out

    def grafico(self, serie, titulo):
        """Barras en pesos de 2026, en SVG (sin JavaScript)."""
        if len(serie) < 3:
            return ""
        vals = [(a, self.real(v, a), t) for a, v, t in serie]
        mx = max(v for _, v, _ in vals) or 1
        W, H, pad, base = 560, 230, 6, 192
        bw = (W - pad * 2) / len(vals)
        barras = []
        for i, (a, v, t) in enumerate(vals):
            h = max(1.5, v / mx * 150)
            xx = pad + i * bw + bw * 0.14
            ww = bw * 0.72
            color = {"gastado": "var(--c1)", "autorizado": "var(--mutedbar)", "proyecto": "var(--acc)"}[t]
            corto = plata(v).replace(" millones", " M").replace(" billones", " bn")
            barras.append(f'<rect x="{xx:.1f}" y="{base - h:.1f}" width="{ww:.1f}" height="{h:.1f}" rx="3" fill="{color}"><title>{a}: {plata(v)} en pesos de 2026 ({t})</title></rect>'
                          f'<text x="{xx + ww / 2:.1f}" y="{base - h - 6:.1f}" text-anchor="middle" font-size="12" fill="currentColor">{e(corto)}</text>'
                          f'<text x="{xx + ww / 2:.1f}" y="{base + 16:.1f}" text-anchor="middle" font-size="13" fill="currentColor" opacity=".75">{a}</text>')
        desc = "; ".join(f"{a}: {plata(v)}" for a, v, _ in vals)
        return (f'<figure style="margin:0"><svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label="{e(titulo)}. {e(desc)}" style="max-width:720px;color:var(--fg)">{"".join(barras)}'
                f'<line x1="{pad}" x2="{W - pad}" y1="{base}" y2="{base}" stroke="var(--axis)"/></svg>'
                '<figcaption class="note"><span style="color:var(--c1)">■</span> gastado &nbsp; <span style="color:var(--mutedbar)">■</span> 2026: autorizado &nbsp; <span style="color:var(--acc)">■</span> 2027: proyecto · en pesos de 2026, descontada la inflación</figcaption></figure>')

    def serie_org(self, x):
        """Serie del organismo entero cuando el programa no se puede seguir en el tiempo."""
        if not x["e"]:
            return None
        h = self.HO.get(re.sub(r"[^a-z0-9]+", " ", unicodedata.normalize("NFD", x["e"]).encode("ascii", "ignore").decode().lower()).strip())
        if not h:
            return None
        hermanos = [p for p in self.P if p["e"] == x["e"]]
        se = [(a, v, "gastado") for a, v in h]
        v26 = sum(p.get("v26") or 0 for p in hermanos)
        a27 = sum(p.get("a27") or 0 for p in hermanos)
        if v26:
            se.append((2026, v26, "autorizado"))
        if a27:
            se.append((2027, a27, "proyecto"))
        return se

    def seccion_real_corta(self, x):
        d = {a: self.real(v, a) for a, v, _ in self.serie(x)}
        fin = 2027 if 2027 in d else 2026 if 2026 in d else None
        if not fin or 2023 not in d or not d[2023]:
            return ""
        c = (d[fin] / d[2023] - 1) * 100
        return f'{"+" if c >= 0 else "−"}{miles(abs(c))}% (2023→{fin})'

    def seccion_historia(self, x):
        se = self.serie(x)
        sujeto = ""
        if len(se) < 4:
            so = self.serie_org(x)
            if so and len(so) >= 4:
                se, sujeto = so, x["e"]
        if len(se) < 3:
            return ""
        filas = [[str(a), dn(v), dn(self.real(v, a)), {"gastado": "Gastado (devengado)", "autorizado": "Autorizado (crédito vigente)", "proyecto": "Proyecto de ley"}[t]] for a, v, t in se]
        d = {a: self.real(v, a) for a, v, _ in se}
        frase = ""
        ult = 2027 if 2027 in d else 2026 if 2026 in d else None
        base = 2023 if 2023 in d else min(d)
        if ult and base < ult and d[base] > 0:
            cambio = (d[ult] / d[base] - 1) * 100
            frase = (f'<p class="respuesta" style="font-size:19px">{("Este programa cambió de nombre o se reorganizó en estos años, así que se muestra el gasto de todo el organismo (" + e(sujeto) + "). ") if sujeto else ""}Descontada la inflación, {"lo pedido para 2027" if ult == 2027 else "lo autorizado para 2026"} {"para todo el organismo " if sujeto else ""}es '
                     f'<strong>{miles(abs(cambio))}% {"más" if cambio >= 0 else "menos"}</strong> que lo que se gastó en {base}.</p>')
        return (f'<section class="card"><h2>¿Cómo cambió desde 2020?</h2>{frase}{self.grafico(se, "Gasto por año en pesos de 2026")}'
                f'<details><summary class="note">Ver los números</summary>{tabla(["Año", "Pesos de cada año", "En pesos de 2026", "Qué es"], filas)}</details>'
                f'<p class="note">Para comparar años se descuenta la inflación con el IPC del INDEC (promedio anual). 2026 usa lo autorizado hoy y estima los meses que faltan con la inflación prevista; 2027, la inflación que supone el proyecto. Si un año no aparece, el programa no existía con ese nombre o no se pudo emparejar. <a href="/metodologia#evolucion">Cómo se calcula</a>.</p></section>')

    # ---------- envoltorio común ----------
    def pagina(self, ruta, titulo, descripcion, cuerpo, migas, og_img=None, ld_extra=None, h1=None):
        url = self.site + ruta
        img = self.site + (og_img or "/og.png")
        crumbs = [{"@type": "ListItem", "position": i + 1, "name": n, "item": self.site + u} for i, (n, u) in enumerate(migas)]
        ld = [{"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": crumbs}]
        if ld_extra:
            ld.append(ld_extra)
        migas_html = '<nav class="migas" aria-label="Estás en">' + ' <span aria-hidden="true">›</span> '.join(
            (f'<a href="{u}">{e(n)}</a>' if i < len(migas) - 1 else f'<span aria-current="page">{e(n)}</span>') for i, (n, u) in enumerate(migas)) + "</nav>"
        doc = f"""<!doctype html>
<html lang="es-AR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)}</title>
<meta name="description" content="{e(descripcion)}">
<link rel="canonical" href="{url}">
<meta name="theme-color" content="#13294b">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<meta property="og:type" content="article">
<meta property="og:locale" content="es_AR">
<meta property="og:site_name" content="Presupuesto Argentina">
<meta property="og:title" content="{e(titulo)}">
<meta property="og:description" content="{e(descripcion)}">
<meta property="og:url" content="{url}">
<meta property="og:image" content="{img}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" href="/tipografias/source-sans-3-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/estilos.css">
<link rel="alternate" type="application/rss+xml" title="Presupuesto Argentina: novedades" href="/novedades.xml">
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
<script>window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};</script>
<script defer src="/_vercel/insights/script.js"></script>
<script defer src="/_vercel/speed-insights/script.js"></script>
<script defer src="/js/descargas.js?v={self.v_desc}"></script>
</head>
<body>
<div class="wrap">
{self.cabecera("/provincias" if ruta.startswith("/provincias") else "/programas")}
<main id="contenido" style="display:flex;flex-direction:column;gap:var(--g-lg)">
{migas_html}
{f"<h1>{e(h1 or titulo)}</h1>"}
{cuerpo}
</main>
<footer class="src">
<p>Sitio independiente, sin relación con el Gobierno nacional ni con partidos políticos. Montos en pesos corrientes. Fuentes: Proyecto de Presupuesto 2027 y sus datasets (Oficina Nacional de Presupuesto), Ley 27.798 y Presupuesto Abierto (Ministerio de Economía). Datos al {self.fecha_sitio}.</p>
<nav><a href="/">Inicio</a><a href="/programas">Buscar un gasto</a><a href="/gasto">Todos los programas</a><a href="/provincias">Por provincia</a><a href="/glosario">Glosario</a><a href="/novedades">Novedades</a><a href="/metodologia#programas">Cómo se calcula</a><a href="{self.repo}/issues/new" target="_blank" rel="noopener">Avisar un error</a></nav>
</footer>
</div>
</body>
</html>
"""
        archivo = self.raiz / (ruta.strip("/") + ".html")
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(doc, encoding="utf-8")
        self.urls.append(ruta)

    def embed(self, ruta, kicker, titulo, cifras, nota=""):
        """Tarjeta para insertar en otros sitios (/embed/...): sin indexar, con link a la página completa.
        Devuelve el bloque «Insertar en tu sitio» para la página principal."""
        url = self.site + ruta
        cif = "".join(f'<div class="c"><span>{e(k)}</span><b>{e(v)}</b></div>' for k, v in cifras if v)
        doc = f"""<!doctype html><html lang="es-AR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(titulo)} · Presupuesto Argentina</title><meta name="robots" content="noindex"><link rel="canonical" href="{url}">
<style>
:root{{--fg:#1a1d21;--mu:#565d66;--bg:#fff;--li:#e0dcd2;--c1:#1d4f91;--ac:#f2b632}}
@media (prefers-color-scheme:dark){{:root{{--fg:#e8eaed;--mu:#a4abb4;--bg:#181b20;--li:#2e333a;--c1:#7fb0ee}}}}
*{{box-sizing:border-box}}body{{margin:0;font:15px/1.4 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;color:var(--fg);background:var(--bg)}}
a.t{{display:flex;flex-direction:column;gap:10px;padding:14px 16px;border:1px solid var(--li);border-top:4px solid var(--ac);border-radius:10px;color:inherit;text-decoration:none;min-height:100vh}}
.k{{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--mu);font-weight:600}}h1{{margin:0;font:600 18px/1.25 Georgia,serif}}
.g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(9rem,1fr));gap:8px}}.c{{display:flex;flex-direction:column}}.c span{{font-size:12px;color:var(--mu)}}.c b{{font-size:17px}}
.n{{font-size:12px;color:var(--mu)}}.f{{display:flex;justify-content:space-between;gap:8px;font-size:12px;color:var(--c1);font-weight:600;margin-top:auto}}
</style></head><body><a class="t" href="{url}" target="_blank" rel="noopener"><span class="k">{e(kicker)}</span><h1>{e(titulo)}</h1><div class="g">{cif}</div>{f'<p class="n" style="margin:0">{e(nota)}</p>' if nota else ""}<span class="f"><span>Presupuesto Argentina</span><span>Ver el detalle →</span></span></a></body></html>"""
        destino = self.raiz / "embed" / (ruta.strip("/") + ".html")
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(doc, encoding="utf-8")
        cid = "cod-" + __import__("hashlib").md5(ruta.encode()).hexdigest()[:8]
        codigo = f'<iframe src="{self.site}/embed{ruta}" width="100%" height="230" style="border:0;max-width:640px" title="{e(titulo)} · Presupuesto Argentina" loading="lazy"></iframe>'
        return (f'<details class="card insertar"><summary><strong>Insertar en tu sitio o nota</strong> <span class="note">· tarjeta con estos datos y link a esta página</span></summary>'
                f'<iframe src="/embed{ruta}" width="100%" height="230" style="border:0;max-width:640px;margin-top:8px;display:block" title="Vista previa" loading="lazy"></iframe>'
                f'<label class="note" for="{cid}" style="display:block">Copiá este código y pegalo en tu página:</label>'
                f'<textarea id="{cid}" readonly rows="3" style="width:100%;font:13px/1.4 monospace;padding:8px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);color:var(--fg)">{e(codigo)}</textarea>'
                f'<button type="button" class="btn mini" data-copiar="{cid}">Copiar código</button></details>')

    def dataset(self, nombre, descripcion, ruta):
        return {"@context": "https://schema.org", "@type": "Dataset", "name": nombre, "description": descripcion, "url": self.site + ruta,
                "inLanguage": "es-AR", "isAccessibleForFree": True, "license": "https://creativecommons.org/licenses/by/4.0/",
                "spatialCoverage": "Argentina", "temporalCoverage": "2026/2027",
                "creator": {"@type": "Organization", "name": "Presupuesto Argentina", "url": self.site + "/"},
                "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": self.site + "/datos/programas.json"}]}

    def og_trabajo(self, archivo, **d):
        self.og.append({"archivo": archivo, **d})
        return "/og/" + archivo

    # ---------- programa ----------
    def programa(self, x, hermanos):
        org = x["e"] or x["j"]
        ruta = f"/gasto/{x['s']}"
        real = (x["a27"] / x["v26"] / (1 + self.infl27 / 100) - 1) * 100 if x.get("a27") is not None and x.get("v26") else None
        frases = []
        if x.get("a27") is not None:
            u27 = self.usd(x["a27"], 2027)
            frases.append(f"El proyecto de Presupuesto 2027 pide <strong>{plata(x['a27'])}</strong>{f' (unos {u27})' if u27 and x['a27'] else ''} para {e(x['n'])} ({e(org)}).")
        else:
            frases.append(f"{e(x['n'])} ({e(org)}) no figura con este nombre en el proyecto 2027: puede haberse reorganizado o cerrado.")
        if x.get("v26") is not None:
            frases.append(f"En 2026 la ley le asignó {plata(x['l26'])}; hoy tiene {plata(x['v26'])} autorizados y lleva gastado {plata(x['d26'])} ({pct(x['d26'], x['v26'])}) hasta el {fecha(self.corte)}.")
        if real is not None:
            frases.append(("Descontando la inflación que supone el proyecto, " + ("crece" if real >= 0 else "cae") + f" alrededor de {miles(abs(real))}% en términos reales."))
        stats = []
        if x.get("a27") is not None:
            stats.append(stat("Pedido para 2027", plata(x["a27"]), "Proyecto de ley", ink=True, u=self.usd(x["a27"], 2027)))
        if x.get("v26") is not None:
            stats.append(stat("2026: aprobado por ley", plata(x["l26"]), "Ley 27.798", u=self.usd(x["l26"], 2026)))
            stats.append(stat("2026: autorizado hoy", plata(x["v26"]), "con los cambios del año", u=self.usd(x["v26"], 2026)))
            stats.append(stat("2026: gastado", plata(x["d26"]), f"{pct(x['d26'], x['v26'])} al {fecha(self.corte)}", barra=x["d26"] / x["v26"] * 100 if x["v26"] else 0, u=self.usd(x["d26"], 2026)))
        cuerpo = [f'<p class="note" style="margin-top:-12px">{e(x["j"])}{" › " + e(x["e"]) if x["e"] else ""}</p>']
        if x.get("b"):
            cuerpo.append(f'<p class="sub" style="font-size:18px">{e(x["b"])}</p>')
        cuerpo.append(f'<p class="respuesta">{" ".join(frases)}</p>')
        cuerpo.append(f'<div class="stats">{"".join(stats)}</div>{self.nota_usd()}')
        if real is not None:
            cuerpo.append(f'<p><span class="etq{" warn" if real < 0 else ""}">Variación real 2027 contra lo autorizado en 2026: {"+" if real >= 0 else "−"}{miles(abs(real))}%</span></p>')
        cuerpo.append(self.seccion_historia(x))
        if x.get("act27"):
            filas = [[e(n), dn(v), pct(v, x["a27"]) if x["a27"] else "—"] for n, v in x["act27"]]
            cuerpo.append(f'<section class="card"><h2>¿En qué se gasta en 2027?</h2><p class="note">Cada actividad u obra del programa en el proyecto 2027 ({len(filas)}).</p>{tabla(["Actividad u obra", "Pedido 2027", "% del programa"], filas)}</section>')
        if x.get("inc27"):
            cuerpo.append(f'<section class="card"><h2>¿Qué tipo de gasto es?</h2>{tabla(["Tipo de gasto", "Pedido 2027", "% del programa"], [[e(n), dn(v), pct(v, x["a27"])] for n, v in x["inc27"]])}</section>')
        if x.get("metas"):
            filas = [[e(m[0]), e(str(m[1] or "")), miles(m[2], 0 if float(m[2]).is_integer() else 2)] for m in x["metas"]]
            cuerpo.append(f'<section class="card"><h2>¿Qué promete hacer en 2027?</h2><p class="note">Metas físicas e indicadores del proyecto.</p>{tabla(["Meta o indicador", "Unidad", "Cantidad 2027"], filas)}</section>')
        if x.get("act26"):
            filas = [[e(a[0]), dn(a[1]), dn(a[2]), dn(a[3]), pct(a[3], a[2])] for a in x["act26"]]
            cuerpo.append(f'<section class="card"><h2>¿Cuánto se gastó en 2026?</h2><p class="note">Por actividad: lo aprobado por ley, lo autorizado hoy y lo gastado (devengado) hasta el {fecha(self.corte)}.</p>{tabla(["Actividad u obra", "Ley", "Autorizado hoy", "Gastado", "%"], filas)}</section>')
        if x.get("prov26"):
            filas = []
            for p, v, d in x["prov26"]:
                nom = f'<a href="/provincias/{slug(p)}">{e(p)}</a>' if p not in ESPECIALES else e(p)
                filas.append([nom, dn(v), dn(d), pct(d, v)])
            cuerpo.append(f'<section class="card"><h2>¿En qué provincias se gasta?</h2><p class="note">Gasto 2026 según la ubicación que le asigna el Estado. «Nacional» o «No clasificado» es gasto sin provincia asignada.</p>{tabla(["Provincia", "Autorizado 2026", "Gastado", "%"], filas)}</section>')
        if hermanos:
            lis = "".join(f'<li><a href="/gasto/{h["s"]}">{e(h["n"])}</a><span>{plata(h["a27"] if h["a27"] is not None else h.get("v26"))}</span></li>' for h in hermanos[:40])
            cuerpo.append(f'<section class="card"><h2>Otros programas de {e(org)}</h2><ul class="lista-links">{lis}</ul></section>')
        rh = self.seccion_real_corta(x)
        cuerpo.append(self.embed(ruta, "Presupuesto 2027 · " + org, x["n"], [("Pedido para 2027", plata(x.get("a27"))) if x.get("a27") is not None else ("", ""),
                                 ("2026: autorizado", plata(x.get("v26"))) if x.get("v26") else ("", ""),
                                 ("2026: gastado", f'{pct(x["d26"], x["v26"])}') if x.get("v26") else ("", ""), ("Cambio real desde 2023", rh)]))
        cuerpo.append(f'<div class="acciones" style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn primary" href="/programas?q={e(x["n"])}">Abrir en el buscador</a><a class="btn" href="/cuadros?q={e(org)}">Buscar en los cuadros oficiales</a><a class="btn" href="/gasto">Ver todos los programas</a></div>')
        a27 = plata(x["a27"]) if x.get("a27") is not None else None
        desc = (x.get("b", "") + " " if x.get("b") else "") + (f"Presupuesto 2027: {a27}." if a27 else "") + (f" En 2026: {plata(x['v26'])} autorizados, {pct(x['d26'], x['v26'])} gastado." if x.get("v26") else "")
        n1, u1 = plata_og(x["a27"] if x.get("a27") is not None else x.get("v26"))
        n2, u2 = plata_og(x.get("l26")) if x.get("l26") is not None else (None, None)
        img = self.og_trabajo(f"gasto/{x['s']}.jpg", kicker="Presupuesto 2027 · " + x["j"], titulo=x["n"], org=x["e"] or "",
                              l1="Pedido para 2027" if x.get("a27") is not None else "Autorizado 2026", n1=n1, u1=u1, l2="Ley 2026" if n2 else "", n2=n2, u2=u2)
        titulo = f"{x['n']} ({org}): presupuesto 2027 y gasto 2026"
        self.pagina(ruta, titulo, desc.strip()[:300], "\n".join(cuerpo),
                    [("Inicio", "/"), ("Todos los programas", "/gasto"), (x["j"], f"/gasto#{slug(x['j'])}"), (x["n"], ruta)], img,
                    self.dataset(titulo, desc.strip(), ruta), h1=x["n"])

    # ---------- organismo fuera de los programas ----------
    def ente(self, x, hermanos):
        ruta = f"/gasto/{x['s']}"
        u27 = self.usd(x["g27"], 2027)
        frases = [f"El proyecto de Presupuesto 2027 prevé un gasto de <strong>{plata(x['g27'])}</strong>{f' (unos {u27})' if u27 and x['g27'] else ''} para {e(x['n'])} en 2027."]
        if x.get("g26") is not None:
            frases.append(f"La Ley 27.798 le fijó {plata(x['g26'])} para 2026: {pct(x['g27'] - x['g26'], x['g26'])} más en pesos, aunque la ley 2026 suponía 10,1% de inflación y el año cerraría cerca de {miles(self.infl26)}%.")
        stats = [stat("Gasto total 2027", plata(x["g27"]), "Proyecto de ley", ink=True, u=self.usd(x["g27"], 2027))]
        if x.get("g26") is not None:
            stats.append(stat("Gasto total 2026", plata(x["g26"]), "Ley 27.798", u=self.usd(x["g26"], 2026)))
        stats += [stat(d[0] + " 2027", plata(d[1]), u=self.usd(d[1], 2027)) for d in x.get("det", [])]
        cuerpo = [f'<p class="note" style="margin-top:-12px">{e(x["tipo"])} · tiene presupuesto propio, fuera de los programas de la Administración Nacional</p>',
                  f'<p class="respuesta">{" ".join(frases)}</p>', f'<div class="stats">{"".join(stats)}</div>{self.nota_usd()}']
        if x.get("nota"):
            cuerpo.append(f'<p class="sub">{e(x["nota"])}</p>')
        if x["tipo"].startswith("Univ"):
            cuerpo.append('<p class="sub">La plata de las universidades nacionales sale del programa <a href="/gasto/' + next((p["s"] for p in self.P if p["n"].startswith("Desarrollo de la Educación Superior")), "") + '">Desarrollo de la Educación Superior</a> del Ministerio de Capital Humano, que se reparte según la planilla anexa al artículo 12 de la ley.</p>')
        botones = [f'<a class="btn primary" href="/cuadros#p{x["pag"]}">Ver el cuadro 2027 (pág. {x["pag"]})</a>']
        if x.get("pag26"):
            botones.append(f'<a class="btn" href="/cuadros#ley2026-p{x["pag26"]}">Ver el cuadro de la ley 2026 (pág. {x["pag26"]})</a>')
        cuerpo.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap">{"".join(botones)}</div>')
        cuerpo.append(self.embed(ruta, "Presupuesto 2027 · " + x["tipo"], x["n"], [("Gasto total 2027", plata(x["g27"])), ("Ley 2026", plata(x["g26"]) if x.get("g26") is not None else "")]))
        if hermanos:
            lis = "".join(f'<li><a href="/gasto/{h["s"]}">{e(h["n"])}</a><span>{plata(h["g27"])}</span></li>' for h in hermanos)
            cuerpo.append(f'<section class="card"><h2>{"Las otras universidades nacionales" if x["tipo"].startswith("Univ") else "Otros " + ("fondos fiduciarios" if x["tipo"] == "Fondo fiduciario" else "organismos del mismo tipo")}</h2><ul class="lista-links">{lis}</ul></section>')
        n1, u1 = plata_og(x["g27"])
        n2, u2 = plata_og(x.get("g26")) if x.get("g26") is not None else (None, None)
        img = self.og_trabajo(f"gasto/{x['s']}.jpg", kicker="Presupuesto 2027 · " + x["tipo"], titulo=x["n"], org="",
                              l1="Gasto total 2027", n1=n1, u1=u1, l2="Ley 2026" if n2 else "", n2=n2, u2=u2)
        desc = f"{x['n']}: gasto previsto de {plata(x['g27'])} en el Presupuesto 2027" + (f" contra {plata(x['g26'])} en la ley 2026." if x.get("g26") is not None else ".")
        titulo = f"{x['n']}: presupuesto 2027" + (" y 2026" if x.get("g26") is not None else "")
        self.pagina(ruta, titulo, desc, "\n".join(cuerpo), [("Inicio", "/"), ("Todos los programas", "/gasto"), (x["tipo"], f"/gasto#{slug(x['tipo'])}"), (x["n"], ruta)],
                    img, self.dataset(titulo, desc, ruta), h1=x["n"])

    # ---------- provincia ----------
    def provincias(self):
        por = defaultdict(list)
        for x in self.P:
            for p, v, d in x.get("prov26", []):
                por[p].append((x, v, d))
        geo = sum(v for p, xs in por.items() if p not in ESPECIALES for _, v, _ in xs)
        lista = sorted(((p, sum(v for _, v, _ in xs), sum(d for _, _, d in xs)) for p, xs in por.items() if p not in ESPECIALES), key=lambda z: -z[1])
        pobf = json.loads((self.raiz / "fuentes" / "poblacion_censo2022.json").read_text(encoding="utf-8"))
        pob = pobf["provincias"]
        hab = {p: tv * 1e6 / pob[p] for p, tv, _ in lista if p in pob}
        rank = {p: i + 1 for i, p in enumerate(sorted(hab, key=lambda q: -hab[q]))}
        for p, tv, td in lista:
            ruta = f"/provincias/{slug(p)}"
            xs = sorted(por[p], key=lambda z: -z[1])
            frases = [f"En 2026 el Estado nacional tiene <strong>{plata(tv)}</strong> (unos {self.usd(tv, 2026)}) autorizados para gastar en {e(p)} y lleva gastado {plata(td)} ({pct(td, tv)}) hasta el {fecha(self.corte)}.",
                      f"Es el {miles(tv / geo * 100, 1)}% de lo que la Nación asigna a alguna provincia"
                      + (f" y equivale a <strong>${miles(hab[p])} por habitante</strong> (unos {self.usd_hab(hab[p], 2026)}) en el año, el {rank[p]}.º puesto entre las 24 jurisdicciones." if p in hab else ".")]
            filas = [[f'<a href="/gasto/{x["s"]}">{e(x["n"])}</a><br><span class="note">{e(x["e"] or x["j"])}</span>', dn(v), dn(d), pct(d, v)] for x, v, d in xs[:60]]
            cuerpo = [f'<p class="respuesta">{" ".join(frases)}</p>',
                      f'<div class="stats">{stat("Autorizado 2026", plata(tv), "gasto nacional con ubicación en la provincia", ink=True, u=self.usd(tv, 2026))}{stat("Gastado", plata(td), pct(td, tv) + " al " + fecha(self.corte), barra=td / tv * 100 if tv else 0, u=self.usd(td, 2026))}{stat("Por habitante en 2026", "$" + miles(hab[p]) if p in hab else "—", f"puesto {rank[p]} de 24 · {miles(pob[p])} habitantes (Censo 2022)" if p in hab else "", u=self.usd_hab(hab[p], 2026) if p in hab else None)}{stat("Programas con gasto en la provincia", miles(len(xs)))}</div>' + self.nota_usd(),
                      '<div class="caveat">Cuenta solo el gasto que el Estado nacional ubica en esta provincia. Una parte grande del gasto, como muchas jubilaciones y asignaciones o las transferencias a fondos, figura como «Nacional» o «No clasificado», así que lo que llega a la gente de la provincia es más que esto. Tampoco incluye la coparticipación, que no es gasto del presupuesto nacional.' + (' En la Ciudad de Buenos Aires, además, figura mucho gasto de organismos nacionales que tienen ahí su sede.' if p.startswith('Ciudad') else '') + '</div>',
                      self.obras_provincia(p),
                      f'<section class="card"><h2>¿En qué gasta la Nación en {e(p)}?</h2><p class="note">Los {min(60, len(xs))} programas con más gasto en la provincia en 2026.</p>{tabla(["Programa", "Autorizado 2026", "Gastado", "%"], filas)}</section>',
                      f'<div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn primary" href="/programas?provincia={e(p)}">Buscar dentro de {e(p)}</a><a class="btn" href="/provincias">Ver todas las provincias</a></div>',
                      self.embed(ruta, "Gasto nacional en la provincia · 2026", f"¿Cuánto gasta la Nación en {p}?", [("Autorizado 2026", plata(tv)), ("Gastado", pct(td, tv)), ("Por habitante", ("$" + miles(hab[p])) if p in hab else ""), ("Puesto", f"{rank[p]} de 24" if p in hab else "")])]
            n1, u1 = plata_og(tv)
            img = self.og_trabajo(f"provincias/{slug(p)}.jpg", kicker="Presupuesto nacional 2026", titulo=f"¿Cuánto gasta la Nación en {p}?", org="",
                                  l1="Autorizado 2026", n1=n1, u1=u1, l2="Por habitante", n2=("$" + miles(hab[p])) if p in hab else pct(td, tv), u2=(f"puesto {rank[p]} de 24") if p in hab else "", fuente="Fuentes: Presupuesto Abierto y Censo 2022")
            titulo = f"¿Cuánto gasta la Nación en {p}? Presupuesto 2026 por provincia"
            desc = f"El Estado nacional tiene {plata(tv)} autorizados para gastar en {p} en 2026" + (f" (${miles(hab[p])} por habitante, puesto {rank[p]} de 24)" if p in hab else "") + f" y lleva gastado el {pct(td, tv)}. Programa por programa."
            self.pagina(ruta, titulo, desc, "\n".join(cuerpo), [("Inicio", "/"), ("Por provincia", "/provincias"), (p, ruta)], img, self.dataset(titulo, desc, ruta), h1=f"¿Cuánto gasta la Nación en {p}?")
        filas = [[f'<a href="/provincias/{slug(p)}">{e(p)}</a>', "$" + miles(hab[p]) if p in hab else "—", (self.usd_hab(hab[p], 2026) or "—") if p in hab else "—", dn(tv), dn(td), pct(td, tv), f"{miles(tv / geo * 100, 1)}%"] for p, tv, td in sorted(lista, key=lambda z: -hab.get(z[0], 0))]
        esp = [[e(p), plata(sum(v for _, v, _ in por[p])), plata(sum(d for _, _, d in por[p]))] for p in sorted(ESPECIALES) if p in por]
        prov_solo = {q: v for q, v in hab.items() if not q.startswith("Ciudad")}
        mx, mn = max(prov_solo, key=prov_solo.get), min(prov_solo, key=prov_solo.get)
        cuerpo = [f'<p class="respuesta">Por habitante, la Nación asigna en 2026 entre <strong>${miles(hab[mn])}</strong> (unos {self.usd_hab(hab[mn], 2026)}) en {e(mn)} y <strong>${miles(hab[mx])}</strong> (unos {self.usd_hab(hab[mx], 2026)}) en {e(mx)}. La Ciudad de Buenos Aires queda arriba de todas porque ahí se registra el gasto de muchos organismos nacionales. Tocá una provincia para ver en qué se gasta, programa por programa.</p>',
                  '<div class="caveat">Solo cuenta el gasto que el presupuesto nacional ubica en cada provincia: no incluye lo clasificado como «Nacional» o «No clasificado» (como buena parte de las jubilaciones y asignaciones) ni la coparticipación. En la Ciudad de Buenos Aires figura además mucho gasto de organismos que tienen ahí su sede. Población: Censo 2022 (INDEC, resultados provisionales).</div>',
                  tabla(["Provincia", "Por habitante", "Por habitante en dólares", "Autorizado 2026", "Gastado", "%", "Parte del total con provincia"], filas),
                  '<section class="card"><h2>Gasto sin provincia asignada</h2><p class="note">Este gasto no se puede atribuir a una provincia en el presupuesto, aunque llegue a personas de todo el país.</p>' + tabla(["Ubicación", "Autorizado 2026", "Gastado"], esp) + "</section>"]
        self.pagina("/provincias", "¿Cuánto gasta la Nación en cada provincia? Ranking por habitante 2026", "Ranking del gasto del Estado nacional por habitante en cada provincia argentina en 2026, con lo autorizado y lo gastado, programa por programa.",
                    "\n".join(cuerpo), [("Inicio", "/"), ("Por provincia", "/provincias")], h1="¿Cuánto gasta la Nación en cada provincia?")

    def obras_provincia(self, p):
        ob = self.OB.get(p)
        if not ob:
            return ""
        partes = []
        o = ob.get("o27", [])
        if o:
            tot = sum(z[3] for z in o)
            filas = [[e(z[0]) + (' <span class="note">(compartida con otra provincia)</span>' if z[4] else ""),
                      (f'<a href="/gasto/{z[2]}">{e(z[1])}</a>' if z[2] else e(z[1])), plata(z[3])] for z in o[:80]]
            partes.append(f'<section class="card"><h2>¿Qué obras pide el proyecto 2027 para {e(p)}?</h2>'
                          f'<p class="respuesta" style="font-size:19px">El proyecto 2027 tiene <strong>{len(o)} obras y actividades</strong> que nombran a {e(p)}, por <strong>{plata(tot)}</strong>.</p>'
                          f'{tabla(["Obra o actividad", "Programa", "Pedido 2027"], filas)}'
                          '<p class="note">Son las actividades y obras del proyecto (datasets de la Oficina Nacional de Presupuesto) cuyo nombre menciona la provincia, por ejemplo «Ruta Nacional 40, Provincia de…» o «Distrito…». Incluye también juzgados, parques nacionales y otros gastos con nombre provincial. Muchas obras no dicen dónde están en su nombre, así que la lista no es completa.</p></section>')
        i = ob.get("i26", [])
        if i:
            tv, td = sum(z[3] for z in i), sum(z[4] for z in i)
            filas = [[e(z[0]), (f'<a href="/gasto/{z[2]}">{e(z[1])}</a>' if z[2] else e(z[1])), dn(z[3]), dn(z[4]), pct(z[4], z[3])] for z in i[:50]]
            partes.append(f'<section class="card"><h2>Obras y equipamiento de la Nación en {e(p)} en 2026</h2>'
                          f'<p class="respuesta" style="font-size:19px">En 2026 la Nación tiene <strong>{plata(tv)}</strong> autorizados para obras y equipamiento propios en {e(p)} y lleva gastado {plata(td)} ({pct(td, tv)}).</p>'
                          f'{tabla(["Actividad u obra", "Programa", "Autorizado 2026", "Gastado", "%"], filas)}'
                          '<p class="note">Inversión directa del Estado nacional (bienes de uso: obras, maquinaria y equipos) ubicada en la provincia, según Presupuesto Abierto. No incluye las transferencias a la provincia o a municipios para que ellos hagan obras.</p></section>')
        return "\n".join(partes)

    # ---------- índice de todo el gasto ----------
    def indice(self):
        por_j = defaultdict(list)
        for x in self.P:
            por_j[x["j"]].append(x)
        orden = sorted(por_j, key=lambda j: -sum((x["a27"] or 0) for x in por_j[j]))
        partes = ['<p class="sub">Todos los programas del presupuesto nacional, ordenados por ministerio, con lo pedido para 2027. Además, las universidades, los fondos fiduciarios, los otros entes y las empresas públicas, que tienen presupuesto propio.</p>',
                  '<form class="busca" action="/programas" method="get" role="search"><label for="q" class="vh">Buscar</label><input id="q" name="q" type="search" placeholder="Buscá un programa, obra u organismo"><button class="btn primary">Buscar</button></form>',
                  '<nav class="chips" aria-label="Ir a">' + "".join(f'<a href="#{slug(j)}">{e(j)}</a>' for j in orden) + "".join(f'<a href="#{slug(t)}">{e(t)}</a>' for t in dict.fromkeys(x["tipo"] for x in self.E)) + "</nav>"]
        for j in orden:
            xs = sorted(por_j[j], key=lambda x: -((x["a27"] if x["a27"] is not None else x.get("v26", 0)) or 0))
            tot = sum((x["a27"] or 0) for x in xs)
            lis = "".join(f'<li><a href="/gasto/{x["s"]}">{e(x["n"])}{(" <span class=note>· " + e(x["e"]) + "</span>") if x["e"] else ""}</a><span>{plata(x["a27"]) if x["a27"] is not None else "2026: " + plata(x.get("v26"))}</span></li>' for x in xs)
            partes.append(f'<section class="card" id="{slug(j)}"><h2>{e(j)} <span class="note">· {plata(tot)} en 2027</span></h2><ul class="lista-links">{lis}</ul></section>')
        for t in dict.fromkeys(x["tipo"] for x in self.E):
            xs = sorted((x for x in self.E if x["tipo"] == t), key=lambda x: -x["g27"])
            lis = "".join(f'<li><a href="/gasto/{x["s"]}">{e(x["n"])}</a><span>{plata(x["g27"])}</span></li>' for x in xs)
            partes.append(f'<section class="card" id="{slug(t)}"><h2>{e(t)} <span class="note">· presupuesto propio</span></h2><ul class="lista-links">{lis}</ul></section>')
        self.pagina("/gasto", "Todos los programas del Presupuesto 2027, ministerio por ministerio", f"Los {len(self.P)} programas del presupuesto nacional y {len(self.E)} universidades, fondos, entes y empresas públicas, con lo pedido para 2027 y lo gastado en 2026.",
                    "\n".join(partes), [("Inicio", "/"), ("Todos los programas", "/gasto")], h1="Todos los programas del presupuesto")

    # ---------- evolución 2020-2027 ----------
    def evolucion(self):
        tot = [(a, v, "gastado") for a, v in self.HT]
        tot.append((2026, sum(x.get("v26") or 0 for x in self.P), "autorizado"))
        tot.append((2027, sum(x.get("a27") or 0 for x in self.P), "proyecto"))
        d = {a: self.real(v, a) for a, v, _ in tot}
        cambios = []
        for x in self.P:
            h = dict(x.get("h", []))
            if 2023 in h and x.get("a27") and x["a27"] >= 50000 and h[2023] > 0:
                r23, r27 = self.real(h[2023], 2023), self.real(x["a27"], 2027)
                if r23 >= 50000:  # sin bases chiquitas, que dan porcentajes engañosos
                    cambios.append((x, r23, r27, (r27 / r23 - 1) * 100))
        orgs = []
        por_e = defaultdict(list)
        for x in self.P:
            if x["e"]:
                por_e[x["e"]].append(x)
        for org, xs in por_e.items():
            so = self.serie_org(xs[0])
            if not so:
                continue
            m = {a: v for a, v, _ in so}
            if 2023 in m and 2027 in m and m[2027] >= 50000:
                orgs.append((org, xs[0]["j"], self.real(m[2023], 2023), self.real(m[2027], 2027)))
        def fila(x, r23, r27, c):
            return [f'<a href="/gasto/{x["s"]}">{e(x["n"])}</a><br><span class="note">{e(x["e"] or x["j"])}</span>', dn(r23), dn(r27), f'{"+" if c >= 0 else "−"}{miles(abs(c))}%']
        sube = sorted(cambios, key=lambda z: -z[3])[:20]
        baja = sorted(cambios, key=lambda z: z[3])[:20]
        grandes = sorted(cambios, key=lambda z: -z[2])[:30]
        c_tot = (d[2027] / d[2023] - 1) * 100
        cab = ["Programa", "2023 (gastado)", "2027 (proyecto)", "Cambio real"]
        cuerpo = [f'<p class="respuesta">Descontada la inflación, el gasto total que pide el proyecto para 2027 es <strong>{miles(abs(c_tot))}% {"más" if c_tot >= 0 else "menos"}</strong> que lo gastado en 2023. Pero no todo se movió igual: acá está qué creció y qué se achicó, programa por programa.</p>',
                  (f'<section class="card"><h2>El gasto total, año por año</h2>{tabla(["Año", "Pesos de cada año", "Pesos de 2026 (sin inflación)", "En dólares"], [[str(a) + ("" if t == "gastado" else f" ({t})"), dn(v), dn(d[a]), self.usd(v, a) or "—"] for a, v, t in tot])}'
                   '<p class="note">Suma de los programas de la Administración Nacional. Hasta 2025, lo gastado; 2026, lo autorizado hoy; 2027, lo pedido en el proyecto. '
                   'Dólares al oficial promedio de cada año (BCRA); 2027, con el dólar que proyecta el Ministerio de Economía.</p></section>' if self.TC else ""),
                  f'<section class="card"><h2>Gasto total del Estado nacional, 2020-2027</h2>{self.grafico(tot, "Gasto total por año en pesos de 2026")}</section>',
                  f'<section class="card"><h2>Los que más cayeron desde 2023</h2><p class="note">Programas con más de $50.000 millones (en pesos de 2026) tanto en 2023 como en 2027.</p>{tabla(cab, [fila(*z) for z in baja])}</section>',
                  f'<section class="card"><h2>Los que más crecieron desde 2023</h2><p class="note">Programas con más de $50.000 millones (en pesos de 2026) tanto en 2023 como en 2027.</p>{tabla(cab, [fila(*z) for z in sube])}</section>',
                  f'<section class="card"><h2>Los 30 programas más grandes</h2>{tabla(cab, [fila(*z) for z in grandes])}</section>']
        if orgs:
            fo = [[e(o), dn(a), dn(b), f'{"+" if b >= a else "−"}{miles(abs((b / a - 1) * 100))}%'] for o, j, a, b in sorted(orgs, key=lambda z: z[3] / z[2] - 1)]
            cuerpo.append(f'<section class="card"><h2>Organismo por organismo</h2><p class="note">Sirve cuando los programas cambiaron de nombre (por ejemplo, en Vialidad). Montos en pesos de 2026.</p>{tabla(["Organismo", "2023 (gastado)", "2027 (proyecto)", "Cambio real"], fo)}</section>')
        cuerpo.append('<div class="caveat">2020 a 2025: gasto devengado de cada año (Presupuesto Abierto). 2027: lo que pide el proyecto, que todavía puede cambiar en el Congreso y en la ejecución. Se descuenta la inflación con el IPC promedio del INDEC; para 2027, con la que supone el proyecto. Si la inflación de 2027 es mayor, la caída real será más grande. <a href="/metodologia#evolucion">Cómo se calcula</a>.</div>')
        n1, u1 = (f"{'+' if c_tot >= 0 else '−'}{miles(abs(c_tot))}%", "real")
        img = self.og_trabajo("evolucion.jpg", kicker="Presupuesto nacional 2020-2027", titulo="¿Qué creció y qué se achicó desde 2023?", org="Descontada la inflación, programa por programa",
                              l1="Gasto total 2027 contra 2023", n1=n1, u1=u1, fuente="Fuentes: Presupuesto Abierto, Proyecto 2027 e IPC del INDEC")
        desc = f"Cuánto cambió en términos reales el gasto de cada programa del Estado nacional entre 2020 y el Presupuesto 2027: universidades, jubilaciones, obra pública, CONICET y más."
        self.pagina("/evolucion", "Qué creció y qué se achicó en el presupuesto nacional, 2020-2027", desc, "\n".join(cuerpo),
                    [("Inicio", "/"), ("Evolución 2020-2027", "/evolucion")], img, self.dataset("Evolución real del gasto nacional por programa, 2020-2027", desc, "/evolucion"),
                    h1="¿Qué creció y qué se achicó desde 2023?")

    # ---------- ejecución 2026: lo que va atrasado ----------
    def ejecucion(self):
        import datetime
        f = datetime.date.fromisoformat(self.corte)
        avance = (f - datetime.date(f.year, 1, 1)).days / 365
        filas = []
        for x in self.P:
            v, d = x.get("v26") or 0, x.get("d26") or 0
            if v >= 20000 and not x["n"].startswith("Otras Asistencias Financieras"):  # fondo de reserva que se reparte durante el año
                filas.append((x, v, d, d / v, avance - d / v, v * avance - d))
        if not filas:
            return
        tv, td = sum(z[1] for z in filas), sum(z[2] for z in filas)
        cab = ["Programa", "Autorizado 2026", "Gastado", "% gastado", "Sin gastar respecto del ritmo"]
        def fila(z):
            x, v, d, ej, atr, plata_ = z
            return [f'<a href="/gasto/{x["s"]}">{e(x["n"])}</a><br><span class="note">{e(x["e"] or x["j"])}</span>', dn(v), dn(d), f"{miles(ej * 100)}%", dn(max(0, plata_))]
        atrasados = sorted(filas, key=lambda z: -z[4])[:30]
        plata_quieta = sorted(filas, key=lambda z: -z[5])[:20]
        adelantados = sorted(filas, key=lambda z: z[4])[:15]
        por_j = defaultdict(lambda: [0.0, 0.0])
        for x in self.P:
            if x.get("v26"):
                por_j[x["j"]][0] += x["v26"]; por_j[x["j"]][1] += x.get("d26") or 0
        fj = [[e(j), dn(v), dn(d), f"{miles(d / v * 100)}%"] for j, (v, d) in sorted(por_j.items(), key=lambda z: z[1][1] / z[1][0] if z[1][0] else 1) if v >= 50000]
        cuerpo = [f'<p class="respuesta">Al {fecha(self.corte)} pasó el <strong>{miles(avance * 100)}% del año</strong>, y el Estado nacional lleva gastado el {pct(td, tv)} de lo autorizado en sus programas grandes. Estos son los que van más atrasados y los que más plata tienen sin usar respecto de ese ritmo.</p>',
                  f'<div class="stats">{stat("Parte del año transcurrida", miles(avance * 100) + "%", "al " + fecha(self.corte), ink=True)}{stat("Gastado de lo autorizado", pct(td, tv), plata(td) + " de " + plata(tv), barra=td / tv * 100)}{stat("Programas analizados", miles(len(filas)), "con más de $20.000 millones autorizados")}</div>',
                  f'<section class="card"><h2>Los que más plata tienen sin gastar</h2><p class="note">Diferencia entre lo que habrían gastado a ritmo parejo ({miles(avance * 100)}% de lo autorizado) y lo que gastaron.</p>{tabla(cab, [fila(z) for z in plata_quieta])}</section>',
                  f'<section class="card"><h2>Los más atrasados</h2><p class="note">Ordenados por la distancia entre el porcentaje gastado y el {miles(avance * 100)}% del año que ya pasó.</p>{tabla(cab, [fila(z) for z in atrasados])}</section>',
                  f'<section class="card"><h2>Los que van más adelantados</h2>{tabla(cab, [fila(z) for z in adelantados])}</section>',
                  f'<section class="card"><h2>Ministerio por ministerio</h2>{tabla(["Jurisdicción", "Autorizado 2026", "Gastado", "% gastado"], fj)}</section>',
                  '<div class="caveat">Atrasado no siempre quiere decir recortado: hay gastos que se concentran a fin de año (aguinaldo, certificados de obra, transferencias trimestrales) y créditos que se van a reasignar. Se deja afuera «Otras Asistencias Financieras» (Obligaciones a Cargo del Tesoro), un fondo de reserva que se reparte a otros programas durante el año. Pero un programa que a esta altura gastó muy poco difícilmente use todo lo autorizado. Datos: Presupuesto Abierto (Ministerio de Economía), gasto devengado; se actualizan solos todas las semanas.</div>']
        img = self.og_trabajo("ejecucion-2026.jpg", kicker="Presupuesto 2026 · ejecución", titulo="¿Qué se está dejando de gastar?", org=f"Al {fecha(self.corte)}",
                              l1="Pasó del año", n1=f"{miles(avance * 100)}%", u1="", l2="Gastado de lo autorizado", n2=pct(td, tv), u2="", fuente="Fuente: Presupuesto Abierto (Ministerio de Economía)")
        desc = f"Qué programas del Presupuesto 2026 van más atrasados en su ejecución y cuánta plata tienen sin gastar, al {fecha(self.corte)}. Se actualiza todas las semanas."
        self.pagina("/ejecucion-2026", "¿Qué se está dejando de gastar del Presupuesto 2026? Programas atrasados", desc, "\n".join(cuerpo),
                    [("Inicio", "/"), ("2026: ¿se cumplió?", "/cumplimiento-2026"), ("Qué se está dejando de gastar", "/ejecucion-2026")], img,
                    self.dataset("Ejecución del Presupuesto 2026 por programa", desc, "/ejecucion-2026"), h1="¿Qué se está dejando de gastar en 2026?")

    # ---------- comparador ----------
    def comparar(self):
        items = []
        for x in self.P:
            se = self.serie(x)
            org = False
            if len(se) < 4:
                so = self.serie_org(x)
                if so and len(so) >= 4:
                    se, org = so, True
            items.append({"id": x["s"], "t": "p", "n": x["n"], "o": x["e"] or x["j"], "a27": x.get("a27"), "l26": x.get("l26"), "v26": x.get("v26"), "d26": x.get("d26"),
                          "r": [[a, round(self.real(v, a), 1), t[0]] for a, v, t in se], "so": org})
        for x in self.E:
            items.append({"id": x["s"], "t": "e", "n": x["n"], "o": x["tipo"], "g27": x["g27"], "g26": x.get("g26")})
        por = defaultdict(lambda: [0.0, 0.0])
        for x in self.P:
            for p, v, d in x.get("prov26", []):
                por[p][0] += v; por[p][1] += d
        pob = json.loads((self.raiz / "fuentes" / "poblacion_censo2022.json").read_text(encoding="utf-8"))["provincias"]
        for p, (v, d) in por.items():
            if p in pob:
                items.append({"id": "provincia-" + slug(p), "t": "v", "n": p, "o": "Provincia", "v26": round(v, 1), "d26": round(d, 1), "pob": pob[p], "hab": round(v * 1e6 / pob[p])})
        (self.raiz / "datos" / "comparar.json").write_text(json.dumps({"corte": self.corte, "items": items}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        buscar = lambda pre: next((x["s"] for x in self.P if x["n"].startswith(pre)), None)
        ente = lambda pre: next((x["s"] for x in self.E if x["n"].startswith(pre)), None)
        ejemplos = [("Universidades vs. Policía Federal", [buscar("Desarrollo de la Educación Superior"), buscar("Seguridad Federal")]),
                    ("Jubilaciones vs. intereses de la deuda", [buscar("Prestaciones Previsionales"), buscar("Deudas Directas")]),
                    ("Córdoba vs. Santa Fe vs. Mendoza", ["provincia-cordoba", "provincia-santa-fe", "provincia-mendoza"]),
                    ("Rutas: construcción vs. mantenimiento", [buscar("Construcciones Viales"), buscar("Mantenimiento en Rutas Nacionales")]),
                    ("INCAA vs. INAMU", [ente("Instituto Nacional de Cine"), ente("Instituto Nacional de la Música")]),
                    ("UBA vs. Universidad de Córdoba", [ente("Universidad de Buenos Aires"), ente("Universidad Nacional de Córdoba")])]
        chips = "".join(f'<a href="/comparar?c={",".join(i for i in ids if i)}">{e(t)}</a>' for t, ids in ejemplos if all(ids))
        cuerpo = f"""<p class="sub">Elegí hasta tres programas, organismos o provincias y miralos lado a lado: lo que pide el proyecto 2027, lo que se autorizó y gastó en 2026, y cómo cambió desde 2020 descontada la inflación.</p>
<div class="card" id="cmp-elegir">
<div class="cmp-slots" id="slots"></div>
<div class="chips" aria-label="Ejemplos"><span class="note" style="align-self:center">Ejemplos:</span>{chips}</div>
</div>
<p class="vh" id="cmp-anuncio" role="status"></p>
<div id="cmp-res"></div>
<p class="note">Montos en pesos corrientes salvo donde dice «pesos de 2026». La evolución usa lo gastado de 2020 a 2025, lo autorizado en 2026 y lo pedido para 2027, con el IPC del INDEC. Universidades, entes y empresas tienen presupuesto propio y no se pueden seguir año por año. Los dólares son al oficial promedio de cada año (BCRA); 2027, con el que proyecta el Ministerio de Economía. <a href="/metodologia#evolucion">Cómo se calcula</a>.</p>
<style>
.cmp-slots{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:var(--g-sm)}}
@media (max-width:760px){{.cmp-slots{{grid-template-columns:1fr}}}}
.slot{{position:relative;display:flex;flex-direction:column;gap:4px}}
.slot label{{font-size:var(--fs-cap);font-weight:600;display:flex;align-items:center;gap:6px}}
.slot label i{{display:inline-block;width:12px;height:12px;border-radius:3px}}
.slot input{{font:inherit;min-height:44px;padding:8px 12px;border:1.5px solid var(--line);border-radius:var(--r);background:var(--card);color:var(--fg);width:100%}}
.slot ul{{position:absolute;z-index:40;top:100%;left:0;right:0;margin:4px 0 0;padding:4px;list-style:none;background:var(--card);border:1px solid var(--line);border-radius:var(--r);box-shadow:0 8px 24px rgba(0,0,0,.12);max-height:20rem;overflow:auto}}
.slot li{{display:block;padding:8px 10px;border-radius:6px;cursor:pointer;font-size:var(--fs-cap)}}
.slot li:hover,.slot li[aria-selected="true"]{{background:var(--panel)}}
.slot li[aria-selected="true"]{{outline:2px solid var(--c1);outline-offset:-2px}}
.slot li small{{display:block;color:var(--muted)}}
.cmp-tabla th[scope=col] i{{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}}
</style>
<script>window.CMP_SITE = {json.dumps(self.site)}; window.CMP_TC = {json.dumps({str(k): v for k, v in self.TC.items()})};</script>
<script defer src="/js/comparar.js?v={__import__("hashlib").sha1((self.raiz / "src" / "js" / "comparar.js").read_bytes()).hexdigest()[:10]}"></script>"""
        desc = "Compará lado a lado programas, organismos y provincias del presupuesto nacional: universidades, jubilaciones, rutas, INCAA, PAMI y más, con su evolución desde 2020."
        img = self.og_trabajo("comparar.jpg", kicker="Presupuesto nacional", titulo="Compará programas, organismos y provincias", org="Lado a lado, con la evolución desde 2020",
                              l1="Programas y organismos", n1=miles(len(self.P) + len(self.E)), u1="", l2="Provincias", n2="24", u2="")
        self.pagina("/comparar", "Comparador del presupuesto: programas, organismos y provincias lado a lado", desc, cuerpo,
                    [("Inicio", "/"), ("Comparar", "/comparar")], img, h1="Comparar programas, organismos y provincias")

    # ---------- novedades y RSS ----------
    def novedades(self, lista):
        import email.utils, datetime
        lista = sorted(lista, key=lambda n: n["fecha"], reverse=True)
        items = "".join(f'<li class="card"><span class="note">{fecha(n["fecha"])}</span><h2><a href="{n["link"]}">{e(n["titulo"])}</a></h2><p>{e(n["texto"])}</p></li>' for n in lista)
        from urllib.parse import quote
        feed = self.site + "/novedades.xml"
        suscribir = ('<section class="card prose" id="suscribirse"><h2>Enterate sin tener que entrar</h2>'
                     '<p>Podés seguir las novedades con un lector de noticias (RSS): te avisa solo cuando hay algo nuevo, sin registrarte en este sitio ni dejar tu mail. '
                     'Elegí uno y tocá el botón; si no usás ninguno, Feedly e Inoreader son gratis.</p>'
                     '<div style="display:flex;flex-wrap:wrap;gap:8px;margin:var(--g-sm) 0">'
                     f'<a class="btn" href="https://feedly.com/i/subscription/feed/{quote(feed, safe="")}" target="_blank" rel="noopener">Seguir en Feedly</a>'
                     f'<a class="btn" href="https://www.inoreader.com/?add_feed={quote(feed, safe="")}" target="_blank" rel="noopener">Seguir en Inoreader</a>'
                     '<button class="btn" type="button" data-copiar="feed-url" data-ok="Link copiado" data-evento="rss">Copiar el link del canal</button></div>'
                     f'<label class="note" for="feed-url">Si usás otro lector, pegale este link:</label>'
                     f'<input id="feed-url" readonly value="{e(feed)}" style="font:inherit;width:100%;padding:8px 10px;border:1px solid var(--line);border-radius:var(--r);background:var(--panel);color:var(--fg)" onclick="this.select()">'
                     '</section>')
        cuerpo = ('<p class="sub">Lo nuevo del sitio y cada actualización de los datos. <a href="#suscribirse">¿Querés que te avise cuando haya algo nuevo?</a></p>'
                  f'<ol style="list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:var(--g-sm)">{items}</ol>'
                  + suscribir)
        self.pagina("/novedades", "Novedades: lo nuevo del sitio y las actualizaciones del presupuesto", "Las últimas novedades de Presupuesto Argentina: nuevas secciones y la actualización semanal de la ejecución del presupuesto nacional.",
                    cuerpo, [("Inicio", "/"), ("Novedades", "/novedades")], h1="Novedades")
        def rfc(f):
            d = datetime.datetime.fromisoformat(f + "T12:00:00-03:00")
            return email.utils.format_datetime(d)
        rss = ['<?xml version="1.0" encoding="UTF-8"?>', '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"><channel>',
               "<title>Presupuesto Argentina: novedades</title>", f"<link>{self.site}/novedades</link>",
               f'<atom:link href="{self.site}/novedades.xml" rel="self" type="application/rss+xml"/>',
               "<description>Nuevas secciones y actualizaciones del sitio Presupuesto Argentina.</description>", "<language>es-AR</language>"]
        for n in lista[:30]:
            u = self.site + n["link"]
            rss.append(f'<item><title>{e(n["titulo"])}</title><link>{e(u)}</link><guid isPermaLink="false">{e(n["fecha"] + "-" + slug(n["titulo"]))}</guid><pubDate>{rfc(n["fecha"])}</pubDate><description>{e(n["texto"])}</description></item>')
        rss.append("</channel></rss>")
        (self.raiz / "novedades.xml").write_text("\n".join(rss), encoding="utf-8")

    # ---------- recaudación mensual ----------
    def recaudacion(self):
        R = self.datos.get("recaudacion")
        if not R:
            return
        ipcm = json.loads((self.raiz / "fuentes" / "ipc_indec.json").read_text(encoding="utf-8"))["mensual_2025_2026"]
        S = {k: dict(v) for k, v in R["series"].items()}
        ult = max(S["total"])
        anio, mes = int(ult[:4]), int(ult[5:])
        prev = anio - 1
        meses = [f"{anio}-{m:02d}" for m in range(1, mes + 1)]
        ant = lambda m: f"{prev}-{m[5:]}"
        con_ipc = [m for m in meses if m in ipcm and ant(m) in ipcm]
        def acum(k, ms, a=None):
            return sum(S[k].get(m if a is None else ant(m), 0) for m in ms)
        def real_var(k, ms):
            hoy = acum(k, ms)
            antes = sum(S[k].get(ant(m), 0) * ipcm[m] / ipcm[ant(m)] for m in ms)
            return (hoy / antes - 1) * 100 if antes else None
        t_hoy, t_ant = acum("total", meses), acum("total", meses, True)
        nom = (t_hoy / t_ant - 1) * 100
        rv = real_var("total", con_ipc)
        estim = sum(r["y2026"] for r in self.datos["recursos"]) if anio == 2026 else None
        mes_txt = MESES[mes - 1]
        ult_ipc = MESES[int(con_ipc[-1][5:]) - 1] if con_ipc else ""
        frases = [f"De enero a {mes_txt} de {anio} la Nación recaudó <strong>{plata(t_hoy)}</strong>, {miles(abs(nom))}% {'más' if nom >= 0 else 'menos'} en pesos que en el mismo período de {prev}."]
        if rv is not None:
            frases.append(f"Descontada la inflación (enero a {ult_ipc}), es <strong>{miles(abs(rv), 1)}% {'más' if rv >= 0 else 'menos'}</strong> en términos reales.")
        if estim:
            frases.append(f"Lleva el {pct(t_hoy, estim)} de lo que el proyecto 2027 estima que se recaudará en todo {anio} ({plata(estim)}), con el {miles(mes / 12 * 100)}% del año transcurrido.")
        comp = [("dgi", "Impuestos (DGI): IVA, Ganancias, cheque y otros"), ("dga", "Comercio exterior (Aduana): derechos de exportación e importación"), ("seguridad_social", "Seguridad social: aportes y contribuciones")]
        filas_c = []
        for k, nombre in comp:
            v = real_var(k, con_ipc)
            filas_c.append([e(nombre), dn(acum(k, meses)), dn(acum(k, meses, True)), (f"{'+' if (acum(k, meses) >= acum(k, meses, True)) else '−'}{miles(abs((acum(k, meses) / acum(k, meses, True) - 1) * 100))}%" if acum(k, meses, True) else "—"),
                            (f"{'+' if v >= 0 else '−'}{miles(abs(v), 1)}%" if v is not None else "—")])
        filas_m = []
        for m in meses:
            a = ant(m)
            nv = (S["total"][m] / S["total"][a] - 1) * 100 if S["total"].get(a) else None
            rr = ((S["total"][m] / S["total"][a]) / (ipcm[m] / ipcm[a]) - 1) * 100 if (m in ipcm and a in ipcm and S["total"].get(a)) else None
            filas_m.append([f"{MESES[int(m[5:]) - 1].capitalize()} {m[:4]}", dn(S["total"][m]), dn(S["dgi"].get(m, 0)), dn(S["dga"].get(m, 0)), dn(S["seguridad_social"].get(m, 0)),
                            f"{'+' if nv >= 0 else '−'}{miles(abs(nv))}%" if nv is not None else "—", f"{'+' if rr >= 0 else '−'}{miles(abs(rr), 1)}%" if rr is not None else "s/d"])
        # gráfico: cada mes del año contra el mismo mes del año anterior, en pesos de hoy
        barras = [(m, S["total"][m], S["total"].get(ant(m), 0) * ipcm[m] / ipcm[ant(m)]) for m in con_ipc]
        mx = max(max(b, c) for _, b, c in barras) or 1
        W, base, bw = 560, 200, 560 / len(barras)
        svg = []
        for i, (m, b, c) in enumerate(barras):
            x0 = 6 + i * bw
            for j, (v, col) in enumerate(((c, "var(--mutedbar)"), (b, "var(--c1)"))):
                h = v / mx * 160
                svg.append(f'<rect x="{x0 + bw * (0.12 + j * 0.38):.1f}" y="{base - h:.1f}" width="{bw * 0.36:.1f}" height="{h:.1f}" rx="2" fill="{col}"><title>{MESES[int(m[5:]) - 1]}: {plata(v)}</title></rect>')
            svg.append(f'<text x="{x0 + bw / 2:.1f}" y="{base + 16}" text-anchor="middle" font-size="12" fill="currentColor" opacity=".75">{MESES[int(m[5:]) - 1][:3]}</text>')
        grafico = (f'<figure style="margin:0"><svg viewBox="0 0 {W} 222" width="100%" style="max-width:720px;color:var(--fg)" role="img" aria-label="Recaudación mensual {anio} contra {prev}">{"".join(svg)}'
                   f'<line x1="6" x2="{W - 6}" y1="{base}" y2="{base}" stroke="var(--axis)"/></svg><figcaption class="note"><span style="color:var(--c1)">■</span> {anio} &nbsp; <span style="color:var(--mutedbar)">■</span> {prev}, llevado a pesos del mismo mes de {anio} con el IPC (solo los meses con inflación publicada)</figcaption></figure>')
        cuerpo = [f'<p class="respuesta">{" ".join(frases)}</p>',
                  f'<div class="stats">{stat(f"Recaudado ene-{mes_txt[:3]} {anio}", plata(t_hoy), "pesos corrientes", ink=True, u=self.usd(t_hoy, anio))}{stat("Variación real", (("+" if rv >= 0 else "−") + miles(abs(rv), 1) + "%") if rv is not None else "—", f"contra ene-{ult_ipc[:3]} {prev}")}'
                  + (stat(f"De lo estimado para {anio}", pct(t_hoy, estim), plata(estim) + " en el año", barra=t_hoy / estim * 100) if estim else "") + "</div>",
                  f'<section class="card"><h2>Mes por mes</h2>{grafico}{tabla(["Mes", "Total", "DGI", "Aduana (DGA)", "Seguridad social", "Var. nominal", "Var. real"], filas_m)}</section>',
                  f'<section class="card"><h2>¿De dónde viene?</h2><p class="note">Enero a {mes_txt} de {anio} contra el mismo período de {prev}.</p>{tabla(["Componente", str(anio), str(prev), "Var. nominal", "Var. real"], filas_c)}</section>',
                  f'<div class="caveat">Fuente: Secretaría de Hacienda (Ministerio de Economía), recaudación tributaria mensual, publicada en la API de Series de Tiempo de datos.gob.ar; inflación: IPC del INDEC. La recaudación incluye lo que después se reparte a las provincias por coparticipación. La estimación anual es la que hace el proyecto 2027 para el cierre de {anio}. Se actualiza sola cada mes. <a href="/de-donde-sale">Más sobre los recursos</a>.</div>']
        img = self.og_trabajo("recaudacion.jpg", kicker=f"Recaudación nacional {anio}", titulo="¿Cuánto recauda la Nación?", org=f"Enero a {mes_txt} de {anio}",
                              l1="Recaudado", n1=plata_og(t_hoy)[0], u1=plata_og(t_hoy)[1], l2="Variación real", n2=(("+" if rv >= 0 else "−") + miles(abs(rv), 1) + "%") if rv is not None else "", u2="",
                              fuente="Fuentes: Ministerio de Economía e INDEC")
        desc = f"Recaudación nacional de enero a {mes_txt} de {anio}: {plata(t_hoy)}, comparada con {prev} y descontada la inflación, mes por mes y por componente. Se actualiza cada mes."
        self.pagina("/recaudacion", f"Recaudación nacional {anio} mes a mes: cuánto entra y cómo viene contra {prev}", desc, "\n".join(cuerpo),
                    [("Inicio", "/"), ("De dónde sale la plata", "/de-donde-sale"), ("Recaudación mes a mes", "/recaudacion")], img,
                    self.dataset(f"Recaudación tributaria nacional mensual {prev}-{anio}", desc, "/recaudacion"), h1=f"¿Cuánto recauda la Nación en {anio}?")

    # ---------- glosario ----------
    def glosario(self):
        T = json.loads((self.raiz / "scripts" / "glosario.json").read_text(encoding="utf-8"))
        indice = '<nav class="chips" aria-label="Términos">' + "".join(f'<a href="#{t["id"]}">{e(t["t"])}</a>' for t in T) + "</nav>"
        items = "".join(f'<section class="card" id="{t["id"]}"><h2>{e(t["t"])}</h2><p>{e(t["d"])}</p>'
                        + (f'<p class="note">{e(t["ej"])}</p>' if t.get("ej") else "")
                        + (f'<p class="note"><a href="{t["link"]}">Verlo en el sitio</a></p>' if t.get("link") else "") + "</section>" for t in T)
        ld = {"@context": "https://schema.org", "@type": "DefinedTermSet", "name": "Glosario del presupuesto nacional", "url": self.site + "/glosario", "inLanguage": "es-AR",
              "hasDefinedTerm": [{"@type": "DefinedTerm", "name": t["t"], "description": t["d"], "url": f'{self.site}/glosario#{t["id"]}'} for t in T]}
        self.pagina("/glosario", "Glosario del presupuesto: qué es el devengado, el crédito vigente, el superávit primario y más",
                    "Los términos del presupuesto nacional explicados en castellano simple: devengado, crédito vigente, superávit primario, coparticipación, gasto tributario, fondos fiduciarios y más.",
                    '<p class="sub">Las palabras que aparecen en el presupuesto, explicadas en castellano simple y con un ejemplo de este presupuesto.</p>' + indice + items,
                    [("Inicio", "/"), ("Glosario", "/glosario")], ld_extra=ld, h1="Glosario del presupuesto")

    def todo(self):
        org = defaultdict(list)
        for x in self.P:
            org[x["e"] or x["j"]].append(x)
        for x in self.P:
            hs = sorted((h for h in org[x["e"] or x["j"]] if h is not x), key=lambda h: -((h["a27"] if h["a27"] is not None else h.get("v26", 0)) or 0))
            self.programa(x, hs)
        tipo = defaultdict(list)
        for x in self.E:
            tipo[x["tipo"]].append(x)
        for x in self.E:
            self.ente(x, sorted((h for h in tipo[x["tipo"]] if h is not x), key=lambda h: -h["g27"]))
        self.provincias()
        self.indice()
        if self.HT:
            self.evolucion()
        self.glosario()
        self.ejecucion()
        self.comparar()
        self.recaudacion()
        self.novedades(self.datos.get("novedades", []))
        (self.raiz / "scripts" / ".og-paginas.json").write_text(json.dumps(self.og, ensure_ascii=False), encoding="utf-8")
        return self.urls
