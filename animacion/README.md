# Animación "¡Feliz vuelta al Sol!" (Blender)

Video de 10 s (1280×720, 24 fps) hecho completamente por script en Blender 5.2:

1. Una Tierra (con su Luna) da una vuelta completa alrededor del Sol, que
   tiene la superficie "hirviendo", y va dejando una estela dorada sobre la órbita.
2. Al cerrar la vuelta (a los 7 s) estalla confeti de colores.
3. Aparece el texto dorado **¡Feliz vuelta al Sol!** y la cámara se acomoda.

- `vuelta_al_sol.py`: arma la escena y renderiza los frames (Cycles).
- `vuelta_al_sol.mp4`: el video final.

## Volver a renderizar

Con Blender instalado:

```bash
blender -b -P animacion/vuelta_al_sol.py -- --out animacion/frames/
```

O sin instalar Blender, con el módulo `bpy` de PyPI (requiere Python 3.13):

```bash
pip install bpy==5.2.3
```

```bash
python animacion/vuelta_al_sol.py --out animacion/frames/
```

Después, unir los frames en un video:

```bash
ffmpeg -framerate 24 -i animacion/frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 animacion/vuelta_al_sol.mp4
```

Opciones útiles: `--samples 16 --res-pct 50` para pruebas rápidas,
`--frames 160-200` para un tramo, `--blend escena.blend` para guardar el
archivo de Blender y seguir editándolo a mano, `--no-render` para sólo armar la escena.
