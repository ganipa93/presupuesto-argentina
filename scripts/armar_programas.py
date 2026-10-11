#!/usr/bin/env python3
"""Arma datos/programas.json para el buscador "¿Cuánto se gasta en…?".

Junta, programa por programa:
  - 2027 (proyecto): apertura programática hasta actividad/obra, gasto por inciso y
    metas físicas (datasets del Presupuesto Ciudadano, ONP).
  - 2026: crédito de la ley, crédito vigente y gasto devengado por actividad y por
    provincia (API de Presupuesto Abierto).
  - Lo que está fuera de la Administración Nacional y por eso no tiene programas:
    universidades una por una, fondos fiduciarios, otros entes (INCAA, PAMI, ARCA…)
    y empresas públicas, leídos de las planillas del PDF del proyecto.

Entrada: fuentes/datasets/ (scripts/bajar_datasets.py) y cuadros/paginas/ (scripts/extraer_cuadros.py).
Uso: python3 scripts/armar_programas.py
"""
import csv, datetime, json, pathlib, re, subprocess, unicodedata
from collections import defaultdict
import openpyxl

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DS = RAIZ / "fuentes" / "datasets"
PAG = RAIZ / "cuadros" / "paginas"
DESTINO = RAIZ / "datos" / "programas.json"
M = 1e6  # los xlsx vienen en pesos; todo se guarda en millones


def norm(s):
    s = unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


EXCLUIR_TILDE = {"que", "como", "donde", "cual", "quien", "esta", "este", "estas", "solo", "si", "el", "tu", "mi", "se", "de", "te", "aun", "continua", "practica", "publico", "transito", "termino", "deposito", "ultimo", "medico", "numero", "credito", "titulo", "calculo", "limite", "liquido", "basico", "rapido"}
_TILDES = None


def tildes(s):
    """Las bases de 2027 vienen sin tildes: se reponen con las palabras de las bases que sí las tienen."""
    global _TILDES
    if _TILDES is None:
        _TILDES = {}
        cuenta = defaultdict(lambda: defaultdict(int))
        textos = []
        with open(DS / "2026-credito-por-programa.csv", encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                textos += [r[k] for k in ("jurisdiccion_desc", "entidad_desc", "programa_desc", "subprograma_desc", "actividad_desc")]
        for f in ("2026-apertura-programatica.xlsx", "2027-mediciones-fisicas.xlsx"):
            for fila_ in filas_xlsx(f):
                textos += [v for v in fila_ if isinstance(v, str)]
        for t in textos:
            for w in re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", t):
                base = norm(w)
                if base and w.lower() != base:
                    cuenta[base][w.lower()] += 1
        _TILDES = {k: max(v, key=v.get) for k, v in cuenta.items() if k not in EXCLUIR_TILDE}
        _TILDES.update({"publico": "público", "publicos": "públicos", "credito": "crédito", "creditos": "créditos", "medico": "médico", "medicos": "médicos", "transito": "tránsito", "numero": "número", "basico": "básico", "basica": "básica"})

    def cambiar(m):
        w = m.group(0)
        n = _TILDES.get(w.lower())
        if not n or len(n) != len(w):
            return w
        if w.isupper() and len(w) > 1:
            return n.upper()
        return "".join(c.upper() if o.isupper() else c for c, o in zip(n, w))
    return re.sub(r"[A-Za-z]+", cambiar, str(s or ""))


def filas_xlsx(nombre):
    ws = openpyxl.load_workbook(DS / nombre, read_only=True).worksheets[0]
    filas = list(ws.iter_rows(values_only=True))
    i = next(i for i, f in enumerate(filas) if f[0] and str(f[0]).startswith(("Cod", "Cód")))
    return [f for f in filas[i + 1:] if isinstance(f[0], (int, float))]


def r1(v):
    return round(v, 1)


def num_ar(t):
    t = t.strip()
    if t in ("-", "", "--"):
        return 0.0
    return float(t.replace(".", "").replace(",", "."))


def main():
    progs = {}

    # ---------- 2027: apertura programática ----------
    for f in filas_xlsx("2027-apertura-programatica.xlsx"):
        (cj, j, cs, sj, ce, e, cp, p, csub, sub, cpy, py, ca, a, monto) = f
        k = (cj, cs, ce, cp)
        j, sj, e, p, sub, py, a = (tildes(v) for v in (j, sj, e, p, sub, py, a))
        g = progs.setdefault(k, {"j": j, "s": sj, "e": e, "n": p, "a27": 0.0, "act27": defaultdict(float)})
        g["a27"] += (monto or 0) / M
        hoja = a if ca else py
        etiqueta = hoja
        if csub and norm(sub) != norm(p) and norm(sub) != norm(hoja):
            etiqueta = f"{sub} · {hoja}"
        g["act27"][etiqueta] += (monto or 0) / M

    # gasto por inciso 2027
    for f in filas_xlsx("2027-partida-presupuestaria.xlsx"):
        k = (f[0], f[2], f[4], f[6])
        if k in progs:
            inc = progs[k].setdefault("inc27", defaultdict(float))
            inc[tildes(f[11])] += (f[14] or 0) / M

    # metas físicas 2027
    for f in filas_xlsx("2027-mediciones-fisicas.xlsx"):
        k = (f[0], f[2], f[4], f[6])
        if k in progs and f[15] is not None:
            desc = tildes(f[12] if not f[8] or norm(f[9]) == norm(f[7]) else f"{f[12]} ({f[9]})")
            progs[k].setdefault("metas", []).append([desc, tildes(f[14]), f[15], "i" if str(f[10]).lower().startswith("ind") else "m"])

    # ---------- 2026: ejecución por programa (Presupuesto Abierto) ----------
    p26 = {}
    with open(DS / "2026-credito-por-programa.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            k = (norm(r["entidad_desc"]), norm(r["programa_desc"]))
            g = p26.setdefault(k, {"j": r["jurisdiccion_desc"], "s": r["subjurisdiccion_desc"], "e": r["entidad_desc"],
                                   "n": r["programa_desc"], "t": [0.0, 0.0, 0.0],
                                   "act": defaultdict(lambda: [0.0, 0.0, 0.0]), "prov": defaultdict(lambda: [0.0, 0.0])})
            v = [float(r[c] or 0) for c in ("credito_presupuestado", "credito_vigente", "credito_devengado")]
            hoja = r["actividad_desc"]
            if norm(r["subprograma_desc"]) not in (norm(r["programa_desc"]), norm(hoja)):
                hoja = f'{r["subprograma_desc"]} · {hoja}'
            for i in range(3):
                g["t"][i] += v[i]
                g["act"][hoja][i] += v[i]
            pv = g["prov"][r["ubicacion_geografica_desc"].replace("Provincia de ", "").replace("Provincia del ", "")]
            pv[0] += v[1]
            pv[1] += v[2]

    # ---------- unir 2027 con 2026 ----------
    salida, usados = [], set()
    por_jur_prog = defaultdict(list)
    for k, g in p26.items():
        por_jur_prog[(norm(g["j"]), k[1])].append(k)
    for k, g in progs.items():
        clave = (norm(g["e"]), norm(g["n"]))
        if clave not in p26:  # la entidad cambió de nombre: probar por jurisdicción
            cand = [c for c in por_jur_prog.get((norm(g["j"]), clave[1]), []) if c not in usados]
            clave = cand[0] if len(cand) == 1 else clave
        if clave not in p26 or clave in usados:  # cambió el ministerio: probar solo por nombre del programa
            cand = [c for c in p26 if c[1] == norm(g["n"]) and c not in usados]
            if len(cand) == 1 and sum(1 for o in progs.values() if norm(o["n"]) == norm(g["n"])) == 1:
                clave = cand[0]
        x = {"j": g["j"], "e": g["e"] if norm(g["e"]) != norm(g["j"]) else "", "n": g["n"], "a27": r1(g["a27"]),
             "act27": sorted(([n, r1(v)] for n, v in g["act27"].items() if abs(v) >= 0.05), key=lambda z: -z[1])}
        if "inc27" in g:
            x["inc27"] = sorted(([n, r1(v)] for n, v in g["inc27"].items() if abs(v) >= 0.05), key=lambda z: -z[1])
        if "metas" in g:
            x["metas"] = g["metas"]
        if clave in p26 and clave not in usados:
            usados.add(clave)
            agregar_2026(x, p26[clave])
        salida.append(x)
    for k, g in p26.items():  # programas de 2026 que no siguen en 2027
        if k in usados or not any(g["t"]):
            continue
        x = {"j": tildes(g["j"]), "e": tildes(g["e"]) if norm(g["e"]) != norm(g["j"]) else "", "n": tildes(g["n"]), "a27": None}
        agregar_2026(x, g)
        salida.append(x)
    salida.sort(key=lambda x: -max(x["a27"] or 0, x.get("v26", 0)))
    bajadas = json.loads((RAIZ / "scripts" / "bajadas_programas.json").read_text(encoding="utf-8"))
    for x in salida:
        b = bajadas.get(norm(x["e"] or x["j"]) + "|" + norm(x["n"])) or bajadas.get(norm(x["n"]))
        if b:
            x["b"] = b

    entes = universidades() + entes_fuera()
    poner_slugs(salida, entes)
    agregar_historia(salida)
    obras_por_provincia(salida)
    ley26 = json.loads((RAIZ / "fuentes" / "ley2026_planillas.json").read_text(encoding="utf-8"))
    for e in entes:
        x = ley26["universidades"].get(e["n"]) or ley26["entes"].get(e["n"])
        if x:
            e["g26"] = x["g26"]
            e["pag26"] = x.get("pag", 74)
    t27 = sum(x["a27"] or 0 for x in salida)
    t26 = [sum(x.get(c, 0) for x in salida) for c in ("l26", "v26", "d26")]
    emparejados = sum(1 for x in salida if x["a27"] is not None and "v26" in x)
    datos = {
        "unidad": "millones de pesos",
        "corte26": fecha_csv(),
        "fuentes": {
            "2027": "Proyecto de Presupuesto 2027, datasets del Presupuesto Ciudadano (Oficina Nacional de Presupuesto)",
            "2026": "Presupuesto Abierto (Ministerio de Economía), API de crédito",
            "entes": "Proyecto de Presupuesto 2027, planillas anexas (PDF)",
        },
        "totales": {"a27": r1(t27), "l26": r1(t26[0]), "v26": r1(t26[1]), "d26": r1(t26[2])},
        "programas": salida,
        "historia_org": historia_organismos(salida),
        "historia_total": totales_historicos(),
        "entes": entes,
    }
    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(salida)} programas ({emparejados} con datos de los dos años), {len(entes)} entes fuera de la APN")
    print(f"Total 2027: {t27/1e6:,.2f} billones · 2026 ley {t26[0]/1e6:,.2f} vigente {t26[1]/1e6:,.2f} devengado {t26[2]/1e6:,.2f}")
    print(f"{DESTINO.stat().st_size/1e6:.2f} MB")


ABREV = {"administracion nacional de la seguridad social": "anses", "direccion nacional de vialidad": "vialidad",
         "consejo nacional de investigaciones cientificas y tecnicas": "conicet", "instituto nacional de tecnologia agropecuaria": "inta",
         "instituto nacional de tecnologia industrial": "inti", "administracion nacional de laboratorios e institutos de salud dr carlos g malbran": "anlis-malbran",
         "registro nacional de las personas renaper": "renaper", "gendarmeria nacional": "gendarmeria", "prefectura naval argentina": "prefectura",
         "policia federal argentina": "policia-federal", "servicio penitenciario federal": "servicio-penitenciario", "comision nacional de energia atomica cnea": "cnea",
         "estado mayor general del ejercito argentino": "ejercito", "estado mayor general de la armada argentina": "armada",
         "estado mayor general de la fuerza aerea argentina": "fuerza-aerea", "obligaciones a cargo del tesoro": "tesoro", "servicio de la deuda publica": "deuda",
         "poder judicial de la nacion": "poder-judicial", "poder legislativo nacional": "congreso", "ministerio publico": "ministerio-publico",
         "jefatura de gabinete de ministros": "jefatura-de-gabinete", "ente nacional de comunicaciones": "enacom",
         "instituto nacional de servicios sociales para jubilados y pensionados": "pami", "agencia nacional de discapacidad": "andis",
         "administracion de parques nacionales": "parques-nacionales", "servicio nacional de sanidad y calidad agroalimentaria": "senasa"}
VACIAS = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "para", "por", "a", "al", "con"}


def slug(s, max_palabras=9):
    ps = [w for w in norm(s).split() if w]
    return "-".join(ps[:max_palabras])


def org_corto(x):
    o = x["e"] or x["j"]
    if norm(o) in ABREV:
        return ABREV[norm(o)]
    o = re.sub(r"^(ministerio|secretaria|subsecretaria) (de |del )?", "", norm(o))
    return "-".join([w for w in o.split() if w not in VACIAS][:4])


def poner_slugs(programas, entes):
    """Dirección fija de cada página de detalle (/gasto/<slug>)."""
    usados = set()
    def unico(b):
        b = b.strip("-")[:90].strip("-")
        s, i = b, 2
        while s in usados:
            s, i = f"{b}-{i}", i + 1
        usados.add(s)
        return s
    for e in entes:  # primero los entes, que tienen nombres más buscados
        m = re.match(r"^(.*?)\s*\(([^)]*)\)", e["n"])
        if m and re.fullmatch(r"[A-Z][A-Za-z-]{1,7}", m.group(2).strip()):  # "Nombre (SIGLA)"
            base = slug(m.group(2)) + "-" + slug(m.group(1), 7)
        elif m and re.fullmatch(r"[A-Z][A-Za-z.-]{1,8}( S\.A\.)?", m.group(1).strip()):  # "SIGLA (nombre)"
            base = slug(m.group(1)) + "-" + slug(m.group(2), 6)
        else:
            base = slug(m.group(1) if m else e["n"], 10)
        e["s"] = unico(base)
    for x in sorted(programas, key=lambda x: -max(x["a27"] or 0, x.get("v26", 0))):
        nom = re.sub(r"^asistencia financiera a empresas publicas y otros entes (dependientes )?(de la |del |de )?", "asistencia financiera ", norm(x["n"]))
        x["s"] = unico(slug(nom, 14)[:70].rstrip("-") + "-" + org_corto(x))


PROVINCIAS = ["Buenos Aires", "Catamarca", "Chaco", "Chubut", "Córdoba", "Corrientes", "Entre Ríos", "Formosa", "Jujuy", "La Pampa", "La Rioja",
              "Mendoza", "Misiones", "Neuquén", "Río Negro", "Salta", "San Juan", "San Luis", "Santa Cruz", "Santa Fe", "Santiago del Estero",
              "Tierra del Fuego, Antártida e Islas del Atlántico Sur", "Tucumán", "Ciudad Autónoma de Buenos Aires"]
_BASE = {p: norm(p.split(",")[0]) for p in PROVINCIAS}
_BASE["Ciudad Autónoma de Buenos Aires"] = "ciudad autonoma de buenos aires"


def provincias_en(texto):
    """Provincias que nombra una obra. Primero las menciones explícitas («Provincia de Salta», «Distrito Salta»);
    si no hay, el nombre suelto, salvo cuando es un límite («límite con Chaco»)."""
    t = " " + norm(texto) + " "
    t = t.replace(" pcia ", " provincia ").replace(" prov ", " provincia ").replace(" bs as ", " buenos aires ").replace(" pba ", " provincia de buenos aires ")
    caba = any(k in t for k in (" ciudad autonoma de buenos aires ", " caba ", " c a b a "))
    if caba:
        t = t.replace(" ciudad autonoma de buenos aires ", " ").replace(" caba ", " ").replace(" c a b a ", " ")
    t = t.replace(" san juan bosco ", " ").replace(" universidad nacional de ", " ")
    for b in _BASE.values():  # «límite con la provincia de Chaco» no es una obra en Chaco
        t = re.sub(rf" (limite|lte|lim|limites) (con )?(la )?(provincia |pcia )?(de |del )?{b} ", " ", t)
    explicitas, sueltas = set(), set()
    for p, b in _BASE.items():
        if p.startswith("Ciudad"):
            continue
        if re.search(rf" (provincia|provincias|distrito|distritos|prov) (de |del )?{b} ", t) or (b == "buenos aires" and " provincia de buenos aires " in t):
            explicitas.add(p)
        elif re.search(rf" {b} ", t) and not re.search(rf" (limite|lte|lim) (con )?(la )?(provincia )?(de )?{b} ", t):
            sueltas.add(p)
    out = explicitas or sueltas
    if caba:
        out = set(out) | {"Ciudad Autónoma de Buenos Aires"}
    return sorted(out)


def obras_por_provincia(programas):
    """Obras y actividades 2027 que nombran una provincia, y la inversión 2026 (bienes de uso) que el Estado ubica en cada una."""
    out = {p: {"o27": [], "i26": []} for p in PROVINCIAS}
    for x in programas:
        for etiqueta, monto in x.get("act27", []):
            if monto <= 0 or norm(etiqueta).startswith(("conduccion", "actividades centrales")):
                continue
            ps = provincias_en(etiqueta)
            for p in ps:
                out[p]["o27"].append([etiqueta, x["n"], x["s"], monto, len(ps) > 1])
    clave = {(norm(x["e"] or x["j"]), norm(x["n"])): x for x in programas}
    inv = defaultdict(lambda: [0.0, 0.0])
    nombres = {}
    with open(DS / "2026-credito-por-programa.csv", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if r["inciso_desc"] != "Bienes de uso":
                continue
            prov = r["ubicacion_geografica_desc"].replace("Provincia de ", "").replace("Provincia del ", "")
            prov = next((p for p in PROVINCIAS if p.split(",")[0] == prov.split(",")[0]), None)
            if not prov:
                continue
            x = clave.get((norm(r["entidad_desc"]), norm(r["programa_desc"])))
            k = (prov, tildes(r["actividad_desc"]), x["s"] if x else "", x["n"] if x else tildes(r["programa_desc"]))
            inv[k][0] += float(r["credito_vigente"] or 0)
            inv[k][1] += float(r["credito_devengado"] or 0)
    for (prov, act, slug_, prog), (v, d) in inv.items():
        if v >= 1 or d >= 1:
            out[prov]["i26"].append([act, prog, slug_, r1(v), r1(d)])
    for p in out:
        out[p]["o27"].sort(key=lambda z: -z[3])
        out[p]["i26"].sort(key=lambda z: -z[3])
        out[p]["o27"] = [z[:3] + [r1(z[3]), z[4]] for z in out[p]["o27"]]
    (RAIZ / "datos" / "obras_provincias.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return out


def historia_organismos(programas):
    """Gasto devengado 2020-2025 de cada organismo descentralizado (Vialidad, CONICET, ANSES…), para cuando el
    programa cambió de nombre y no se puede seguir solo."""
    orgs = {norm(x["e"]) for x in programas if x["e"]}
    out = defaultdict(list)
    for f in sorted(DS.glob("historia-*.csv")):
        anio = int(f.stem.split("-")[1])
        if anio >= 2026:
            continue
        tot = defaultdict(float)
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                if norm(r["entidad_desc"]) != norm(r["jurisdiccion_desc"]):
                    tot[norm(r["entidad_desc"])] += float(r["credito_devengado"] or 0)
        for k, v in tot.items():
            if k in orgs and v > 0:
                out[k].append([anio, r1(v)])
    return dict(out)


def totales_historicos():
    out = []
    for f in sorted(DS.glob("historia-*.csv")):
        anio = int(f.stem.split("-")[1])
        if anio < 2026:
            with open(f, encoding="utf-8-sig") as fh:
                out.append([anio, r1(sum(float(r["credito_devengado"] or 0) for r in csv.DictReader(fh)))])
    return out


def agregar_historia(programas):
    """Serie 2020-2025 del gasto devengado de cada programa (Presupuesto Abierto), en millones de pesos corrientes.
    Se empareja por organismo y nombre del programa; si el organismo cambió, por el nombre solo cuando hay uno igual ese año."""
    for f in sorted(DS.glob("historia-*.csv")):
        anio = int(f.stem.split("-")[1])
        if anio >= 2026:
            continue  # 2026 y 2027 ya están con más detalle
        por_clave, por_nombre = defaultdict(float), defaultdict(lambda: defaultdict(float))
        with open(f, encoding="utf-8-sig") as fh:
            for r in csv.DictReader(fh):
                d = float(r["credito_devengado"] or 0)
                por_clave[(norm(r["entidad_desc"]), norm(r["programa_desc"]))] += d
                por_nombre[norm(r["programa_desc"])][norm(r["entidad_desc"])] += d
        for x in programas:
            n = norm(x["n"])
            v = por_clave.get((norm(x["e"] or x["j"]), n))
            if v is None and n not in ("actividades centrales", "actividades comunes") and not n.startswith("actividades comunes"):
                cand = por_nombre.get(n, {})
                if len(cand) == 1:
                    v = next(iter(cand.values()))
            if v is not None and v > 0:
                x.setdefault("h", []).append([anio, r1(v)])


def fecha_csv():
    """Día en que se bajó la ejecución 2026: el del último commit del CSV, o hoy si todavía no se commiteó."""
    f = DS / "2026-credito-por-programa.csv"
    r = subprocess.run(["git", "status", "--porcelain", "--", str(f)], cwd=RAIZ, capture_output=True, text=True)
    if r.returncode == 0 and not r.stdout.strip():
        r = subprocess.run(["git", "log", "-1", "--format=%cs", "--", str(f)], cwd=RAIZ, capture_output=True, text=True)
        if r.stdout.strip():
            return r.stdout.strip()
    return datetime.date.today().isoformat()


def agregar_2026(x, g):
    x["l26"], x["v26"], x["d26"] = (r1(v) for v in g["t"])
    x["act26"] = sorted(([tildes(n)] + [r1(v) for v in vs] for n, vs in g["act"].items() if any(abs(v) >= 0.05 for v in vs)),
                        key=lambda z: -max(z[1], z[2]))
    x["prov26"] = sorted(([n, r1(v[0]), r1(v[1])] for n, v in g["prov"].items() if abs(v[0]) >= 0.05 or abs(v[1]) >= 0.05),
                         key=lambda z: -z[1])
    if not x.get("j"):
        x["j"] = g["j"]


NOMBRES_UNI = {
    "Centro": "Universidad Nacional del Centro de la Provincia de Buenos Aires", "Sur": "Universidad Nacional del Sur",
    "Litoral": "Universidad Nacional del Litoral", "Nordeste": "Universidad Nacional del Nordeste",
    "Noroeste": "Universidad Nacional del Noroeste de la Provincia de Buenos Aires", "Comahue": "Universidad Nacional del Comahue",
    "Chaco Austral": "Universidad Nacional del Chaco Austral", "Delta": "Universidad Nacional del Delta",
    "Alto Uruguay": "Universidad Nacional del Alto Uruguay", "Tecnológica": "Universidad Tecnológica Nacional (UTN)",
    "Pedagógica Nacional": "Universidad Pedagógica Nacional", "Defensa Nacional": "Universidad de la Defensa Nacional",
    "Scalabrini Ortiz": "Universidad Nacional Raúl Scalabrini Ortiz", "Madres de Plaza de Mayo": "Universidad Nacional de las Madres de Plaza de Mayo",
    "Arturo Jauretche": "Universidad Nacional Arturo Jauretche", "José Clemente Paz": "Universidad Nacional de José C. Paz",
    "Guillermo Brown": "Universidad Nacional Guillermo Brown", "De las Artes": "Universidad Nacional de las Artes",
    "Del Oeste": "Universidad Nacional del Oeste", "La Patagonia San Juan Bosco": "Universidad Nacional de la Patagonia San Juan Bosco",
    "La Patagonia Austral": "Universidad Nacional de la Patagonia Austral", "Buenos Aires": "Universidad de Buenos Aires (UBA)",
}


def universidades():
    """Planilla anexa al art. 12 (p. 198): crédito de cada universidad nacional, en pesos."""
    out = []
    for p in (198, 199):
        texto = json.loads((PAG / f"p{p:03d}.json").read_text(encoding="utf-8"))["texto"]
        if "UNIVERSIDADES" not in texto.upper() and p != 198:
            continue
        for l in texto.split("\n"):
            l = re.sub(r"(?<=\s)(\d) (\.?\d)", r"\1\2", l.strip())
            m = re.match(r"^([A-Za-zÁÉÍÓÚáéíóúÑñ][A-Za-zÁÉÍÓÚáéíóúÑñ .]+?)\s+((?:-|[\d.]+)(?:\s+(?:-|[\d.]+)){3})$", l)
            if l.upper().startswith("SUBTOTAL"):
                return out  # lo que sigue son partidas comunes, no universidades
            if not m:
                continue
            v = [num_ar(t) / M for t in m.group(2).split()]
            if abs(v[0] + v[1] + v[2] - v[3]) > 0.01:
                continue
            nombre = m.group(1).strip()
            nombre = NOMBRES_UNI.get(nombre, "Universidad Nacional de " + nombre)
            out.append({"n": nombre,
                        "tipo": "Universidad nacional", "g27": r1(v[3]),
                        "det": [["Salud (hospitales universitarios)", r1(v[0])], ["Educación y cultura", r1(v[1])], ["Ciencia, tecnología e innovación", r1(v[2])]],
                        "pag": 198, "nota": "Transferencia del Tesoro (Ministerio de Capital Humano), planilla anexa al art. 12."})
    return out


ENTES = [
    (206, "Fondo fiduciario", ["Fondo Fiduciario del Sistema de Infraestructura de Transporte (rutas, trenes y subsidios al transporte)",
                               "Fondo Fiduciario de Infraestructura Hídrica", "Fondo Fiduciario para Subsidios de Consumos Residenciales de Gas",
                               "Fondo para el Desarrollo de Energías Renovables (FODER)", "Fondo de Garantías Argentino (FOGAR)",
                               "Fondo Fiduciario para la Promoción de la Economía del Conocimiento (FONPEC)", "Fondo Fiduciario Ampliación de la Matriz Fueguina"]),
    (207, "Otro ente del Estado", ["ARCA (Agencia de Recaudación y Control Aduanero)", "Comisión Nacional Antidopaje (CNAD)",
                                   "Instituto Nacional de la Música (INAMU)", "Instituto Nacional de Cine y Artes Audiovisuales (INCAA)",
                                   "PAMI (Instituto Nacional de Servicios Sociales para Jubilados y Pensionados)"]),
    (124, "Otro ente del Estado", [None, "Superintendencia de Bienestar de la Policía Federal (SBPFA)", "Obra Social del Servicio Penitenciario Federal (OSSPF)",
                                   "Obra Social de las Fuerzas Armadas (OSFA)", "Obra Social de las Fuerzas de Seguridad (OSFFESEG)"]),
    (127, "Empresa pública", ["ADIF (Administración de Infraestructuras Ferroviarias)", "AGP (Administración General de Puertos)", "Aerolíneas Argentinas",
                              "APE S.A. (Agua y Saneamientos)", "AR-SAT (satélites y fibra óptica)", "AySA (agua y cloacas del AMBA)",
                              "Belgrano Cargas y Logística", "Casa de Moneda", "COVIARA (construcciones navales)",
                              "Contenidos Públicos (canal Encuentro, Paka Paka, DeporTV)", "Corredores Viales (autopistas y rutas con peaje)",
                              "Correo Argentino", "Desarrollo del Capital Humano Ferroviario"]),
    (128, "Empresa pública", ["Dioxitek (uranio)", "Educ.ar", "EANA (navegación aérea)", "ENARSA (Energía Argentina)", "FADEA (fábrica de aviones)",
                              "Fabricaciones Militares", "Ferrocarriles Argentinos", "INTEA", "Intercargo", "LT10 Radio Universidad Nacional del Litoral",
                              "Nucleoeléctrica Argentina (NASA)", "Playas Ferroviarias de Buenos Aires", "Polo Tecnológico Constituyentes"]),
    (129, "Empresa pública", ["Radio y Televisión Argentina (TV Pública, Radio Nacional)", "Servicios de Radio y TV de la Universidad Nacional de Córdoba",
                              "Trenes Argentinos Operaciones (Sociedad Operadora Ferroviaria)", "Tandanor (astillero)", "VENG (lanzadores espaciales)",
                              "YCRT (Yacimientos Carboníferos Río Turbio y central termoeléctrica)"]),
]


NOTAS = {
    "Instituto Nacional de Cine y Artes Audiovisuales (INCAA)":
        "Se financia sobre todo con un impuesto del 10% a las entradas de cine y a la venta o alquiler de videos, más un porcentaje de otro gravamen (pág. 109). "
        "El proyecto estima que el 59,2% de su gasto va a la promoción de producciones (pág. 110). No recibe aporte del Tesoro.",
    "PAMI (Instituto Nacional de Servicios Sociales para Jubilados y Pensionados)":
        "Da cobertura médica a 5.428.096 jubilados, pensionados, familiares a cargo y veteranos de Malvinas (pág. 110). "
        "Se financia con aportes y contribuciones de la seguridad social y con transferencias, $2,51 billones de ellas del Tesoro (pág. 207).",
    "Fondo Fiduciario del Sistema de Infraestructura de Transporte (rutas, trenes y subsidios al transporte)":
        "Paga sobre todo los subsidios al transporte automotor (SISTAU) y ferroviario (SIFER). El 81,9% de sus ingresos corrientes son impuestos "
        "asignados y recibe $762.320 millones del Tesoro (pág. 105).",
}


def fila(texto, patron):
    for l in texto.split("\n"):
        if re.match(r"\s*" + patron, l, re.I):
            return [num_ar(t) for t in re.findall(r"-?[\d.]+,\d", l)]
    return []


def entes_fuera():
    out = []
    for p, tipo, nombres in ENTES:
        texto = json.loads((PAG / f"p{p:03d}.json").read_text(encoding="utf-8"))["texto"]
        gastos = fila(texto, r"(VII ?- ?GASTOS TOTALES|TOTAL GASTOS)")
        ingresos = fila(texto, r"(VI ?- ?INGRESOS TOTALES|TOTAL INGRESOS)")
        tesoro = fila(texto, r"(Tesoro Nacional|Del Tesoro Nacional)")
        cap = fila(texto, r"\.Transferencias de la Adm")
        pers = fila(texto, r"Remuneraciones")
        for i, n in enumerate(nombres):
            if n is None or i >= len(gastos):
                continue
            aporte = (tesoro[i] if i < len(tesoro) else 0) + (cap[i] if i < len(cap) else 0)
            det = [["Ingresos totales", r1(ingresos[i])]] if i < len(ingresos) else []
            if aporte:
                det.append(["Aporte del Tesoro y de la Administración Nacional", r1(aporte)])
            if i < len(pers) and pers[i]:
                det.append(["Sueldos (remuneraciones)", r1(pers[i])])
            x = {"n": n, "tipo": tipo, "g27": r1(gastos[i]), "det": det, "pag": p}
            if n in NOTAS:
                x["nota"] = NOTAS[n]
            out.append(x)
    return out


if __name__ == "__main__":
    main()
