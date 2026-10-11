# Presupuesto Argentina 2026 y 2027

Sitio interactivo que compara la Ley de Presupuesto 2026 (Ley 27.798) con el Proyecto de Ley de Presupuesto 2027: en qué se gasta, de dónde sale el dinero y qué tan probable es que se cumpla.

Sitio publicado: https://presupuesto-argentina.vercel.app

## Secciones

- **Resumen:** gasto total 2027, variación real por función y semáforo de cumplimiento.
- **En qué se gasta:** por ministerio, por función y por tipo de gasto, más personas alcanzadas.
- **De dónde sale:** recaudación por impuesto, cuenta ahorro-inversión, fuentes de financiamiento y gasto tributario.
- **2026: ¿se cumplió?:** ejecución a julio de 2026, variación real a agosto y supuestos de la ley contra lo que pasó.
- **2027: ¿se cumplirá?:** evaluación de los supuestos y un simulador de inflación y dólar.
- **Ley 2026 vs proyecto 2027:** cambios en los montos fijados en artículos.
- **Artículos clave:** los artículos del proyecto con efecto directo en la gente.

## Estructura

- `index.html`: el sitio completo (HTML, CSS y JavaScript, sin dependencias ni build). Los datos van incluidos en la página.
- `datos/`: los mismos datos en JSON, uno por tabla, para consultarlos o reutilizarlos.

## Fuentes

- Proyecto de Ley de Presupuesto 2027 (MEN-2026-43-APN-JGM, 15/9/2026).
- Ley 27.798 de Presupuesto 2026.
- ASAP (Asociación Argentina de Presupuesto), ejecución a agosto de 2026.

Los porcentajes en términos reales y el semáforo de cumplimiento son estimaciones propias, no datos oficiales. Datos actualizados al 10/10/2026.

## Publicación

El proyecto está conectado a Vercel: cada push a `main` publica una nueva versión.
