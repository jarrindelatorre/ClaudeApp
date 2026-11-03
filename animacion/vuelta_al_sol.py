"""
Vuelta al Sol — animación en Blender (generada 100% por script).

Una Tierra da una vuelta completa alrededor del Sol dejando una estela dorada;
al cerrar la vuelta estalla confeti y aparece "¡Feliz vuelta al Sol!".

Uso (Blender instalado):
    blender -b -P animacion/vuelta_al_sol.py -- --out animacion/frames/
Uso (módulo bpy de PyPI: pip install bpy):
    python animacion/vuelta_al_sol.py --out animacion/frames/

Opciones:
    --out DIR        carpeta donde se escriben los PNG (default: ./frames/)
    --samples N      muestras de Cycles (default: 48)
    --res-pct N      % de resolución sobre 1280x720 (default: 100)
    --frames A-B     rango de frames a renderizar (default: todo)
    --blend PATH     además guarda el .blend
    --no-render      sólo arma la escena

Después, para armar el video:
    ffmpeg -framerate 24 -i frames/%04d.png -c:v libx264 -pix_fmt yuv420p -crf 18 vuelta_al_sol.mp4
"""

import argparse
import math
import random
import sys

import bpy
from mathutils import Vector

# ---------------------------------------------------------------- argumentos
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--out", default="frames/")
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--res-pct", type=int, default=100)
ap.add_argument("--frames", default=None)
ap.add_argument("--blend", default=None)
ap.add_argument("--no-render", action="store_true")
args = ap.parse_args(argv)

FPS = 24
FRAME_END = 240          # 10 s
LAP_END = 168            # la vuelta completa termina en el frame 168 (7 s)
ORBIT_R = 6.0
random.seed(7)

# ---------------------------------------------------------------- escena vacía
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end = FRAME_END
scene.render.fps = FPS


def link(obj):
    scene.collection.objects.link(obj)
    return obj


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    return m, nt, out


def add_driver(obj, path, expr, index=-1):
    fc = obj.driver_add(path, index) if index >= 0 else obj.driver_add(path)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr
    return fc


def sphere(name, radius, loc=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=loc,
                                         segments=segments, ring_count=rings)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return o


# ---------------------------------------------------------------- mundo: estrellas
world = bpy.data.worlds.new("Cielo")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()
w_out = wn.new("ShaderNodeOutputWorld")
w_bg = wn.new("ShaderNodeBackground")
w_coord = wn.new("ShaderNodeTexCoord")
w_vor = wn.new("ShaderNodeTexVoronoi")
w_vor.inputs["Scale"].default_value = 90.0
w_ramp = wn.new("ShaderNodeValToRGB")
w_ramp.color_ramp.elements[0].position = 0.0
w_ramp.color_ramp.elements[0].color = (1, 1, 1, 1)
w_ramp.color_ramp.elements[1].position = 0.06
w_ramp.color_ramp.elements[1].color = (0, 0, 0, 1)
w_noise = wn.new("ShaderNodeTexNoise")       # nebulosa suave de fondo
w_noise.inputs["Scale"].default_value = 1.6
w_neb = wn.new("ShaderNodeValToRGB")
w_neb.color_ramp.elements[0].color = (0.0005, 0.0004, 0.002, 1)
w_neb.color_ramp.elements[1].color = (0.012, 0.003, 0.02, 1)
w_add = wn.new("ShaderNodeMix")
w_add.data_type = "RGBA"
w_add.blend_type = "ADD"
w_add.inputs["Factor"].default_value = 1.0
wl.new(w_coord.outputs["Generated"], w_vor.inputs["Vector"])
wl.new(w_vor.outputs["Distance"], w_ramp.inputs["Fac"])
wl.new(w_coord.outputs["Generated"], w_noise.inputs["Vector"])
wl.new(w_noise.outputs["Fac"], w_neb.inputs["Fac"])
wl.new(w_neb.outputs["Color"], w_add.inputs["A"])
wl.new(w_ramp.outputs["Color"], w_add.inputs["B"])
wl.new(w_add.outputs["Result"], w_bg.inputs["Color"])
w_bg.inputs["Strength"].default_value = 1.0
wl.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

# ---------------------------------------------------------------- Sol
sun = sphere("Sol", 1.6)
m, nt, out = new_mat("SolSuperficie")
tc = nt.nodes.new("ShaderNodeTexCoord")
noise = nt.nodes.new("ShaderNodeTexNoise")
noise.inputs["Scale"].default_value = 3.5
noise.inputs["Detail"].default_value = 8.0
ramp = nt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.35
ramp.color_ramp.elements[0].color = (1.0, 0.18, 0.01, 1)
ramp.color_ramp.elements[1].position = 0.7
ramp.color_ramp.elements[1].color = (1.0, 0.85, 0.3, 1)
em = nt.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 2.2
nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
nt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
nt.links.new(em.outputs["Emission"], out.inputs["Surface"])
sun.data.materials.append(m)
sun.visible_shadow = False
# la superficie "hierve": el ruido se mueve con el tiempo (4D)
noise.noise_dimensions = "4D"
fc = noise.inputs["W"].driver_add("default_value")
fc.driver.expression = "frame/60"
# el Sol gira lento
add_driver(sun, "rotation_euler", "frame*0.004", 2)


def halo(name, radius, color, strength, power):
    o = sphere(name, radius, segments=48, rings=24)
    m, nt, out = new_mat(name)
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    pw = nt.nodes.new("ShaderNodeMath")
    pw.operation = "POWER"
    pw.inputs[1].default_value = power
    inv = nt.nodes.new("ShaderNodeMath")       # facing: 0 de frente -> 1 en el borde
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = color
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = strength
    add = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(lw.outputs["Facing"], inv.inputs[1])
    nt.links.new(inv.outputs[0], pw.inputs[0])
    nt.links.new(pw.outputs[0], mul.inputs[0])
    nt.links.new(mul.outputs[0], e.inputs["Strength"])
    nt.links.new(tr.outputs[0], add.inputs[0])
    nt.links.new(e.outputs[0], add.inputs[1])
    nt.links.new(add.outputs[0], out.inputs["Surface"])
    o.data.materials.append(m)
    o.visible_shadow = False
    return o


halo("HaloSol1", 2.3, (1.0, 0.45, 0.05, 1), 1.0, 2.5)
halo("HaloSol2", 3.6, (1.0, 0.25, 0.03, 1), 0.35, 3.0)

# luz del Sol (dentro de la esfera; el Sol no proyecta sombra)
ld = bpy.data.lights.new("LuzSol", "POINT")
ld.energy = 6000
ld.color = (1.0, 0.85, 0.65)
ld.shadow_soft_size = 1.5
link(bpy.data.objects.new("LuzSol", ld))

# luz de relleno tenue para que el lado nocturno no sea negro puro
fill = bpy.data.lights.new("Relleno", "SUN")
fill.energy = 0.25
fill.color = (0.5, 0.6, 1.0)
fo = link(bpy.data.objects.new("Relleno", fill))
fo.rotation_euler = (math.radians(60), 0, math.radians(200))

# ---------------------------------------------------------------- órbita: anillo tenue + estela dorada
bpy.ops.curve.primitive_bezier_circle_add(radius=ORBIT_R)
ring = bpy.context.active_object
ring.name = "Orbita"
ring.data.bevel_depth = 0.012
ring.data.resolution_u = 64
m, nt, out = new_mat("OrbitaTenue")
e = nt.nodes.new("ShaderNodeEmission")
e.inputs["Color"].default_value = (0.5, 0.6, 1.0, 1)
e.inputs["Strength"].default_value = 0.35
nt.links.new(e.outputs[0], out.inputs["Surface"])
ring.data.materials.append(m)

# la Tierra arranca a la izquierda del Sol y pasa primero por detrás
theta0 = math.pi
direction = -1.0

# estela: polilínea abierta exactamente sobre la órbita (bevel_factor sólo
# funciona en splines abiertas), que se va revelando a medida que avanza
N_TRAIL = 256
tc_ = bpy.data.curves.new("Estela", "CURVE")
tc_.dimensions = "3D"
tc_.bevel_depth = 0.045
tc_.bevel_resolution = 4
spl = tc_.splines.new("POLY")
spl.points.add(N_TRAIL)
for k in range(N_TRAIL + 1):
    a_ = theta0 + direction * 2 * math.pi * k / N_TRAIL
    spl.points[k].co = (ORBIT_R * math.cos(a_), ORBIT_R * math.sin(a_), 0, 1)
trail = link(bpy.data.objects.new("Estela", tc_))
m, nt, out = new_mat("EstelaDorada")
e = nt.nodes.new("ShaderNodeEmission")
e.inputs["Color"].default_value = (1.0, 0.7, 0.2, 1)
e.inputs["Strength"].default_value = 2.5
nt.links.new(e.outputs[0], out.inputs["Surface"])
tc_.materials.append(m)
fc = tc_.driver_add("bevel_factor_end")
fc.driver.expression = f"min(max(frame-1,0)/{LAP_END - 1},1)"

# ---------------------------------------------------------------- Tierra
pivot = link(bpy.data.objects.new("PivoteOrbita", None))
add_driver(pivot, "rotation_euler",
           f"{theta0} + {direction}*2*pi*(frame-1)/{LAP_END - 1}", 2)

earth = sphere("Tierra", 0.55, loc=(ORBIT_R, 0, 0))
earth.parent = pivot
earth.rotation_euler[0] = math.radians(23.4)
add_driver(earth, "rotation_euler", "frame*0.12", 2)
m, nt, out = new_mat("TierraMat")
tc = nt.nodes.new("ShaderNodeTexCoord")
n = nt.nodes.new("ShaderNodeTexNoise")
n.inputs["Scale"].default_value = 2.2
n.inputs["Detail"].default_value = 10.0
r = nt.nodes.new("ShaderNodeValToRGB")
r.color_ramp.interpolation = "CONSTANT"
r.color_ramp.elements[0].color = (0.01, 0.08, 0.35, 1)   # océano
r.color_ramp.elements[1].position = 0.55
r.color_ramp.elements[1].color = (0.08, 0.35, 0.08, 1)   # tierra
el = r.color_ramp.elements.new(0.66)
el.color = (0.45, 0.38, 0.2, 1)                          # montaña
bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
bsdf.inputs["Roughness"].default_value = 0.6
nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
nt.links.new(n.outputs["Fac"], r.inputs["Fac"])
nt.links.new(r.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(bsdf.outputs[0], out.inputs["Surface"])
earth.data.materials.append(m)

atmo = halo("Atmosfera", 0.63, (0.25, 0.55, 1.0, 1), 1.0, 4.0)
atmo.parent = pivot
atmo.location = (ORBIT_R, 0, 0)

# Luna
moon_pivot = link(bpy.data.objects.new("PivoteLuna", None))
moon_pivot.parent = pivot
moon_pivot.location = (ORBIT_R, 0, 0)
add_driver(moon_pivot, "rotation_euler", "frame*0.09", 2)
moon = sphere("Luna", 0.15, loc=(1.05, 0, 0.1), segments=32, rings=16)
moon.parent = moon_pivot
m, nt, out = new_mat("LunaMat")
b = nt.nodes.new("ShaderNodeBsdfPrincipled")
b.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
nt.links.new(b.outputs[0], out.inputs["Surface"])
moon.data.materials.append(m)

# ---------------------------------------------------------------- confeti al cerrar la vuelta
burst_origin = Vector((ORBIT_R * math.cos(theta0), ORBIT_R * math.sin(theta0), 0))
COLORS = [(1.0, 0.25, 0.4), (1.0, 0.8, 0.15), (0.2, 0.8, 1.0),
          (0.6, 0.35, 1.0), (0.3, 1.0, 0.5), (1.0, 0.5, 0.1)]
conf_mats = []
for i, c in enumerate(COLORS):
    m, nt, out = new_mat(f"Confeti{i}")
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    b.inputs["Base Color"].default_value = (*c, 1)
    b.inputs["Emission Color"].default_value = (*c, 1)
    b.inputs["Emission Strength"].default_value = 0.9
    nt.links.new(b.outputs[0], out.inputs["Surface"])
    conf_mats.append(m)

bpy.ops.mesh.primitive_plane_add(size=0.14)
conf_proto = bpy.context.active_object
conf_mesh = conf_proto.data
bpy.data.objects.remove(conf_proto)

GRAV = Vector((0, 0, -9.0))
start = LAP_END - 2
for i in range(140):
    me = conf_mesh.copy()
    me.materials.append(random.choice(conf_mats))
    o = link(bpy.data.objects.new(f"Confeti{i:03d}", me))
    # dirección aleatoria hacia arriba / afuera
    v = Vector((random.gauss(0, 1), random.gauss(0, 1), abs(random.gauss(0, 1)) + 0.8))
    v = v.normalized() * random.uniform(4.5, 8.5)
    spin = Vector([random.uniform(-14, 14) for _ in range(3)])
    delay = random.uniform(0, 4)
    for f in range(int(start), FRAME_END + 1, 3):
        t = max(0.0, (f - start - delay) / FPS)
        drag = 1.0 - math.exp(-1.2 * t)          # el aire frena el confeti
        pos = burst_origin + v * (drag / 1.2) + GRAV * 0.5 * t * t * 0.35
        o.location = pos
        o.rotation_euler = spin * t
        s = 0.0 if t == 0 else min(1.0, t * 8)
        o.scale = (s, s, s)
        o.keyframe_insert("location", frame=f)
        o.keyframe_insert("rotation_euler", frame=f)
        o.keyframe_insert("scale", frame=f)
    o.scale = (0, 0, 0)
    o.keyframe_insert("scale", frame=1)

# ---------------------------------------------------------------- texto final
cam_loc = Vector((0, -17.5, 6.8))
tilt = math.atan2(cam_loc.z - 3.9, -cam_loc.y)

txt_curve = bpy.data.curves.new("TextoFeliz", "FONT")
txt_curve.body = "¡Feliz vuelta al Sol!"
txt_curve.align_x = "CENTER"
txt_curve.align_y = "CENTER"
txt_curve.size = 1.05
txt_curve.extrude = 0.06
txt_curve.bevel_depth = 0.015
txt = link(bpy.data.objects.new("TextoFeliz", txt_curve))
txt.location = (0, -2.5, 3.9)
txt.rotation_euler = (math.radians(90) - tilt, 0, 0)
m, nt, out = new_mat("TextoOro")
b = nt.nodes.new("ShaderNodeBsdfPrincipled")
b.inputs["Base Color"].default_value = (1.0, 0.75, 0.25, 1)
b.inputs["Metallic"].default_value = 1.0
b.inputs["Roughness"].default_value = 0.25
b.inputs["Emission Color"].default_value = (1.0, 0.7, 0.25, 1)
b.inputs["Emission Strength"].default_value = 0.6
nt.links.new(b.outputs[0], out.inputs["Surface"])
txt_curve.materials.append(m)

for f, s in [(1, 0.0), (LAP_END + 4, 0.0), (LAP_END + 18, 1.12), (LAP_END + 26, 1.0)]:
    txt.scale = (s, s, s)
    txt.keyframe_insert("scale", frame=f)

# ---------------------------------------------------------------- cámara
target = link(bpy.data.objects.new("ObjetivoCam", None))
target.location = (0, 0, 0.3)
target.keyframe_insert("location", frame=1)
target.keyframe_insert("location", frame=LAP_END - 10)
target.location = (0, 0, 1.6)
target.keyframe_insert("location", frame=LAP_END + 20)

cam_data = bpy.data.cameras.new("Camara")
cam_data.lens = 32
cam = link(bpy.data.objects.new("Camara", cam_data))
scene.camera = cam
tr = cam.constraints.new("TRACK_TO")
tr.target = target
tr.track_axis = "TRACK_NEGATIVE_Z"
tr.up_axis = "UP_Y"
# arranca más cerca y de costado, se abre a la vista general
for f, loc in [(1, (7.5, -12.5, 3.2)),
               (90, (2.5, -16.0, 5.2)),
               (LAP_END, (0, -17.5, 6.8)),
               (FRAME_END, (0, -16.2, 6.2))]:
    cam.location = loc
    cam.keyframe_insert("location", frame=f)

# ---------------------------------------------------------------- render
r = scene.render
r.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 4
scene.cycles.transparent_max_bounces = 16
r.resolution_x = 1280
r.resolution_y = 720
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
