set -x
mkdir -p sondeo_files
for y in 1995 2003 2015 2023 2025; do
  echo "== $y"; curl -sSL -m 60 "https://www.presupuestoabierto.gob.ar/datasets/$y/" | grep -o 'href="[^"]*"' | head -60
done
for u in "https://www.presupuestoabierto.gob.ar/datasets/1995/credito-anual-1995.zip" "https://www.presupuestoabierto.gob.ar/datasets/2024/credito-anual-2024.zip"; do
  curl -sSL -m 120 -o /tmp/c.zip -w "%{http_code} %{size_download}\n" "$u"; unzip -l /tmp/c.zip | head; unzip -p /tmp/c.zip | head -3
done
echo "== series PIB"
for q in "pib%20precios%20corrientes" "producto%20interno%20bruto%20corriente%20anual"; do
  curl -sS -m 60 "https://apis.datos.gob.ar/series/api/search/?q=$q&limit=25" | python3 -c "import json,sys;d=json.load(sys.stdin);[print(x['field']['id'],x['field']['frequency'],x['field']['time_index_start'],x['field']['time_index_end'],x['field']['description'][:90],x['dataset']['title'][:50]) for x in d['data']]"
done
echo "== ONP"
curl -sSL -m 60 "https://www.economia.gob.ar/onp/presupuestos/presupuestos" | grep -oi 'href="[^"]*"' | head -80
curl -sSL -m 60 "https://www.economia.gob.ar/onp/presupuestos/2015" | grep -oi 'href="[^"]*"' | head -60
# v2
