echo "== API por año"
for y in 1995 2003 2010 2016 2019; do
  curl -sS -m 300 -X POST "https://www.presupuestoabierto.gob.ar/api/v1/credito?format=csv" -H "Authorization: $PRESUPUESTO_ABIERTO_TOKEN" -H "Content-Type: application/json" \
   -d "{\"title\":\"sondeo\",\"ejercicios\":[$y],\"columns\":[\"ejercicio_presupuestario\",\"finalidad_desc\",\"funcion_desc\",\"inciso_desc\",\"jurisdiccion_desc\",\"credito_presupuestado\",\"credito_vigente\",\"credito_devengado\"],\"filters\":[]}" -o /tmp/a.csv -w "$y http=%{http_code} bytes=%{size_download}\n"
  head -c 600 /tmp/a.csv; echo; wc -l /tmp/a.csv
done
echo "== sici links"
curl -sSL -m 60 "https://www.presupuestoabierto.gob.ar/sici/datos-abiertos" | grep -oi 'https\?://[^"]*\(zip\|csv\)' | sort -u | head -80
curl -sSL -m 60 "https://www.presupuestoabierto.gob.ar/sici/datos-abiertos" | grep -oi 'href="[^"]*"' | sort -u | head -80
echo "== series PIB"
for q in "pib%20nominal" "producto%20interno%20bruto%20precios%20corrientes" "oferta%20demanda%20global%20precios%20corrientes" "gasto%20publico%20pbi" "resultado%20fiscal%20pbi"; do
  echo "-- $q"
  curl -sS -m 60 "https://apis.datos.gob.ar/series/api/search/?q=$q&limit=40" | python3 -c "import json,sys;d=json.load(sys.stdin);[print(x['field']['id'],x['field']['frequency'],x['field']['time_index_start'][:4],x['field']['time_index_end'][:4],'|',x['field']['description'][:80],'|',x['dataset']['title'][:60],'|',x['field'].get('units','')) for x in d['data']]"
done
