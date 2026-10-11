# Presupuesto Argentina 2026 y 2027

Sitio interactivo que compara la Ley de Presupuesto 2026 (Ley 27.798) con el Proyecto de Ley de Presupuesto 2027: en qué se gasta, de dónde sale el dinero y qué tan probable es que se cumpla.

Sitio publicado: https://presupuesto-argentina.vercel.app

## Secciones

- **Resumen:** las tres conclusiones principales, gasto total 2027, variación real por función y semáforo de cumplimiento.
- **¿Qué me cambia a mí?:** qué dice el proyecto para jubilados, familias con AUH, estudiantes, personas con discapacidad, trabajadores, empleados públicos, provincias, usuarios de servicios y contribuyentes.
- **En qué se gasta:** por ministerio, por función y por tipo de gasto, más personas alcanzadas.
- **De dónde sale:** recaudación por impuesto, cuenta ahorro-inversión, fuentes de financiamiento y gasto tributario.
- **2026: ¿se cumplió?:** ejecución a julio de 2026, variación real a agosto y supuestos de la ley contra lo que pasó.
- **2027: ¿se cumplirá?:** evaluación de los supuestos y un simulador de inflación y dólar.
- **Ley 2026 vs proyecto 2027:** cambios en los montos fijados en artículos.
- **Artículos clave:** los artículos del proyecto con efecto directo en la gente.

## Estructura

- `datos/*.json`: la fuente de verdad. Un archivo por tabla, con las páginas del PDF en `metodologia.html`.
- `src/`: plantillas de la página principal, de metodología y de la imagen para redes.
- `scripts/build.py`: arma `index.html`, `metodologia.html`, `datos/index.html`, `sitemap.xml` y `robots.txt` a partir de los datos.
- `scripts/prerender.mjs`: deja el contenido escrito en `index.html` (para buscadores y vistas previas) y genera `og.png`.
- `fuentes/`: copia del Proyecto de Ley de Presupuesto 2027.
- `tipografias/`: Source Sans 3 y Source Serif 4 (licencia SIL OFL).

Los archivos generados se suben al repositorio, así Vercel solo publica archivos estáticos.

## Cómo actualizar

1. Editar los JSON de `datos/` (y la fecha en `scripts/build.py`).
2. `python3 scripts/build.py`
3. `cd scripts && npm install && cd .. && node scripts/prerender.mjs`
4. Commit y push a `main`.

## Fuentes

- Proyecto de Ley de Presupuesto 2027 (MEN-2026-43-APN-JGM, 15/9/2026).
- Ley 27.798 de Presupuesto 2026.
- ASAP (Asociación Argentina de Presupuesto), ejecución a agosto de 2026.
- INDEC (inflación), BCRA (Relevamiento de Expectativas de Mercado) y FMI (proyecciones de abril 2026).

El detalle, con links y páginas, está en [metodologia.html](https://presupuesto-argentina.vercel.app/metodologia).

Los porcentajes en términos reales y el semáforo de cumplimiento son estimaciones propias, no datos oficiales. Datos actualizados al 10/10/2026.

## Publicación

El proyecto está conectado a Vercel: cada push a `main` publica una nueva versión.
