#!/usr/bin/env python3
"""Baja de la API de Series de Tiempo (datos.gob.ar) las series de INDEC que describen la estructura
productiva de cada año: valor agregado por sector (industria, agro, etc.), importaciones, exportaciones,
inversión y consumo a precios corrientes, más desempleo y comercio exterior en dólares.

Guarda fuentes/historia_larga/estructura.json con:
- "valores": {id: {año: valor}} de las series de ESTRUCTURA_IDS (suma anual; para tasas, promedio)
- "candidatos": resultados de búsqueda, para revisar o reemplazar ids que dejen de existir.

No necesita token. Uso: python3 scripts/bajar_estructura.py
"""
import datetime, json, os, pathlib, time, urllib.parse, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DEST = RAIZ / "fuentes" / "historia_larga" / "estructura.json"
SERIES = "https://apis.datos.gob.ar/series/api"

# Series que se suman por año (montos) y series que se promedian (tasas, índices).
SUMA = [i for i in os.environ.get("ESTRUCTURA_SUMA", "").split(",") if i]
PROMEDIO = [i for i in os.environ.get("ESTRUCTURA_PROMEDIO", "").split(",") if i]

BUSQUEDAS = [
    "oferta y demanda globales precios corrientes anual",
    "importaciones de bienes y servicios reales precios corrientes",
    "exportaciones de bienes y servicios reales precios corrientes",
    "formación bruta de capital fijo precios corrientes",
    "consumo privado precios corrientes",
    "consumo público precios corrientes",
    "valor agregado bruto industria manufacturera precios corrientes",
    "valor agregado bruto a precios de productor anual industria manufacturera",
    "valor agregado bruto agricultura ganadería precios corrientes",
    "valor agregado bruto explotación de minas y canteras precios corrientes",
    "valor agregado bruto construcción precios corrientes",
    "valor agregado bruto comercio precios corrientes",
    "valor agregado bruto electricidad gas agua precios corrientes",
    "valor agregado bruto a precios básicos total precios corrientes",
    "tasa de desocupación",
    "exportaciones totales intercambio comercial argentino",
    "importaciones totales intercambio comercial argentino",
    "índice de producción industrial manufacturero",
]


def get_json(url):
    for intento in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "presupuesto-argentina"}), timeout=120) as r:
                return json.loads(r.read())
        except Exception:  # noqa: BLE001 - la API corta por exceso de pedidos: esperar y reintentar
            if intento == 3:
                raise
            time.sleep(5 * (intento + 1))


def buscar(q, limit=100):
    d = get_json(f"{SERIES}/search/?q={urllib.parse.quote(q)}&limit={limit}")
    return [{"id": x["field"]["id"], "desc": x["field"]["description"], "freq": x["field"]["frequency"],
             "desde": x["field"]["time_index_start"], "hasta": x["field"]["time_index_end"],
             "unidad": x["field"].get("units"), "dataset": x["dataset"]["title"]} for x in d["data"]]


def valores(ids, agregacion):
    out = {}
    for i in range(0, len(ids), 20):
        grupo = ids[i:i + 20]
        try:
            d = get_json(f"{SERIES}/series/?ids={','.join(grupo)}&format=json&limit=5000&collapse=year&collapse_aggregation={agregacion}")
        except Exception as e:  # noqa: BLE001 - un id malo tira todo el grupo: probar de a uno
            print("grupo falló, de a uno:", e)
            for sid in grupo:
                try:
                    out.update(valores([sid], agregacion))
                except Exception as e2:  # noqa: BLE001
                    print("FALLÓ", sid, e2)
            continue
        for j, sid in enumerate(grupo):
            out[sid] = {f[0][:4]: f[j + 1] for f in d["data"] if f[j + 1] is not None}
    return out


# Algunas series figuran en el catálogo pero la API las devuelve vacías: se baja el CSV original.
CSVS = {
    "intercambio-comercial-anual.csv": "https://infra.datos.gob.ar/catalog/sspm/dataset/74/distribution/74.1/download/intercambio-comercial-argentino-anual.csv",
    "eph-puntual.csv": "https://infra.datos.gob.ar/catalog/sspm/dataset/42/distribution/42.2/download/evolucion-principales-variables-ocupacionales-eph-puntual-valores-mensuales.csv",
}


def main():
    for nombre, url in CSVS.items():
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "presupuesto-argentina"}), timeout=120) as r:
                (DEST.parent / nombre).write_bytes(r.read())
            print("OK", nombre)
        except Exception as e:  # noqa: BLE001
            print("FALLÓ", nombre, e)
    previo = json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {}
    candidatos = {}
    for q in BUSQUEDAS:
        try:
            candidatos[q] = buscar(q)
        except Exception as e:  # noqa: BLE001
            print("FALLÓ búsqueda", q, e)
    vals = {**previo.get("valores", {}), **valores(SUMA, "sum"), **valores(PROMEDIO, "avg")}
    # Series que vinieron vacías: guardar la respuesta cruda sin agregar, para revisar
    debug = {}
    for sid in [i for i in SUMA + PROMEDIO if not vals.get(i)]:
        try:
            d = get_json(f"{SERIES}/series/?ids={sid}&format=json&limit=40&sort=desc")
            debug[sid] = {"data": d.get("data"), "meta": d.get("meta")}
        except Exception as e:  # noqa: BLE001
            debug[sid] = str(e)
    out = {"debug": debug, "fuente": "API de Series de Tiempo, datos.gob.ar (INDEC)", "bajado": datetime.date.today().isoformat(),
           "suma": sorted(set(previo.get("suma", [])) | set(SUMA)), "promedio": sorted(set(previo.get("promedio", [])) | set(PROMEDIO)), "valores": vals, "candidatos": candidatos or previo.get("candidatos", {})}
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("OK estructura:", len(vals), "series,", sum(len(v) for v in candidatos.values()), "candidatos")


if __name__ == "__main__":
    main()
