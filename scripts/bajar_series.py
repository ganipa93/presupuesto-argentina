#!/usr/bin/env python3
"""Baja series oficiales de la API de Series de Tiempo (datos.gob.ar) y actualiza:
  - fuentes/ipc_indec.json: IPC nacional del INDEC (promedios anuales y meses recientes).
  - datos/recaudacion.json: recaudación tributaria mensual (total, DGI, DGA y seguridad social),
    Secretaría de Hacienda, Ministerio de Economía.
  - datos/dolar.json: dólar oficial (BCRA, Comunicación A 3500), promedio de cada mes y de cada año,
    para mostrar los montos también en dólares.
Si aparece un mes nuevo de recaudación, deja una novedad en datos/novedades.json.
Uso: python3 scripts/bajar_series.py
"""
import datetime, json, pathlib, sys, urllib.parse, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
API = "https://apis.datos.gob.ar/series/api/series/"
IPC = "148.3_INIVELNAL_DICI_M_26"
DOLAR = "168.1_T_CAMBI500_D_0_0_17"  # BCRA, tipo de cambio de referencia Com. A 3500, diario
RECAUDACION = {"total": "172.3_TL_RECAION_M_0_0_17", "dgi": "172.3_SOTAL_DDGI_M_0_0_12",
               "dga": "172.3_SOTAL_DDGA_M_0_0_12", "seguridad_social": "172.3_SRIDAD_IAL_M_0_0_16"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def serie(ids, desde, **extra):
    q = urllib.parse.urlencode({"ids": ids, "format": "json", "start_date": desde, "limit": 1000, **extra})
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": "presupuesto-argentina"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["data"]


def armar_dolar(mensual, hoy):
    """mensual: [("AAAA-MM", promedio)] → datos/dolar.json con el promedio de cada año.
    El año en curso usa los meses publicados. 2027 sale de la proyección del proyecto de ley
    (dólar de diciembre 2026 y diciembre 2027): promedio de un camino parejo entre ambos."""
    por_anio = {}
    for m, v in mensual:
        por_anio.setdefault(m[:4], []).append(v)
    sup = {r["clave"]: r for r in json.loads((RAIZ / "datos" / "supuestos.json").read_text(encoding="utf-8"))}
    d26, d27 = sup["tc"]["estimado2026"], sup["tc"]["proyecto2027"]
    p27 = sum(d26 * (d27 / d26) ** (k / 12) for k in range(1, 13)) / 12
    anio = str(hoy.year)
    return {"fuente": "BCRA, tipo de cambio de referencia (Comunicación A 3500), promedio mensual, vía API de Series de Tiempo de datos.gob.ar. 2027: proyección del Ministerio de Economía en el proyecto de Presupuesto 2027.",
            "url": "https://apis.datos.gob.ar/series/api/series/?ids=" + DOLAR + "&collapse=month&collapse_aggregation=avg",
            "unidad": "pesos por dólar",
            "promedio": {**{a: round(sum(vs) / len(vs), 2) for a, vs in por_anio.items()}, "2027": round(p27, 2)},
            "meses_en_curso": len(por_anio.get(anio, [])), "ultimo_mes": mensual[-1][0],
            "proyecto2027": {"dic2026": d26, "dic2027": d27},
            "mensual": [[m, round(v, 2)] for m, v in mensual]}


def main():
    hoy = datetime.date.today()
    # IPC
    ipc = serie(IPC, "2019-01-01")
    por_anio = {}
    for f, v in ipc:
        por_anio.setdefault(f[:4], []).append(v)
    f_ipc = RAIZ / "fuentes" / "ipc_indec.json"
    datos = json.loads(f_ipc.read_text(encoding="utf-8"))
    datos["promedio_anual"] = {a: sum(vs) / 12 for a, vs in por_anio.items() if len(vs) == 12}
    datos["mensual_2025_2026"] = {f[:7]: v for f, v in ipc if f >= "2025-01"}
    f_ipc.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    print("IPC hasta", ipc[-1][0])
    # Dólar oficial
    dol = serie(DOLAR, "2019-01-01", collapse="month", collapse_aggregation="avg")
    out_d = armar_dolar([(f[:7], v) for f, v in dol if v is not None], hoy)
    f_dol = RAIZ / "datos" / "dolar.json"
    if not f_dol.exists() or json.loads(f_dol.read_text(encoding="utf-8")).get("mensual") != out_d["mensual"]:
        out_d["actualizado"] = hoy.isoformat()
        f_dol.write_text(json.dumps(out_d, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Dólar hasta", out_d["ultimo_mes"])
    # Recaudación
    desde = f"{hoy.year - 2}-01-01"
    out = {"fuente": "Secretaría de Hacienda (Ministerio de Economía), recaudación tributaria mensual, vía API de Series de Tiempo de datos.gob.ar.",
           "url": "https://apis.datos.gob.ar/series/api/series/?ids=" + ",".join(RECAUDACION.values()), "unidad": "millones de pesos", "series": {}}
    for k, i in RECAUDACION.items():
        out["series"][k] = [[f[:7], round(v, 1)] for f, v in serie(i, desde) if v is not None]
    f_rec = RAIZ / "datos" / "recaudacion.json"
    anterior = json.loads(f_rec.read_text(encoding="utf-8")) if f_rec.exists() else {}
    if anterior.get("series") == out["series"]:
        print("Recaudación sin cambios.")
        return
    # Si la API devuelve una serie vacía o más corta que la que ya tenemos, es un fallo de la fuente:
    # se conservan los datos anteriores en vez de publicar una página rota.
    for k, filas in out["series"].items():
        previo = anterior.get("series", {}).get(k) or []
        if not filas or len(filas) < len(previo) or (previo and filas[-1][0] < previo[-1][0]):
            print(f"Recaudación: la serie «{k}» vino incompleta ({len(filas)} meses contra {len(previo)}); se conservan los datos anteriores.")
            return
    out["actualizado"] = hoy.isoformat()
    f_rec.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    ultimo = out["series"]["total"][-1][0]
    print("Recaudación hasta", ultimo)
    viejo = (anterior.get("series", {}).get("total") or [[None]])[-1][0]
    if ultimo != viejo:
        nov = RAIZ / "datos" / "novedades.json"
        lista = json.loads(nov.read_text(encoding="utf-8"))
        a, m = ultimo.split("-")
        lista.append({"fecha": hoy.isoformat(), "titulo": f"Recaudación actualizada con datos de {MESES[int(m) - 1]} de {a}",
                      "texto": "Cuánto recaudó la Nación en el mes y en lo que va del año, comparado con el año anterior y descontada la inflación.", "link": "/recaudacion"})
        nov.write_text(json.dumps(lista, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        sys.exit(f"No se pudieron bajar las series: {e}")
