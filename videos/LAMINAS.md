# Láminas animadas para presentaciones · guía rápida

Lo mínimo necesario para producir láminas (series El Telégrafo, Pública, …) con HyperFrames.

## Formato aprobado
- 1920×1080, **25 s**, sin audio (se presenta en vivo).
- **0–10 s:** animación principal. **10–25 s:** solo movimiento lento (parallax) para hablar encima.
- Entregar en calidad `delivery` (HD, ~12 Mbps) como descarga directa.

## Sistema visual
- Fondo: arte de ondas de la marca (`assets/fondo-ondas-2.png`) con parallax lento y sombra azul; desplazarlo si mete ruido detrás de un elemento clave.
- Encabezado: `0X · Tema` en amarillo, 18 px, con línea fina que se dibuja.
- Títulos: Archivo 600, `font-stretch: 118%`, mayúsculas. Texto: Inter.
- **Amarillo solo para lo que se destaca** (fechas, cifras clave, palabra fuerte). Cifras intermedias de un conteo en gris (`--count: #c9d1da`).
- Texto a la izquierda, centrado verticalmente; imágenes/gráficos a la derecha.
- Colores Telégrafo: navy `#002c4f`, azul `#3a8fc4` / logo `#1b91bc`, teal `#35b9b8`, amarillo `#f4ba1a`, texto `#f4f1ec`.
- Grano y viñeteado sutiles.

## Patrones ya resueltos
- **Collage de fotos** que se apilan con giro leve y etiqueta (lámina 01).
- **Conteo de años/cifras** determinista (`onUpdate` sobre un objeto del timeline).
- **Barrido digital** (retícula + línea turquesa) para transformar foto antigua → actual.
- **Foto silueteada** (sin fondo) para que el fondo se vea en movimiento (lámina 02).
- **Logo dibujado con línea blanca** (SVG `pathLength=1` + `stroke-dashoffset`), luego relleno; recortes con `<mask>` para que no quede blanco.
- **Gráficos animados** redibujados en SVG oscuro: barras que crecen con totales que cuentan; líneas/áreas que se revelan con `clipPath` (lámina 03).

## Estado
| Serie | Lámina | Carpeta |
|---|---|---|
| El Telégrafo | 01 · Historia (1884 → 2020) | `telegrafo/01-historia` |
| El Telégrafo | 02 · Identidad (Torre del reloj) — pendiente retomar | `telegrafo/02-identidad` |
| El Telégrafo | 03 · Alcance (gráficos) | `telegrafo/03-alcance` |
| Pública | — | siguiente |

Recursos compartidos de cada serie en `<serie>/assets/` (fuentes, gsap, fondos, fotos); cada lámina enlaza `assets -> ../assets`.

## Para pedir una lámina
Texto exacto · qué va en amarillo · encabezado `0X · …` · fotos/gráficos · idea de animación · fondo.

## Notas técnicas
- Nueva lámina: copiar una carpeta existente, cambiar `meta.json`/`package.json` y el `index.html`.
- Comandos: `npx hyperframes@0.8.181 lint` · `snapshot . --at 1,5,9 --no-end --keep --describe false` · `render <ruta-absoluta> --quality delivery --output <archivo>.mp4`.
- Todo local: fuentes y GSAP en `assets/` (el CDN jsdelivr está bloqueado en este entorno).
- Quitar fondo de fotos de objetos/edificios: `rembg` con modelo `isnet-general-use` (el de HyperFrames solo sirve para personas).
- Un `<video>` debe estar declarado en el HTML (no creado por script) para que se renderice en movimiento.
- Las descargas de Canva (`media.canva.com`) están bloqueadas: pedir al usuario que descargue y suba la imagen.
- Archivos subidos mientras trabajo no se guardan: pedir que los reenvíe en un mensaje nuevo.
