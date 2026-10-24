"""Fuentes primarias para completar las series cuando la API de datos.gob.ar se atrasa.

  - IPC: archivo de series del INDEC (nivel general, total nacional, base diciembre 2016 = 100).
  - Dólar: API de estadísticas del BCRA, variable 5 (tipo de cambio de referencia, Com. A 3500).

Los meses de la fuente primaria solo se agregan si, en los meses que tienen en común con la API,
los valores coinciden (dentro de una tolerancia). Si no coinciden o la fuente falla, se sigue con
lo que dio la API y se explica por qué en la salida.
"""
import csv, datetime, io, json, urllib.error, urllib.request
from collections import defaultdict

UA = {"User-Agent": "presupuesto-argentina (https://github.com/ganipa93/presupuesto-argentina)"}
INDEC_CSV = [
    "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_divisiones.csv",
    "https://www.indec.gob.ar/ftp/cuadros/economia/serie_ipc_aperturas.csv",
]
BCRA_API = [
    "https://api.bcra.gob.ar/estadisticas/v4.0/monetarias/5",
    "https://api.bcra.gob.ar/estadisticas/v3.0/monetarias/5",
]


def _bajar(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _num(s):
    s = str(s).strip()
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    return float(s)


def ipc_indec():
    """[("AAAA-MM-01", índice)] del nivel general nacional."""
    errores = []
    for url in INDEC_CSV:
        try:
            crudo = _bajar(url)
            texto = crudo.decode("utf-8-sig", errors="replace")
            if "Descripci" not in texto[:500]:
                texto = crudo.decode("latin-1")
            sep = ";" if texto[:500].count(";") > texto[:500].count(",") else ","
            filas = list(csv.DictReader(io.StringIO(texto), delimiter=sep))
            col = lambda f, *nombres: next((f[k] for k in f if k and k.strip().lower() in nombres), "")
            out = {}
            for f in filas:
                desc = col(f, "descripcion", "descripción").strip().lower()
                region = col(f, "region", "región").strip().lower()
                codigo = col(f, "codigo", "código").strip()
                if region not in ("nacional", "total nacional") or not (codigo == "0" or desc == "nivel general"):
                    continue
                per = col(f, "periodo", "período").strip()
                val = col(f, "indice_ipc", "índice_ipc")
                if len(per) == 6 and val not in ("", "NA"):
                    out[f"{per[:4]}-{per[4:]}-01"] = _num(val)
            if out:
                return sorted(out.items())
            errores.append(f"{url}: no encontré el nivel general nacional (columnas: {list(filas[0])[:8] if filas else 'ninguna'})")
        except Exception as e:  # noqa: BLE001
            errores.append(f"{url}: {e}")
    raise RuntimeError("; ".join(errores))


def dolar_bcra():
    """[("AAAA-MM-01", promedio del mes)] del tipo de cambio Com. A 3500, desde 2019."""
    hoy = datetime.date.today()
    errores = []
    for base in BCRA_API:
        try:
            diario = {}
            # la API limita el rango por consulta: se pide año por año
            for anio in range(2019, hoy.year + 1):
                url = f"{base}?desde={anio}-01-01&hasta={min(datetime.date(anio, 12, 31), hoy)}&limit=3000"
                res = json.loads(_bajar(url)).get("results") or []
                filas = res[0].get("detalle", []) if res and isinstance(res[0], dict) and "detalle" in res[0] else res
                for x in filas:
                    if x.get("fecha") and x.get("valor") is not None:
                        diario[x["fecha"][:10]] = float(x["valor"])
            if not diario:
                raise RuntimeError("respuesta vacía")
            por_mes = defaultdict(list)
            for f, v in diario.items():
                por_mes[f[:7]].append(v)
            return [(m + "-01", sum(vs) / len(vs)) for m, vs in sorted(por_mes.items())]
        except Exception as e:  # noqa: BLE001
            errores.append(f"{base}: {e}")
    raise RuntimeError("; ".join(errores))


def completar(nombre, api, primaria, tolerancia, rehacer_ultimo=False):
    """api: [("AAAA-MM-DD", valor)] de datos.gob.ar. Devuelve la serie con los meses nuevos de la
    fuente primaria agregados al final, si ambas coinciden en los meses comunes."""
    api = [(f[:7] + "-01", v) for f, v in api if v is not None]
    try:
        prim = primaria()
    except Exception as e:  # noqa: BLE001
        print(f"{nombre}: no se pudo consultar la fuente primaria ({e}); queda la API hasta {api[-1][0][:7]}.")
        return api
    base = api[:-1] if rehacer_ultimo else api  # el último mes de la API puede estar incompleto
    pv = dict(prim)
    comunes = [(f, v) for f, v in base if f in pv][-12:]
    if not comunes:
        print(f"{nombre}: la fuente primaria no tiene meses en común con la API; no se usa.")
        return api
    peor = max(abs(pv[f] / v - 1) for f, v in comunes)
    if peor > tolerancia:
        print(f"{nombre}: la fuente primaria difiere de la API hasta {peor:.2%} en meses comunes; no se usa.")
        return api
    ultimo = base[-1][0]
    nuevos = [(f, v) for f, v in prim if f > ultimo]
    if not nuevos:
        print(f"{nombre}: la API está al día ({api[-1][0][:7]}).")
        return api
    print(f"{nombre}: la API llega a {api[-1][0][:7]}; se suman {', '.join(f[:7] for f, _ in nuevos)} de la fuente primaria (coinciden en {len(comunes)} meses comunes, diferencia máxima {peor:.3%}).")
    return base + nuevos
