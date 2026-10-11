# Presupuesto Argentina

El Presupuesto nacional 2026 y el proyecto 2027, explicados en lenguaje simple: qué le cambia a cada persona, en qué se gasta la plata, de dónde sale y si se cumple.

**Sitio:** https://presupuesto-argentina.vercel.app

## Qué vas a encontrar

- **Qué te cambia:** jubilados, familias con AUH, estudiantes, trabajadores, provincias, tarifas y más.
- **¿A dónde van tus impuestos?:** una calculadora con tu sueldo y tus gastos.
- **Buscar un gasto:** cualquier programa, obra u organismo, con lo pedido para 2027 y lo gastado en 2026. Cada uno tiene su página.
- **Por provincia:** cuánto gasta la Nación en cada una, cuánto es por habitante y qué obras pide el proyecto 2027.
- **Qué creció y qué cayó:** la evolución de cada programa desde 2020, descontada la inflación.
- **¿Se cumple?:** la ley 2026 contra lo que pasó, qué programas se están dejando de gastar (se actualiza cada mes), el realismo del 2027 y el debate en el Congreso.
- **Todos los cuadros:** las páginas completas del proyecto 2027 y de la Ley 27.798, con buscador.
- **Comparar:** hasta tres programas, organismos o provincias lado a lado.
- **Glosario:** los términos del presupuesto en castellano simple.
- **Novedades:** lo nuevo del sitio, también por RSS (`/novedades.xml`).

Todas las tablas se pueden descargar en Excel (CSV).

## De dónde salen los datos

Todo sale de fuentes oficiales y públicas:

- Proyecto de Ley de Presupuesto 2027 y sus datasets (Oficina Nacional de Presupuesto).
- Ley 27.798 de Presupuesto 2026.
- Presupuesto Abierto (Ministerio de Economía), para lo gastado mes a mes.
- INDEC (inflación y Censo 2022), BCRA, FMI y ASAP.

Los cálculos en términos reales y el semáforo de cumplimiento son estimaciones propias. El detalle está en [Metodología y fuentes](https://presupuesto-argentina.vercel.app/metodologia).

## Actualización

- **Automática, todos los meses (día 12):** se baja lo gastado de Presupuesto Abierto, se rearma el sitio, se prueba y se publica.
- **A mano, cuando haga falta** (desde la pestaña *Actions* de GitHub):
  - *Bajar datasets oficiales*: cuando se publiquen nuevos datos del presupuesto (por ejemplo, la ley 2027 aprobada).
  - *Bajar serie histórica*: para sumar un año nuevo a la evolución.
- El seguimiento del Congreso se actualiza editando `datos/congreso.json`.

## Avisar un error

Si encontrás un dato mal, [abrí un aviso acá](https://github.com/ganipa93/presupuesto-argentina/issues/new). Los datos se pueden reutilizar citando la fuente (licencia CC BY 4.0).

---

### Para quien quiera modificar el sitio

Es un sitio estático: los datos están en `datos/` y `fuentes/`, las plantillas en `src/` y los programas que arman todo en `scripts/`. Las páginas `.html` del repositorio se generan solas; no se editan a mano.

```bash
python3 scripts/build.py                 # arma el sitio
cd scripts && npm install && cd ..
node scripts/prerender.mjs               # deja el contenido escrito e imágenes para redes
python3 scripts/revisar_sitio.py         # links y datos estructurados
node scripts/test-local.mjs capturas     # pruebas en un navegador
```

Cada cambio en `main` se prueba automáticamente y se publica en Vercel. Para bajar datos de Presupuesto Abierto hace falta el secreto `PRESUPUESTO_ABIERTO_TOKEN`.
