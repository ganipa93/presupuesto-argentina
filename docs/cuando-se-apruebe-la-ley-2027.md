# Qué hacer cuando se apruebe la ley de Presupuesto 2027

Hoy el sitio muestra el **proyecto** 2027 que el Poder Ejecutivo mandó al Congreso. Cuando el
Congreso lo sancione, algunos números y casi todos los textos que dicen «proyecto» van a cambiar de
sentido. Este documento deja anotado el orden de trabajo para no improvisar ese día.

## Por qué no hay un «selector» armado de antemano

Un selector proyecto / ley necesita las dos versiones de los datos, y la ley todavía no existe.
Además, lo que el Congreso cambie (artículos, montos, partidas) decide qué hay que mostrar. Armar la
estructura antes de ver esos cambios sería adivinar. Lo que sí hay es un precedente: para 2026 el
sitio ya muestra **ley (Ley 27.798)**, **autorizado hoy** y **gastado**. 2027 va a tener el mismo
trío, más el **proyecto original** para comparar.

## Orden de trabajo

1. **Esperar los documentos oficiales de la ley**: el texto en el Boletín Oficial / InfoLEG y los
   datasets de Presupuesto Ciudadano de la ley (no del proyecto). Los archivos tienen otros nombres.
2. **Conservar el proyecto original.** Antes de pisar nada, dejar una copia de `fuentes/datasets/2027-*`
   y de `fuentes/proyecto-presupuesto-2027.pdf` con un nombre que diga «proyecto». Sin eso se pierde la
   comparación proyecto vs ley.
3. **Actualizar `ARCHIVOS` en `scripts/bajar_datasets.py`** con los archivos de la ley y correr el
   workflow *Bajar datasets oficiales* (Actions). Rearma `datos/programas.json`.
4. **Agregar la página «Proyecto vs. ley 2027»**, siguiendo el modelo de `/ley-2026-vs-proyecto-2027`
   (se arma en `scripts/paginas.py` con `datos/ley_vs_proyecto.json`).
5. **Revisar los textos que dicen «proyecto»** (lista abajo) y decidir uno por uno: algunos pasan a
   «ley», otros tienen que seguir diciendo «proyecto» porque comparan contra él.
6. **Actualizar `datos/congreso.json`** (etapas: dictamen, media sanción, Senado, sanción, promulgación) y
   sumar la novedad en `datos/novedades.json`.
7. **Historia (`/historia`):** 2027 deja de ser «proyecto» y pasa a la ley que corresponda (en
   `LEYES` de `scripts/armar_historia.py`). Si el Congreso no la aprueba y se prorroga el presupuesto,
   el sitio ya sabe mostrarlo («Sin ley nueva (prórroga)»): se agrega el año a `PRORROGAS`.
8. **Probar:** `python3 scripts/build.py`, `node scripts/prerender.mjs`, `python3 scripts/revisar_sitio.py`,
   `python3 scripts/controlar_datos.py`, `node scripts/test-local.mjs` y `node scripts/test-programas.mjs`.

## Dónde hay texto que dice «proyecto» (cantidad de menciones al 18/11/2026)

| Archivo | Menciones |
|---|---|
| `scripts/paginas.py` | 30 |
| `scripts/build.py` | 28 |
| `src/metodologia.html` | 20 |
| `src/plantilla.html` | 18 |
| `src/js/portada.js` | 8 |
| `src/cuadros.html`, `src/programas.html` | 4 y 4 |
| `scripts/armar_programas.py`, `src/js/buscador.js` | 2 y 1 |

(Se cuentan con `grep -o -i 'proyecto[^.<]\{0,12\}2027\|proyecto de ley\|el proyecto'`. Es una guía,
no una lista exacta: conviene volver a contar ese día.)

## Cosas que no se pueden hacer con un reemplazo automático

- «Lo que el gobierno pide gastar en 2027» (buscador): tras la sanción es «lo que autorizó el Congreso».
- Las comparaciones «2027 contra 2026» usan hoy el gasto que estima el propio proyecto para 2026 (ver
  Metodología, «Base 2026»); hay que decidir si siguen así.
- El semáforo «2027: ¿es realista?» evalúa supuestos del proyecto (inflación 18%, dólar, crecimiento);
  si el Congreso los cambia, cambia lo que se evalúa.
