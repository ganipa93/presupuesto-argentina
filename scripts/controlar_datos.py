#!/usr/bin/env python3
"""Controles de sentido común sobre datos/historia.json: que los números cierren y no haya valores absurdos.
Corre en «Probar el sitio»; si algo falla, sale con error y dice qué. Uso: python3 scripts/controlar_datos.py"""
import json, pathlib, sys

RAIZ = pathlib.Path(__file__).resolve().parent.parent
H = json.loads((RAIZ / "datos" / "historia.json").read_text(encoding="utf-8"))
errores = []
mal = lambda m: errores.append(m)

A = H["anios"]
anios = [x["anio"] for x in A]
if anios != list(range(anios[0], anios[-1] + 1)):
    mal(f"faltan años en la serie: {anios}")

# cada año del gobierno que corresponde, sin huecos ni superposiciones
G = H["gobiernos"]
for g1, g2 in zip(G, G[1:]):
    if g2["desde"] != g1["hasta"] + 1:
        mal(f"hueco o superposición entre {g1['id']} y {g2['id']}")

for x in A:
    a = x["anio"]
    if not x.get("pib") or x["pib"] <= 0:
        mal(f"{a}: PIB vacío")
        continue
    pct = x["gastado"] / x["pib"] * 100
    if not 8 <= pct <= 35:
        mal(f"{a}: gasto de {pct:.1f}% del PIB, fuera de rango")
    suma = sum(x["rubros"].values())
    if abs(suma / x["gastado"] - 1) > 0.005:
        mal(f"{a}: los rubros suman {suma:,.0f} y el total es {x['gastado']:,.0f}")
    if x.get("tipos") and abs(sum(x["tipos"].values()) / x["gastado"] - 1) > 0.005:
        mal(f"{a}: los tipos de gasto no suman el total")
    for k in ("res_prim", "res_fin"):
        if x.get(k) is not None and abs(x[k] / x["pib"] * 100) > 12:
            mal(f"{a}: {k} de {x[k] / x['pib'] * 100:.1f}% del PIB, fuera de rango")
    if x.get("pib_real") and x.get("poblacion") and not 30e6 < x["poblacion"] < 55e6:
        mal(f"{a}: población {x['poblacion']:,}")
    rangos = {"industria": (8, 30), "agro": (2, 15), "mineria": (0.5, 10), "construccion": (1, 10), "exportaciones": (5, 35),
              "importaciones": (5, 30), "inversion": (8, 30), "inv_equipo": (2, 15), "desempleo": (3, 30), "moi": (10, 50),
              "bk": (15, 60), "industria_real_hab": (50, 200)}
    for k, (lo, hi) in rangos.items():
        v = (x.get("eco") or {}).get(k)
        if v is not None and not lo <= v <= hi:
            mal(f"{a}: {k} = {v}, fuera de rango ({lo}-{hi})")

# saltos bruscos de un año a otro en el gasto (más de 6 puntos del PIB) suelen ser errores de datos
pcts = {x["anio"]: x["gastado"] / x["pib"] * 100 for x in A}
for a in anios[1:]:
    if abs(pcts[a] - pcts[a - 1]) > 6:
        mal(f"{a}: el gasto salta {pcts[a] - pcts[a - 1]:+.1f} puntos del PIB contra {a - 1}")

# el PIB en pesos corrientes no baja de un año a otro salvo en deflación (1999-2002 la hubo, poca)
for a in anios[1:]:
    if A[anios.index(a)]["pib"] < A[anios.index(a - 1)]["pib"] * 0.85:
        mal(f"{a}: el PIB nominal cae más de 15%")

if errores:
    print("Problemas en datos/historia.json:\n- " + "\n- ".join(errores))
    sys.exit(1)
print(f"datos/historia.json: {len(A)} años, sin problemas")
