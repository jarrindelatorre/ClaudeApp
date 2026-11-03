# Animación en Blender: bolas que saltan

Video corto de 4 s (1280×720, 24 fps) hecho completamente por script en
Blender 5.2. Siete esferas de colores saltan en ola sobre un piso brillante,
se aplastan un poco al tocar el piso y se estiran en el aire. El video hace
loop perfecto.

- `bolas.py`: arma la escena y renderiza los frames (Cycles).
- `bolas.mp4`: el video final.

## Volver a renderizar

Con Blender instalado:

```bash
blender -b -P animacion/bolas.py -- --out animacion/frames/
```

O sin instalar Blender, con el módulo `bpy` de PyPI (requiere Python 3.13):

```bash
pip install bpy==5.2.3
```

```bash
python animacion/bolas.py --out animacion/frames/
```

Después, unir los frames en un video:

```bash
ffmpeg -framerate 24 -i animacion/frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 animacion/bolas.mp4
```

Opciones útiles: `--samples 16 --res-pct 50` para pruebas rápidas,
`--frames 1-24` para un tramo, `--blend escena.blend` para guardar el archivo
de Blender y seguir editándolo a mano.

---

# Logo 3D con giro (`logo/`)

Animación de 5 s (1280×720, 24 fps): el logo de `logo/logo.png` se extruye a
un objeto 3D con volumen, usando el propio logo como textura. Entra girando
una vuelta y media sobre un fondo claro, frena de frente y queda flotando.

- `logo/logo_3d.py`: script (necesita además `numpy pillow scipy scikit-image`).
- `logo/logo_3d.mp4`: el video final.

```bash
python animacion/logo/logo_3d.py --logo animacion/logo/logo.png --out animacion/frames/
```

```bash
ffmpeg -framerate 24 -i animacion/frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 animacion/logo/logo_3d.mp4
```

Sirve para cualquier otro logo PNG con fondo transparente: basta cambiar `--logo`.
