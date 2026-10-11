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


def stat(k, n, s="", ink=False, barra=None):
    b = f'<div class="ejbar"><span style="width:{max(0, min(100, barra)):.1f}%"></span></div>' if barra is not None else ""
    return f'<div class="stat{" ink" if ink else ""}"><span class="k">{e(k)}</span><span class="n">{e(n)}</span>{f"<span class=s>{e(s)}</span>" if s else ""}{b}</div>'


class Generador:
    def __init__(self, raiz, site, repo, fecha_sitio, cabecera, datos, infl_prom27, infl26):
        self.raiz, self.site, self.repo, self.fecha_sitio, self.cabecera = raiz, site, repo, fecha_sitio, cabecera
        self.P = datos["programas"]["programas"]
        self.E = datos["programas"]["entes"]
        self.corte = datos["programas"]["corte26"]
        self.infl27, self.infl26 = infl_prom27, infl26
        self.urls, self.og = [], []

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
<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False).replace("</", "<\\/")}</script>
<script>window.va = window.va || function () {{ (window.vaq = window.vaq || []).push(arguments); }};</script>
<script defer src="/_vercel/insights/script.js"></script>
</head>
<body>
<div class="wrap">
{self.cabecera("/provincias" if ruta.startswith("/provincias") else "/programas")}
<main style="display:flex;flex-direction:column;gap:var(--g-lg)">
{migas_html}
{f"<h1>{e(h1 or titulo)}</h1>"}
{cuerpo}
</main>
<footer class="src">
<p>Sitio independiente, sin relación con el Gobierno nacional ni con partidos políticos. Montos en pesos corrientes. Fuentes: Proyecto de Presupuesto 2027 y sus datasets (Oficina Nacional de Presupuesto), Ley 27.798 y Presupuesto Abierto (Ministerio de Economía). Datos al {self.fecha_sitio}.</p>
<nav><a href="/">Inicio</a><a href="/programas">Buscar un gasto</a><a href="/gasto">Todos los programas</a><a href="/provincias">Por provincia</a><a href="/metodologia#programas">Cómo se calcula</a><a href="{self.repo}/issues/new" target="_blank" rel="noopener">Avisar un error</a></nav>
</footer>
</div>
</body>
</html>
"""
        archivo = self.raiz / (ruta.strip("/") + ".html")
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(doc, encoding="utf-8")
        self.urls.append(ruta)

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
            frases.append(f"El proyecto de Presupuesto 2027 pide <strong>{plata(x['a27'])}</strong> para {e(x['n'])} ({e(org)}).")
        else:
            frases.append(f"{e(x['n'])} ({e(org)}) no figura con este nombre en el proyecto 2027: puede haberse reorganizado o cerrado.")
        if x.get("v26") is not None:
            frases.append(f"En 2026 la ley le asignó {plata(x['l26'])}; hoy tiene {plata(x['v26'])} autorizados y lleva gastado {plata(x['d26'])} ({pct(x['d26'], x['v26'])}) hasta el {fecha(self.corte)}.")
        if real is not None:
            frases.append(("Descontando la inflación que supone el proyecto, " + ("crece" if real >= 0 else "cae") + f" alrededor de {miles(abs(real))}% en términos reales."))
        stats = []
        if x.get("a27") is not None:
            stats.append(stat("Pedido para 2027", plata(x["a27"]), "Proyecto de ley", ink=True))
        if x.get("v26") is not None:
            stats.append(stat("2026: aprobado por ley", plata(x["l26"]), "Ley 27.798"))
            stats.append(stat("2026: autorizado hoy", plata(x["v26"]), "con los cambios del año"))
            stats.append(stat("2026: gastado", plata(x["d26"]), f"{pct(x['d26'], x['v26'])} al {fecha(self.corte)}", barra=x["d26"] / x["v26"] * 100 if x["v26"] else 0))
        cuerpo = [f'<p class="note" style="margin-top:-12px">{e(x["j"])}{" › " + e(x["e"]) if x["e"] else ""}</p>']
        if x.get("b"):
            cuerpo.append(f'<p class="sub" style="font-size:18px">{e(x["b"])}</p>')
        cuerpo.append(f'<p class="respuesta">{" ".join(frases)}</p>')
        cuerpo.append(f'<div class="stats">{"".join(stats)}</div>')
        if real is not None:
            cuerpo.append(f'<p><span class="etq{" warn" if real < 0 else ""}">Variación real 2027 contra lo autorizado en 2026: {"+" if real >= 0 else "−"}{miles(abs(real))}%</span></p>')
        if x.get("act27"):
            filas = [[e(n), plata(v), pct(v, x["a27"]) if x["a27"] else "—"] for n, v in x["act27"]]
            cuerpo.append(f'<section class="card"><h2>¿En qué se gasta en 2027?</h2><p class="note">Cada actividad u obra del programa en el proyecto 2027 ({len(filas)}).</p>{tabla(["Actividad u obra", "Pedido 2027", "% del programa"], filas)}</section>')
        if x.get("inc27"):
            cuerpo.append(f'<section class="card"><h2>¿Qué tipo de gasto es?</h2>{tabla(["Tipo de gasto", "Pedido 2027", "% del programa"], [[e(n), plata(v), pct(v, x["a27"])] for n, v in x["inc27"]])}</section>')
        if x.get("metas"):
            filas = [[e(m[0]), e(str(m[1] or "")), miles(m[2], 0 if float(m[2]).is_integer() else 2)] for m in x["metas"]]
            cuerpo.append(f'<section class="card"><h2>¿Qué promete hacer en 2027?</h2><p class="note">Metas físicas e indicadores del proyecto.</p>{tabla(["Meta o indicador", "Unidad", "Cantidad 2027"], filas)}</section>')
        if x.get("act26"):
            filas = [[e(a[0]), plata(a[1]), plata(a[2]), plata(a[3]), pct(a[3], a[2])] for a in x["act26"]]
            cuerpo.append(f'<section class="card"><h2>¿Cuánto se gastó en 2026?</h2><p class="note">Por actividad: lo aprobado por ley, lo autorizado hoy y lo gastado (devengado) hasta el {fecha(self.corte)}.</p>{tabla(["Actividad u obra", "Ley", "Autorizado hoy", "Gastado", "%"], filas)}</section>')
        if x.get("prov26"):
            filas = []
            for p, v, d in x["prov26"]:
                nom = f'<a href="/provincias/{slug(p)}">{e(p)}</a>' if p not in ESPECIALES else e(p)
                filas.append([nom, plata(v), plata(d), pct(d, v)])
            cuerpo.append(f'<section class="card"><h2>¿En qué provincias se gasta?</h2><p class="note">Gasto 2026 según la ubicación que le asigna el Estado. «Nacional» o «No clasificado» es gasto sin provincia asignada.</p>{tabla(["Provincia", "Autorizado 2026", "Gastado", "%"], filas)}</section>')
        if hermanos:
            lis = "".join(f'<li><a href="/gasto/{h["s"]}">{e(h["n"])}</a><span>{plata(h["a27"] if h["a27"] is not None else h.get("v26"))}</span></li>' for h in hermanos[:40])
            cuerpo.append(f'<section class="card"><h2>Otros programas de {e(org)}</h2><ul class="lista-links">{lis}</ul></section>')
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
        frases = [f"El proyecto de Presupuesto 2027 prevé un gasto de <strong>{plata(x['g27'])}</strong> para {e(x['n'])} en 2027."]
        if x.get("g26") is not None:
            frases.append(f"La Ley 27.798 le fijó {plata(x['g26'])} para 2026: {pct(x['g27'] - x['g26'], x['g26'])} más en pesos, aunque la ley 2026 suponía 10,1% de inflación y el año cerraría cerca de {miles(self.infl26)}%.")
        stats = [stat("Gasto total 2027", plata(x["g27"]), "Proyecto de ley", ink=True)]
        if x.get("g26") is not None:
            stats.append(stat("Gasto total 2026", plata(x["g26"]), "Ley 27.798"))
        stats += [stat(d[0] + " 2027", plata(d[1])) for d in x.get("det", [])]
        cuerpo = [f'<p class="note" style="margin-top:-12px">{e(x["tipo"])} · tiene presupuesto propio, fuera de los programas de la Administración Nacional</p>',
                  f'<p class="respuesta">{" ".join(frases)}</p>', f'<div class="stats">{"".join(stats)}</div>']
        if x.get("nota"):
            cuerpo.append(f'<p class="sub">{e(x["nota"])}</p>')
        if x["tipo"].startswith("Univ"):
            cuerpo.append('<p class="sub">La plata de las universidades nacionales sale del programa <a href="/gasto/' + next((p["s"] for p in self.P if p["n"].startswith("Desarrollo de la Educación Superior")), "") + '">Desarrollo de la Educación Superior</a> del Ministerio de Capital Humano, que se reparte según la planilla anexa al artículo 12 de la ley.</p>')
        botones = [f'<a class="btn primary" href="/cuadros#p{x["pag"]}">Ver el cuadro 2027 (pág. {x["pag"]})</a>']
        if x.get("pag26"):
            botones.append(f'<a class="btn" href="/cuadros#ley2026-p{x["pag26"]}">Ver el cuadro de la ley 2026 (pág. {x["pag26"]})</a>')
        cuerpo.append(f'<div style="display:flex;gap:8px;flex-wrap:wrap">{"".join(botones)}</div>')
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
        for p, tv, td in lista:
            ruta = f"/provincias/{slug(p)}"
            xs = sorted(por[p], key=lambda z: -z[1])
            frases = [f"En 2026 el Estado nacional tiene <strong>{plata(tv)}</strong> autorizados para gastar en {e(p)} y lleva gastado {plata(td)} ({pct(td, tv)}) hasta el {fecha(self.corte)}.",
                      f"Es el {miles(tv / geo * 100, 1)}% de lo que la Nación asigna a alguna provincia."]
            filas = [[f'<a href="/gasto/{x["s"]}">{e(x["n"])}</a><br><span class="note">{e(x["e"] or x["j"])}</span>', plata(v), plata(d), pct(d, v)] for x, v, d in xs[:60]]
            cuerpo = [f'<p class="respuesta">{" ".join(frases)}</p>',
                      f'<div class="stats">{stat("Autorizado 2026", plata(tv), "gasto nacional con ubicación en la provincia", ink=True)}{stat("Gastado", plata(td), pct(td, tv) + " al " + fecha(self.corte), barra=td / tv * 100 if tv else 0)}{stat("Programas con gasto en la provincia", miles(len(xs)))}</div>',
                      '<div class="caveat">Cuenta solo el gasto que el Estado nacional ubica en esta provincia. Una parte grande del gasto, como muchas jubilaciones y asignaciones o las transferencias a fondos, figura como «Nacional» o «No clasificado», así que lo que llega a la gente de la provincia es más que esto. Tampoco incluye la coparticipación, que no es gasto del presupuesto nacional.' + (' En la Ciudad de Buenos Aires, además, figura mucho gasto de organismos nacionales que tienen ahí su sede.' if p.startswith('Ciudad') else '') + '</div>',
                      f'<section class="card"><h2>¿En qué gasta la Nación en {e(p)}?</h2><p class="note">Los {min(60, len(xs))} programas con más gasto en la provincia en 2026.</p>{tabla(["Programa", "Autorizado 2026", "Gastado", "%"], filas)}</section>',
                      f'<div style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn primary" href="/programas?provincia={e(p)}">Buscar dentro de {e(p)}</a><a class="btn" href="/provincias">Ver todas las provincias</a></div>']
            n1, u1 = plata_og(tv)
            img = self.og_trabajo(f"provincias/{slug(p)}.jpg", kicker="Presupuesto nacional 2026", titulo=f"¿Cuánto gasta la Nación en {p}?", org="",
                                  l1="Autorizado 2026", n1=n1, u1=u1, l2="Gastado hasta ahora", n2=pct(td, tv), u2="", fuente="Fuente: Presupuesto Abierto (Ministerio de Economía)")
            titulo = f"¿Cuánto gasta la Nación en {p}? Presupuesto 2026 por provincia"
            desc = f"El Estado nacional tiene {plata(tv)} autorizados para gastar en {p} en 2026 y lleva gastado el {pct(td, tv)}. Programa por programa: obras, rutas, salud, educación y más."
            self.pagina(ruta, titulo, desc, "\n".join(cuerpo), [("Inicio", "/"), ("Por provincia", "/provincias"), (p, ruta)], img, self.dataset(titulo, desc, ruta), h1=f"¿Cuánto gasta la Nación en {p}?")
        filas = [[f'<a href="/provincias/{slug(p)}">{e(p)}</a>', plata(tv), plata(td), pct(td, tv), f"{miles(tv / geo * 100, 1)}%"] for p, tv, td in lista]
        esp = [[e(p), plata(sum(v for _, v, _ in por[p])), plata(sum(d for _, _, d in por[p]))] for p in ESPECIALES if p in por]
        cuerpo = ['<p class="sub">Lo que el Estado nacional asignó en 2026 a cada provincia en su presupuesto, y cuánto lleva gastado. Tocá una provincia para ver en qué se gasta, programa por programa.</p>',
                  tabla(["Provincia", "Autorizado 2026", "Gastado", "%", "Parte del total con provincia"], filas),
                  '<section class="card"><h2>Gasto sin provincia asignada</h2><p class="note">Este gasto no se puede atribuir a una provincia en el presupuesto, aunque llegue a personas de todo el país.</p>' + tabla(["Ubicación", "Autorizado 2026", "Gastado"], esp) + "</section>"]
        self.pagina("/provincias", "¿Cuánto gasta la Nación en cada provincia? Presupuesto 2026", "El gasto del Estado nacional en cada provincia argentina en 2026: autorizado y gastado, programa por programa.",
                    "\n".join(cuerpo), [("Inicio", "/"), ("Por provincia", "/provincias")], h1="¿Cuánto gasta la Nación en cada provincia?")

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
        (self.raiz / "scripts" / ".og-paginas.json").write_text(json.dumps(self.og, ensure_ascii=False), encoding="utf-8")
        return self.urls
