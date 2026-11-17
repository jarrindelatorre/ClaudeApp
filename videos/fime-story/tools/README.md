# Historia FIME · grabación con parallax

`grabar-scroll.js` recorre festivalesmeraldas.com en vista móvil (430 px, 1080×1920 de salida) siguiendo una curva de scroll continua de 30 s y guarda un JPG por cuadro (30 fps), así se conservan los parallax de la web.

    node grabar-scroll.js <carpeta-de-cuadros>
    ffmpeg -framerate 30 -i <carpeta>/f%04d.jpg -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,format=yuv420p" -c:v libx264 -crf 17 fime-story.mp4

La curva de velocidad está en la constante `K` (segundo → píxel CSS).
