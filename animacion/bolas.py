"""
Bolas que saltan — animación corta en Blender, generada 100% por script.

Siete esferas de colores saltan en ola sobre un piso brillante, con
"squash & stretch" al tocar el piso. Dura 4 s (96 frames a 24 fps) y
hace loop perfecto.

Uso (Blender instalado):
    blender -b -P animacion/bolas.py -- --out animacion/frames/
Uso (módulo bpy de PyPI, Python 3.13: pip install bpy==5.2.3):
    python animacion/bolas.py --out animacion/frames/

Video:
    ffmpeg -framerate 24 -i animacion/frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 animacion/bolas.mp4

Opciones: --samples N, --res-pct N, --frames A-B, --blend PATH, --no-render
"""

import argparse
import colorsys
import math
import sys

import bpy

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="frames/")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--res-pct", type=int, default=100)
ap.add_argument("--frames", default=None)
ap.add_argument("--blend", default=None)
ap.add_argument("--no-render", action="store_true")
args = ap.parse_args(argv)

FRAMES = 96          # 4 s a 24 fps
PERIOD = 48          # cada bola salta 2 veces -> loop perfecto
N = 7
R = 0.4              # radio de las bolas
JUMP = 1.6           # altura del salto

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = 24


def link(o):
    scene.collection.objects.link(o)
    return o


def mat(name, color, rough=0.2, emission=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.6
    if emission:
        b.inputs["Emission Color"].default_value = (*color, 1)
        b.inputs["Emission Strength"].default_value = emission
    return m


def driver(obj, path, index, expr):
    fc = obj.driver_add(path, index)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr


# ------------------------------------------------------------ fondo
world = bpy.data.worlds.new("Fondo")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.012, 0.02, 1)

# ------------------------------------------------------------ piso brillante
bpy.ops.mesh.primitive_plane_add(size=60)
floor = bpy.context.active_object
floor.data.materials.append(mat("Piso", (0.02, 0.02, 0.03), rough=0.12))

# ------------------------------------------------------------ bolas
for i in range(N):
    hue = i / N
    color = colorsys.hsv_to_rgb(hue, 0.85, 0.95)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=R, segments=64, ring_count=32)
    b = bpy.context.active_object
    b.name = f"Bola{i}"
    bpy.ops.object.shade_smooth()
    b.data.materials.append(mat(f"Bola{i}", color, rough=0.15, emission=0.15))
    b.location.x = (i - (N - 1) / 2) * 1.3
    # origen en la base de la bola para que el squash apoye en el piso
    b.data.transform(__import__("mathutils").Matrix.Translation((0, 0, R)))

    phase = f"(frame/{PERIOD} - {i}/{N * 2})"
    h = f"abs(sin(pi*{phase}))"                       # 0 en el piso, 1 arriba
    squash = f"(1 - 0.35*max(0, 1 - {h}*5))"           # se aplasta al tocar
    stretch = f"(1 + 0.12*min(1, {h}*5)*(1-{h}))"      # se estira en el aire
    driver(b, "location", 2, f"{JUMP}*{h}*(2-{h})")   # subida rápida, arriba suave
    driver(b, "scale", 2, f"{squash}*{stretch}")
    driver(b, "scale", 0, f"1/sqrt({squash}*{stretch})")
    driver(b, "scale", 1, f"1/sqrt({squash}*{stretch})")

# ------------------------------------------------------------ luces
def area(name, loc, rot, energy, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy, d.size, d.color = energy, size, color
    o = link(bpy.data.objects.new(name, d))
    o.location, o.rotation_euler = loc, [math.radians(a) for a in rot]


area("Clave", (-4, -5, 6), (50, 0, -35), 900, 4)
area("Contra", (5, 6, 4), (-60, 0, 140), 600, 6, (0.6, 0.7, 1.0))
area("Cenital", (0, 0, 8), (0, 0, 0), 300, 10)

# ------------------------------------------------------------ cámara (vaivén suave, también en loop)
target = link(bpy.data.objects.new("Objetivo", None))
target.location = (0, 0, 0.9)
cam = link(bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara")))
cam.data.lens = 35
cam.data.dof.use_dof = True
cam.data.dof.focus_object = target
cam.data.dof.aperture_fstop = 2.8
scene.camera = cam
c = cam.constraints.new("TRACK_TO")
c.target = target
driver(cam, "location", 0, f"11*sin(0.15*sin(2*pi*frame/{FRAMES}))")
driver(cam, "location", 1, f"-11*cos(0.15*sin(2*pi*frame/{FRAMES}))")
cam.location.z = 2.6

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
scene.view_settings.view_transform = "Standard"
scene.view_settings.look = "Medium High Contrast"

if args.frames:
    a, b = args.frames.split("-")
    scene.frame_start, scene.frame_end = int(a), int(b)
if args.blend:
    bpy.ops.wm.save_as_mainfile(filepath=args.blend)
if not args.no_render:
    bpy.ops.render.render(animation=True)
