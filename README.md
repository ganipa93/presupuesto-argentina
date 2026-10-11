# Presupuesto Argentina 2026 y 2027

Sitio interactivo que compara la Ley de Presupuesto 2026 (Ley 27.798) con el Proyecto de Ley de Presupuesto 2027: en qué se gasta, de dónde sale el dinero y qué tan probable es que se cumpla.

Sitio publicado: https://presupuesto-argentina.vercel.app

## Secciones

- **Resumen:** las tres conclusiones principales, gasto total 2027, variación real por función y semáforo de cumplimiento.
- **¿Qué me cambia a mí?:** qué dice el proyecto para jubilados, familias con AUH, estudiantes, personas con discapacidad, trabajadores, empleados públicos, provincias, usuarios de servicios y contribuyentes.
- **¿A dónde van tus impuestos?:** calculadora que estima cuánto pagás por mes en impuestos y aportes nacionales y cómo se reparte según el Presupuesto 2027.
- **En qué se gasta:** por ministerio, por función y por tipo de gasto, más personas alcanzadas.
- **De dónde sale:** recaudación por impuesto, cuenta ahorro-inversión, fuentes de financiamiento y gasto tributario.
- **2026: ¿se cumplió?:** ejecución a julio de 2026, variación real a agosto y supuestos de la ley contra lo que pasó.
- **2027: ¿se cumplirá?:** evaluación de los supuestos y un simulador de inflación y dólar.
- **Ley 2026 vs proyecto 2027:** cambios en los montos fijados en artículos.
- **Artículos clave:** los artículos del proyecto con efecto directo en la gente.

## Otras páginas

- **¿Cuánto se gasta en…? (`/programas`):** buscador con los programas del presupuesto, cada actividad y obra, lo pedido para 2027, lo autorizado y gastado en 2026 (también por provincia), las metas físicas, y además universidades, fondos fiduciarios, otros entes (INCAA, PAMI, ARCA) y empresas públicas.
- **Todos los cuadros (`/cuadros`):** las 248 páginas del proyecto 2027 y las 125 de la Ley 27.798 (2026) como imagen, con buscador de texto en los dos documentos y tablas en CSV.

- **Páginas fijas para buscadores:** una por programa u organismo (`/gasto/<slug>`, más el índice `/gasto`), una por provincia (`/provincias/<slug>`), y una por sección de la portada (`/impuestos`, `/que-me-cambia/jubilados`, …), cada una con su título, descripción, datos estructurados e imagen para redes (`og/`). Las arma `scripts/paginas.py` (llamado por `build.py`) y las imágenes `scripts/prerender.mjs`, que solo rehace las que cambiaron.

## Otras funciones

- Selector para ver los montos en billones de pesos o en pesos por habitante por mes.
- Imágenes para compartir en redes de cada punto del semáforo, cada perfil y el resultado de la calculadora, generadas en el navegador.
- Links directos a cada sección y perfil.
- Seguimiento del proyecto en el Congreso (`datos/congreso.json`).
- Ejecución por ministerio actualizada todos los meses desde Presupuesto Abierto.

## Estructura

- `datos/*.json`: la fuente de verdad. Un archivo por tabla, con las páginas del PDF en `metodologia.html`.
- `src/`: plantillas de la página principal, de metodología y de la imagen para redes.
- `scripts/build.py`: arma `index.html`, `metodologia.html`, `datos/index.html`, `sitemap.xml` y `robots.txt` a partir de los datos.
- `scripts/prerender.mjs`: deja el contenido escrito en `index.html` (para buscadores y vistas previas) y genera `og.png`.
- `fuentes/`: copia del Proyecto de Ley de Presupuesto 2027 y, en `fuentes/datasets/`, los datasets oficiales por programa.
- `scripts/extraer_cuadros.py`: genera `cuadros/` (imágenes, texto y tablas de cada página del PDF).
- `scripts/extraer_ley2026.py`: genera `cuadros/2026/` a partir del escaneo de la Ley 27.798 (endereza las páginas y hace OCR en castellano; necesita tesseract con `spa`). Títulos en `scripts/titulos_ley2026.json`.
- `scripts/bajar_datasets.py`: baja los datasets del Presupuesto Ciudadano 2027/2026 (ONP) y la ejecución 2026 por programa (API de Presupuesto Abierto).
- `scripts/armar_programas.py`: arma `datos/programas.json` para el buscador, a partir de los datasets y de las planillas del PDF. `datos/programas.json` no se incrusta en `index.html`: la página `/programas` lo carga aparte.
- `tipografias/`: Source Sans 3 y Source Serif 4 (licencia SIL OFL).

Los archivos generados se suben al repositorio, así Vercel solo publica archivos estáticos.

## Cómo actualizar

1. Editar los JSON de `datos/` (y la fecha en `scripts/build.py`).
2. `python3 scripts/build.py`
3. `cd scripts && npm install && cd .. && node scripts/prerender.mjs`
4. Opcional: `node scripts/test-local.mjs <carpeta>` prueba el sitio en un navegador y guarda capturas.
5. Commit y push a `main`.

## Fuentes

- Proyecto de Ley de Presupuesto 2027 (MEN-2026-43-APN-JGM, 15/9/2026).
- Ley 27.798 de Presupuesto 2026.
- ASAP (Asociación Argentina de Presupuesto), ejecución a agosto de 2026.
- INDEC (inflación), BCRA (Relevamiento de Expectativas de Mercado) y FMI (proyecciones de abril 2026).

El detalle, con links y páginas, está en [metodologia.html](https://presupuesto-argentina.vercel.app/metodologia).

Los porcentajes en términos reales y el semáforo de cumplimiento son estimaciones propias, no datos oficiales. Datos actualizados al 10/10/2026.

## Actualización automática

El workflow `.github/workflows/actualizar-ejecucion.yml` corre el día 12 de cada mes (y a mano desde la pestaña **Actions**). Baja la ejecución por jurisdicción de la API de Presupuesto Abierto con `scripts/actualizar_ejecucion.py`, también la ejecución 2026 por programa, actividad y provincia (`scripts/bajar_datasets.py --solo-api` y `scripts/armar_programas.py`), rearma el sitio y hace push, lo que dispara la publicación en Vercel.

El workflow `.github/workflows/bajar-datasets.yml` se corre a mano para bajar de nuevo todos los datasets (por ejemplo, cuando se apruebe la ley 2027 y la ONP publique los definitivos).

Necesita un token gratuito de Presupuesto Abierto (se pide en https://www.presupuestoabierto.gob.ar/sici/api-pac) guardado en el repositorio como secreto `PRESUPUESTO_ABIERTO_TOKEN` (Settings → Secrets and variables → Actions).

El seguimiento del Congreso se actualiza editando `datos/congreso.json`.

## Publicación

El proyecto está conectado a Vercel: cada push a `main` publica una nueva versión.
