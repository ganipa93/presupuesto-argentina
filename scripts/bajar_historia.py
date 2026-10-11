#!/usr/bin/env python3
"""Baja de Presupuesto Abierto el crédito y el gasto (devengado) por programa de cada año
desde 2020, para las series históricas. Guarda fuentes/datasets/historia-AAAA.csv.

Necesita PRESUPUESTO_ABIERTO_TOKEN. Uso: python3 scripts/bajar_historia.py [desde] [hasta]
"""
import datetime, json, os, pathlib, sys, time, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DEST = RAIZ / "fuentes" / "datasets"
API = "https://www.presupuestoabierto.gob.ar/api/v1/credito?format=csv"
COLUMNAS = ["jurisdiccion_desc", "subjurisdiccion_desc", "entidad_desc", "programa_desc",
            "credito_presupuestado", "credito_vigente", "credito_devengado"]


def bajar(anio, token):
    cuerpo = json.dumps({"title": f"presupuesto-argentina historia {anio}", "ejercicios": [anio], "columns": COLUMNAS, "filters": []}).encode()
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
            except Exception as e:  # noqa: BLE001  (cortes de red: se reintenta)
                ultimo = e
        time.sleep(10 * (intento + 1))
    raise RuntimeError(f"{anio}: {ultimo}")


def main():
    token = os.environ.get("PRESUPUESTO_ABIERTO_TOKEN")
    if not token:
        sys.exit("Falta PRESUPUESTO_ABIERTO_TOKEN.")
    desde = int(sys.argv[1]) if len(sys.argv) > 1 else 2020
    hasta = int(sys.argv[2]) if len(sys.argv) > 2 else datetime.date.today().year
    DEST.mkdir(parents=True, exist_ok=True)
    fallas = []
    for anio in range(desde, hasta + 1):
        try:
            datos = bajar(anio, token)
            (DEST / f"historia-{anio}.csv").write_bytes(datos)
            print(f"OK {anio}: {len(datos):,} bytes")
        except Exception as e:  # noqa: BLE001
            fallas.append(str(e)); print("FALLÓ", e)
    if len(fallas) == hasta - desde + 1:
        sys.exit("No se pudo bajar ningún año.")


if __name__ == "__main__":
    main()
