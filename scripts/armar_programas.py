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
            inc[f[11]] += (f[14] or 0) / M

    # metas físicas 2027
    for f in filas_xlsx("2027-mediciones-fisicas.xlsx"):
        k = (f[0], f[2], f[4], f[6])
        if k in progs and f[15] is not None:
            desc = f[12] if not f[8] or norm(f[9]) == norm(f[7]) else f"{f[12]} ({f[9]})"
            progs[k].setdefault("metas", []).append([desc, f[14], f[15], "i" if str(f[10]).lower().startswith("ind") else "m"])

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
        x = {"j": g["j"], "e": g["e"] if norm(g["e"]) != norm(g["j"]) else "", "n": g["n"], "a27": None}
        agregar_2026(x, g)
        salida.append(x)
    salida.sort(key=lambda x: -max(x["a27"] or 0, x.get("v26", 0)))

    entes = universidades() + entes_fuera()
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
        "entes": entes,
    }
    DESTINO.write_text(json.dumps(datos, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(salida)} programas ({emparejados} con datos de los dos años), {len(entes)} entes fuera de la APN")
    print(f"Total 2027: {t27/1e6:,.2f} billones · 2026 ley {t26[0]/1e6:,.2f} vigente {t26[1]/1e6:,.2f} devengado {t26[2]/1e6:,.2f}")
    print(f"{DESTINO.stat().st_size/1e6:.2f} MB")


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
    x["act26"] = sorted(([n] + [r1(v) for v in vs] for n, vs in g["act"].items() if any(abs(v) >= 0.05 for v in vs)),
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
