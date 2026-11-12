# Normaliza las fotos: cara del mismo tamaño y posición en un cuadrado; rellena lo que falta con la misma foto desenfocada.
import cv2, numpy as np, glob, os, sys
src, out = sys.argv[1], sys.argv[2]
S = 800; FACE_W = 0.40 * S; CX, CY = 0.5 * S, 0.42 * S
casc = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
for f in sorted(glob.glob(src + "/*.png")):
    im = cv2.imread(f, cv2.IMREAD_UNCHANGED)
    if im.shape[2] == 4:  # aplanar transparencia sobre blanco
        a = im[..., 3:] / 255.0; im = (im[..., :3] * a + 255 * (1 - a)).astype(np.uint8)
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    faces = casc.detectMultiScale(g, 1.08, 5, minSize=(40, 40))
    if len(faces) == 0: print("SIN CARA", f); continue
    x, y, w, h = max(faces, key=lambda r: r[2] * r[3])
    k = FACE_W / w
    M = np.float32([[k, 0, CX - k * (x + w / 2)], [0, k, CY - k * (y + h / 2)]])
    fg = cv2.warpAffine(im, M, (S, S), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    mask = cv2.warpAffine(np.full(im.shape[:2], 255, np.uint8), M, (S, S), borderValue=0)
    # fondo: la misma foto escalada a cubrir y muy desenfocada
    hh, ww = im.shape[:2]; c = max(S / ww, S / hh)
    bg = cv2.resize(im, (int(ww * c) + 1, int(hh * c) + 1)); bg = bg[:S, :S]
    bg = cv2.GaussianBlur(bg, (0, 0), 30)
    mask = cv2.erode(mask, np.ones((9, 9), np.uint8)); m = cv2.GaussianBlur(mask, (0, 0), 14)[..., None] / 255.0
    res = (fg * m + bg * (1 - m)).astype(np.uint8)
    cv2.imwrite(os.path.join(out, os.path.basename(f).replace(".png", ".jpg")), res, [cv2.IMWRITE_JPEG_QUALITY, 90])
    print(os.path.basename(f), "cara", w, "escala %.2f" % k)
