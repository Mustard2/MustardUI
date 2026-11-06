# Build dust_motes.blend: the Dust Motes node group, its motes and haze materials
# Usage: Blender --background --factory-startup --python dust_motes_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, socket, write

RESOURCE = "dust_motes.blend"
NODE_GROUP = "MustardUI Dust Motes"
MOTES = "MustardUI Dust Motes"
HAZE = "MustardUI Dust Motes Haze"
# Most motes, not to run out of memory in a large box
MAX_MOTES = 2000000
# Meters at the box sides the motes fade in, at most a quarter of the box
BORDER = 0.2
# Swing of the motes in the swirls, relative to their size, and the flutter of each mote, in m,
# and its rates, per second
SWING = 1.5
# Rate the swirls change at, for the median mote to move at the Swirl Speed
SWIRL_RATE = 0.6
FLUTTER = 0.002
FLUTTER_RATE = (0.05, 0.15)
# Twinkles per second, the share of light kept by the faces turned off, and the twinkle scale to
# keep the mean light
TWINKLE_RATE = (0.3, 1.5)
TWINKLE_POWER = 3.0
TWINKLE_MEAN = 2 * math.pi / (4 / 3)
# Share of the light the motes scatter back, most going through them, lighting them up against
# the light
DIFFUSE = 0.15
# Haze: size of its voxels and of its wisps, in m, and its swirling speed, per second
HAZE_VOXEL = 0.15
HAZE_WISPS = 0.8
HAZE_SPEED = 0.02


def build_inputs(ng):
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        default_value=800.0,
        min_value=0.0,
        description="Motes per cubic meter of the box",
    )
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0012,
        min_value=0.0,
        description="Diameter of the motes, in average, a few larger",
    )
    add_input(
        ng,
        "Camera Fade",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.4,
        min_value=0.0,
        description="Distance from the active camera the motes fade out in, not to blur into "
        "large blobs in front of it",
    )
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the random motes")

    panel = ng.interface.new_panel("Look")
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        panel,
        default_value=(1.0, 0.96, 0.9, 1.0),
        description="Color of the motes",
    )
    add_input(
        ng,
        "Brightness",
        "NodeSocketFloat",
        panel,
        default_value=10.0,
        min_value=0.0,
        description="Light the motes scatter, only where the lights reach them",
    )
    add_input(
        ng,
        "Glow",
        "NodeSocketFloat",
        panel,
        default_value=0.0,
        min_value=0.0,
        description="Light of the motes on their own, also in the shadows",
    )
    add_input(
        ng,
        "Twinkle",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Flickering of the motes tumbling in the light",
    )

    panel = ng.interface.new_panel("Motion")
    add_input(
        ng,
        "Swirl Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.4,
        min_value=0.001,
        description="Size of the air swirls carrying the motes together",
    )
    add_input(
        ng,
        "Swirl Speed",
        "NodeSocketFloat",
        panel,
        default_value=0.005,
        min_value=0.0,
        description="Speed of the motes in the swirls, in m/s",
    )
    add_input(
        ng,
        "Wind",
        "NodeSocketVector",
        panel,
        subtype="VELOCITY",
        default_value=(0.0, 0.0, -0.001),
        description="Drift of all the motes, wrapping around the box, settling down by default",
    )

    panel = ng.interface.new_panel("Haze")
    add_input(
        ng,
        "Haze",
        "NodeSocketFloat",
        panel,
        default_value=0.1,
        min_value=0.0,
        description="Density of the fine dust in the air, showing the light beams, 0 for none",
    )

    panel = ng.interface.new_panel("Materials", default_closed=True)
    add_input(
        ng, "Motes Material", "NodeSocketMaterial", panel, description="Material of the motes"
    ).default_value = bpy.data.materials.get(MOTES)
    add_input(
        ng, "Haze Material", "NodeSocketMaterial", panel, description="Volume material of the haze"
    ).default_value = bpy.data.materials.get(HAZE)
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")


def random(t, low, high, seed, offset, x, y, data_type="FLOAT"):
    """Random value of the seed plus the offset, different for each use"""
    node = t.node(
        "FunctionNodeRandomValue",
        x,
        y,
        {"Min": low, "Max": high, "Seed": t.math("ADD", seed, offset, x=x - 1, y=y)},
        data_type=data_type,
    )
    return socket(node.outputs, "Value")


def smallest(t, vector, x, y):
    """Smallest component of the vector"""
    xyz = t.node("ShaderNodeSeparateXYZ", x, y, {0: vector}).outputs
    return t.math("MINIMUM", t.math("MINIMUM", xyz[0], xyz[1], x=x + 1, y=y), xyz[2], x=x + 2, y=y)


def border_fade(t, position, low, high, scale, width, x, y):
    """0 at the box sides, to 1 inside them by the width, in m"""
    inside = t.vmath(
        "MINIMUM",
        t.vmath("SUBTRACT", position, low, x=x, y=y),
        t.vmath("SUBTRACT", high, position, x=x, y=y - 1),
        x=x + 1,
        y=y,
    )
    inside = smallest(t, t.vmath("MULTIPLY", inside, scale, x=x + 2, y=y), x + 3, y)
    fade = t.node(
        "ShaderNodeMapRange",
        x + 6,
        y,
        {"Value": inside, "From Min": 0.0, "From Max": width},
        interpolation_type="SMOOTHSTEP",
    )
    return fade.outputs["Result"]


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = "Dust motes floating in the box, lit where the lights reach them"
    build_inputs(ng)
    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -10, 0).outputs

    t.section("Box: the motes in the bounds of the mesh, by its world scale", row=True)
    bounds = t.node("GeometryNodeBoundBox", 0, 0, {"Geometry": inputs["Geometry"]}).outputs
    low, high = bounds["Min"], bounds["Max"]
    self_object = t.node("GeometryNodeSelfObject", 0, -2).outputs[0]
    info = t.node(
        "GeometryNodeObjectInfo", 1, -2, {"Object": self_object}, transform_space="ORIGINAL"
    )
    matrix = info.outputs["Transform"]
    inverse = t.node("FunctionNodeInvertMatrix", 2, -2, {"Matrix": matrix}).outputs["Matrix"]
    scale = t.vmath("ABSOLUTE", info.outputs["Scale"], x=2, y=-3)
    size = t.vmath("SUBTRACT", high, low, x=1, y=0)
    world_size = t.vmath("MULTIPLY", size, scale, x=3, y=0)
    xyz = t.node("ShaderNodeSeparateXYZ", 4, 0, {0: world_size}).outputs
    volume = t.math("MULTIPLY", t.math("MULTIPLY", xyz[0], xyz[1], x=5, y=0), xyz[2], x=6, y=0)
    count = t.math(
        "MINIMUM", t.math("MULTIPLY", volume, inputs["Density"], x=7, y=0), MAX_MOTES, x=8, y=0
    )
    # Radius by the mean scale, the motes round in a stretched box
    xyz = t.node("ShaderNodeSeparateXYZ", 3, -3, {0: scale}).outputs
    mean_scale = t.math(
        "POWER",
        t.math("MULTIPLY", t.math("MULTIPLY", xyz[0], xyz[1], x=4, y=-3), xyz[2], x=5, y=-3),
        1 / 3,
        x=6,
        y=-3,
    )
    width = t.math(
        "MINIMUM",
        BORDER,
        t.math("MULTIPLY", smallest(t, world_size, 4, -5), 0.25, x=7, y=-5),
        x=8,
        y=-5,
    )
    time = t.node("GeometryNodeInputSceneTime", 0, -6).outputs["Seconds"]
    seed = inputs["Seed"]

    t.section("Motes: at random in the box, drifting with the Wind and wrapping around it")
    rest = t.vmath(
        "ADD",
        low,
        t.vmath(
            "MULTIPLY",
            random(t, (0, 0, 0), (1, 1, 1), seed, 0, 10, 0, "FLOAT_VECTOR"),
            size,
            x=11,
            y=0,
        ),
        x=12,
        y=0,
    )
    drift = t.node(
        "FunctionNodeTransformDirection",
        11,
        -2,
        {"Direction": t.vmath("SCALE", inputs["Wind"], time, x=10, y=-2), "Transform": inverse},
    ).outputs[0]
    drifted = t.node(
        "ShaderNodeVectorMath",
        14,
        0,
        {0: t.vmath("ADD", rest, drift, x=13, y=0), 1: high, 2: low},
        operation="WRAP",
    ).outputs[0]

    t.section("Swirls: the motes carried by the air together, each fluttering")
    at = t.node(
        "FunctionNodeTransformPoint", 30, -2, {"Vector": drifted, "Transform": matrix}
    ).outputs[0]
    # Swinging about the size of the swirls, at their speed
    phase = t.math(
        "ADD",
        t.math(
            "MULTIPLY",
            time,
            t.math(
                "DIVIDE",
                t.math("MULTIPLY", inputs["Swirl Speed"], SWIRL_RATE, x=29, y=-5),
                inputs["Swirl Size"],
                x=30,
                y=-5,
            ),
            x=31,
            y=-5,
        ),
        t.math("MULTIPLY", seed, 7.31, x=31, y=-6),
        x=32,
        y=-5,
    )
    swirl = t.node(
        "ShaderNodeTexNoise",
        33,
        -2,
        {
            "Vector": at,
            "W": phase,
            "Scale": t.math("DIVIDE", 1.0, inputs["Swirl Size"], x=32, y=-4),
            "Detail": 0.0,
        },
        noise_dimensions="4D",
    ).outputs["Color"]
    swirl = t.vmath(
        "SCALE",
        t.vmath("SUBTRACT", swirl, (0.5, 0.5, 0.5), x=34, y=-2),
        t.math("MULTIPLY", inputs["Swirl Size"], SWING, x=34, y=-4),
        x=35,
        y=-2,
    )
    # Waves of a random rate and phase on each axis, far cheaper than a noise per mote
    waves = t.vmath(
        "MULTIPLY_ADD",
        random(t, (FLUTTER_RATE[0],) * 3, (FLUTTER_RATE[1],) * 3, seed, 1, 31, -7, "FLOAT_VECTOR"),
        t.node("ShaderNodeCombineXYZ", 31, -8, {"X": time, "Y": time, "Z": time}).outputs[0],
        random(t, (0, 0, 0), (1, 1, 1), seed, 5, 31, -9, "FLOAT_VECTOR"),
        x=32,
        y=-7,
    )
    flutter = t.vmath(
        "SCALE",
        t.vmath("SINE", t.vmath("SCALE", waves, 2 * math.pi, x=33, y=-7), x=34, y=-7),
        FLUTTER,
        x=35,
        y=-7,
    )
    moved = t.vmath("ADD", t.vmath("ADD", at, swirl, x=36, y=-2), flutter, x=37, y=-2)
    position = t.node(
        "FunctionNodeTransformPoint", 38, -2, {"Vector": moved, "Transform": inverse}
    ).outputs[0]

    t.section("Size: a few larger motes, none past the box sides or close to the camera")
    # Faded at the sides where they wrap, and where the swirls move them off them
    fade = t.math(
        "MINIMUM",
        border_fade(t, drifted, low, high, scale, width, 40, -4),
        border_fade(t, position, low, high, scale, width, 40, -2),
        x=47,
        y=-2,
    )
    camera = t.node(
        "GeometryNodeObjectInfo",
        41,
        -8,
        {"Object": t.node("GeometryNodeInputActiveCamera", 40, -8).outputs[0]},
        transform_space="ORIGINAL",
    ).outputs["Location"]
    near = t.node(
        "ShaderNodeMapRange",
        43,
        -7,
        {
            "Value": t.vmath("DISTANCE", moved, camera, x=42, y=-7),
            "From Min": 0.0,
            "From Max": inputs["Camera Fade"],
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs["Result"]
    fade = t.math("MULTIPLY", fade, near, x=47, y=-3)
    larger = t.math("POWER", random(t, 0.0, 1.0, seed, 2, 40, -5), 3.0, x=41, y=-5)
    # 0.6 to 2.2 times the mean
    larger = t.math("MULTIPLY_ADD", larger, 1.6, 0.6, x=42, y=-5)
    radius = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Size"], 0.5, x=43, y=-6),
        t.math("DIVIDE", larger, mean_scale, x=43, y=-5),
        x=44,
        y=-5,
    )
    radius = t.math("MULTIPLY", radius, fade, x=48, y=-2)
    # Position and radius evaluated together, sharing the swirls and fades
    points = t.node(
        "GeometryNodePoints", 49, 0, {"Count": count, "Position": position, "Radius": radius}
    ).outputs[0]
    # Read by the random values, the same for each mote when others are deleted
    points = t.store(
        points, "id", "INT", t.node("GeometryNodeInputIndex", 49, -1).outputs[0], 50, 0
    )
    hidden = t.math(
        "LESS_THAN", t.node("GeometryNodeInputRadius", 50, -2).outputs[0], 1e-7, x=51, y=-2
    )
    points = t.node(
        "GeometryNodeDeleteGeometry",
        52,
        0,
        {"Geometry": points, "Selection": hidden},
        domain="POINT",
    ).outputs[0]

    t.section("Light: read by the material, flickering as the motes tumble")
    rate = random(t, TWINKLE_RATE[0], TWINKLE_RATE[1], seed, 3, 52, -2)
    offset = random(t, 0.0, 1.0, seed, 4, 52, -3)
    wave = t.math(
        "SINE",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY_ADD", time, rate, offset, x=53, y=-2),
            2 * math.pi,
            x=54,
            y=-2,
        ),
        x=55,
        y=-2,
    )
    flash = t.math(
        "MULTIPLY",
        t.math("POWER", t.math("MAXIMUM", wave, 0.0, x=56, y=-2), TWINKLE_POWER, x=57, y=-2),
        TWINKLE_MEAN,
        x=58,
        y=-2,
    )
    twinkle = t.node(
        "ShaderNodeMix", 59, -2, {"Factor": inputs["Twinkle"], "A": 1.0, "B": flash}
    ).outputs[0]
    # Scattered light and glow in one attribute, the twinkle evaluated once
    light = t.vmath(
        "SCALE",
        t.node(
            "ShaderNodeCombineXYZ", 59, -4, {"X": inputs["Brightness"], "Y": inputs["Glow"]}
        ).outputs[0],
        twinkle,
        x=60,
        y=-2,
    )
    points = t.store(points, "dust_motes_light", "FLOAT_VECTOR", light, 61, 0)
    points = t.store(points, "dust_motes_color", "FLOAT_COLOR", inputs["Color"], 63, 0)
    points = t.node(
        "GeometryNodeSetMaterial",
        65,
        0,
        {"Geometry": points, "Material": inputs["Motes Material"]},
    ).outputs[0]

    t.section("Haze: fine dust filling the box, in slow wisps", row=True)
    voxels = t.vmath("CEIL", t.vmath("SCALE", world_size, 1 / HAZE_VOXEL, x=0, y=-2), x=1, y=-2)
    voxels = t.vmath(
        "MINIMUM", t.vmath("MAXIMUM", voxels, (2, 2, 2), x=2, y=-2), (64, 64, 64), x=3, y=-2
    )
    resolution = t.node("ShaderNodeSeparateXYZ", 4, -2, {0: voxels}).outputs
    at = t.node(
        "FunctionNodeTransformPoint",
        1,
        -4,
        {"Vector": t.node("GeometryNodeInputPosition", 0, -4).outputs[0], "Transform": matrix},
    ).outputs[0]
    wisps = t.node(
        "ShaderNodeTexNoise",
        2,
        -4,
        {
            "Vector": at,
            "W": t.math(
                "ADD",
                t.math("MULTIPLY", time, HAZE_SPEED, x=1, y=-6),
                t.math("MULTIPLY", seed, 7.31, x=1, y=-7),
                x=2,
                y=-6,
            ),
            "Scale": 1 / HAZE_WISPS,
            "Detail": 1.0,
        },
        noise_dimensions="4D",
    ).outputs["Factor"]
    # 0.4 to 1.6 times the Haze
    wisps = t.node(
        "ShaderNodeMapRange",
        3,
        -4,
        {"Value": wisps, "From Min": 0.3, "From Max": 0.7, "To Min": 0.4, "To Max": 1.6},
    ).outputs["Result"]
    haze = t.node(
        "GeometryNodeVolumeCube",
        5,
        0,
        {
            "Density": t.math("MULTIPLY", wisps, inputs["Haze"], x=4, y=-4),
            "Min": low,
            "Max": high,
            "Resolution X": resolution[0],
            "Resolution Y": resolution[1],
            "Resolution Z": resolution[2],
        },
    ).outputs[0]
    haze = t.node(
        "GeometryNodeSetMaterial", 6, 0, {"Geometry": haze, "Material": inputs["Haze Material"]}
    ).outputs[0]
    haze = t.node(
        "GeometryNodeSwitch",
        7,
        0,
        {"Switch": t.math("GREATER_THAN", inputs["Haze"], 0.0, x=6, y=-2), "True": haze},
        input_type="GEOMETRY",
    ).outputs[0]

    t.section("Output: the box edges, to see it, the motes and the haze")
    edges = t.node(
        "GeometryNodeDeleteGeometry",
        8,
        2,
        {"Geometry": inputs["Geometry"], "Selection": True},
        domain="FACE",
        mode="ONLY_FACE",
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 9, 0)
    for geometry in (haze, points, edges):
        t.connect(geometry, joined.inputs[0])
    t.node("NodeGroupOutput", 10, 0, {0: joined.outputs[0]})
    t.arrange()
    return ng


def build_motes_material():
    """Soft round motes scattering the light, mostly forward, and casting no shadows"""
    material = bpy.data.materials.new(MOTES)
    material.use_transparent_shadow = True
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))
    color = t.node("ShaderNodeAttribute", -900, 200, attribute_name="dust_motes_color")
    light = t.node("ShaderNodeAttribute", -1100, 0, attribute_name="dust_motes_light")
    light = t.node("ShaderNodeSeparateXYZ", -900, 0, {0: light.outputs["Vector"]}).outputs
    color = color.outputs["Color"]
    lit = t.vmath("SCALE", color, light["X"], x=-650, y=100)
    forward = t.node("ShaderNodeBsdfTranslucent", -400, 200, {"Color": lit})
    diffuse = t.node("ShaderNodeBsdfDiffuse", -400, 50, {"Color": lit})
    scatter = t.node(
        "ShaderNodeMixShader", -200, 150, {0: DIFFUSE, 1: forward.outputs[0], 2: diffuse.outputs[0]}
    )
    emission = t.node("ShaderNodeEmission", -400, -150, {"Color": color, "Strength": light["Y"]})
    mote = t.node("ShaderNodeAddShader", 0, 100, {0: scatter.outputs[0], 1: emission.outputs[0]})
    # Soft edges, the motes being blurry specks
    facing = t.node("ShaderNodeLayerWeight", -200, -300, {"Blend": 0.5}).outputs["Facing"]
    alpha = t.math("POWER", t.math("SUBTRACT", 1.0, facing, x=0, y=-300), 2.0, x=150, y=-300)
    transparent = t.node("ShaderNodeBsdfTransparent", 150, -100).outputs[0]
    soft = t.node("ShaderNodeMixShader", 300, 0, {0: alpha, 1: transparent, 2: mote.outputs[0]})
    shadow = t.node("ShaderNodeLightPath", 300, 300).outputs["Is Shadow Ray"]
    shader = t.node("ShaderNodeMixShader", 500, 0, {0: shadow, 1: soft.outputs[0], 2: transparent})
    t.node("ShaderNodeOutputMaterial", 700, 0, {"Surface": shader.outputs[0]})
    return material


def build_haze_material():
    """Fine dust scattering the light forward, glowing toward the lights"""
    material = bpy.data.materials.new(HAZE)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))
    volume = t.node(
        "ShaderNodeVolumePrincipled",
        0,
        0,
        {"Color": (0.9, 0.88, 0.85, 1.0), "Density": 1.0, "Anisotropy": 0.6},
    )
    t.node("ShaderNodeOutputMaterial", 300, 0, {"Volume": volume.outputs[0]})
    return material


if __name__ == "__main__":
    motes = build_motes_material()
    haze = build_haze_material()
    write(RESOURCE, (build_node_group(), motes, haze))
