# Retratos parejos sin relleno borroso: recorte de la persona sobre un fondo de estudio dorado,
# cara del mismo tamaño y posición; el busto se funde en oscuro abajo.
import cv2, numpy as np, glob, os, sys
from PIL import Image
from rembg import remove, new_session
from scipy import ndimage
src, out = sys.argv[1], sys.argv[2]
S = 800; FACE_W = 0.36 * S; CX, CY = 0.5 * S, 0.42 * S
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
ses = new_session("isnet-general-use")
yy, xx = np.mgrid[0:S, 0:S]
r = np.hypot((xx - S * 0.5) / S, (yy - S * 0.38) / S)
studio = np.clip(1 - r * 1.25, 0, 1)[..., None]
bg = (np.array([20, 34, 52])[None, None] * (1 - studio) + np.array([120, 178, 214])[None, None] * studio)  # BGR: marrón oscuro → dorado cálido
for f in sorted(glob.glob(src + "/*.png")):
    rgb = Image.open(f).convert("RGB"); im = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
    a = np.array(remove(rgb, session=ses))[..., 3]
    # alfa sólido: umbral bajo + rellenar huecos (camisas claras) + borde suave
    m = ndimage.binary_fill_holes(ndimage.binary_closing(a > 20, iterations=3))
    a = np.maximum(a, (m * 255).astype(np.uint8)); a = cv2.GaussianBlur(a, (0, 0), 1.2)
    x, y, w, h = max(casc.detectMultiScale(cv2.cvtColor(im, cv2.COLOR_BGR2GRAY), 1.08, 5, minSize=(40, 40)), key=lambda q: q[2] * q[3])
    k = FACE_W / w
    M = np.float32([[k, 0, CX - k * (x + w / 2)], [0, k, CY - k * (y + h / 2)]])
    fg = cv2.warpAffine(im, M, (S, S), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    al = cv2.warpAffine(a, M, (S, S), flags=cv2.INTER_LINEAR, borderValue=0).astype(float) / 255
    # donde la foto original se acaba (bordes del recorte), fundir suave hacia el fondo
    inside = cv2.warpAffine(np.full(a.shape, 255, np.uint8), M, (S, S), borderValue=0)
    inside = cv2.GaussianBlur(cv2.erode(inside, np.ones((7, 7), np.uint8)), (0, 0), 10).astype(float) / 255
    al = (al * inside)[..., None]
    res = fg * al + bg * (1 - al)
    fade = np.clip((yy - S * 0.78) / (S * 0.22), 0, 1)[..., None]  # busto que se funde abajo
    res = res * (1 - fade * 0.85) + np.array([10, 16, 24]) * fade * 0.85
    cv2.imwrite(os.path.join(out, os.path.basename(f).replace(".png", ".jpg")), res.astype(np.uint8), [cv2.IMWRITE_JPEG_QUALITY, 90])
