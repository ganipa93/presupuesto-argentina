#!/usr/bin/env python3
"""Baja las fuentes de la serie larga de presupuestos (1995 en adelante):

1. Presupuesto Abierto (Ministerio de Economía): por año, el crédito de la ley (presupuestado),
   el vigente y el devengado de la Administración Nacional, abierto por finalidad, función,
   inciso (tipo de gasto) y jurisdicción. -> fuentes/historia_larga/credito-AAAA.csv
2. API de Series de Tiempo (datos.gob.ar): PIB a precios corrientes (INDEC, bases 1993 y 2004)
   y el Gasto Público Consolidado nacional por función en % del PIB (Ministerio de Economía).
   -> fuentes/historia_larga/series.json

Necesita PRESUPUESTO_ABIERTO_TOKEN. Uso: python3 scripts/bajar_historia_larga.py [desde] [hasta]
"""
import datetime, json, os, pathlib, sys, time, urllib.error, urllib.parse, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DEST = RAIZ / "fuentes" / "historia_larga"
API = "https://www.presupuestoabierto.gob.ar/api/v1/credito?format=csv"
SERIES = "https://apis.datos.gob.ar/series/api"
COLUMNAS = ["finalidad_desc", "funcion_desc", "inciso_desc", "jurisdiccion_desc",
            "credito_presupuestado", "credito_vigente", "credito_devengado"]
# PIB a precios corrientes (millones de $). Si un id deja de existir, se buscan candidatos y se guardan para revisar.
PIB_IDS = os.environ.get("PIB_IDS", "")
BUSQUEDAS_PIB = ["producto interno bruto precios corrientes base 2004", "producto interno bruto precios corrientes base 1993",
                 "pib precios de mercado corrientes", "valor agregado bruto precios corrientes"]


def credito(anio, token):
    cuerpo = json.dumps({"title": f"presupuesto-argentina historia larga {anio}", "ejercicios": [anio], "columns": COLUMNAS, "filters": []}).encode()
    ultimo = None
    for intento in range(3):
        for auth in ("Bearer " + token, token):
            req = urllib.request.Request(API, data=cuerpo, method="POST", headers={"Authorization": auth, "Content-Type": "application/json"})
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    return r.read()
            except urllib.error.HTTPError as e:
                ultimo = e
                if e.code in (401, 403):
                    continue
                break
            except Exception as e:  # noqa: BLE001
                ultimo = e
        time.sleep(10 * (intento + 1))
    raise RuntimeError(f"{anio}: {ultimo}")


def get_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "presupuesto-argentina"}), timeout=120) as r:
        return json.loads(r.read())


def buscar(q, limit=100):
    d = get_json(f"{SERIES}/search/?q={urllib.parse.quote(q)}&limit={limit}")
    return [{"id": x["field"]["id"], "desc": x["field"]["description"], "freq": x["field"]["frequency"],
             "desde": x["field"]["time_index_start"], "hasta": x["field"]["time_index_end"],
             "unidad": x["field"].get("units"), "dataset": x["dataset"]["title"]} for x in d["data"]]


def valores(ids):
    out = {}
    for i in range(0, len(ids), 20):
        grupo = ids[i:i + 20]
        d = get_json(f"{SERIES}/series/?ids={','.join(grupo)}&format=json&limit=5000&collapse=year&collapse_aggregation=sum")
        for j, sid in enumerate(grupo):
            out[sid] = {f[0][:4]: f[j + 1] for f in d["data"] if f[j + 1] is not None}
    return out


def main():
    token = os.environ.get("PRESUPUESTO_ABIERTO_TOKEN")
    if not token:
        sys.exit("Falta PRESUPUESTO_ABIERTO_TOKEN.")
    desde = int(sys.argv[1]) if len(sys.argv) > 1 else 1995
    hasta = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.date.today().year
    DEST.mkdir(parents=True, exist_ok=True)
    fallas = 0
    for anio in range(desde, hasta + 1):
        try:
            datos = credito(anio, token)
            (DEST / f"credito-{anio}.csv").write_bytes(datos)
            print(f"OK {anio}: {len(datos):,} bytes")
        except Exception as e:  # noqa: BLE001
            fallas += 1
            print("FALLÓ", e)
    if fallas == hasta - desde + 1:
        sys.exit("No se pudo bajar ningún año.")

    # Series: candidatos de PIB (para revisar) y Gasto Público Consolidado nacional en % del PIB
    try:
        candidatos = {q: buscar(q, 60) for q in BUSQUEDAS_PIB}
        gpc = [x for q in ("Gasto público nacional en porcentaje del PIB", "Gasto público nacional en", "Gasto público consolidado en porcentaje del PIB")
               for x in buscar(q, 200) if x["desc"].startswith(("Gasto público nacional", "Gasto público consolidado en porcentaje")) and "PIB" in (x["unidad"] or "")]
        gpc = list({x["id"]: x for x in gpc}.values())
        ids = [x["id"] for x in gpc] + [i for i in PIB_IDS.split(",") if i]
        series = {"fuente": "API de Series de Tiempo, datos.gob.ar", "bajado": datetime.date.today().isoformat(),
                  "metadatos": {x["id"]: x for x in gpc}, "valores": valores(ids), "candidatos_pib": candidatos}
        (DEST / "series.json").write_text(json.dumps(series, ensure_ascii=False, indent=1), encoding="utf-8")
        print("OK series:", len(ids))
    except Exception as e:  # noqa: BLE001
        print("FALLÓ series:", e)


if __name__ == "__main__":
    main()
