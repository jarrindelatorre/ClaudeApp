"""
Logo 3D con giro — animación en Blender generada por script.

Toma un PNG con fondo transparente (logo.png), extruye su silueta a un
objeto 3D con volumen, le aplica el propio logo como textura (de frente y
y lo hace entrar con un giro 3D completo sobre
un fondo claro. 5 s, 1280x720, 24 fps.

Requiere: bpy (Blender 5.x como módulo o dentro de Blender), numpy, pillow,
scikit-image, scipy.

    python animacion/logo/logo_3d.py --logo animacion/logo/logo.png --out frames/
    blender -b -P animacion/logo/logo_3d.py -- --logo ... --out frames/

Video:
    ffmpeg -framerate 24 -i frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 logo_3d.mp4
"""

import argparse
import math
import os
import sys
import tempfile

import bpy
import numpy as np
from PIL import Image, ImageFilter
from scipy import ndimage
from skimage import measure

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--logo", default="animacion/logo/logo.png")
ap.add_argument("--out", default="frames/")
ap.add_argument("--samples", type=int, default=64)
ap.add_argument("--res-pct", type=int, default=100)
ap.add_argument("--frames", default=None)
ap.add_argument("--blend", default=None)
ap.add_argument("--no-render", action="store_true")
args = ap.parse_args(argv)

FPS = 24
FRAMES = 120            # 5 s
UPSCALE = 4             # el PNG es chico: se agranda para bordes y textura más limpios
WIDTH = 4.0             # ancho del logo en unidades de Blender
DEPTH = 0.09            # medio espesor de la extrusión

# ------------------------------------------------------------ preparar la imagen
src = Image.open(args.logo).convert("RGBA")
big = src.resize((src.width * UPSCALE, src.height * UPSCALE), Image.LANCZOS)
rgba = np.asarray(big).astype(np.float32) / 255.0
alpha = rgba[..., 3]

# textura: los píxeles transparentes toman el color opaco más cercano, para
# que los bordes y los laterales de la extrusión no salgan negros ni blancos
solid = alpha > 0.6
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
rgb = rgba[..., :3][iy, ix]
tex_path = os.path.join(tempfile.mkdtemp(), "logo_textura.png")
Image.fromarray((rgb * 255).astype(np.uint8)).save(tex_path)

# silueta: alfa suavizado -> contornos -> polígonos simplificados
mask = np.asarray(big.getchannel("A").filter(ImageFilter.GaussianBlur(1.2))) / 255.0
mask = np.pad(mask, 2)
H_px, W_px = alpha.shape
px = WIDTH / W_px
HEIGHT = H_px * px
contours = []
for c in measure.find_contours(mask, 0.5):
    c = measure.approximate_polygon(c, tolerance=0.7)
    if len(c) < 4:
        continue
    # (fila, col) -> (x, y) centrado
    xy = [((col - 2) * px - WIDTH / 2, -(row - 2) * px + HEIGHT / 2) for row, col in c[:-1]]
    area = 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1]))
    if abs(area) < (3 * px) ** 2:      # descartar motas
        continue
    contours.append(xy)

# ------------------------------------------------------------ escena
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = FPS


def link(o):
    scene.collection.objects.link(o)
    return o


# ------------------------------------------------------------ logo extruido
cu = bpy.data.curves.new("LogoCurva", "CURVE")
cu.dimensions = "2D"
cu.fill_mode = "BOTH"
cu.extrude = DEPTH
cu.bevel_depth = 0.008
cu.bevel_resolution = 2
for xy in contours:
    s = cu.splines.new("POLY")
    s.points.add(len(xy) - 1)
    for p, (x, y) in zip(s.points, xy):
        p.co = (x, y, 0, 1)
    s.use_cyclic_u = True
curve_obj = link(bpy.data.objects.new("Logo", cu))
bpy.context.view_layer.objects.active = curve_obj
curve_obj.select_set(True)
bpy.ops.object.convert(target="MESH")
logo = bpy.context.active_object
me = logo.data

# UV por proyección frontal (atrás se ve espejado, como un objeto sólido real)
while me.uv_layers:                      # quitar el UV automático de la curva
    me.uv_layers.remove(me.uv_layers[0])
uv = me.uv_layers.new(name="UVMap")
for poly in me.polygons:
    for li in poly.loop_indices:
        v = me.vertices[me.loops[li].vertex_index].co
        uv.data[li].uv = (v.x / WIDTH + 0.5, v.y / HEIGHT + 0.5)
for poly in me.polygons:
    poly.use_smooth = abs(poly.normal.z) < 0.5   # laterales suaves, caras planas

m = bpy.data.materials.new("LogoMat")
m.use_nodes = True
nt = m.node_tree
bsdf = nt.nodes["Principled BSDF"]
bsdf.inputs["Roughness"].default_value = 0.32
bsdf.inputs["Coat Weight"].default_value = 0.35
img = nt.nodes.new("ShaderNodeTexImage")
img.image = bpy.data.images.load(tex_path)
img.interpolation = "Cubic"
img.extension = "EXTEND"
# los laterales salen del mismo color pero más oscuros
geo = nt.nodes.new("ShaderNodeNewGeometry")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
vt = nt.nodes.new("ShaderNodeVectorTransform")
vt.convert_from, vt.convert_to = "WORLD", "OBJECT"
vt.vector_type = "NORMAL"
absn = nt.nodes.new("ShaderNodeMath")
absn.operation = "ABSOLUTE"
mr = nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = 0.0
mr.inputs["From Max"].default_value = 0.9
mr.inputs["To Min"].default_value = 0.55
mr.inputs["To Max"].default_value = 1.0
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mix.blend_type = "MULTIPLY"
mix.inputs["Factor"].default_value = 1.0
nt.links.new(geo.outputs["Normal"], vt.inputs["Vector"])
nt.links.new(vt.outputs["Vector"], sep.inputs["Vector"])
nt.links.new(sep.outputs["Z"], absn.inputs[0])
nt.links.new(absn.outputs[0], mr.inputs["Value"])
nt.links.new(img.outputs["Color"], mix.inputs["A"])
nt.links.new(mr.outputs["Result"], mix.inputs["B"])
nt.links.new(mix.outputs["Result"], bsdf.inputs["Base Color"])
me.materials.append(m)

# pivote para animar (el logo queda parado, mirando a la cámara)
pivot = link(bpy.data.objects.new("Pivote", None))
logo.parent = pivot
logo.rotation_euler = (math.radians(90), 0, 0)
BASE_Z = HEIGHT / 2 + 0.55

# ------------------------------------------------------------ animación
# entra desde abajo girando 1 vuelta y media, frena suave de frente,
# después flota y se mece apenas.
def key(f, z, rot_deg, s, tilt=0.0):
    pivot.location = (0, 0, z)
    pivot.rotation_euler = (math.radians(tilt), 0, math.radians(rot_deg))
    pivot.scale = (s, s, s)
    pivot.keyframe_insert("location", frame=f)
    pivot.keyframe_insert("rotation_euler", frame=f)
    pivot.keyframe_insert("scale", frame=f)


key(1, BASE_Z - 0.6, -540, 0.0, 12)
key(16, BASE_Z + 0.05, -380, 1.0, 6)
key(66, BASE_Z, 0, 1.0, 0)
pivot.keyframe_insert("location", frame=FRAMES)
pivot.keyframe_insert("rotation_euler", frame=FRAMES)
pivot.keyframe_insert("scale", frame=FRAMES)

# flotación suave después del giro (se suma con un driver sobre el logo hijo)
fc = logo.driver_add("location", 2)
fc.driver.expression = "0.06*sin(max(frame-66,0)/12)"
fc = logo.driver_add("rotation_euler", 2)
fc.driver.expression = "0.05*sin(max(frame-66,0)/17)"

# ------------------------------------------------------------ fondo claro (ciclorama)
WALL_Y, R = 4.0, 3.0      # pared detrás del logo, radio de la curva piso-pared
pts = [(-20.0, 0.0)]
for k in range(13):
    t = math.radians(90 * k / 12)
    pts.append((WALL_Y - R + R * math.sin(t), R - R * math.cos(t)))
pts.append((WALL_Y, 20.0))
mesh = bpy.data.meshes.new("Fondo")
verts, faces = [], []
for i, (y, z) in enumerate(pts):
    verts += [(-30, y, z), (30, y, z)]
    if i:
        a = 2 * (i - 1)
        faces.append((a, a + 1, a + 3, a + 2))
mesh.from_pydata(verts, [], faces)
for p in mesh.polygons:
    p.use_smooth = True
cyc = link(bpy.data.objects.new("Fondo", mesh))
fm = bpy.data.materials.new("FondoMat")
fm.use_nodes = True
fb = fm.node_tree.nodes["Principled BSDF"]
fb.inputs["Base Color"].default_value = (0.93, 0.95, 0.93, 1)
fb.inputs["Roughness"].default_value = 0.8
mesh.materials.append(fm)

world = bpy.data.worlds.new("Cielo")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.95, 0.97, 0.95, 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.3

# ------------------------------------------------------------ luces
def area(name, loc, energy, size, color=(1, 1, 1), target=(0, 0, 1.5)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy, d.size, d.color = energy, size, color
    o = link(bpy.data.objects.new(name, d))
    o.location = loc
    t = o.constraints.new("TRACK_TO")
    e = bpy.data.objects.get("LuzObjetivo") or link(bpy.data.objects.new("LuzObjetivo", None))
    e.location = target
    t.target = e


area("Clave", (-4.5, -6, 6), 380, 5, (1.0, 0.97, 0.92))
area("Relleno", (6, -5, 2.5), 140, 6, (0.92, 0.96, 1.0))
area("Contra", (0, 3, 6), 200, 4)

# ------------------------------------------------------------ cámara
target = link(bpy.data.objects.new("ObjetivoCam", None))
target.location = (0, 0, BASE_Z)
cam = link(bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara")))
cam.data.lens = 68
cam.location = (0, -10.5, BASE_Z + 0.9)
scene.camera = cam
tc = cam.constraints.new("TRACK_TO")
tc.target = target
# leve acercamiento durante todo el plano
cam.keyframe_insert("location", frame=1)
cam.location = (0, -9.6, BASE_Z + 0.75)
cam.keyframe_insert("location", frame=FRAMES)

# ------------------------------------------------------------ render
r = scene.render
r.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
r.resolution_x, r.resolution_y = 1280, 720
r.resolution_percentage = args.res_pct
r.image_settings.file_format = "PNG"
r.filepath = args.out.rstrip("/") + "/"
scene.view_settings.view_transform = "Standard"   # colores de marca fieles

if args.frames:
    a, b = args.frames.split("-")
    scene.frame_start, scene.frame_end = int(a), int(b)
if args.blend:
    bpy.ops.wm.save_as_mainfile(filepath=args.blend)
if not args.no_render:
    bpy.ops.render.render(animation=True)
