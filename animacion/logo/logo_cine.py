"""
Logo 3D con acabado cinematográfico — Blender, generado por script.

Cielo de atardecer físico, cordillera, mar de nubes en capas, niebla por
distancia, resplandor (glow) en postproducción. La cámara emerge de entre
las nubes mientras el logo (colores originales, acabado brillante) gira y
queda de frente con el sol a contraluz. 6 s, 1280x720, 24 fps.

La "niebla" es simulada (sin volúmenes) para que renderice rápido en CPU;
en GPU funciona igual.

    python animacion/logo/logo_cine.py --logo animacion/logo/logo.png --out frames/
    blender -b -P animacion/logo/logo_cine.py -- --logo ... --out frames/

Requiere: bpy, numpy, pillow, scipy, scikit-image.
Opciones: --samples N, --res-pct N, --frames A-B, --blend PATH, --no-render, --gpu
"""

import argparse
import math
import os
import random
import sys
import tempfile

import bpy
import numpy as np
from mathutils import Vector, noise
from PIL import Image, ImageFilter
from scipy import ndimage
from skimage import measure

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else argv[1:]
ap = argparse.ArgumentParser()
ap.add_argument("--logo", default="animacion/logo/logo.png")
ap.add_argument("--out", default="frames/")
ap.add_argument("--samples", type=int, default=32)
ap.add_argument("--res-pct", type=int, default=100)
ap.add_argument("--frames", default=None)
ap.add_argument("--blend", default=None)
ap.add_argument("--no-render", action="store_true")
ap.add_argument("--gpu", action="store_true", help="usar GPU (CUDA/OptiX) si hay")
args = ap.parse_args(argv)

FPS = 24
FRAMES = 144             # 6 s
LOGO_Z = 9.0             # altura del centro del logo
WIDTH = 4.0
DEPTH = 0.1
FOG = (0.95, 0.58, 0.34)  # color de la bruma del atardecer
random.seed(3)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.frame_start, scene.frame_end = 1, FRAMES
scene.render.fps = FPS


def link(o):
    scene.collection.objects.link(o)
    return o


def driver(target, path, expr, index=-1):
    fc = target.driver_add(path, index) if index >= 0 else target.driver_add(path)
    fc.driver.type = "SCRIPTED"
    fc.driver.expression = expr


def fog_mix(nt, shader_out, out_node, dist_scale, strength=1.0):
    """Mezcla un shader con bruma según la distancia a la cámara."""
    cam = nt.nodes.new("ShaderNodeCameraData")
    m = nt.nodes.new("ShaderNodeMath")
    m.operation = "MULTIPLY"
    m.inputs[1].default_value = -1.0 / dist_scale
    ex = nt.nodes.new("ShaderNodeMath")
    ex.operation = "EXPONENT"
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "SUBTRACT"
    inv.inputs[0].default_value = 1.0
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = (*FOG, 1)
    e.inputs["Strength"].default_value = strength
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(cam.outputs["View Distance"], m.inputs[0])
    nt.links.new(m.outputs[0], ex.inputs[0])
    nt.links.new(ex.outputs[0], inv.inputs[1])
    nt.links.new(inv.outputs[0], mix.inputs[0])
    nt.links.new(shader_out, mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out_node.inputs["Surface"])
    return mix


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    return m, nt, nt.nodes.new("ShaderNodeOutputMaterial")


# ================================================================ cielo + sol
SUN_ELEV = math.radians(4.5)
SUN_AZ = math.radians(0.0)        # 0 = hacia +Y: justo detrás del logo, a contraluz
world = bpy.data.worlds.new("Cielo")
scene.world = world
world.use_nodes = True
wn = world.node_tree.nodes
wn.clear()
sky = wn.new("ShaderNodeTexSky")
sky.sky_type = "MULTIPLE_SCATTERING"
sky.sun_elevation = SUN_ELEV
sky.sun_rotation = SUN_AZ
sky.altitude = 2500
sky.air_density = 2.0
sky.aerosol_density = 6.0
sky.sun_intensity = 0.3
bg = wn.new("ShaderNodeBackground")
bg.inputs["Strength"].default_value = 0.22
wo = wn.new("ShaderNodeOutputWorld")
world.node_tree.links.new(sky.outputs[0], bg.inputs[0])
world.node_tree.links.new(bg.outputs[0], wo.inputs[0])

# dirección del sol (convención del Sky Texture: azimut medido desde +Y)
sun_dir = Vector((math.sin(SUN_AZ) * math.cos(SUN_ELEV),
                  math.cos(SUN_AZ) * math.cos(SUN_ELEV),
                  math.sin(SUN_ELEV)))
sl = bpy.data.lights.new("Sol", "SUN")
sl.energy = 5.0
sl.color = (1.0, 0.68, 0.42)
sl.angle = math.radians(1.5)
so = link(bpy.data.objects.new("Sol", sl))
so.rotation_euler = (-sun_dir).to_track_quat("-Z", "Y").to_euler()

# luz de cielo azulada desde arriba-atrás para que el frente del logo no quede negro
fl = bpy.data.lights.new("Relleno", "AREA")
fl.energy = 1400
fl.size = 12
fl.color = (0.75, 0.82, 1.0)
fo = link(bpy.data.objects.new("Relleno", fl))
fo.location = (3, -14, LOGO_Z + 6)
fo.rotation_euler = (math.radians(35), 0, math.radians(10))

# ================================================================ montañas
N = 220
SIZE = 900.0
verts, faces = [], []
for j in range(N):
    for i in range(N):
        x = (i / (N - 1) - 0.5) * SIZE
        y = (j / (N - 1) - 0.5) * SIZE + SIZE * 0.35
        d = math.hypot(x, y)
        ridge = noise.ridged_multi_fractal(Vector((x / 140, y / 140, 0.3)), 1.0, 2.0, 7, 1.0, 2.0)
        base = noise.fractal(Vector((x / 300, y / 300, 1.7)), 1.0, 2.0, 5)
        mask = min(1.0, max(0.0, (d - 60) / 140))          # bajo cerca del logo, alto lejos
        h = -12 + mask * (ridge * 24 + base * 9)
        verts.append((x, y, h))
for j in range(N - 1):
    for i in range(N - 1):
        a = j * N + i
        faces.append((a, a + 1, a + N + 1, a + N))
me = bpy.data.meshes.new("Montanas")
me.from_pydata(verts, [], faces)
me.shade_smooth() if hasattr(me, "shade_smooth") else None
mtn = link(bpy.data.objects.new("Montanas", me))
m, nt, out = new_mat("Roca")
geo = nt.nodes.new("ShaderNodeNewGeometry")
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nt.links.new(geo.outputs["Normal"], sep.inputs[0])
ramp = nt.nodes.new("ShaderNodeValToRGB")          # pendiente: roca oscura / cima con polvo claro
ramp.color_ramp.elements[0].position = 0.55
ramp.color_ramp.elements[0].color = (0.09, 0.065, 0.05, 1)
ramp.color_ramp.elements[1].position = 0.85
ramp.color_ramp.elements[1].color = (0.32, 0.25, 0.2, 1)
nt.links.new(sep.outputs["Z"], ramp.inputs[0])
tx = nt.nodes.new("ShaderNodeTexNoise")
tx.inputs["Scale"].default_value = 0.08
tx.inputs["Detail"].default_value = 12
mixc = nt.nodes.new("ShaderNodeMix")
mixc.data_type = "RGBA"
mixc.blend_type = "MULTIPLY"
mixc.inputs["Factor"].default_value = 0.6
nt.links.new(ramp.outputs[0], mixc.inputs["A"])
nt.links.new(tx.outputs["Color"], mixc.inputs["B"])
b = nt.nodes.new("ShaderNodeBsdfPrincipled")
b.inputs["Roughness"].default_value = 0.9
nt.links.new(mixc.outputs["Result"], b.inputs["Base Color"])
bump = nt.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.4
nt.links.new(tx.outputs["Fac"], bump.inputs["Height"])
nt.links.new(bump.outputs[0], b.inputs["Normal"])
fog_mix(nt, b.outputs[0], out, dist_scale=700, strength=0.9)
me.materials.append(m)

# ================================================================ mar de nubes (capas)
def cloud_layer(name, z, seed, scale, density, drift, bright=1.0):
    bpy.ops.mesh.primitive_plane_add(size=1200, location=(0, 200, z))
    o = bpy.context.active_object
    o.name = name
    m, nt, out = new_mat(name)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    n = nt.nodes.new("ShaderNodeTexNoise")
    n.noise_dimensions = "4D"
    n.inputs["Scale"].default_value = scale
    n.inputs["Detail"].default_value = 9
    n.inputs["Roughness"].default_value = 0.62
    n.inputs["W"].default_value = seed
    driver(n.inputs["W"], "default_value", f"{seed} + frame*0.0025")
    r = nt.nodes.new("ShaderNodeValToRGB")
    r.color_ramp.elements[0].position = 0.5 - density
    r.color_ramp.elements[0].color = (0, 0, 0, 1)
    r.color_ramp.elements[1].position = 0.68 - density
    r.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(tc.outputs["Object"], n.inputs["Vector"])
    nt.links.new(n.outputs["Fac"], r.inputs[0])
    # cuerpo de la nube: difuso + translúcido (brilla a contraluz) + algo de emisión cálida
    dif = nt.nodes.new("ShaderNodeBsdfDiffuse")
    dif.inputs["Color"].default_value = (0.85, 0.8, 0.78, 1)
    tr = nt.nodes.new("ShaderNodeBsdfTranslucent")
    tr.inputs["Color"].default_value = (1.0, 0.7, 0.45, 1)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*FOG, 1)
    em.inputs["Strength"].default_value = 0.08 * bright
    a1 = nt.nodes.new("ShaderNodeAddShader")
    a2 = nt.nodes.new("ShaderNodeAddShader")
    nt.links.new(dif.outputs[0], a1.inputs[0])
    nt.links.new(tr.outputs[0], a1.inputs[1])
    nt.links.new(a1.outputs[0], a2.inputs[0])
    nt.links.new(em.outputs[0], a2.inputs[1])
    tp = nt.nodes.new("ShaderNodeBsdfTransparent")
    body = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(r.outputs["Color"], body.inputs[0])
    nt.links.new(tp.outputs[0], body.inputs[1])
    nt.links.new(a2.outputs[0], body.inputs[2])
    # bruma por distancia, respetando la transparencia de la nube
    fm = fog_mix(nt, body.outputs[0], out, dist_scale=900, strength=0.9)
    fogged = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(r.outputs["Color"], fogged.inputs[0])
    nt.links.new(tp.outputs[0], fogged.inputs[1])
    nt.links.new(fm.outputs[0], fogged.inputs[2])
    nt.links.new(fogged.outputs[0], out.inputs["Surface"])
    o.data.materials.append(m)
    o.visible_shadow = False
    driver(o, "location", f"frame*{drift}", 0)
    return o


for k, (z, sc, de) in enumerate([(-2.0, 0.012, 0.18), (0.0, 0.016, 0.12), (1.8, 0.02, 0.08),
                                  (3.4, 0.028, 0.04), (4.8, 0.04, -0.02)]):
    cloud_layer(f"Nubes{k}", z, seed=k * 7.3, scale=sc, density=de, drift=0.02 + 0.012 * k)

# ================================================================ logo 3D (colores originales)
UPSCALE = 4
src = Image.open(args.logo).convert("RGBA")
big = src.resize((src.width * UPSCALE, src.height * UPSCALE), Image.LANCZOS)
rgba = np.asarray(big).astype(np.float32) / 255.0
solid = rgba[..., 3] > 0.6
_, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
tex_path = os.path.join(tempfile.mkdtemp(), "logo_textura.png")
Image.fromarray((rgba[..., :3][iy, ix] * 255).astype(np.uint8)).save(tex_path)

mask = np.pad(np.asarray(big.getchannel("A").filter(ImageFilter.GaussianBlur(1.2))) / 255.0, 2)
H_px, W_px = rgba.shape[:2]
px = WIDTH / W_px
HEIGHT = H_px * px
cu = bpy.data.curves.new("LogoCurva", "CURVE")
cu.dimensions = "2D"
cu.fill_mode = "BOTH"
cu.extrude = DEPTH
cu.bevel_depth = 0.012
cu.bevel_resolution = 2
for c in measure.find_contours(mask, 0.5):
    c = measure.approximate_polygon(c, tolerance=0.7)
    if len(c) < 4:
        continue
    xy = [((col - 2) * px - WIDTH / 2, -(row - 2) * px + HEIGHT / 2) for row, col in c[:-1]]
    area = 0.5 * sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(xy, xy[1:] + xy[:1]))
    if abs(area) < (3 * px) ** 2:
        continue
    s = cu.splines.new("POLY")
    s.points.add(len(xy) - 1)
    for p, (x, y) in zip(s.points, xy):
        p.co = (x, y, 0, 1)
    s.use_cyclic_u = True
co = link(bpy.data.objects.new("Logo", cu))
bpy.context.view_layer.objects.active = co
co.select_set(True)
bpy.ops.object.convert(target="MESH")
logo = bpy.context.active_object
lm = logo.data
while lm.uv_layers:
    lm.uv_layers.remove(lm.uv_layers[0])
uv = lm.uv_layers.new(name="UVMap")
for poly in lm.polygons:
    poly.use_smooth = abs(poly.normal.z) < 0.5
    for li in poly.loop_indices:
        v = lm.vertices[lm.loops[li].vertex_index].co
        uv.data[li].uv = (v.x / WIDTH + 0.5, v.y / HEIGHT + 0.5)

m, nt, out = new_mat("LogoMat")
b = nt.nodes.new("ShaderNodeBsdfPrincipled")
b.inputs["Roughness"].default_value = 0.22
b.inputs["Coat Weight"].default_value = 1.0
b.inputs["Coat Roughness"].default_value = 0.05
b.inputs["Specular IOR Level"].default_value = 0.6
img = nt.nodes.new("ShaderNodeTexImage")
img.image = bpy.data.images.load(tex_path)
img.interpolation = "Cubic"
img.extension = "EXTEND"
geo = nt.nodes.new("ShaderNodeNewGeometry")
vt = nt.nodes.new("ShaderNodeVectorTransform")
vt.convert_from, vt.convert_to, vt.vector_type = "WORLD", "OBJECT", "NORMAL"
sep = nt.nodes.new("ShaderNodeSeparateXYZ")
ab = nt.nodes.new("ShaderNodeMath")
ab.operation = "ABSOLUTE"
mr = nt.nodes.new("ShaderNodeMapRange")
mr.inputs["From Max"].default_value = 0.9
mr.inputs["To Min"].default_value = 0.5
mix = nt.nodes.new("ShaderNodeMix")
mix.data_type = "RGBA"
mix.blend_type = "MULTIPLY"
mix.inputs["Factor"].default_value = 1.0
nt.links.new(geo.outputs["Normal"], vt.inputs[0])
nt.links.new(vt.outputs[0], sep.inputs[0])
nt.links.new(sep.outputs["Z"], ab.inputs[0])
nt.links.new(ab.outputs[0], mr.inputs["Value"])
nt.links.new(img.outputs["Color"], mix.inputs["A"])
nt.links.new(mr.outputs["Result"], mix.inputs["B"])
nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
nt.links.new(b.outputs[0], out.inputs["Surface"])
lm.materials.append(m)

pivot = link(bpy.data.objects.new("Pivote", None))
logo.parent = pivot
logo.rotation_euler = (math.radians(90), 0, 0)
logo.scale = (1.0, 1.0, 1.0)


def key(f, z, rot, tilt=0.0):
    pivot.location = (0, 0, z)
    pivot.rotation_euler = (math.radians(tilt), 0, math.radians(rot))
    pivot.keyframe_insert("location", frame=f)
    pivot.keyframe_insert("rotation_euler", frame=f)


# el logo sube desde las nubes girando y se asienta de frente
key(1, LOGO_Z - 3.2, -200, 8)
key(40, LOGO_Z - 0.6, -70, 3)
key(96, LOGO_Z, 0, 0)
key(FRAMES, LOGO_Z + 0.15, 4, 0)
driver(logo, "location", "0.05*sin(max(frame-96,0)/10)", 2)

# ================================================================ cámara
tgt = link(bpy.data.objects.new("ObjetivoCam", None))
cam = link(bpy.data.objects.new("Camara", bpy.data.cameras.new("Camara")))
cam.data.lens = 50
cam.data.sensor_width = 36
cam.data.dof.use_dof = True
cam.data.dof.focus_object = pivot
cam.data.dof.aperture_fstop = 4.0
scene.camera = cam
tc = cam.constraints.new("TRACK_TO")
tc.target = tgt
# arranca entre las nubes, sube por encima de la capa superior y se acerca
for f, loc, look in [(1, (-3.5, -34, 3.9), (0, 0, LOGO_Z - 2.5)),
                     (50, (-1.8, -24, 7.2), (0, 0, LOGO_Z - 0.6)),
                     (110, (0.0, -12.5, LOGO_Z + 0.5), (0, 0, LOGO_Z + 0.5)),
                     (FRAMES, (0.3, -11.2, LOGO_Z + 0.4), (0, 0, LOGO_Z + 0.55))]:
    cam.location = loc
    tgt.location = look
    cam.keyframe_insert("location", frame=f)
    tgt.keyframe_insert("location", frame=f)
# pequeño temblor de cámara en mano
driver(cam, "rotation_euler", "0.003*sin(frame/7.3)+0.002*sin(frame/3.1)", 1)

# ================================================================ render
r = scene.render
r.engine = "CYCLES"
if args.gpu:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for dev_type in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = dev_type
            prefs.get_devices()
            if any(d.type == dev_type for d in prefs.devices):
                for d in prefs.devices:
                    d.use = True
                scene.cycles.device = "GPU"
                break
        except TypeError:
            continue
else:
    scene.cycles.device = "CPU"
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.cycles.transparent_max_bounces = 24
scene.cycles.blur_glossy = 1.0
scene.cycles.sample_clamp_direct = 12.0     # evita destellos sueltos en los biseles
scene.cycles.sample_clamp_indirect = 4.0
r.resolution_x, r.resolution_y = 1280, 720
r.resolution_percentage = args.res_pct
r.image_settings.file_format = "PNG"
r.filepath = args.out.rstrip("/") + "/"
r.use_motion_blur = True
r.motion_blur_shutter = 0.5
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "AgX - Medium High Contrast"
scene.view_settings.exposure = -1.0

# ---------------------------------------------------------------- postproducción
ct = bpy.data.node_groups.new("Post", "CompositorNodeTree")
scene.compositing_node_group = ct
rl = ct.nodes.new("CompositorNodeRLayers")
gout = ct.nodes.new("NodeGroupOutput")
ct.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
bloom = ct.nodes.new("CompositorNodeGlare")       # resplandor
bloom.inputs["Type"].default_value = "Fog Glow"
bloom.inputs["Threshold"].default_value = 1.6
bloom.inputs["Strength"].default_value = 0.35
ct.links.new(rl.outputs["Image"], bloom.inputs["Image"])
ct.links.new(bloom.outputs["Image"], gout.inputs[0])
scene.render.use_compositing = True
scene.render.compositor_device = "GPU" if args.gpu else "CPU"


if args.frames:
    a, b = args.frames.split("-")
    scene.frame_start, scene.frame_end = int(a), int(b)
if args.blend:
    bpy.ops.file.pack_all()          # el .blend lleva la textura adentro
    bpy.ops.wm.save_as_mainfile(filepath=args.blend)
if not args.no_render:
    bpy.ops.render.render(animation=True)
