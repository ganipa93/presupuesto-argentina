#!/usr/bin/env python3
"""Avisa si la inflación, el dólar o la recaudación del sitio quedaron atrasados.

Sale con código 1 y explica qué falta si algún dato está más viejo de lo esperable:
  - IPC: el INDEC publica el mes anterior a mediados de mes → desde el día 16 se espera el mes anterior.
  - Recaudación: Hacienda publica el mes anterior en los primeros días → desde el día 8, el mes anterior.
  - Dólar: es diario → desde el día 6 se espera el mes en curso.
Uso: python3 scripts/revisar_frescura.py [AAAA-MM-DD]   (fecha opcional, para probar)
"""
import datetime, json, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent


def mes_menos(fecha, n):
    m = fecha.year * 12 + fecha.month - 1 - n
    return f"{m // 12:04d}-{m % 12 + 1:02d}"


def problemas(hoy):
    leer = lambda p: json.loads((RAIZ / p).read_text(encoding="utf-8"))
    out = []
    ipc = max(leer("fuentes/ipc_indec.json")["mensual_2025_2026"])
    esperado = mes_menos(hoy, 1 if hoy.day >= 16 else 2)
    if ipc < esperado:
        out.append(f"Inflación (IPC): el sitio llega hasta {ipc} y ya debería tener {esperado}.")
    dol = leer("datos/dolar.json")["ultimo_mes"]
    esperado = mes_menos(hoy, 0 if hoy.day >= 6 else 1)
    if dol < esperado:
        out.append(f"Dólar oficial: el sitio llega hasta {dol} y ya debería tener {esperado}.")
    rec = leer("datos/recaudacion.json")["series"]["total"][-1][0]
    esperado = mes_menos(hoy, 1 if hoy.day >= 8 else 2)
    if rec < esperado:
        out.append(f"Recaudación: el sitio llega hasta {rec} y ya debería tener {esperado}.")
    return out


if __name__ == "__main__":
    hoy = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    p = problemas(hoy)
    for x in p:
        print("- " + x)
    sys.exit(1 if p else 0)
