#!/usr/bin/env python3
"""Baja los datasets oficiales con el detalle por programa y los guarda en fuentes/datasets/.

- Presupuesto ciudadano (Ministerio de Economía, ONP): apertura programática, partidas,
  finalidad-función, metas físicas y recursos, del proyecto 2027 y de 2026.
- Presupuesto Abierto (API de crédito): crédito y gasto 2026 por organismo, programa,
  actividad y provincia. Necesita PRESUPUESTO_ABIERTO_TOKEN.

Uso: python3 scripts/bajar_datasets.py            (todo)
     python3 scripts/bajar_datasets.py --solo-api  (solo la ejecución 2026, para la actualización mensual)
"""
import json, os, pathlib, sys, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DEST = RAIZ / "fuentes" / "datasets"
BASE = "https://www.argentina.gob.ar/sites/default/files/"
ARCHIVOS = {
    "2027-apertura-programatica.xlsx": "data_set_presupuesto_ciudadano_apertura_2027.xlsx",
    "2027-partida-presupuestaria.xlsx": "data_set_presupuesto_ciudadano_partida_presupuestaria_2027.xlsx",
    "2027-recursos.xlsx": "data_set_presupuesto_ciudadano_recursos_2027.xlsx",
    "2027-mediciones-fisicas.xlsx": "data_set_presupuesto_ciudadno_mediciones_fisicas_2027.xlsx",
    "2027-finalidad-funcion.xlsx": "data_set_presupuesto_ciudadano_finalidad_funcion_2027.xlsx",
    "2026-apertura-programatica.xlsx": "data_set_presupuesto_ciudadano_apertura_.xlsx",
    "2026-apertura-por-inciso.xlsx": "data_set_presupuesto_ciudadano_apertura_inciso_.xlsx",
}


def bajar(url, destino):
    req = urllib.request.Request(url, headers={"User-Agent": "presupuesto-argentina (github.com/ganipa93/presupuesto-argentina)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        datos = r.read()
    destino.write_bytes(datos)
    print(f"OK {destino.name}: {len(datos):,} bytes")


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    fallas = []
    solo_api = "--solo-api" in sys.argv
    for nombre, archivo in ({} if solo_api else ARCHIVOS).items():
        try:
            bajar(BASE + archivo, DEST / nombre)
        except Exception as e:  # noqa: BLE001
            fallas.append(f"{nombre}: {e}")
            print("FALLÓ", nombre, e)
    token = os.environ.get("PRESUPUESTO_ABIERTO_TOKEN")
    if token:
        columnas = ["jurisdiccion_desc", "subjurisdiccion_desc", "entidad_desc", "programa_desc", "subprograma_desc",
                    "actividad_desc", "ubicacion_geografica_desc", "inciso_desc",
                    "credito_presupuestado", "credito_vigente", "credito_devengado"]
        cuerpo = json.dumps({"title": "presupuesto-argentina programas", "ejercicios": [2026], "columns": columnas, "filters": []}).encode()
        for auth in ("Bearer " + token, token):
            try:
                req = urllib.request.Request("https://www.presupuestoabierto.gob.ar/api/v1/credito?format=csv", data=cuerpo, method="POST",
                                             headers={"Authorization": auth, "Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=300) as r:
                    (DEST / "2026-credito-por-programa.csv").write_bytes(r.read())
                print("OK 2026-credito-por-programa.csv")
                break
            except urllib.error.HTTPError as e:
                if e.code not in (401, 403):
                    fallas.append(f"API: {e}"); print("FALLÓ API", e); break
    if solo_api and (not token or fallas):
        sys.exit("No se pudo bajar la ejecución por programa.")
    if fallas and len(fallas) == len(ARCHIVOS) + (1 if token else 0):
        sys.exit("No se pudo bajar nada.")


if __name__ == "__main__":
    main()
