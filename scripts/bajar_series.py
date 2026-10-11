#!/usr/bin/env python3
"""Baja series oficiales de la API de Series de Tiempo (datos.gob.ar) y actualiza:
  - fuentes/ipc_indec.json: IPC nacional del INDEC (promedios anuales y meses recientes).
  - datos/recaudacion.json: recaudación tributaria mensual (total, DGI, DGA y seguridad social),
    Secretaría de Hacienda, Ministerio de Economía.
Si aparece un mes nuevo de recaudación, deja una novedad en datos/novedades.json.
Uso: python3 scripts/bajar_series.py
"""
import datetime, json, pathlib, sys, urllib.parse, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
API = "https://apis.datos.gob.ar/series/api/series/"
IPC = "148.3_INIVELNAL_DICI_M_26"
RECAUDACION = {"total": "172.3_TL_RECAION_M_0_0_17", "dgi": "172.3_SOTAL_DDGI_M_0_0_12",
               "dga": "172.3_SOTAL_DDGA_M_0_0_12", "seguridad_social": "172.3_SRIDAD_IAL_M_0_0_16"}
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def serie(ids, desde):
    q = urllib.parse.urlencode({"ids": ids, "format": "json", "start_date": desde, "limit": 1000})
    req = urllib.request.Request(API + "?" + q, headers={"User-Agent": "presupuesto-argentina"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)["data"]


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
