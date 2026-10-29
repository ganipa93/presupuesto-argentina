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
        self.pie = ""

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
<meta name="theme-color" content="#0B1220">
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
{self.cabecera(ruta)}
<main id="contenido" style="display:flex;flex-direction:column;gap:var(--g-lg)">
{migas_html}
{f"<h1>{e(h1 or titulo)}</h1>" if h1 is not False else ""}
{cuerpo}
</main>
<footer class="src">
{self.pie}
<p>Sitio independiente, sin relación con el Gobierno nacional ni con partidos políticos. Montos en pesos corrientes. Fuentes: Proyecto de Presupuesto 2027 y sus datasets (Oficina Nacional de Presupuesto), Ley 27.798 y Presupuesto Abierto (Ministerio de Economía). Datos al {self.fecha_sitio}.</p>
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
:root{{--fg:#0B1220;--mu:#4A5568;--bg:#fff;--li:#E1E5EC;--c1:#2B59FF;--ac:#FF8A3D}}
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
        cuerpo.append('<p class="note">¿Y antes de 2020? En <a href="/historia">el presupuesto desde 1995, gobierno por gobierno</a> está la serie larga, en % del PIB.</p>')
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
        self.historia()
        self.glosario()
        self.ejecucion()
        self.comparar()
        self.recaudacion()
        self.novedades(self.datos.get("novedades", []))
        (self.raiz / "scripts" / ".og-paginas.json").write_text(json.dumps(self.og, ensure_ascii=False), encoding="utf-8")
        return self.urls


# ---------- historia 1995-2027: presupuestos y gobiernos ----------
def _pp(v, dec=1):
    """Porcentaje del PIB como texto («14,5%»)."""
    return "—" if v is None else f"{miles(v, dec)}%"


def _signo(v):
    """Variación con signo («+12%», «−3%»), sin «−0%»."""
    if v is None:
        return "—"
    r = round(v)
    return "0%" if r == 0 else f"{'+' if r > 0 else '−'}{miles(abs(r))}%"


def _cal(k, naranja=False):
    """Clase de color de una celda de mapa de calor (10 tonos de azul u naranja, definidos en estilos.css)."""
    return f'{"o" if naranja else "h"}{max(0, min(9, round(k * 10)))}'


def _puntos(v):
    return "—" if v is None else f"{'+' if v >= 0 else '−'}{miles(abs(v), 1)} pp"


def historia(self):
    H = self.datos.get("historia")
    if not H:
        return
    A = H["anios"]
    por_a = {x["anio"]: x for x in A}
    G = H["gobiernos"]
    R = [(r["id"], r["nombre"]) for r in H["rubros"]]
    T = [(t["id"], t["nombre"]) for t in H["tipos"]]
    pct = lambda x, v: v / x["pib"] * 100 if v is not None and x["pib"] else None
    tot = {a: pct(x, x["gastado"]) for a, x in por_a.items()}
    rub = lambda a, r: pct(por_a[a], por_a[a]["rubros"].get(r, 0))
    de_gob = {a: g for g in G for a in range(g["desde"], g["hasta"] + 1)}
    prim, ult_ej = min(por_a), max(a for a, x in por_a.items() if x["tipo"] == "gastado")
    pico = max((a for a in por_a if a <= ult_ej), key=lambda a: tot[a])
    minimo = min((a for a in por_a if a <= ult_ej), key=lambda a: tot[a])

    def prom(anios, f):
        vals = [f(a) for a in anios if f(a) is not None]
        return sum(vals) / len(vals) if vals else None

    # --- gráfico de barras: gasto total en % del PIB, con franjas por gobierno ---
    def grafico_total():
        anios = sorted(por_a)
        W, base, top, pad = 760, 250, 40, 34
        bw = (W - pad - 8) / len(anios)
        mx = max(tot.values()) * 1.1
        y = lambda v: base - v / mx * (base - top)
        x0 = lambda i: pad + i * bw
        partes = []
        for k, g in enumerate(G):
            ii = [i for i, a in enumerate(anios) if g["desde"] <= a <= g["hasta"]]
            if not ii:
                continue
            xa, xb = x0(ii[0]), x0(ii[-1] + 1)
            if k % 2 == 0:
                partes.append(f'<rect x="{xa:.1f}" y="{top - 30}" width="{xb - xa:.1f}" height="{base - top + 30}" fill="var(--panel)"/>')
            ape = g["nombre"].split()[-1] if g["id"] != "cfk" else "C. Kirchner"
            ape = {"nkirchner": "N. Kirchner", "afernandez": "A. Fernández", "delarua": "De la Rúa"}.get(g["id"], ape)
            partes.append(f'<text x="{(xa + xb) / 2:.1f}" y="{top - 16 if len(ii) > 1 else top - 2}" text-anchor="middle" font-size="{11 if len(ii) > 1 else 9}" fill="currentColor" opacity=".8">{e(ape)}</text>')
        for v in (5, 10, 15, 20, 25):
            if v < mx:
                partes.append(f'<line x1="{pad}" x2="{W - 8}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--line)"/><text x="{pad - 6}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="currentColor" opacity=".7">{v}%</text>')
        for i, a in enumerate(anios):
            x, v = por_a[a], tot[a]
            col = {"gastado": "var(--c1)", "estimado": "var(--mutedbar)", "proyecto": "var(--acc)"}[x["tipo"]]
            h = base - y(v)
            partes.append(f'<rect x="{x0(i) + bw * .15:.1f}" y="{y(v):.1f}" width="{bw * .7:.1f}" height="{h:.1f}" rx="2" fill="{col}"><title>{a}: {_pp(v)} del PIB ({e(x["norma"])})</title></rect>')
            if x["prorroga"]:
                partes.append(f'<circle cx="{x0(i) + bw / 2:.1f}" cy="{y(v) - 6:.1f}" r="3" fill="none" stroke="var(--bad)" stroke-width="1.5"/>')
            if a % 5 == 0 or a in (prim, max(anios)):
                partes.append(f'<text x="{x0(i) + bw / 2:.1f}" y="{base + 15}" text-anchor="middle" font-size="11" fill="currentColor" opacity=".75">{a}</text>')
        desc = "; ".join(f"{a}: {_pp(tot[a])}" for a in anios)
        return (f'<figure style="margin:0"><div style="overflow-x:auto"><svg viewBox="0 0 {W} {base + 22}" width="100%" role="img" aria-label="Gasto de la Administración Nacional en % del PIB. {e(desc)}" style="color:var(--fg);min-width:640px">{"".join(partes)}'
                f'<line x1="{pad}" x2="{W - 8}" y1="{base}" y2="{base}" stroke="var(--axis)"/></svg></div>'
                '<figcaption class="note"><span style="color:var(--c1)">■</span> gastado (devengado) &nbsp; <span style="color:var(--mutedbar)">■</span> 2026: cierre estimado &nbsp; '
                '<span style="color:var(--acc)">■</span> 2027: proyecto &nbsp; <span style="color:var(--bad)">○</span> año con presupuesto prorrogado (sin ley nueva)</figcaption></figure>')

    # --- mini gráficos por rubro ---
    def mini(r, nombre):
        anios = sorted(por_a)
        vals = [rub(a, r) for a in anios]
        mx = max(vals) or 1
        W, H2, pad = 300, 92, 4
        bw = (W - 2 * pad) / len(anios)
        barras = "".join(f'<rect x="{pad + i * bw + bw * .12:.1f}" y="{H2 - 16 - v / mx * 60:.1f}" width="{bw * .76:.1f}" height="{max(.8, v / mx * 60):.1f}" fill="{"var(--c1)" if por_a[a]["tipo"] == "gastado" else "var(--acc)" if por_a[a]["tipo"] == "proyecto" else "var(--mutedbar)"}"><title>{a}: {_pp(v, 2)} del PIB</title></rect>' for i, (a, v) in enumerate(zip(anios, vals)))
        cortes = "".join(f'<line x1="{pad + anios.index(g["desde"]) * bw:.1f}" x2="{pad + anios.index(g["desde"]) * bw:.1f}" y1="10" y2="{H2 - 16}" stroke="var(--line)" stroke-dasharray="2 2"/>' for g in G[1:] if g["desde"] in anios)
        a_max = anios[vals.index(mx)]
        return (f'<div class="card" style="padding:12px"><h3 style="font-size:15px">{e(nombre)}</h3>'
                f'<p class="note" style="margin:2px 0 0">{prim}: {_pp(vals[0])} · máximo {a_max}: {_pp(mx)} · 2027: {_pp(vals[-1])}</p>'
                f'<svg viewBox="0 0 {W} {H2}" width="100%" role="img" aria-label="{e(nombre)} en % del PIB por año" style="color:var(--fg)">{cortes}{barras}'
                f'<text x="{pad}" y="{H2 - 3}" font-size="10" fill="currentColor" opacity=".7">{prim}</text><text x="{W - pad}" y="{H2 - 3}" font-size="10" text-anchor="end" fill="currentColor" opacity=".7">{max(anios)}</text></svg></div>')

    # --- tabla gobierno por gobierno ---
    filas_g, filas_r, filas_t, filas_c, cortos = [], [], [], [], []
    for g in G:
        anios = [a for a in range(g["desde"], g["hasta"] + 1) if a in por_a]
        if not anios:
            continue
        recibio = g["desde"] - 1 if g["desde"] - 1 in por_a else None
        dejo = g["hasta"]
        nombre = f'<strong>{e(g["nombre"])}</strong><br><span class="note">{e(g["periodo"])} · ' + (f'años {anios[0]}-{anios[-1]}' if len(anios) > 1 else f'año {anios[0]}') + '</span>'
        pro = [a for a in anios if por_a[a]["prorroga"]]
        filas_g.append([nombre, _pp(prom(anios, lambda a: tot[a])),
                        (_pp(tot[recibio]) + f' <span class="note">({recibio})</span>') if recibio else "—",
                        _pp(tot[dejo]) + f' <span class="note">({dejo}{", est." if por_a[dejo]["tipo"] != "gastado" else ""})</span>',
                        _puntos(tot[dejo] - tot[recibio]) if recibio else "—",
                        ", ".join(map(str, pro)) or "Ninguno"])
        filas_r.append([prom(anios, lambda a, r=r: rub(a, r)) for r, _ in R] + [prom(anios, lambda a: tot[a])])
        cortos.append(g["nombre"].replace("Cristina Fernández de Kirchner", "C. Kirchner").replace("Néstor Kirchner", "N. Kirchner").replace("Alberto Fernández", "A. Fernández").replace("Fernando de la Rúa", "De la Rúa").split()[-1] if g["id"] not in ("cfk", "nkirchner", "afernandez", "delarua") else {"cfk": "C. Kirchner", "nkirchner": "N. Kirchner", "afernandez": "A. Fernández", "delarua": "De la Rúa"}[g["id"]])
        aa = [a for a in anios if por_a[a]["tipos"]]
        if aa:
            filas_t.append([f'<strong>{e(g["nombre"])}</strong>'] + [_pp(prom(aa, lambda a, t=t: pct(por_a[a], por_a[a]["tipos"].get(t, 0))), 2) for t, _ in T])
        filas_c.append(f'<li><strong>{e(g["nombre"])}</strong> ({e(g["periodo"])}): {e(g.get("contexto", ""))}{(" " + e(g["nota"])) if g.get("nota") else ""}</li>')

    # --- composición: de cada $100 gastados ---
    def composicion():
        filas = []
        colores = ["#1d4f91", "#4f7fc0", "#8fb3e3", "#2f8f6f", "#7cc2a6", "#b9dfcd", "#c9822b", "#e6b45a", "#f2d99a", "#7a5aa6", "#b39ad6", "#8a9099", "#c0392b"]
        for g in G:
            anios = [a for a in range(g["desde"], g["hasta"] + 1) if a in por_a]
            if not anios:
                continue
            sh = [prom(anios, lambda a, r=r: por_a[a]["rubros"].get(r, 0) / por_a[a]["gastado"] * 100) for r, _ in R]
            x, segs = 0.0, []
            for (r, n), v, c in zip(R, sh, colores):
                segs.append(f'<rect x="{x:.2f}" y="0" width="{v:.2f}" height="22" fill="{c}"><title>{e(n)}: ${miles(v)} de cada $100</title></rect>')
                x += v
            filas.append(f'<div style="display:grid;grid-template-columns:minmax(7rem,11rem) 1fr;gap:8px;align-items:center"><span style="font-size:14px">{e(g["nombre"])}</span>'
                         f'<svg viewBox="0 0 100 22" preserveAspectRatio="none" width="100%" height="22" role="img" aria-label="{e(g["nombre"])}: ' +
                         e("; ".join(f"{n} {miles(v)}%" for (r, n), v in zip(R, sh))) + f'">{"".join(segs)}</svg></div>')
        ley = "".join(f'<span style="display:inline-flex;align-items:center;gap:4px;margin-right:10px;font-size:13px"><span style="width:10px;height:10px;background:{c};display:inline-block;border-radius:2px"></span>{e(n)}</span>' for (r, n), c in zip(R, colores))
        return f'<div style="display:flex;flex-direction:column;gap:6px">{"".join(filas)}</div><p class="note" style="margin-top:8px">{ley}</p>'

    # --- ley contra lo modificado y lo gastado ---
    filas_l = []
    for a in sorted(por_a):
        x = por_a[a]
        if x["tipo"] == "proyecto":
            continue
        mod = (x["vigente"] / x["ley"] - 1) * 100 if x.get("vigente") and x.get("ley") else None
        ej = (x["gastado"] / x["ley"] - 1) * 100 if x.get("ley") else None
        filas_l.append([f'{a}{" (est.)" if x["tipo"] == "estimado" else ""}', ("⚠ " if x["prorroga"] else "") + e(x["norma"]),
                        dn(x["ley"]), dn(x["vigente"]), dn(x["gastado"]),
                        _signo(mod), _signo(ej)])

    # --- todos los números, año por año ---
    filas_a = [[str(a) + {"gastado": "", "estimado": " (est.)", "proyecto": " (proy.)"}[por_a[a]["tipo"]], e(de_gob.get(a, {}).get("nombre", "Proyecto 2027" if a == 2027 else "")), dn(por_a[a]["gastado"]),
                dn(por_a[a]["pib"]), _pp(tot[a])] + [_pp(rub(a, r), 2) for r, _ in R] for a in sorted(por_a)]

    # --- mirada larga: Gasto Público Consolidado, 1980-2023 ---
    gpc = {int(a): v for a, v in H["gpc"].get("nacional", {}).items()}
    largo = ""
    if gpc:
        aa = sorted(gpc)
        W, base, top, pad = 760, 230, 50, 34
        bw = (W - pad - 8) / len(aa)
        mx = max(gpc.values()) * 1.1
        y = lambda v: base - v / mx * (base - top)
        pts = " ".join(f"{pad + i * bw + bw / 2:.1f},{y(gpc[a]):.1f}" for i, a in enumerate(aa))
        ejes = "".join(f'<line x1="{pad}" x2="{W - 8}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--line)"/><text x="{pad - 6}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="currentColor" opacity=".7">{v}%</text>' for v in (10, 15, 20, 25) if v < mx)
        etis = "".join(f'<text x="{pad + i * bw + bw / 2:.1f}" y="{base + 15}" text-anchor="middle" font-size="11" fill="currentColor" opacity=".75">{a}</text>' for i, a in enumerate(aa) if a % 5 == 0)
        pres = [(1983, "Alfonsín"), (1989, "Menem"), (1999, "De la Rúa"), (2002, "Duhalde"), (2003, "N. Kirchner"), (2007, "C. Kirchner"), (2015, "Macri"), (2019, "A. Fernández")]
        marcas = "".join(f'<line x1="{pad + aa.index(a) * bw + bw:.1f}" x2="{pad + aa.index(a) * bw + bw:.1f}" y1="{top - 38 + (i % 2) * 13}" y2="{base}" stroke="var(--axis)" stroke-dasharray="3 3" opacity=".6"/>'
                         f'<text x="{pad + aa.index(a) * bw + bw + 3:.1f}" y="{top - 28 + (i % 2) * 13}" font-size="10" fill="currentColor" opacity=".75">{n}</text>' for i, (a, n) in enumerate(pres) if a in aa)
        puntos = "".join(f'<circle cx="{pad + i * bw + bw / 2:.1f}" cy="{y(gpc[a]):.1f}" r="2.5" fill="var(--c1)"><title>{a}: {_pp(gpc[a])} del PIB</title></circle>' for i, a in enumerate(aa))
        largo = (f'<section class="hx-card"><h2>La mirada larga: 1980 a 2023</h2>'
                 f'<p>Para ver más atrás que 1995 hay otra serie oficial, el <strong>Gasto Público Consolidado</strong> del Ministerio de Economía. Mide algo más amplio que el presupuesto de la Administración Nacional (suma, por ejemplo, el PAMI, las obras sociales nacionales y los fondos fiduciarios), así que sus porcentajes son más altos y no se deben mezclar con los de arriba. Sirve para ver la tendencia: el gasto nacional pasó de {_pp(gpc[aa[0]])} del PIB en {aa[0]} a {_pp(gpc[aa[-1]])} en {aa[-1]}, con su mínimo en {min(gpc, key=gpc.get)} ({_pp(min(gpc.values()))}) y su máximo en {max(gpc, key=gpc.get)} ({_pp(max(gpc.values()))}).</p>'
                 f'<figure style="margin:0"><div style="overflow-x:auto"><svg viewBox="0 0 {W} {base + 22}" width="100%" role="img" aria-label="Gasto público nacional en % del PIB, {aa[0]}-{aa[-1]}" style="color:var(--fg);min-width:640px">{ejes}{marcas}'
                 f'<polyline points="{pts}" fill="none" stroke="var(--c1)" stroke-width="2"/>{puntos}{etis}<line x1="{pad}" x2="{W - 8}" y1="{base}" y2="{base}" stroke="var(--axis)"/></svg></div>'
                 '<figcaption class="note">Gasto público nacional en % del PIB. Las líneas marcan el último año completo antes de cada cambio de gobierno. Fuente: Ministerio de Economía, Gasto Público Consolidado (API de Series de Tiempo, datos.gob.ar).</figcaption></figure></section>')


    # --- contra el tamaño de la economía: PIB real, población y gasto real ---
    def economia():
        if not all(x.get("pib_real") and x.get("poblacion") for x in A):
            return ""
        ref = ult_ej
        dref = por_a[ref]["pib"] / por_a[ref]["pib_real"]  # deflactor del PIB del año de referencia
        greal = {a: x["gastado"] / (x["pib"] / x["pib_real"]) * dref for a, x in por_a.items()}  # millones de pesos de ref
        ghab = {a: greal[a] * 1e6 / por_a[a]["poblacion"] for a in por_a}
        pibhab = {a: por_a[a]["pib_real"] / por_a[a]["poblacion"] for a in por_a}
        anios = sorted(por_a)
        i_pib = {a: por_a[a]["pib_real"] / por_a[prim]["pib_real"] * 100 for a in anios}
        i_gas = {a: greal[a] / greal[prim] * 100 for a in anios}
        W, base, top, pad = 760, 240, 20, 40
        bw = (W - pad - 8) / len(anios)
        mx = max(max(i_pib.values()), max(i_gas.values())) * 1.08
        y = lambda v: base - v / mx * (base - top)
        cx = lambda i: pad + i * bw + bw / 2
        partes = []
        for k, g in enumerate(G):
            ii = [i for i, a in enumerate(anios) if g["desde"] <= a <= g["hasta"]]
            if ii and k % 2 == 0:
                partes.append(f'<rect x="{pad + ii[0] * bw:.1f}" y="{top}" width="{len(ii) * bw:.1f}" height="{base - top}" fill="var(--panel)"/>')
        for v in (50, 100, 150, 200, 250, 300):
            if v < mx:
                partes.append(f'<line x1="{pad}" x2="{W - 8}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="var(--line)"{" stroke-dasharray=\"4 3\"" if v == 100 else ""}/><text x="{pad - 6}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="11" fill="currentColor" opacity=".7">{v}</text>')
        for serie, col, nombre in ((i_pib, "var(--acc)", "PIB real"), (i_gas, "var(--c1)", "Gasto nacional real")):
            pts = " ".join(f"{cx(i):.1f},{y(serie[a]):.1f}" for i, a in enumerate(anios))
            partes.append(f'<polyline points="{pts}" fill="none" stroke="{col}" stroke-width="2.5"/>')
            partes += [f'<circle cx="{cx(i):.1f}" cy="{y(serie[a]):.1f}" r="2.5" fill="{col}"><title>{a}: {nombre} {miles(serie[a])} ({prim} = 100)</title></circle>' for i, a in enumerate(anios)]
        partes += [f'<text x="{cx(i):.1f}" y="{base + 15}" text-anchor="middle" font-size="11" fill="currentColor" opacity=".75">{a}</text>' for i, a in enumerate(anios) if a % 5 == 0 or a == anios[-1]]
        grafico = (f'<figure style="margin:0"><div style="overflow-x:auto"><svg viewBox="0 0 {W} {base + 22}" width="100%" role="img" aria-label="Índice {prim} = 100 del PIB real y del gasto nacional real" style="color:var(--fg);min-width:640px">{"".join(partes)}'
                   f'<line x1="{pad}" x2="{W - 8}" y1="{base}" y2="{base}" stroke="var(--axis)"/></svg></div>'
                   f'<figcaption class="note"><span style="color:var(--acc)">■</span> tamaño de la economía (PIB real) &nbsp; <span style="color:var(--c1)">■</span> gasto nacional real · índice {prim} = 100 · 2026 y 2027 con el crecimiento y el gasto que estima el Proyecto 2027</figcaption></figure>')
        filas = []
        for g in G:
            aa = [a for a in range(g["desde"], g["hasta"] + 1) if a in por_a]
            if not aa:
                continue
            ini = g["desde"] - 1 if g["desde"] - 1 in por_a else g["desde"]
            fin = g["hasta"]
            n = fin - ini
            crec = ((por_a[fin]["pib_real"] / por_a[ini]["pib_real"]) ** (1 / n) - 1) * 100 if n else None
            filas.append([f'<strong>{e(g["nombre"])}</strong><br><span class="note">{ini}→{fin}{" (est.)" if por_a[fin]["tipo"] != "gastado" else ""}</span>',
                          (f"{'+' if crec >= 0 else '−'}{miles(abs(crec), 1)}%" if crec is not None else "—"),
                          _signo((pibhab[fin] / pibhab[ini] - 1) * 100) if n else "—",
                          f'<span data-n="{round(prom(aa, lambda a: ghab[a]))}">${miles(prom(aa, lambda a: ghab[a]))}</span>',
                          _signo((ghab[fin] / ghab[ini] - 1) * 100) if n else "—"])
        c_pib = (por_a[ref]["pib_real"] / por_a[prim]["pib_real"] - 1) * 100
        c_hab = (pibhab[ref] / pibhab[prim] - 1) * 100
        c_ghab = (ghab[ref] / ghab[prim] - 1) * 100
        pico_g = max((a for a in anios if a <= ref), key=lambda a: ghab[a])
        return (f'<section class="card" id="economia"><h2>Contra el tamaño de la economía</h2>'
                f'<p>El % del PIB dice qué parte de la torta se lleva el Estado nacional, pero no el tamaño de la torta: no es lo mismo gastar el 15% de una economía chica que el 15% de una grande. '
                f'Por eso acá se mira también la economía en términos reales. Entre {prim} y {ref} el PIB real creció <strong>{miles(c_pib)}%</strong>, pero la población también creció y el PIB por habitante aumentó <strong>{miles(c_hab)}%</strong>. '
                f'Medido así, el gasto nacional por habitante de {ref} fue {miles(abs(c_ghab))}% {"más" if c_ghab >= 0 else "menos"} que el de {prim}, y su máximo fue en {pico_g}.</p>'
                f'{grafico}'
                f'{tabla(["Gobierno", "Crecimiento del PIB (promedio anual)", "PIB por habitante (cambio)", f"Gasto nacional por habitante (promedio, pesos de {ref})", "Gasto por habitante (cambio)"], filas, "libre")}'
                f'<p class="note">El PIB real y el gasto real se calculan con el índice de precios implícitos del PIB del INDEC (no con el IPC), y los pesos de cada año se llevan a pesos de {ref}. «Cambio» compara el último año del gobierno anterior con el último propio; para Menem, la serie arranca en {prim}. '
                f'El PIB mide lo que se produce en el país; no muestra cuánto de eso es industria o qué parte de lo que se consume se importa. <a href="/metodologia#historia">Cómo se calcula</a>.</p></section>')


    # ======== diseño nuevo (hx) ========
    corto = {"cfk": "C. Kirchner", "nkirchner": "N. Kirchner", "afernandez": "A. Fernández", "delarua": "De la Rúa"}
    corto_de = lambda g: corto.get(g["id"], g["nombre"].split()[-1])
    anios_all = sorted(por_a)
    tipo_txt = {"gastado": "gastado", "estimado": "cierre estimado", "proyecto": "proyecto de ley"}

    def hx_chart():
        mx = max(tot.values()) * 1.08
        botones, etis = [], []
        for a in anios_all:
            x = por_a[a]
            g = de_gob.get(a)
            info = f'{a}|{_pp(tot[a])}|{tipo_txt[x["tipo"]]}|{g["nombre"] if g else "Proyecto del gobierno actual"}|{x["norma"]}'
            botones.append(f'<button type="button" data-t="{x["tipo"]}"' + (' data-p' if x["prorroga"] else "") + f' data-info="{e(info)}" aria-pressed="{"true" if a == ult_ej else "false"}"'
                           f' style="height:{tot[a] / mx * 100:.1f}%" aria-label="{a}: {_pp(tot[a])} del PIB, {tipo_txt[x["tipo"]]}" title="{a}: {_pp(tot[a])} del PIB"></button>')
            etis.append(f'<span>{a if a % 5 == 0 or a == anios_all[-1] else ""}</span>')
        strip = "".join(f'<span style="flex:{len([a for a in anios_all if g["desde"] <= a <= g["hasta"]])} 1 0">{e(corto_de(g))}</span>' for g in G) + '<span style="flex:1 1 0">2027</span>'
        x = por_a[ult_ej]
        sel = (f'<div class="hx-sel" id="hx-sel" aria-live="polite"><b>{ult_ej}</b><div><span><strong>{_pp(tot[ult_ej])}</strong> del PIB · {tipo_txt[x["tipo"]]}</span>'
               f'<span>{e(de_gob[ult_ej]["nombre"])} · {e(x["norma"])}</span></div></div>')
        js = ("<script>(function(){var b=document.querySelectorAll('.hx-bars button'),s=document.getElementById('hx-sel'),w=document.querySelector('#total .hx-scroll');if(w)w.scrollLeft=w.scrollWidth;"
              "b.forEach(function(x){x.addEventListener('click',function(){b.forEach(function(y){y.setAttribute('aria-pressed','false')});x.setAttribute('aria-pressed','true');"
              "var d=x.dataset.info.split('|');s.children[0].textContent=d[0];var l=s.children[1].children;l[0].innerHTML='<strong>'+d[1]+'</strong> del PIB · '+d[2];l[1].textContent=d[3]+' · '+d[4];});});})();</script>")
        return (f'<div class="hx-scroll"><div class="hx-chart"><div class="hx-bars" role="group" aria-label="Gasto por año en % del PIB">{"".join(botones)}</div>'
                f'<div class="hx-years" aria-hidden="true">{"".join(etis)}</div><div class="hx-strip" aria-hidden="true">{strip}</div></div></div>{sel}{js}')

    def hx_govs():
        ref = ult_ej
        dref = por_a[ref]["pib"] / por_a[ref]["pib_real"] if por_a[ref].get("pib_real") else None
        tarj = []
        for g in G:
            aa = [a for a in range(g["desde"], g["hasta"] + 1) if a in por_a]
            if not aa:
                continue
            ini = g["desde"] - 1 if g["desde"] - 1 in por_a else None
            fin = g["hasta"]
            base = ini if ini else g["desde"]
            n = fin - base
            d = tot[fin] - tot[ini] if ini else None
            crec = ((por_a[fin]["pib_real"] / por_a[base]["pib_real"]) ** (1 / n) - 1) * 100 if n and dref else None
            ghab = prom(aa, lambda a: por_a[a]["gastado"] / (por_a[a]["pib"] / por_a[a]["pib_real"]) * dref * 1e6 / por_a[a]["poblacion"]) if dref else None
            pro = [str(a) for a in aa if por_a[a]["prorroga"]]
            tarj.append(
                f'<article class="hx-gov"><div><h3>{e(g["nombre"])}</h3><span class="per">{e(g["periodo"])} · ' + (f'años {aa[0]}-{aa[-1]}' if len(aa) > 1 else f'año {aa[0]}') + '</span></div>'
                f'<div class="hx-flow"><span class="de">{(_pp(tot[ini]) + f" ({ini})") if ini else f"desde {prim}"}</span>'
                '<svg width="22" height="12" viewBox="0 0 22 12" aria-hidden="true"><path d="M1 6h18m-5-5 5 5-5 5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'
                f'<span class="a">{_pp(tot[fin])}</span>' + (f'<span class="hx-pill{" baja" if d < 0 else ""}">{_puntos(d)}</span>' if d is not None else "") + '</div>'
                f'<div class="hx-dos"><div>Economía por año<b>{(("+" if crec >= 0 else "−") + miles(abs(crec), 1) + "%") if crec is not None else "—"}</b></div>'
                f'<div>Gasto por habitante<b>{("$" + miles(ghab / 1e6, 2) + " M") if ghab else "—"}</b></div></div>'
                + (f'<div class="hx-dos"><div>Resultado financiero<b>{_pp(prom(aa, lambda a: pct(por_a[a], por_a[a]["res_fin"])), 1)} del PIB</b></div><div>Años con superávit<b>{len([a for a in aa if a <= ult_ej and por_a[a]["res_fin"] > 0])} de {len([a for a in aa if a <= ult_ej])}</b></div></div>' if all(por_a[a].get("res_fin") is not None for a in aa) else "")
                + (f'<div class="hx-dos"><div>Industria<b>{_pp(prom(ae, lambda a: por_a[a]["eco"]["industria"]))} del PIB</b></div><div>Desempleo en {ae[-1]}<b>{_pp(por_a[ae[-1]]["eco"]["desempleo"])}</b></div></div>' if (ae := [a for a in aa if por_a[a].get("eco")]) else "")
                + (f'<span class="hx-pro">Sin ley nueva en {", ".join(pro)}</span>' if pro else "")
                + (f'<p class="hx-ctx">{e(g.get("contexto", ""))}</p>' if g.get("contexto") else "") + '</article>')
        return f'<div class="hx-govs">{"".join(tarj)}</div>'

    def hx_heat():
        cab = "".join(f'<th scope="col">{e(corto_de(g))}</th>' for g in G)
        filas = []
        for j, (r, n) in enumerate(R + [("total", "Total")]):
            vals = [f[j] for f in filas_r]
            mx_ = max(v for v in vals if v is not None)
            celdas = []
            for v in vals:
                k = 0.08 + 0.82 * (v / mx_ if mx_ else 0)
                celdas.append(f'<td class="{_cal(k)}"><span data-n="{v:.2f}">{_pp(v, 2 if r != "total" else 1)}</span></td>')
            filas.append(f'<tr><th scope="row">{"<strong>Total</strong>" if r == "total" else e(n)}</th>{"".join(celdas)}</tr>')
        return f'<div class="hx-scroll"><table class="hx-heat"><thead><tr><th scope="col" style="text-align:left">Rubro</th>{cab}</tr></thead><tbody>{"".join(filas)}</tbody></table></div>'

    def hx_eco():
        if not all(x.get("pib_real") and x.get("poblacion") for x in A):
            return ""
        ref = ult_ej
        dref = por_a[ref]["pib"] / por_a[ref]["pib_real"]
        greal = {a: x["gastado"] / (x["pib"] / x["pib_real"]) * dref for a, x in por_a.items()}
        ghab = {a: greal[a] * 1e6 / por_a[a]["poblacion"] for a in por_a}
        pibhab = {a: por_a[a]["pib_real"] / por_a[a]["poblacion"] for a in por_a}
        ip = {a: por_a[a]["pib_real"] / por_a[prim]["pib_real"] * 100 for a in anios_all}
        ig = {a: greal[a] / greal[prim] * 100 for a in anios_all}
        top = max(max(ip.values()), max(ig.values())) * 1.08
        X = lambda i: 40 + i * 950 / (len(anios_all) - 1)
        Yy = lambda v: 270 - v / top * 250
        pts = lambda d: " ".join(f"{X(i):.1f},{Yy(d[a]):.1f}" for i, a in enumerate(anios_all))
        lineas = "".join(f'<line x1="40" x2="990" y1="{Yy(v):.1f}" y2="{Yy(v):.1f}" stroke="#24304A"{" stroke-dasharray=\"4 4\"" if v == 100 else ""}/><text x="32" y="{Yy(v) + 4:.1f}" text-anchor="end" font-size="12" fill="#AEB8CE">{v}</text>' for v in (100, 200, 300) if v < top)
        etis = "".join(f'<text x="{X(i):.1f}" y="292" font-size="12" fill="#AEB8CE" text-anchor="middle">{a}</text>' for i, a in enumerate(anios_all) if a % 5 == 0 or a == anios_all[-1])
        puntos = "".join(f'<circle cx="{X(i):.1f}" cy="{Yy(d[a]):.1f}" r="3" fill="{c}"><title>{a}: {n} {miles(d[a])}</title></circle>' for d, c, n in ((ip, "#FF8A3D", "PIB real"), (ig, "#7FA0FF", "gasto real")) for i, a in enumerate(anios_all))
        c_pib = (por_a[ref]["pib_real"] / por_a[prim]["pib_real"] - 1) * 100
        c_hab = (pibhab[ref] / pibhab[prim] - 1) * 100
        c_g = (ghab[ref] / ghab[prim] - 1) * 100
        pico_g = max((a for a in anios_all if a <= ref), key=lambda a: ghab[a])
        sg = lambda v: ("+" if v >= 0 else "−") + miles(abs(v)) + "%"
        return (f'<section class="hx-dark" id="economia"><div class="hx-head"><div><h2>Contra el tamaño de la economía</h2>'
                f'<p>El % del PIB dice qué parte de la torta se lleva el Estado nacional, pero no el tamaño de la torta: no es lo mismo gastar el 15% de una economía chica que de una grande. Las dos líneas, sin inflación, con {prim} = 100.</p></div>'
                '<div class="hx-ley"><span><i style="background:#FF8A3D"></i>Economía (PIB real)</span><span><i style="background:#7FA0FF"></i>Gasto nacional real</span></div></div>'
                f'<figure style="margin:0" class="hx-scroll"><svg viewBox="0 0 1000 300" width="100%" style="min-width:640px;display:block" role="img" aria-label="Índice {prim} = 100 del PIB real y del gasto nacional real">{lineas}'
                f'<polyline points="{pts(ip)}" fill="none" stroke="#FF8A3D" stroke-width="3" stroke-linejoin="round"/><polyline points="{pts(ig)}" fill="none" stroke="#7FA0FF" stroke-width="3" stroke-linejoin="round"/>{puntos}{etis}</svg></figure>'
                f'<div class="hx-trio"><div><b>{sg(c_pib)}</b>creció la economía entre {prim} y {ref}</div><div><b>{sg(c_hab)}</b>el PIB por habitante, porque la población también creció</div>'
                f'<div><b>{sg(c_g)}</b>el gasto nacional por habitante de {ref} contra {prim}; su máximo fue en {pico_g}</div></div>'
                f'<p class="note">Sin inflación: con el índice de precios implícitos del PIB del INDEC (no con el IPC). 2026 y 2027, con el crecimiento y el gasto que estima el Proyecto 2027. Cuánto de eso es industria y cuánto se importa está en <a href="#produccion">qué economía había detrás</a>. <a href="/metodologia#historia">Cómo se calcula</a>.</p></section>')


    def hx_fiscal():
        aa = [a for a in anios_all if por_a[a].get("res_prim") is not None]
        if not aa:
            return ""
        rp = {a: pct(por_a[a], por_a[a]["res_prim"]) for a in aa}
        rf = {a: pct(por_a[a], por_a[a]["res_fin"]) for a in aa}
        mx = max(abs(v) for v in list(rp.values()) + list(rf.values())) or 1

        def celda(v):
            k = 0.12 + 0.78 * min(1, abs(v) / mx)
            return f'<td class="{_cal(k, v < 0)}" title="{_pp(v)} del PIB"><span data-n="{v:.2f}">{miles(0 if round(v, 1) == 0 else v, 1)}</span></td>'
        fila_gob = []
        for g in G:
            n = len([a for a in aa if g["desde"] <= a <= g["hasta"]])
            if n:
                fila_gob.append(f'<th scope="colgroup" colspan="{n}" class="gob">{e(corto_de(g))}</th>')
        n27 = len([a for a in aa if a > G[-1]["hasta"]])
        if n27:
            fila_gob.append(f'<th scope="colgroup" colspan="{n27}" class="gob">Proy.</th>')
        cab = "".join(f'<th scope="col">{str(a)[2:] if a % 5 else a}</th>' for a in aa)
        tabla_h = (f'<div class="hx-scroll"><table class="hx-heat hx-fis"><thead><tr><th></th>{"".join(fila_gob)}</tr><tr><th scope="col" style="text-align:left">% del PIB</th>{cab}</tr></thead><tbody>'
                   f'<tr><th scope="row">Resultado primario<br><span class="note">sin contar intereses</span></th>{"".join(celda(rp[a]) for a in aa)}</tr>'
                   f'<tr><th scope="row">Resultado financiero<br><span class="note">con intereses de la deuda</span></th>{"".join(celda(rf[a]) for a in aa)}</tr></tbody></table></div>')
        filas = []
        for g in G:
            ag = [a for a in aa if g["desde"] <= a <= g["hasta"]]
            if not ag:
                continue
            cer = [a for a in ag if a <= ult_ej]
            sup = len([a for a in cer if rf[a] > 0])
            filas.append([f'<strong>{e(g["nombre"])}</strong>', _pp(prom(ag, lambda a: rp[a]), 1), _pp(prom(ag, lambda a: rf[a]), 1), f"{sup} de {len(cer)}" + (" (sin contar 2026)" if len(cer) < len(ag) else "")])
        sup_total = len([a for a in aa if a <= ult_ej and rf[a] > 0])
        n_total = len([a for a in aa if a <= ult_ej])
        return (f'<section class="hx-card" id="resultado"><div class="hx-head"><div><h2>¿Gastó más de lo que recaudó?</h2>'
                f'<p>Gastar mucho o poco no es bueno ni malo por sí solo: depende de cuánto entra y de cómo se paga la diferencia. Cuando el Estado gasta más de lo que recauda (déficit), lo cubre con deuda o con emisión de dinero; cuando recauda más (superávit), puede pagar deuda o ahorrar. '
                f'Entre {aa[0]} y {ult_ej}, el Estado nacional terminó con superávit financiero en {sup_total} de {n_total} años.</p></div>'
                '<div class="hx-ley"><span><i style="background:#2B59FF"></i>Superávit (entró más de lo que salió)</span><span><i style="background:#FF8A3D"></i>Déficit (salió más de lo que entró)</span></div></div>'
                f'{tabla_h}'
                f'<h3 style="margin-top:8px">Promedio de cada gobierno, en % del PIB</h3>{tabla(["Gobierno", "Resultado primario", "Resultado financiero", "Años con superávit financiero"], filas, "libre")}'
                '<p class="note">El resultado <strong>primario</strong> compara lo que entra con lo que se gasta sin contar los intereses de la deuda; el <strong>financiero</strong> los suma, y es la cifra que dice si hubo que pedir prestado o emitir. '
                'Datos del Sector Público Nacional en base caja (Secretaría de Hacienda), que abarca más que el presupuesto de la Administración Nacional de arriba. Para comparar años se usa el resultado sin las utilidades del BCRA ni las rentas del FGS, que hasta 2014 se contaban como ingresos y mejoraban el número; desde 2015 la metodología oficial ya las excluye. '
                '2026 y 2027: lo que estima y propone el Proyecto 2027 para la Administración Nacional. <a href="/metodologia#historia">Cómo se calcula</a>.</p></section>')

    def hx_prod():
        aa = [a for a in anios_all if por_a[a].get("eco")]
        if not aa:
            return ""
        ev = lambda a, k: por_a[a].get("eco", {}).get(k)
        u = max(aa)
        # (clave, nombre, aclaración, formato, divergente)
        F1 = lambda v: miles(v, 1)
        grupos = [
            ("Qué se produce", [
                ("industria", "Industria", "% del PIB", F1, False),
                ("industria_real_hab", "Producción industrial por habitante", f"sin inflación, {aa[0]} = 100", lambda v: miles(v), False),
                ("agro", "Agro y pesca", "% del PIB", F1, False),
                ("mineria", "Minería, petróleo y gas", "% del PIB", F1, False),
                ("construccion", "Construcción", "% del PIB", F1, False)]),
            ("Comercio con el mundo", [
                ("exportaciones", "Exportaciones", "% del PIB", F1, False),
                ("importaciones", "Importaciones", "% del PIB", F1, False),
                ("saldo_usd", "Saldo comercial", "miles de millones de dólares", lambda v: miles(0 if round(v / 1000, 1) == 0 else v / 1000, 1), True),
                ("moi", "Manufacturas industriales", "% de lo exportado", lambda v: miles(v), False),
                ("bk", "Bienes de capital y piezas", "% de lo importado", lambda v: miles(v), False)]),
            ("Inversión y trabajo", [
                ("inversion", "Inversión", "% del PIB", F1, False),
                ("inv_equipo", "…en maquinaria y equipo", "% del PIB", F1, False),
                ("desempleo", "Desempleo", "% de la población activa", F1, False)]),
        ]

        def celda(v, lo, hi, div):
            if v is None:
                return '<td class="nd">—</td>'
            if div:
                m = max(abs(lo), abs(hi)) or 1
                k = 0.12 + 0.78 * min(1, abs(v) / m)
            else:
                k = 0.06 + 0.84 * ((v - lo) / (hi - lo) if hi > lo else 0)
            return f'<td class="{_cal(k, div and v < 0)}" title="{v:.1f}"><span data-n="{v:.2f}">{{}}</span></td>'
        fila_gob = []
        for g in G:
            n = len([a for a in aa if g["desde"] <= a <= g["hasta"]])
            if n:
                fila_gob.append(f'<th scope="colgroup" colspan="{n}" class="gob">{e(corto_de(g))}</th>')
        cab = "".join(f'<th scope="col">{str(a)[2:] if a % 5 else a}</th>' for a in aa)
        cuerpo_t = []
        for gn, filas_ in grupos:
            cuerpo_t.append(f'<tr class="grupo"><th scope="rowgroup" colspan="{len(aa) + 1}">{e(gn)}</th></tr>')
            for k, n, ac, fmt, div in filas_:
                vals = [ev(a, k) for a in aa]
                ok = [x for x in vals if x is not None]
                lo, hi = min(ok), max(ok)
                cuerpo_t.append(f'<tr><th scope="row">{e(n)}<br><span class="note">{e(ac)}</span></th>' + "".join(celda(x, lo, hi, div).replace("{}", fmt(x)) if x is not None else celda(None, 0, 0, div) for x in vals) + '</tr>')
        tabla_h = (f'<div class="hx-scroll"><table class="hx-heat hx-fis hx-prod"><thead><tr><th></th>{"".join(fila_gob)}</tr><tr><th scope="col" style="text-align:left">Indicador</th>{cab}</tr></thead>'
                   f'<tbody>{"".join(cuerpo_t)}</tbody></table></div>')
        filas = []
        for g in G:
            ag = [a for a in aa if g["desde"] <= a <= g["hasta"]]
            if not ag:
                continue
            ini = g["desde"] - 1 if g["desde"] - 1 in aa else ag[0]
            fin = ag[-1]
            ih = lambda a: ev(a, "industria_real_hab")
            sal = sum(ev(a, "saldo_usd") for a in ag if ev(a, "saldo_usd") is not None)
            filas.append([f'<strong>{e(g["nombre"])}</strong><br><span class="note">{ini}→{fin}</span>',
                          _pp(prom(ag, lambda a: ev(a, "industria"))),
                          _signo((ih(fin) / ih(ini) - 1) * 100) if ini != fin else "—",
                          _pp(prom(ag, lambda a: ev(a, "inversion"))),
                          _pp(prom(ag, lambda a: ev(a, "importaciones"))),
                          f'<span data-n="{sal:.0f}">{"+" if sal >= 0 else "−"}US$ {miles(abs(sal) / 1000, 1)} mil M</span>',
                          f'{_pp(ev(ini, "desempleo"))} → {_pp(ev(fin, "desempleo"))}'])
        ind, ihab = {a: ev(a, "industria") for a in aa}, {a: ev(a, "industria_real_hab") for a in aa}
        i_max = max(aa, key=lambda a: ihab[a])
        d_max = max(aa, key=lambda a: ev(a, "desempleo"))
        d_min = min(aa, key=lambda a: ev(a, "desempleo"))
        js = "<script>document.querySelectorAll('.hx-scroll').forEach(function(w){if(w.querySelector('.hx-fis'))w.scrollLeft=w.scrollWidth});</script>"
        return (f'<section class="hx-card" id="produccion"><div class="hx-head"><div><h2>Qué economía había detrás</h2>'
                f'<p>El mismo gasto no pesa igual en una economía con fábricas trabajando que en una que importa casi todo, o con 7% de desempleo que con 18%. Acá está, año por año, qué se producía, cuánto se compraba y vendía al mundo, cuánto se invertía y cuánta gente buscaba trabajo sin encontrarlo. '
                f'La producción industrial por habitante de {u} quedó en {miles(ihab[u])} ({aa[0]} = 100): su máximo fue en {i_max} ({miles(ihab[i_max])}). El desempleo más alto de la serie fue en {d_max} ({_pp(ev(d_max, "desempleo"))}) y el más bajo, en {d_min} ({_pp(ev(d_min, "desempleo"))}).</p></div>'
                '<div class="hx-ley"><span><i style="background:#2B59FF"></i>Más alto en la fila</span><span><i style="background:#E6ECFF"></i>Más bajo en la fila</span><span><i style="background:#FF8A3D"></i>Saldo comercial negativo</span></div></div>'
                f'<p class="hx-sub">Cada fila se colorea contra sus propios años: más oscuro no quiere decir mejor ni peor, solo más alto. Los datos llegan hasta {u}; 2026 y 2027 todavía no tienen cifras cerradas.</p>'
                f'{tabla_h}'
                f'<h3 style="margin-top:8px">Cada gobierno</h3>{tabla(["Gobierno", "Industria (% del PIB, promedio)", "Producción industrial por habitante (cambio)", "Inversión (% del PIB, promedio)", "Importaciones (% del PIB, promedio)", "Saldo comercial (suma de sus años)", "Desempleo (recibió → dejó)"], filas, "libre")}'
                '<p class="note">Los porcentajes del PIB se miden a precios de cada año, así que también se mueven con los precios relativos: con la devaluación de 2002, por ejemplo, exportaciones, industria y agro pasan a valer más pesos y su parte del PIB salta aunque no se haya producido más. Por eso se agrega la producción industrial <strong>sin inflación</strong> por habitante, que mide cantidades. '
                '«Cambio» compara el último año del gobierno anterior con el último propio (Menem arranca en 1995 y Milei llega hasta 2025). El desempleo sale de dos encuestas distintas: la EPH puntual hasta 2002 y la EPH continua desde 2003, que no son del todo comparables; en 2015 promedia los trimestres que se publicaron. '
                'INDEC advierte que las series que publicó entre 2007 y 2015 deben tomarse con reservas; las de cuentas nacionales se revisaron en 2016 y son las que se usan acá. '
                'Fuente: INDEC (cuentas nacionales, bases 1993 y 2004 empalmadas en 2004; Intercambio Comercial Argentino, en dólares; Encuesta Permanente de Hogares), vía la API de Series de Tiempo de datos.gob.ar. <a href="/metodologia#historia">Cómo se calcula</a>.</p></section>' + js)

    # --- frase principal (solo hechos) ---
    p27 = tot.get(2027)
    frase = (f'En {prim} el Estado nacional gastó el equivalente a <strong>{_pp(tot[prim])} del PIB</strong>. Ese número subió hasta <strong>{_pp(tot[pico])} en {pico}</strong>, '
             f'el máximo de la serie, y en {ult_ej} fue de <strong>{_pp(tot[ult_ej])}</strong>' + (f'; para 2027 el proyecto prevé {_pp(p27)}.' if p27 else '.') +
             ' Acá está cómo se movió el presupuesto con cada gobierno, en qué se gastó y cuánto se respetó la ley que aprobó el Congreso.')

    cab_r = ["Rubro"] + cortos
    filas_rt = []
    for j, (r, n) in enumerate(R + [("total", "Total")]):
        vals = [f[j] for f in filas_r]
        mx_ = max(v for v in vals if v is not None)
        filas_rt.append([("<strong>Total</strong>" if r == "total" else e(n))] + [(f"<strong>{_pp(v, 2 if r != 'total' else 1)}</strong>" if v == mx_ else _pp(v, 2 if r != "total" else 1)) for v in vals])
    cuerpo = [
        '<div class="hx">',
        f'<section class="hx-hero"><div><span class="hx-kick">Presupuesto nacional · {prim} a 2027</span><h1>Tres décadas de gasto público, gobierno por gobierno</h1>'
        f'<p>De Menem a Milei: cuánto gastó el Estado nacional cada año, en qué, cuánto respetó la ley del Congreso y cómo se compara con el tamaño de la economía. Con datos oficiales.</p></div>'
        f'<div class="hx-big"><span>Máximo de la serie · {pico}</span><b>{miles(tot[pico], 1)}<i>%</i></b><span>del PIB gastó la Administración Nacional ese año. En {ult_ej} fue {_pp(tot[ult_ej])}.</span></div></section>',
        '<div class="hx-stats">' + "".join(f'<div class="hx-stat">{k}<b>{v}</b>del PIB</div>' for k, v in ((f"Gasto en {prim}", _pp(tot[prim])), (f"Mínimo · {minimo}", _pp(tot[minimo])), (f"Último año cerrado · {ult_ej}", _pp(tot[ult_ej])), ("Proyecto 2027", _pp(p27)))) + '</div>',
        '<nav class="chips" aria-label="En esta página"><a href="#total">Año por año</a><a href="#gobiernos">Gobierno por gobierno</a><a href="#rubros">En qué se gastó</a><a href="#resultado">¿Gastó más de lo que recaudó?</a><a href="#economia">Contra el tamaño de la economía</a><a href="#produccion">Industria, comercio y empleo</a><a href="#composicion">De cada $100</a><a href="#tipo">Por tipo de gasto</a><a href="#ley">La ley contra lo gastado</a><a href="#largo">Desde 1980</a><a href="#numeros">Todos los números</a></nav>',
        f'<section class="hx-card" id="total"><div class="hx-head"><div><h2>Cuánto gastó la Nación cada año</h2><p>{frase}</p></div>'
        '<div class="hx-ley"><span><i style="background:var(--hx-acc)"></i>Gastado</span><span><i style="background:var(--hx-est)"></i>2026 estimado</span><span><i style="background:var(--hx-acc2)"></i>2027 proyecto</span><span><i style="width:10px;height:10px;border-radius:50%;border:2px solid var(--fg);background:none"></i>Sin ley nueva (prórroga)</span></div></div>'
        f'<p class="hx-sub">En % del PIB: qué parte de todo lo que produce el país pasa por el presupuesto nacional. Se usa el PIB porque permite comparar 1995 con 2025 sin discutir qué índice de inflación usar. Tocá una barra para ver el año.</p>{hx_chart()}</section>',
        f'<section id="gobiernos" style="display:flex;flex-direction:column;gap:16px"><div class="hx-head"><div><h2>Gobierno por gobierno</h2><p>Cómo recibió cada uno el gasto y cómo lo dejó, en % del PIB, junto con lo que creció la economía por año y el gasto por habitante en pesos de {ult_ej}. Cada año se cuenta al gobierno que lo ejecutó, aunque el presupuesto lo haya escrito el anterior.</p></div></div>{hx_govs()}</section>',
        f'<section class="hx-card" id="rubros"><div class="hx-head"><div><h2>En qué se gastó</h2><p>Promedio de cada gobierno en % del PIB. Cuanto más oscura la celda, más alto fue ese rubro con ese gobierno respecto de los demás.</p></div></div>{hx_heat()}'
        '<p class="note">Algunos saltos bruscos de un año a otro (por ejemplo, Salud entre 1995 y 1996) responden a cambios en cómo se clasificó el gasto o en qué organismos entran al presupuesto, no necesariamente a decisiones de política. «Jubilaciones, pensiones y asignaciones» incluye la AUH y las asignaciones familiares (función Seguridad social). «Ayuda a provincias» es la función Relaciones interiores: transferencias que no son coparticipación. «Energía y combustibles» y «Transporte» son, sobre todo, subsidios y obras.</p>'
        f'<details><summary class="note">Ver cada rubro año por año</summary><div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px;margin-top:12px">{"".join(mini(r, n) for r, n in R)}</div></details></section>',
        hx_fiscal(),
        hx_eco(),
        hx_prod(),
        f'<section class="hx-card" id="composicion"><h2>De cada $100 que gastó la Nación</h2><p class="hx-sub">Cómo se repartió el gasto en promedio en cada gobierno. Pasá el dedo o el mouse por cada color para ver el número.</p>{composicion()}</section>',
        f'<section class="hx-card" id="tipo"><h2>Por tipo de gasto</h2><p class="hx-sub">Promedio de cada gobierno, en % del PIB, según el inciso del gasto. Hasta {ult_ej} (para 2026 y 2027 todavía no hay este detalle cerrado).</p>{tabla(["Gobierno"] + [n for _, n in T], filas_t, "libre")}</section>',
        f'<section class="hx-card" id="ley"><h2>La ley contra lo que se gastó</h2><p class="hx-sub">«Ley» es el crédito inicial que aprobó el Congreso (o el prorrogado); «vigente», cómo quedó después de las modificaciones del año (decisiones administrativas, DNU y leyes); «gastado», lo devengado. '
        'Con inflación alta, el gasto siempre supera a la ley en pesos: la diferencia mide sobre todo cuánto se equivocó la inflación prevista, y en los años de prórroga es todavía mayor porque se arranca con los montos de un año anterior. ⚠ = sin ley nueva (presupuesto prorrogado).</p>'
        f'{tabla(["Año", "Qué rigió", "Ley (inicial)", "Vigente (modificado)", "Gastado", "Modificación", "Gastado vs. ley"], filas_l)}</section>',
        f'<div id="largo">{largo}</div>' if largo else "",
        f'<section class="hx-card" id="numeros"><h2>Todos los números, año por año</h2><details><summary class="note">Ver la tabla completa (se puede bajar en Excel)</summary>'
        f'{tabla(["Año", "Gobierno", "Gasto (pesos corrientes)", "PIB (pesos corrientes)", "Gasto % PIB"] + [n + " (% PIB)" for _, n in R], filas_a)}</details></section>',
        '<div class="caveat">Fuentes: Presupuesto Abierto (Ministerio de Economía), crédito y gasto devengado de la Administración Nacional de 1995 a 2025; Proyecto de Presupuesto 2027 para el cierre estimado de 2026 y lo pedido para 2027; '
        f'INDEC, PIB a precios corrientes y constantes y población (base 2004 desde 2004; antes, la base 1993 empalmada en 2004); para 2026 y 2027, el PIB y el crecimiento que usa el propio proyecto. '
        'Leyes y prórrogas: InfoLEG, Boletín Oficial y «Cupos presupuestarios anuales» del Ministerio de Economía. No incluye coparticipación, provincias, municipios, PAMI ni empresas públicas. '
        '<a href="/metodologia#historia">Cómo se calcula</a> · <a href="/datos/historia.json">Bajar los datos (JSON)</a>.</div>',
        '</div>',
    ]
    img = self.og_trabajo("historia.jpg", kicker=f"Presupuesto nacional {prim}-2027", titulo="¿Cómo cambió el gasto con cada gobierno?", org="En % del PIB, año por año",
                          l1=f"Máximo ({pico})", n1=_pp(tot[pico]), u1="del PIB", l2=f"Gastado {ult_ej}", n2=_pp(tot[ult_ej]), u2="del PIB",
                          fuente="Fuentes: Presupuesto Abierto, INDEC y Proyecto 2027")
    desc = (f"Los presupuestos nacionales de {prim} a 2027 con cada gobierno, de Menem a Milei: cuánto se gastó en % del PIB, en qué "
            "(jubilaciones, subsidios, educación, salud, deuda), cuánto se modificó la ley y qué años hubo prórroga.")
    ld = self.dataset(f"Presupuesto nacional de Argentina {prim}-2027: gasto por rubro y por gobierno", desc, "/historia")
    ld["temporalCoverage"] = f"{prim}/2027"
    ld["distribution"] = [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": self.site + "/datos/historia.json"}]
    self.pagina("/historia", f"Presupuestos nacionales {prim}-2027: cómo cambió el gasto con cada gobierno", desc, "\n".join(cuerpo),
                [("Inicio", "/"), ("Historia del presupuesto", "/historia")], img, ld, h1=False)


Generador.historia = historia
