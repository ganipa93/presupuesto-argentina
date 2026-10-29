#!/usr/bin/env python3
"""Arma datos/historia.json: los presupuestos nacionales desde 1995, año por año y por gobierno.

Entradas (las baja scripts/bajar_historia_larga.py):
  fuentes/historia_larga/credito-AAAA.csv  Presupuesto Abierto: ley, vigente y devengado por finalidad,
                                           función, inciso y jurisdicción (millones de $).
  fuentes/historia_larga/series.json       PIB a precios corrientes (INDEC) y Gasto Público Consolidado.
  datos/funciones.json, datos/recursos.json  2026 estimado y proyecto 2027 (Proyecto de Presupuesto 2027).

Todo se compara en % del PIB, que no necesita descontar la inflación (el IPC nacional del INDEC empieza
en 2016 y el de 2007-2015 estuvo intervenido).
"""
import csv, json, pathlib, unicodedata
from collections import defaultdict

RAIZ = pathlib.Path(__file__).resolve().parent.parent
HL = RAIZ / "fuentes" / "historia_larga"

# Gobiernos: a qué gestión se cuenta cada año de ejecución. El año de un cambio de gobierno se le cuenta
# a quien gobernó la mayor parte (2003: N. Kirchner asumió el 25 de mayo).
GOBIERNOS = [
    {"id": "menem", "contexto": "Convertibilidad (1 peso = 1 dólar). Desde 1994 parte de los aportes jubilatorios fue a las AFJP privadas.", "nombre": "Carlos Menem", "periodo": "1989-1999", "desde": 1995, "hasta": 1999,
     "nota": "Gobernó desde julio de 1989; la serie con detalle empieza en 1995."},
    {"id": "delarua", "contexto": "Recesión y suba de los intereses de la deuda. En 2001, ley de «déficit cero»: recorte del 13% en sueldos estatales y jubilaciones altas.", "nombre": "Fernando de la Rúa", "periodo": "1999-2001", "desde": 2000, "hasta": 2001,
     "nota": "Renunció el 20 de diciembre de 2001."},
    {"id": "duhalde", "contexto": "Salida de la convertibilidad, devaluación y default de la deuda. El PIB cayó cerca de 11% en 2002.", "nombre": "Eduardo Duhalde", "periodo": "2002-2003", "desde": 2002, "hasta": 2002,
     "nota": "Gobernó de enero de 2002 a mayo de 2003; 2003 se cuenta a N. Kirchner."},
    {"id": "nkirchner", "contexto": "Crecimiento económico. Empiezan a crecer los subsidios a la energía y el transporte. Moratoria previsional (2005-2007).", "nombre": "Néstor Kirchner", "periodo": "2003-2007", "desde": 2003, "hasta": 2007,
     "nota": "Asumió el 25 de mayo de 2003, con el presupuesto 2003 ya aprobado."},
    {"id": "cfk", "contexto": "Las AFJP pasan al Estado (2008) y se crea la AUH (2009). Crisis internacional de 2009. Los subsidios energéticos llegan a su máximo en 2014.", "nombre": "Cristina Fernández de Kirchner", "periodo": "2007-2015", "desde": 2008, "hasta": 2015,
     "nota": "Dos mandatos seguidos."},
    {"id": "macri", "contexto": "Baja de subsidios energéticos con suba de tarifas. Más deuda e intereses; acuerdo con el FMI en 2018.", "nombre": "Mauricio Macri", "periodo": "2015-2019", "desde": 2016, "hasta": 2019, "nota": ""},
    {"id": "afernandez", "contexto": "Pandemia en 2020 (IFE, refuerzos a jubilados y planes). Acuerdo con el FMI en 2022. Diputados rechazó el presupuesto 2022.", "nombre": "Alberto Fernández", "periodo": "2019-2023", "desde": 2020, "hasta": 2023, "nota": ""},
    {"id": "milei", "contexto": "Fuerte reducción del gasto para lograr superávit: caen la obra pública, las transferencias a provincias y los subsidios. 2024 y 2025 con el presupuesto 2023 prorrogado.", "nombre": "Javier Milei", "periodo": "2023-", "desde": 2024, "hasta": 2026,
     "nota": "En curso: 2026 es el cierre que estima el Proyecto 2027."},
]

# Qué norma rigió cada año. Fuentes: «Cupos presupuestarios anuales» (argentina.gob.ar/node/90949) hasta 2018,
# InfoLEG y Boletín Oficial después. Prórroga = se volvió a usar el presupuesto del año anterior (art. 27, Ley 24.156).
LEYES = {1995: "Ley 24.447", 1996: "Ley 24.624", 1997: "Ley 24.764", 1998: "Ley 24.938", 1999: "Ley 25.064",
         2000: "Ley 25.237", 2001: "Ley 25.401", 2002: "Ley 25.565", 2003: "Ley 25.725", 2004: "Ley 25.827",
         2005: "Ley 25.967", 2006: "Ley 26.078", 2007: "Ley 26.198", 2008: "Ley 26.337", 2009: "Ley 26.422",
         2010: "Ley 26.546", 2011: "Prórroga del presupuesto 2010 (Decreto 2054/2010)", 2012: "Ley 26.728",
         2013: "Ley 26.784", 2014: "Ley 26.895", 2015: "Ley 27.008", 2016: "Ley 27.198", 2017: "Ley 27.341",
         2018: "Ley 27.431", 2019: "Ley 27.467", 2020: "Prórroga del presupuesto 2019", 2021: "Ley 27.591",
         2022: "Prórroga: Diputados rechazó el proyecto 2022", 2023: "Ley 27.701",
         2024: "Prórroga del presupuesto 2023", 2025: "Segunda prórroga del presupuesto 2023 (Decreto 1131/2024)",
         2026: "Ley 27.798", 2027: "Proyecto de ley (en el Congreso)"}
PRORROGAS = {2011, 2020, 2022, 2024, 2025}

# Rubros para el público: (id, nombre). Cada función del clasificador cae en uno.
RUBROS = [("seg_social", "Jubilaciones, pensiones y asignaciones"), ("asistencia", "Asistencia social"),
          ("educacion", "Educación y cultura"), ("salud", "Salud"), ("ciencia", "Ciencia y técnica"),
          ("otros_sociales", "Trabajo, vivienda y agua potable"), ("energia", "Energía y combustibles"),
          ("transporte", "Transporte"), ("otros_econ", "Otros servicios económicos"),
          ("defensa", "Defensa y seguridad"), ("provincias", "Ayuda a provincias"),
          ("estado", "Funcionamiento del Estado"), ("intereses", "Intereses de la deuda")]
TIPOS = [("personal", "Sueldos del Estado"), ("bienes", "Bienes y servicios"), ("obra", "Obras y equipamiento"),
         ("transferencias", "Transferencias (jubilaciones, planes, subsidios, provincias)"), ("intereses", "Intereses de la deuda"),
         ("otros", "Otros (préstamos y aportes de capital)")]


def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return " ".join(s.replace(",", " ").split())


def rubro(fin, fun):
    f, u = norm(fin), norm(fun)
    if f.startswith("deuda"):
        return "intereses"
    if f.startswith("servicios de defensa"):
        return "defensa"
    if f.startswith("administracion"):
        return "provincias" if u.startswith("relaciones interiores") else "estado"
    if f.startswith("servicios sociales"):
        for clave, r in (("seguridad social", "seg_social"), ("promocion", "asistencia"), ("educacion", "educacion"),
                         ("salud", "salud"), ("ciencia", "ciencia")):
            if u.startswith(clave):
                return r
        return "otros_sociales"
    if f.startswith("servicios economicos"):
        if u.startswith("energia"):
            return "energia"
        if u.startswith("transporte"):
            return "transporte"
        return "otros_econ"
    raise ValueError(f"finalidad sin rubro: {fin} / {fun}")


def tipo(inciso):
    i = norm(inciso)
    if i.startswith("gastos en personal"):
        return "personal"
    if i.startswith(("bienes de consumo", "servicios no personales")):
        return "bienes"
    if i.startswith("bienes de uso"):
        return "obra"
    if i.startswith("transferencias"):
        return "transferencias"
    if i.startswith("servicio de la deuda"):
        return "intereses"
    return "otros"


# Para 2026 (estimado) y 2027 (proyecto), el cuadro por finalidad y función del proyecto (datos/funciones.json)
RUBRO_FUNCION = {"1.5": "provincias", "3.1": "salud", "3.2": "asistencia", "3.3": "seg_social",
                 "3.4": "educacion", "3.5": "ciencia", "3.6": "otros_sociales", "3.7": "otros_sociales", "3.8": "otros_sociales",
                 "4.1": "energia", "4.3": "transporte", "4.2": "otros_econ", "4.4": "otros_econ", "4.5": "otros_econ",
                 "4.6": "otros_econ", "4.7": "otros_econ", "4.8": "otros_econ", "5": "intereses"}


def pib_serie():
    """PIB a precios corrientes (millones de $). 2004 en adelante: INDEC base 2004. 1993-2003: la serie base 1993
    empalmada con la base 2004 (se aplica el cociente de 2004, que es como se retropola una serie nueva).
    2026 y 2027: el PIB que usa el propio Proyecto 2027 (recaudación en pesos dividida por su % del PIB)."""
    v = json.loads((HL / "series.json").read_text(encoding="utf-8"))["valores"]
    b93 = {int(a): x for a, x in v["2.3_OGP_1993_A_17"].items()}
    b04 = {int(a): x for a, x in v["4.3_OGP_2004_A_17"].items()}
    k = b04[2004] / b93[2004]
    pib = {a: x * k for a, x in b93.items() if a < 2004}
    pib.update(b04)
    rec = json.loads((RAIZ / "datos" / "recursos.json").read_text(encoding="utf-8"))
    for a in (2026, 2027):
        pib[a] = sum(r[f"y{a}"] for r in rec) / sum(r[f"pib{a}"] for r in rec) * 100
    return pib, k


def real_y_poblacion(pib):
    """PIB a precios constantes (millones de pesos de 2004) y población.
    PIB real: INDEC base 2004 desde 2004; antes, la base 1993 (la API la da trimestral en valores anualizados:
    se suma el año y se divide por 4) empalmada en 2004. 2026 y 2027: crecimiento que supone el Proyecto 2027.
    Población: INDEC (2004-2025); 1995-2003 y 2026-2027 se estiman con la tasa de crecimiento del año más cercano."""
    v = json.loads((HL / "series.json").read_text(encoding="utf-8"))["valores"]
    r93 = {int(a): x / 4 for a, x in v["5.2_PIBPM_1993_T_38"].items()}
    r04 = {int(a): x for a, x in v["6.1_PIBPM_2004_A_38"].items()}
    k = r04[2004] / r93[2004]
    real = {a: x * k for a, x in r93.items() if a < 2004}
    real.update(r04)
    sup = {r["clave"]: r for r in json.loads((RAIZ / "datos" / "supuestos.json").read_text(encoding="utf-8"))}
    real[2026] = real[2025] * (1 + sup["pbi"]["estimado2026"] / 100)
    real[2027] = real[2026] * (1 + sup["pbi"]["proyecto2027"] / 100)
    pob = {int(a): x for a, x in v["9.1_POB_2004_A_9"].items()}
    g0 = pob[2005] / pob[2004]
    for a in range(2003, 1994, -1):
        pob[a] = pob[a + 1] / g0
    g1 = pob[2025] / pob[2024]
    for a in (2026, 2027):
        pob[a] = pob[a - 1] * g1
    return real, pob, round(k, 4), round((g0 - 1) * 100, 2)


def resultado_fiscal(pib):
    """Resultado primario y financiero del Sector Público Nacional (base caja, Secretaría de Hacienda), en millones de $.
    Para que los años sean comparables, el primario es «sin rentas»: sin las utilidades del BCRA ni las rentas del FGS, que
    hasta 2014 se contaban como ingresos (desde 2015 la metodología 2017 ya las excluye). El financiero se arma igual:
    primario sin rentas menos los intereses (intereses = primario oficial menos financiero oficial de cada metodología).
    2026 y 2027: la cuenta de la Administración Nacional del Proyecto 2027 (pág. 92), en % del PIB."""
    v = json.loads((HL / "series.json").read_text(encoding="utf-8"))["valores"]
    get = lambda ids, a: next((v[i][str(a)] for i in ids if str(a) in v.get(i, {})), None)
    prim_of = ["379.1_SUPERAVIT_006__28_89", "379.2_SUPERAVIT_014__28_63", "379.3_SUPERAVIT_017__23_25"]
    fin_of = ["379.1_RESULTADO_006__23_58", "379.2_RESULTADO_014__23_28", "379.3_RESULTADO_017__18_83"]
    prim_sr = ["379.4_RESULTADO_006__36_27", "379.2_RESULTADO_014__36_75"]
    out = {}
    for a in range(1995, 2026):
        po, fo = get(prim_of, a), get(fin_of, a)
        if po is None or fo is None:
            continue
        ps = get(prim_sr, a) if a <= 2014 else po
        if ps is None:
            continue
        out[a] = {"res_prim": round(ps, 1), "res_fin": round(ps - (po - fo), 1), "res_fuente": "spn"}
    cp = {r["concepto"]: r for r in json.loads((RAIZ / "datos" / "cuenta_pib.json").read_text(encoding="utf-8"))}
    for a in (2026, 2027):
        prim = cp["Resultado primario"][f"pib{a}"]
        intereses = cp["Intereses netos y rentas"][f"pib{a}"]
        out[a] = {"res_prim": round(prim * pib[a] / 100, 1), "res_fin": round((prim - intereses) * pib[a] / 100, 1), "res_fuente": "an"}
    return out


def main():
    pib, k_empalme = pib_serie()
    pib_real, pob, k_real, tasa_pob = real_y_poblacion(pib)
    anios = []
    ultimo = max(int(p.stem[-4:]) for p in HL.glob("credito-*.csv"))
    for p in sorted(HL.glob("credito-*.csv")):
        a = int(p.stem[-4:])
        if a >= 2026:
            continue  # 2026 en curso: se usa el cierre estimado del proyecto (abajo)
        tot = defaultdict(float)
        por_r, por_t = defaultdict(float), defaultdict(float)
        for x in csv.DictReader(p.open(encoding="utf-8-sig")):
            ley, vig, dev = (float(x[c] or 0) for c in ("credito_presupuestado", "credito_vigente", "credito_devengado"))
            tot["ley"] += ley; tot["vigente"] += vig; tot["gastado"] += dev
            por_r[rubro(x["finalidad_desc"], x["funcion_desc"])] += dev
            por_t[tipo(x["inciso_desc"])] += dev
        anios.append({"anio": a, "tipo": "gastado", "norma": LEYES.get(a, ""), "prorroga": a in PRORROGAS,
                      "ley": round(tot["ley"], 1), "vigente": round(tot["vigente"], 1), "gastado": round(tot["gastado"], 1),
                      "pib": round(pib[a], 1), "rubros": {r: round(v, 1) for r, v in por_r.items()},
                      "tipos": {t: round(v, 1) for t, v in por_t.items()}})
    F = json.loads((RAIZ / "datos" / "funciones.json").read_text(encoding="utf-8"))
    for a, tip in ((2026, "estimado"), (2027, "proyecto")):
        por_r = defaultdict(float)
        for r in F:
            c = r["codigo"]
            if r["nivel"] == "finalidad" and c != "5":
                continue  # se suman sus funciones; la deuda (5) no tiene funciones
            destino = RUBRO_FUNCION.get(c) or {"1": "estado", "2": "defensa"}.get(c.split(".")[0])
            if not destino:
                raise ValueError(f"función sin rubro: {c} {r['nombre']}")
            por_r[destino] += r[f"y{a}"]
        total = sum(por_r.values())
        anios.append({"anio": a, "tipo": tip, "norma": LEYES[a], "prorroga": False, "ley": None, "vigente": None,
                      "gastado": round(total, 1), "pib": round(pib[a], 1), "rubros": {r: round(v, 1) for r, v in por_r.items()}, "tipos": None})
    # Ley 2026 y vigente 2026 (Presupuesto Abierto), para la comparación ley contra lo modificado
    p26 = HL / "credito-2026.csv"
    if p26.exists():
        filas = list(csv.DictReader(p26.open(encoding="utf-8-sig")))
        x26 = next(x for x in anios if x["anio"] == 2026)
        x26["ley"] = round(sum(float(f["credito_presupuestado"] or 0) for f in filas), 1)
        x26["vigente"] = round(sum(float(f["credito_vigente"] or 0) for f in filas), 1)

    # Gasto Público Consolidado (Nación, provincias y municipios) 1980-2023, Ministerio de Economía
    S = json.loads((HL / "series.json").read_text(encoding="utf-8"))
    gpc = {"nacional": S["valores"].get("451.4_GPN_PIBPIB_0_0_7_95", {}), "consolidado": S["valores"].get("451.2_GPC_PIBPIB_0_0_7_85", {})}

    res = resultado_fiscal(pib)
    for x in anios:
        x.update(res.get(x["anio"], {}))
        x["pib_real"] = round(pib_real[x["anio"]], 1)
        x["poblacion"] = round(pob[x["anio"]])
    out = {"fuente": "Presupuesto Abierto (Ministerio de Economía) para 1995-2025; Proyecto de Presupuesto 2027 para 2026 (estimado) y 2027; "
                     "PIB a precios corrientes del INDEC (bases 1993 y 2004, empalmadas en 2004); Gasto Público Consolidado (Ministerio de Economía).",
           "unidad": "millones de pesos corrientes", "empalme_pib": round(k_empalme, 4), "empalme_pib_real": k_real, "tasa_poblacion_1995_2003": tasa_pob, "bajado_hasta": ultimo,
           "rubros": [{"id": i, "nombre": n} for i, n in RUBROS], "tipos": [{"id": i, "nombre": n} for i, n in TIPOS],
           "gobiernos": GOBIERNOS, "anios": anios, "gpc": {k: {a: round(v, 2) for a, v in s.items()} for k, s in gpc.items()}}
    (RAIZ / "datos" / "historia.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Listo: datos/historia.json ({len(anios)} años)")


if __name__ == "__main__":
    main()
