#!/usr/bin/env python3
"""Baja la ejecución del presupuesto nacional por jurisdicción desde la API de
Presupuesto Abierto y la guarda en datos/ejecucion_ministerios.json.

Necesita un token gratuito: https://www.presupuestoabierto.gob.ar/sici/api-pac
Uso:   PRESUPUESTO_ABIERTO_TOKEN=xxxx python3 scripts/actualizar_ejecucion.py [ejercicio]
Prueba sin conexión: PA_CSV_DIR=carpeta python3 scripts/actualizar_ejecucion.py
  (lee jurisdicciones.csv y mensual.csv de esa carpeta)

Sale con código 0 si actualizó o si no hubo cambios, y con código 1 si falló.
"""
import csv, datetime, io, json, os, pathlib, sys, urllib.error, urllib.request

RAIZ = pathlib.Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "datos" / "ejecucion_ministerios.json"
API = "https://www.presupuestoabierto.gob.ar/api/v1/credito?format=csv"


def numero(v):
    v = (v or "").strip()
    if not v:
        return 0.0
    if "," in v and "." in v:          # 1.234,56
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:                      # 1234,56
        v = v.replace(",", ".")
    return float(v)


def consulta(columnas, ejercicio, nombre):
    carpeta = os.environ.get("PA_CSV_DIR")
    if carpeta:
        texto = (pathlib.Path(carpeta) / f"{nombre}.csv").read_text(encoding="utf-8-sig")
        return list(csv.DictReader(io.StringIO(texto)))
    token = os.environ.get("PRESUPUESTO_ABIERTO_TOKEN")
    if not token:
        sys.exit("Falta PRESUPUESTO_ABIERTO_TOKEN (se pide gratis en https://www.presupuestoabierto.gob.ar/sici/api-pac).")
    cuerpo = json.dumps({"title": "presupuesto-argentina " + nombre, "ejercicios": [ejercicio],
                         "columns": columnas, "filters": []}).encode()
    ultimo = None
    for auth in ("Bearer " + token, token):  # la documentación no aclara si lleva el prefijo
        req = urllib.request.Request(API, data=cuerpo, method="POST", headers={
            "Authorization": auth, "Content-Type": "application/json", "Accept": "text/csv, application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                texto = r.read().decode("utf-8-sig")
            if texto.lstrip().startswith(("{", "[")):
                datos = json.loads(texto)
                if isinstance(datos, dict):
                    datos = next((v for v in datos.values() if isinstance(v, list)), [])
                return datos
            return list(csv.DictReader(io.StringIO(texto)))
        except urllib.error.HTTPError as e:
            ultimo = e
            if e.code in (401, 403):
                continue
            raise
    sys.exit(f"La API rechazó el token ({ultimo.code}). Revisá el secreto PRESUPUESTO_ABIERTO_TOKEN.")


def main():
    ejercicio = int(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today().year
    filas = consulta(["jurisdiccion_desc", "credito_presupuestado", "credito_vigente", "credito_devengado"], ejercicio, "jurisdicciones")
    mensual = consulta(["impacto_presupuestario_mes", "credito_devengado"], ejercicio, "mensual")
    if not filas:
        sys.exit("La API no devolvió filas.")

    por_jur = {}
    for f in filas:
        j = (f.get("jurisdiccion_desc") or "").strip()
        if not j:
            continue
        a = por_jur.setdefault(j, [0.0, 0.0, 0.0])
        a[0] += numero(f.get("credito_presupuestado"))
        a[1] += numero(f.get("credito_vigente"))
        a[2] += numero(f.get("credito_devengado"))
    total_vig = sum(a[1] for a in por_jur.values())
    escala = 1e6 if total_vig > 1e10 else 1  # si viene en pesos, se pasa a millones

    meses = {}
    for f in mensual:
        try:
            m = int(numero(f.get("impacto_presupuestario_mes")))
        except ValueError:
            continue
        meses[m] = meses.get(m, 0.0) + numero(f.get("credito_devengado")) / escala
    con_gasto = [m for m, v in meses.items() if 1 <= m <= 12 and v > 0]
    if not con_gasto:
        sys.exit("No hay meses con gasto devengado.")

    ultimo = max(con_gasto)
    previos = sorted(meses[m] for m in con_gasto if m < ultimo)
    mediana = previos[len(previos) // 2] if previos else 0
    parcial = bool(previos) and meses[ultimo] < 0.5 * mediana  # el mes en curso todavía se está cargando
    salida = {
        "ejercicio": ejercicio,
        "ultimo_mes": ultimo,
        "ultimo_mes_completo": ultimo - 1 if parcial else ultimo,
        "mes_parcial": parcial,
        "fuente": "Presupuesto Abierto (Ministerio de Economía), API de crédito",
        "unidad": "millones de pesos",
        "filas": sorted(({
            "jurisdiccion": j,
            "credito_inicial": round(a[0] / escala, 1),
            "credito_vigente": round(a[1] / escala, 1),
            "devengado": round(a[2] / escala, 1),
            "pct_ejecutado": round(a[2] / a[1] * 100, 1) if a[1] else 0.0,
        } for j, a in por_jur.items() if a[1] > 0), key=lambda r: -r["credito_vigente"]),
        "mensual": [{"mes": m, "devengado": round(meses[m], 1)} for m in sorted(meses) if 1 <= m <= 12],
    }
    anterior = json.loads(DESTINO.read_text(encoding="utf-8")) if DESTINO.exists() else {}
    anterior.pop("actualizado", None)
    if anterior == salida:
        print("Sin cambios.")
        return
    salida["actualizado"] = datetime.date.today().isoformat()
    DESTINO.write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Actualizado: {len(salida['filas'])} jurisdicciones, hasta el mes {salida['ultimo_mes']}.")


if __name__ == "__main__":
    main()
