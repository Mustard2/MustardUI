# Build dirt.blend: the Dirt node group, the Dirt Film shader group and the grains material
# Usage: Blender --background --factory-startup --python dirt_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "dirt.blend"
NODE_GROUP = "MustardUI Dirt"
FILM = "MustardUI Dirt Film"
MATERIAL = "MustardUI Dirt Grains"
# Heights of the Ground fade relative to the Control radius, clean above it at full Ground
GROUND = (0.1, -0.6)
# Spread of the creases and bulges measure in meters, and the most blur iterations for it
CAVITY_SIZE = 0.015
MAX_BLUR = 60
# Depth of the blurred positions per iteration and squared edge length, per mean curvature
BLUR_DEPTH = 0.55
# Mean curvature per meter of the creases fully dirty at full Cavities, of the bulges clean
CURVATURE = 40.0
# Grain shapes, the share of each grain sunk in the surface and its height relative to its width
SHAPES = 3
SINK = 0.35
FLAT = 0.6
# Dirt amount of the grains, covered at any Coverage
GRAIN_DIRT = 10.0
# Spread of the patch noise around its middle, and the half width of the edges in it
NOISE_SPREAD = 0.04
EDGE = 0.012
# Height of the patches relative to their width along the vertical of the rest pose, as
# splashed up and running down
STRETCH = 0.45
# Breakup of the patch edges by the grains, and the noise depth of the thick dirt under its edges
GRAININESS = 0.12
BODY = 0.06
# Reach of the thin dirt around the thick patches in the noise, and its share farther
THIN_REACH = 0.12
HAZE = 0.3
# Height in meters of the thick dirt at full Bump, of the step at its edges and of its lumps
CRUST = 0.002
LIP = 0.4
LUMPS = (150.0, 0.0015)
# Opacity of the thick dirt at its thin edges, and their width in the noise
EDGE_OPACITY = 0.8
EDGE_WIDTH = 0.02
# Height of the grains in the dirt in meters
GRAIN_HEIGHT = 0.00008
# Splatter drops: radius relative to their cells, the smallest relative to it, their crust, and
# their reach around the thick patches in the noise, fewer farther
SPLAT_RADIUS = 0.25
SPLAT_SMALLEST = 0.15
SPLAT_CRUST = 0.6
SPLAT_REACH = 0.1
SPLAT_FAR = 0.35
# Patches of color per meter, and the color spread of the grains
VARIATION = 9.0
SPECKLE = 0.8
# Half width of the cracks relative to their cells, scale and width of the finer ones, the
# surface showing through them and their shadow, and the plates curling up along them
CRACK_WIDTH = 0.05
FINE_CRACKS = (2.6, 0.5)
CRACK_SHOW = 0.35
CRACK_SHADOW = 0.8
CURL = 0.5
# Moisture under which the dirt cracks, fully dry at 0
DRY = 0.6
# Damp patches per meter, and the spread of the Moisture between them
DAMP = 15.0
DAMP_SPREAD = 1.5
# Darkening, roughness and coat of the dirt at full Moisture
WET_DARKEN = 0.6
WET_ROUGHNESS = 0.2
WET_COAT = 0.4
# Lightening and fading of the dried dirt
DRY_LIGHT = 0.6
DRY_FADE = 0.3


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Dirty the mesh inside the sphere of the Control, storing the dirtiness attribute read by "
        "the Dirt Film shader, with grains of dirt on it"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng, "Control", "NodeSocketObject", description="Empty whose sphere defines the dirty area"
    )
    add_input(
        ng,
        "Amount",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Amount of dirt, animate it to clean the mesh",
    )
    add_input(
        ng,
        "Falloff",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Width of the ragged border of the dirty area, relative to the Control radius",
    )
    add_input(
        ng,
        "Ground",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Dirt fading up the Z axis of the Control, as splashed from the ground, "
        "the bottom of its sphere the dirtiest",
    )
    add_input(
        ng,
        "Cavities",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Dirt gathered in the creases and hollows, rubbed off the bulges",
    )
    add_input(
        ng,
        "Patches",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Cleaner patches in the dirty area",
    )
    add_input(
        ng,
        "Patch Scale",
        "NodeSocketFloat",
        default_value=6.0,
        min_value=0.0,
        description="Number of patches per meter",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the dirty area",
    )
    add_input(
        ng,
        "Grains",
        "NodeSocketBool",
        default_value=True,
        description="Grains and crumbs of dirt stuck on the dirtiest parts",
    )
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        default_value=2000.0,
        min_value=0.0,
        max_value=100000.0,
        description="Grains per square meter where fully dirty",
    )
    add_input(
        ng,
        "Min Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0004,
        min_value=0.0,
        description="Width of the smallest grains",
    )
    add_input(
        ng,
        "Max Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.002,
        min_value=0.0,
        description="Width of the largest grains, fewer than the small ones",
    )
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the grains placement")
    add_input(ng, "Material", "NodeSocketMaterial", description="Material of the grains")
    add_input(
        ng,
        "Lasting",
        "NodeSocketBool",
        description="Keep the dirt where the Control sphere passed, as when walking through mud, "
        "simulated from the Start Frame",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    arrange_interface(
        ng,
        [
            (
                None,
                "Grains",
                False,
                "Grains",
                ["Density", "Min Size", "Max Size", "Seed", "Material"],
            ),
            (None, "Lasting", True, "Lasting", ["Start Frame"]),
        ],
    )

    t = Tree(ng, spacing=(200, 160))
    t.section("Dirt")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    position = t.node("GeometryNodeInputPosition", -2, -3).outputs[0]
    rest = t.node(
        "GeometryNodeInputNamedAttribute",
        -2,
        -4,
        {"Name": "rest_position"},
        data_type="FLOAT_VECTOR",
    ).outputs
    rest = t.node(
        "GeometryNodeSwitch",
        -1,
        -4,
        {"Switch": rest["Exists"], "False": position, "True": rest["Attribute"]},
        input_type="VECTOR",
    ).outputs[0]

    # Distance from the center of the Control, in its space, with a ragged border
    info = t.node(
        "GeometryNodeObjectInfo", -1, -2, {"Object": inputs["Control"]}, transform_space="RELATIVE"
    )
    invert = t.node("FunctionNodeInvertMatrix", 0, -2, {"Matrix": info.outputs["Transform"]})
    local = t.node(
        "FunctionNodeTransformPoint",
        1,
        -2,
        {"Vector": position, "Transform": invert.outputs["Matrix"]},
    ).outputs[0]
    edge_noise = t.node(
        "ShaderNodeTexNoise",
        1,
        -4,
        {"Vector": rest, "Scale": t.math("MULTIPLY", inputs["Patch Scale"], 4.0, x=0, y=-5)},
    ).outputs["Fac"]
    falloff = t.math("MAXIMUM", inputs["Falloff"], 0.001, x=2, y=-5)
    ragged = t.math("MULTIPLY", t.math("SUBTRACT", edge_noise, 0.5, x=2, y=-4), falloff, x=3, y=-4)
    distance = t.math("ADD", t.vmath("LENGTH", local, x=2, y=-2), ragged, x=3, y=-3)
    sphere = t.node(
        "ShaderNodeMapRange",
        4,
        -3,
        {
            "Value": distance,
            "From Min": 1.0,
            "From Max": t.math("SUBTRACT", 1.0, falloff, x=3, y=-5),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Dirtier down the Control, as splashed from the ground
    height = t.math(
        "ADD",
        t.node("ShaderNodeSeparateXYZ", 2, -6, {0: local}).outputs["Z"],
        ragged,
        x=3,
        y=-6,
    )
    ground = t.node(
        "ShaderNodeMapRange",
        4,
        -6,
        {"Value": height, "From Min": GROUND[0], "From Max": GROUND[1]},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    ground = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", ground, 1.0, x=5, y=-6), inputs["Ground"], 1.0, x=6, y=-6
    )
    # Cleaner patches
    patch_noise = t.node(
        "ShaderNodeTexNoise", 1, -8, {"Vector": rest, "Scale": inputs["Patch Scale"], "Detail": 3.0}
    ).outputs["Fac"]
    patch = t.node(
        "ShaderNodeMapRange",
        2,
        -8,
        {"Value": patch_noise, "From Min": 0.35, "From Max": 0.6},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    patch = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", patch, 1.0, x=3, y=-8), inputs["Patches"], 1.0, x=4, y=-8
    )
    live = t.math("MULTIPLY", t.math("MULTIPLY", sphere, ground, x=6, y=-4), patch, x=7, y=-4)

    t.section("Lasting", row=True)
    mesh = t.node("GeometryNodeSeparateComponents", 0, 2, {0: inputs["Geometry"]}).outputs
    components, mesh = mesh, mesh["Mesh"]
    kept = build_lasting(t, inputs, mesh, live)

    t.section("Cavities", row=True)
    # Curvature of the rest mesh, from the blurred positions sinking in the creases
    at_rest = t.node("GeometryNodeSetPosition", 0, 0, {"Geometry": mesh, "Position": rest})
    at_rest = at_rest.outputs[0]
    ends = t.node("GeometryNodeInputMeshEdgeVertices", 0, -2).outputs
    edge = t.node(
        "GeometryNodeAttributeStatistic",
        1,
        -2,
        {
            "Geometry": at_rest,
            "Attribute": t.vmath("DISTANCE", ends["Position 1"], ends["Position 2"], x=0.5, y=-3),
        },
        domain="EDGE",
    ).outputs["Mean"]
    spread = t.math("DIVIDE", CAVITY_SIZE, t.math("MAXIMUM", edge, 1e-6, x=1.5, y=-3), x=2, y=-3)
    rounds = t.math(
        "MINIMUM",
        t.math("CEIL", t.math("MULTIPLY", spread, spread, x=2.5, y=-3), x=3, y=-3),
        MAX_BLUR,
        x=3.5,
        y=-3,
    )
    point = t.node("GeometryNodeInputPosition", 2, -5).outputs[0]
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        3,
        -5,
        {"Value": point, "Iterations": rounds},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    depth = t.vmath(
        "DOT_PRODUCT",
        t.vmath("SUBTRACT", blurred, point, x=4, y=-5),
        t.node("GeometryNodeInputNormal", 3, -7).outputs[0],
        x=5,
        y=-5,
    )
    reach = t.math("MULTIPLY", t.math("MULTIPLY", edge, edge, x=4, y=-3), rounds, x=5, y=-3)
    curvature = t.math(
        "DIVIDE", depth, t.math("MULTIPLY", reach, BLUR_DEPTH, x=5.5, y=-3), x=6, y=-4
    )
    crease = t.node(
        "ShaderNodeMapRange",
        7,
        -4,
        {"Value": curvature, "From Min": -CURVATURE, "From Max": CURVATURE},
    ).outputs[0]
    captured = t.node("GeometryNodeCaptureAttribute", 8, 0, {"Geometry": at_rest})
    captured.capture_items.new("FLOAT", "Crease")
    t.connect(crease, captured.inputs["Crease"])
    crease = t.node(
        "GeometryNodeSampleIndex",
        9,
        0,
        {
            "Geometry": captured.outputs["Geometry"],
            "Value": captured.outputs["Crease"],
            "Index": t.node("GeometryNodeInputIndex", 8, -2).outputs[0],
        },
        data_type="FLOAT",
    ).outputs[0]
    # Up to twice as dirty in the creases, as dirty on the flat parts, clean on the bulges
    crease = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY_ADD", crease, 2.0, -1.0, x=10, y=-1),
        inputs["Cavities"],
        1.0,
        x=11,
        y=-1,
    )

    t.section("Attributes", row=True)
    total = t.math("MULTIPLY", kept, crease, x=0, y=-2)
    total = t.math("MULTIPLY", total, inputs["Amount"], x=1, y=-2)
    total = t.math("MULTIPLY", total, inputs["Mask"], x=2, y=-2, clamp=True)
    # The dirt of the previous Dirt modifiers kept
    previous = t.attribute("dirtiness", "FLOAT", 2, -4)
    total = t.math("MAXIMUM", total, previous, x=3, y=-3)
    mesh = t.store(mesh, "dirtiness", "FLOAT", total, 4, 0)
    # Rest position and cleanness in one attribute for EEVEE, clean without it in the shader
    xyz = t.node("ShaderNodeSeparateXYZ", 4, -2, {0: rest}).outputs
    packed = t.node(
        "FunctionNodeCombineColor",
        5,
        -2,
        {
            "Red": xyz["X"],
            "Green": xyz["Y"],
            "Blue": xyz["Z"],
            "Alpha": t.math("SUBTRACT", 1.0, total, x=4, y=-4),
        },
    ).outputs[0]
    mesh = t.store(mesh, "dirt", "FLOAT_COLOR", packed, 6, 0)

    t.section("Grains", row=True)
    grains = build_grains(t, inputs, components["Mesh"], position, rest, previous, total)

    # The mesh first, the grains as instances not to be subdivided by the next modifiers
    output = t.node("GeometryNodeJoinGeometry", 20, 2)
    for name in ("Instances", "Volume", "Point Cloud", "Grease Pencil", "Curve"):
        t.connect(components[name], output.inputs[0])
    t.connect(grains, output.inputs[0])
    t.connect(mesh, output.inputs[0])
    t.node("NodeGroupOutput", 21, 2, {0: output.outputs[0]})
    t.arrange()
    return ng


def build_lasting(t, inputs, mesh, live):
    """The live dirt of each point, or with Lasting the most it had since the Start Frame"""
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    count = t.node("GeometryNodeAttributeDomainSize", 1, 0, {0: mesh}).outputs["Point Count"]
    points = t.node("GeometryNodePoints", 2, 0, {"Count": count}).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 3, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 8, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(points, sim_in.inputs["Geometry"])
    # Started again when the mesh changes
    same = t.node(
        "FunctionNodeCompare",
        3,
        -2,
        {
            "A": t.node(
                "GeometryNodeAttributeDomainSize",
                2,
                -2,
                {0: sim_in.outputs["Geometry"]},
                component="POINTCLOUD",
            ).outputs["Point Count"],
            "B": count,
        },
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    state = t.node(
        "GeometryNodeSwitch",
        4,
        0,
        {
            "Switch": t.math("MULTIPLY", started, same, x=4, y=-2),
            "False": points,
            "True": sim_in.outputs["Geometry"],
        },
        input_type="GEOMETRY",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 4, -4).outputs[0]
    now = t.node(
        "GeometryNodeSampleIndex",
        5,
        -3,
        {"Geometry": mesh, "Value": live, "Index": index},
        data_type="FLOAT",
    ).outputs[0]
    most = t.math("MAXIMUM", t.attribute(".dirt_kept", "FLOAT", 5, -5), now, x=6, y=-4)
    state = t.store(state, ".dirt_kept", "FLOAT", most, 7, 0)
    t.connect(state, sim_out.inputs["Geometry"])
    kept = t.node(
        "GeometryNodeSampleIndex",
        9,
        -1,
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Value": t.attribute(".dirt_kept", "FLOAT", 8, -2),
            "Index": t.node("GeometryNodeInputIndex", 8, -3).outputs[0],
        },
        data_type="FLOAT",
    ).outputs[0]
    return t.node(
        "GeometryNodeSwitch",
        10,
        -1,
        {"Switch": inputs["Lasting"], "False": live, "True": kept},
        input_type="FLOAT",
    ).outputs[0]


def build_grains(t, inputs, mesh, position, rest, previous, total):
    """Grains placed on the rest mesh, more where dirtier, as instances on the deformed one"""
    captured = t.node("GeometryNodeCaptureAttribute", 0, -10, {"Geometry": mesh})
    normal = t.node("GeometryNodeInputNormal", -1, -12).outputs[0]
    for data_type, name, value in (
        ("VECTOR", "Posed", position),
        ("VECTOR", "Normal", normal),
        ("VECTOR", "Rest", rest),
        ("FLOAT", "Previous", previous),
        ("FLOAT", "Total", total),
    ):
        captured.capture_items.new(data_type, name)
        t.connect(value, captured.inputs[name])
    captured = captured.outputs
    at_rest = t.node(
        "GeometryNodeSetPosition",
        1,
        -10,
        {"Geometry": captured["Geometry"], "Position": captured["Rest"]},
    ).outputs[0]
    # Without the attributes of the mesh, not to interpolate them
    points = t.strip(at_rest, 2, -10)
    points = t.node(
        "GeometryNodeDistributePointsOnFaces",
        8,
        -10,
        {
            "Mesh": points,
            "Selection": t.math(
                "GREATER_THAN", captured["Total"], captured["Previous"], x=7, y=-12
            ),
            "Density": inputs["Density"],
            "Seed": inputs["Seed"],
        },
        distribute_method="RANDOM",
    ).outputs["Points"]

    # Randoms of the rest position, each Dirt keeping the grains between the previous dirt and own
    rest_point = t.node("GeometryNodeInputPosition", 8, -12).outputs[0]
    random = t.node(
        "ShaderNodeTexWhiteNoise", 9, -12, {"Vector": rest_point}, noise_dimensions="3D"
    ).outputs
    aspect = t.node(
        "ShaderNodeTexWhiteNoise", 9, -14, {"Vector": rest_point, "W": 1.0}, noise_dimensions="4D"
    ).outputs["Color"]
    # More where dirtier
    dirt = [
        t.math("MULTIPLY", captured[x], captured[x], x=9, y=-16 - i)
        for i, x in enumerate(("Previous", "Total"))
    ]
    clean = t.math(
        "MAXIMUM",
        t.math("LESS_THAN", random["Value"], dirt[0], x=10, y=-16),
        t.math("GREATER_THAN", random["Value"], dirt[1], x=10, y=-17),
        x=11,
        y=-16,
    )
    points = t.node(
        "GeometryNodeDeleteGeometry", 10, -10, {"Geometry": points, "Selection": clean}
    ).outputs[0]
    kept = t.node("GeometryNodeCaptureAttribute", 11, -10, {"Geometry": points})
    for data_type, name, value in (
        ("VECTOR", "Random", random["Color"]),
        ("VECTOR", "Aspect", aspect),
    ):
        kept.capture_items.new(data_type, name)
        t.connect(value, kept.inputs[name])
    kept = kept.outputs
    points = t.node(
        "GeometryNodeSetPosition",
        12,
        -10,
        {"Geometry": kept["Geometry"], "Position": captured["Posed"]},
    ).outputs[0]

    # Mostly small grains, of a random shape and turn, lying on the surface
    random = t.node("ShaderNodeSeparateXYZ", 12, -12, {0: kept["Random"]}).outputs
    size = t.node(
        "ShaderNodeMapRange",
        14,
        -12,
        {
            "Value": t.math("POWER", random["X"], 3.0, x=13, y=-12),
            "To Min": inputs["Min Size"],
            "To Max": inputs["Max Size"],
        },
    ).outputs[0]
    # Of the width, the instances a unit across
    size = t.math("MULTIPLY", size, 0.5, x=15, y=-12)
    aspect = t.vmath(
        "MULTIPLY_ADD", kept["Aspect"], (0.5, 0.5, 0.0), (0.75, 0.75, FLAT), x=13, y=-14
    )
    scale = t.vmath("SCALE", aspect, size, x=16, y=-13)
    shape = t.math("FLOOR", t.math("MULTIPLY", random["Y"], SHAPES, x=13, y=-15), x=14, y=-15)
    turn = t.node(
        "ShaderNodeCombineXYZ",
        14,
        -16,
        {"Z": t.math("MULTIPLY", random["Z"], 2.0 * math.pi, x=13, y=-16)},
    ).outputs[0]
    turn = t.node("FunctionNodeEulerToRotation", 15, -16, {0: turn}).outputs[0]
    rotation = t.node(
        "FunctionNodeAlignRotationToVector",
        16,
        -16,
        {"Rotation": turn, "Vector": t.vmath("NORMALIZE", captured["Normal"], x=15, y=-17)},
        axis="Z",
    ).outputs[0]

    # Lumpy grains, a bit sunk in the surface, fully dirty in the film
    shapes = t.node("GeometryNodeJoinGeometry", 18, -20)
    for i in range(SHAPES):
        ball = t.node(
            "GeometryNodeMeshIcoSphere", 12, -20 - 2 * i, {"Radius": 1.0, "Subdivisions": 2}
        ).outputs["Mesh"]
        lump = t.node(
            "ShaderNodeTexNoise",
            12,
            -21 - 2 * i,
            {
                "Vector": t.node("GeometryNodeInputPosition", 11, -21 - 2 * i).outputs[0],
                "W": float(i),
                "Scale": 1.2,
                "Detail": 2.0,
            },
            noise_dimensions="4D",
        ).outputs["Fac"]
        lump = t.vmath(
            "SCALE",
            t.node("GeometryNodeInputNormal", 12, -22 - 2 * i).outputs[0],
            t.math(
                "MULTIPLY",
                t.math("SUBTRACT", lump, 0.5, x=13, y=-21 - 2 * i),
                1.2,
                x=14,
                y=-21 - 2 * i,
            ),
            x=15,
            y=-21 - 2 * i,
        )
        ball = t.node(
            "GeometryNodeSetPosition", 14, -20 - 2 * i, {"Geometry": ball, "Offset": lump}
        ).outputs[0]
        ball = t.node(
            "GeometryNodeTransform",
            15,
            -20 - 2 * i,
            {"Geometry": ball, "Translation": (0.0, 0.0, -SINK)},
        ).outputs[0]
        # The film coordinates at the grain size, apart for each shape
        coordinates = t.vmath(
            "MULTIPLY_ADD",
            t.node("GeometryNodeInputPosition", 15, -21 - 2 * i).outputs[0],
            (0.001, 0.001, 0.001),
            (0.1 * i, 0.0, 0.0),
            x=16,
            y=-21 - 2 * i,
        )
        xyz = t.node("ShaderNodeSeparateXYZ", 16.5, -21 - 2 * i, {0: coordinates}).outputs
        packed = t.node(
            "FunctionNodeCombineColor",
            17,
            -21 - 2 * i,
            {"Red": xyz["X"], "Green": xyz["Y"], "Blue": xyz["Z"], "Alpha": 1.0 - GRAIN_DIRT},
        ).outputs[0]
        ball = t.store(ball, "dirt", "FLOAT_COLOR", packed, 17, -20 - 2 * i)
        ball = t.node(
            "GeometryNodeSetMaterial",
            17.3,
            -20 - 2 * i,
            {"Geometry": ball, "Material": inputs["Material"]},
        ).outputs[0]
        ball = t.node("GeometryNodeGeometryToInstance", 17.5, -20 - 2 * i, {0: ball}).outputs[0]
        t.connect(ball, shapes.inputs[0])
    grains = t.node(
        "GeometryNodeInstanceOnPoints",
        19,
        -10,
        {
            "Points": points,
            "Instance": shapes.outputs[0],
            "Pick Instance": True,
            "Instance Index": shape,
            "Rotation": rotation,
            "Scale": scale,
        },
    ).outputs[0]
    # Not evaluated at all without Grains
    return t.node(
        "GeometryNodeSwitch",
        20,
        -10,
        {"Switch": inputs["Grains"], "True": grains},
        input_type="GEOMETRY",
    ).outputs[0]


def build_film():
    """The shader under a layer of dirt, crusted, stained and splattered by the dirt attribute"""
    ng = bpy.data.node_groups.new(FILM, "ShaderNodeTree")
    add_input(ng, "Shader", "NodeSocketShader")
    add_input(
        ng,
        "Normal",
        "NodeSocketVector",
        hide_value=True,
        description="Normal of the surface under the dirt, from its normal map",
    )
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Strength of the whole dirt, fading it into the clean surface",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(0.11, 0.055, 0.025, 1.0),
        description="Color of the dirt, darker where wet and paler where dried",
    )
    add_input(
        ng,
        "Variation",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Lighter and darker patches and grains of dirt",
    )
    add_input(
        ng,
        "Roughness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.85,
        min_value=0.0,
        max_value=1.0,
        description="Roughness of the dry dirt",
    )
    add_input(
        ng,
        "Coverage",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        description="Share of the dirty surface under a thick layer of dirt, the rest stained",
    )
    add_input(
        ng,
        "Stain",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Opacity of the thin dirt staining the surface around the thick layer",
    )
    add_input(
        ng,
        "Patch Scale",
        "NodeSocketFloat",
        default_value=20.0,
        min_value=0.0,
        description="Number of patches of thick dirt per meter",
    )
    add_input(
        ng,
        "Moisture",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Wet dirt darker and glossy, cracking as it dries, animate it to dry the mud",
    )
    add_input(
        ng,
        "Cracks",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Cracks in the thick dirt, opening as it dries",
    )
    add_input(
        ng,
        "Crack Scale",
        "NodeSocketFloat",
        default_value=60.0,
        min_value=0.0,
        description="Number of plates between the cracks per meter",
    )
    add_input(
        ng,
        "Splatter",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Drops of dirt splattered around the thick layer",
    )
    add_input(
        ng,
        "Splatter Scale",
        "NodeSocketFloat",
        default_value=150.0,
        min_value=0.0,
        description="Number of splatter drops per meter, smaller when more",
    )
    add_input(
        ng,
        "Bump",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Relief of the thick dirt, its lumps and grains",
    )
    add_input(
        ng,
        "Grain Scale",
        "NodeSocketFloat",
        default_value=700.0,
        min_value=0.0,
        description="Number of grains of dirt per meter, breaking up its edges",
    )
    add_input(
        ng,
        "Simplify",
        "NodeSocketBool",
        default_value=False,
        description="Dirt without relief, faster in the viewport, to turn off for final renders",
    )
    add_output(ng, "Shader", "NodeSocketShader")

    t = Tree(ng, spacing=(200, 180))
    t.section("Coverage")
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    # Rest position and cleanness, stored by the Dirt modifier
    dirt = t.node(
        "ShaderNodeAttribute", 1, 2, attribute_type="GEOMETRY", attribute_name="dirt"
    ).outputs
    rest = dirt["Vector"]
    # Past 1 on the grains, covered at any Coverage
    raw = t.math("SUBTRACT", 1.0, dirt["Alpha"], x=2, y=2)
    amount = t.math("MINIMUM", raw, 1.0, x=3, y=2)
    # Thick patches where the noise is under the threshold, their edges broken up by the grains
    patches = t.node(
        "ShaderNodeTexNoise",
        1,
        0,
        {
            "Vector": t.vmath("MULTIPLY", rest, (1.0, 1.0, STRETCH), x=0.5, y=0),
            "Scale": inputs["Patch Scale"],
            "Detail": 6.0,
            "Roughness": 0.6,
            "Distortion": 0.25,
        },
    ).outputs["Fac"]
    grains = t.node(
        "ShaderNodeTexNoise",
        1,
        -2,
        {"Vector": rest, "Scale": inputs["Grain Scale"], "Detail": 2.0},
    ).outputs["Fac"]
    noise = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", grains, 0.5, x=2, y=-2),
        GRAININESS,
        patches,
        x=3,
        y=-1,
    )
    cover = t.math(
        "MULTIPLY",
        raw,
        t.math("MULTIPLY", inputs["Coverage"], 2.0, x=1, y=-4),
        x=2,
        y=-4,
        clamp=True,
    )
    # The noise quantile of the share, by the logit of the normal distribution
    share = t.node(
        "ShaderNodeClamp", 2.5, -4, {"Value": cover, "Min": 0.002, "Max": 0.998}
    ).outputs[0]
    threshold = t.math(
        "MULTIPLY_ADD",
        t.math(
            "LOGARITHM",
            t.math("DIVIDE", share, t.math("SUBTRACT", 1.0, share, x=2.5, y=-5), x=3, y=-5),
            math.e,
            x=3.5,
            y=-5,
        ),
        NOISE_SPREAD,
        0.5,
        x=4,
        y=-4,
    )
    below = t.math("SUBTRACT", threshold, noise, x=4, y=-2)
    thick = t.node(
        "ShaderNodeMapRange",
        5,
        -2,
        {"Value": below, "From Min": -EDGE, "From Max": EDGE},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Full coverage without the edges of the noise
    full = t.math("GREATER_THAN", cover, 0.999, x=5, y=-4)
    thick = t.math("MAXIMUM", thick, full, x=6, y=-3)
    body = t.math("MAXIMUM", t.math("DIVIDE", below, BODY, x=5, y=-1, clamp=True), full, x=6, y=-1)
    # Thinner dirt around the thick patches, powdery
    thin = t.node(
        "ShaderNodeMapRange",
        5,
        -6,
        {
            "Value": below,
            "From Min": -THIN_REACH,
            "From Max": 0.0,
            "To Min": HAZE,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    thin = t.math(
        "MULTIPLY",
        thin,
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", amount, 2.0, x=4, y=-8, clamp=True),
            inputs["Stain"],
            x=5,
            y=-8,
        ),
        x=6,
        y=-6,
    )
    thin = t.math("MULTIPLY", thin, t.math("MULTIPLY_ADD", grains, 1.0, 0.5, x=6, y=-7), x=7, y=-6)

    t.section("Splatter", row=True)
    # Lumpy drops in cells, mostly small, more of them where dirtier but not covered
    scale = t.math("MAXIMUM", inputs["Splatter Scale"], 0.001, x=0, y=-2)
    warp = t.node(
        "ShaderNodeTexNoise",
        1,
        -3,
        {"Vector": rest, "Scale": t.math("MULTIPLY", scale, 3.0, x=0.5, y=-3), "Detail": 2.0},
    ).outputs["Color"]
    warp = t.vmath(
        "MULTIPLY_ADD",
        t.vmath("SUBTRACT", warp, (0.5, 0.5, 0.5), x=1.5, y=-3),
        t.math("DIVIDE", 0.25, scale, x=1.5, y=-4),
        rest,
        x=2,
        y=-3,
    )
    cells = t.node("ShaderNodeTexVoronoi", 3, -2, {"Vector": warp, "Scale": scale}).outputs
    random = t.node("ShaderNodeSeparateColor", 3.5, -4, {0: cells["Color"]}).outputs
    radius = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", random["Red"], random["Red"], x=4, y=-4),
        SPLAT_RADIUS * (1.0 - SPLAT_SMALLEST),
        SPLAT_RADIUS * SPLAT_SMALLEST,
        x=4.5,
        y=-4,
    )
    spot = t.node(
        "ShaderNodeMapRange",
        5,
        -2,
        {
            "Value": t.math("DIVIDE", cells["Distance"], radius, x=4.5, y=-2),
            "From Min": 1.0,
            "From Max": 0.85,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    chance = t.node(
        "ShaderNodeMapRange",
        4,
        -6,
        {"Value": below, "From Min": -SPLAT_REACH, "From Max": 0.0, "To Min": SPLAT_FAR},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    chance = t.math(
        "MULTIPLY",
        chance,
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", amount, 3.0, x=3.5, y=-7, clamp=True),
            inputs["Splatter"],
            x=4,
            y=-7,
        ),
        x=5,
        y=-6,
    )
    chance = t.math("MULTIPLY", chance, t.math("SUBTRACT", 1.0, thick, x=5, y=-7), x=6, y=-6)
    spot = t.math(
        "MULTIPLY", spot, t.math("LESS_THAN", random["Green"], chance, x=6, y=-5), x=7, y=-3
    )
    plates = t.math("MULTIPLY", thick, body, x=7, y=-1)
    crust = t.math("MAXIMUM", plates, t.math("MULTIPLY", spot, SPLAT_CRUST, x=7, y=-2), x=8, y=-1)
    covered = t.math("MAXIMUM", thick, spot, x=8, y=-3)

    t.section("Cracks", row=True)
    # Damper and drier patches
    damp = t.node(
        "ShaderNodeTexNoise", -1, 0, {"Vector": rest, "Scale": DAMP, "Detail": 3.0}
    ).outputs["Fac"]
    moisture = t.math(
        "MULTIPLY",
        inputs["Moisture"],
        t.math("MULTIPLY_ADD", damp, 2.0 * DAMP_SPREAD, 1.0 - DAMP_SPREAD, x=0, y=0),
        x=0.5,
        y=0,
        clamp=True,
    )
    # Plates of dried dirt between cracks opening with the dryness, finer cracks between them
    dry = t.node(
        "ShaderNodeMapRange",
        0,
        -2,
        {"Value": moisture, "From Min": DRY, "From Max": 0.0},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    width = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", dry, inputs["Cracks"], x=1, y=-2),
        CRACK_WIDTH,
        x=2,
        y=-2,
    )
    crack_scale = t.math("MAXIMUM", inputs["Crack Scale"], 0.001, x=0, y=-4)
    bend = t.node(
        "ShaderNodeTexNoise",
        1,
        -4,
        {"Vector": rest, "Scale": t.math("MULTIPLY", crack_scale, 0.5, x=0.5, y=-5), "Detail": 3.0},
    ).outputs["Color"]
    bend = t.vmath(
        "MULTIPLY_ADD",
        t.vmath("SUBTRACT", bend, (0.5, 0.5, 0.5), x=1.5, y=-4),
        t.math("DIVIDE", 0.6, crack_scale, x=1.5, y=-5),
        rest,
        x=2,
        y=-4,
    )
    # Distance to the cracks relative to their half width
    lines = [
        t.math(
            "DIVIDE",
            t.node(
                "ShaderNodeTexVoronoi",
                3,
                -2 - 2 * i,
                {
                    "Vector": bend,
                    "Scale": t.math("MULTIPLY", crack_scale, times, x=2.5, y=-3 - 2 * i),
                },
                feature="DISTANCE_TO_EDGE",
            ).outputs["Distance"],
            t.math(
                "MAXIMUM", t.math("MULTIPLY", width, share, x=3, y=-7 - i), 1e-6, x=3.5, y=-7 - i
            ),
            x=3.5,
            y=-2 - 2 * i,
        )
        for i, (times, share) in enumerate(((1.0, 1.0), FINE_CRACKS))
    ]
    cracks = [
        t.node(
            "ShaderNodeMapRange",
            4,
            -2 - 2 * i,
            {"Value": x, "From Min": 1.0, "From Max": 0.4},
            interpolation_type="SMOOTHSTEP",
        ).outputs[0]
        for i, x in enumerate(lines)
    ]
    crack = t.math("MAXIMUM", *cracks, x=5, y=-3)
    # Plates curling up along the large cracks
    curl = t.node(
        "ShaderNodeMapRange",
        4,
        -8,
        {"Value": lines[0], "From Min": 4.0, "From Max": 1.0},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Only in the thick patches
    crack = t.math("MULTIPLY", crack, t.math("GREATER_THAN", plates, 0.15, x=5, y=-5), x=6, y=-3)
    # Thinner at the patch edges, the surface showing through the cracks of the dry dirt
    solid = t.math(
        "MULTIPLY_ADD",
        t.math(
            "MAXIMUM",
            t.math("DIVIDE", below, EDGE_WIDTH, x=4.5, y=-8, clamp=True),
            t.math("MAXIMUM", spot, full, x=4.5, y=-9),
            x=5,
            y=-7,
        ),
        1.0 - EDGE_OPACITY,
        EDGE_OPACITY,
        x=6,
        y=-7,
    )
    opacity = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", covered, solid, x=6.5, y=-6),
        t.math(
            "MULTIPLY_ADD",
            t.math("MULTIPLY", crack, dry, x=6, y=-5),
            -CRACK_SHOW,
            1.0,
            x=6.5,
            y=-4,
        ),
        x=7,
        y=-3,
    )
    opacity = t.math("MAXIMUM", opacity, thin, x=8, y=-3)
    opacity = t.math("MULTIPLY", opacity, inputs["Strength"], x=9, y=-3)

    t.section("Relief", row=True)
    # In meters: a crust with a step at its edges, lumps, grains, cracks and curling plates
    lumps = t.node(
        "ShaderNodeTexNoise",
        1,
        -2,
        {
            "Vector": t.vmath("MULTIPLY", rest, (1.0, 1.0, STRETCH), x=0.5, y=-2),
            "Scale": LUMPS[0],
            "Detail": 5.0,
            "Roughness": 0.6,
        },
    ).outputs["Fac"]
    height = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY_ADD", crust, 1.0 - LIP, t.math("MULTIPLY", covered, LIP, x=1, y=0), x=2, y=0
        ),
        CRUST,
        x=3,
        y=0,
    )
    height = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", lumps, crust, x=2, y=-2),
        LUMPS[1],
        height,
        x=4,
        y=0,
    )
    height = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", grains, opacity, x=3, y=-4),
        GRAIN_HEIGHT,
        height,
        x=5,
        y=0,
    )
    curl = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", curl, crust, x=4, y=-6),
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", dry, inputs["Cracks"], x=4, y=-7),
            CURL * CRUST,
            x=5,
            y=-7,
        ),
        x=5,
        y=-6,
    )
    height = t.math("ADD", height, curl, x=6, y=0)
    height = t.math(
        "MULTIPLY",
        height,
        t.math("MULTIPLY_ADD", crack, -1.0, 1.0, x=6, y=-2),
        x=7,
        y=0,
    )
    height = t.math("MULTIPLY", height, inputs["Bump"], x=8, y=0)
    # Simplified with a constant Mix, which shaders compile without the relief at all
    height = t.node(
        "ShaderNodeMix", 9, 0, {"Factor": inputs["Simplify"], "A": height, "B": 0.0}
    ).outputs[0]
    # The normal of the surface for the thin dirt, or of the mesh without one
    surface = inputs["Normal"]
    linked = t.math("GREATER_THAN", t.vmath("LENGTH", surface, x=7, y=-3), 0.5, x=8, y=-3)
    geometry = t.node("ShaderNodeNewGeometry", 7, -5).outputs["Normal"]
    surface = t.node(
        "ShaderNodeMix",
        9,
        -3,
        {"Factor": linked, "A": geometry, "B": surface},
        data_type="VECTOR",
    ).outputs[1]
    surface = t.node(
        "ShaderNodeMix",
        10,
        -3,
        {
            "Factor": t.math(
                "MINIMUM", t.math("MULTIPLY", covered, 2.0, x=9, y=-5), 1.0, x=9.5, y=-5
            ),
            "A": surface,
            "B": geometry,
        },
        data_type="VECTOR",
    ).outputs[1]
    # The height in meters, not scaled down by the default Distance
    normal = t.node(
        "ShaderNodeBump", 11, 0, {"Distance": 1.0, "Height": height, "Normal": surface}
    ).outputs[0]

    t.section("Shading", row=True)
    # Lighter and darker patches, and grains of other colors
    variation = t.node(
        "ShaderNodeTexNoise",
        1,
        0,
        {"Vector": rest, "Scale": VARIATION, "Detail": 6.0, "Roughness": 0.65},
    ).outputs["Color"]
    variation = t.node("ShaderNodeSeparateXYZ", 2, 0, {0: variation}).outputs
    speckles = t.node(
        "ShaderNodeTexWhiteNoise",
        1,
        -3,
        {"Vector": t.vmath("SCALE", rest, inputs["Grain Scale"], x=0, y=-3)},
        noise_dimensions="3D",
    ).outputs["Value"]
    spread = [
        t.math(
            "MULTIPLY",
            t.math("SUBTRACT", value, 0.5, x=3, y=-i),
            t.math("MULTIPLY", inputs["Variation"], weight, x=3, y=-0.5 - i),
            x=4,
            y=-i,
        )
        for i, (value, weight) in enumerate(
            (
                (variation["X"], 0.1),
                (variation["Y"], 1.0),
                (variation["Z"], 3.0),
                (speckles, SPECKLE),
            )
        )
    ]
    color = t.node(
        "ShaderNodeHueSaturation",
        6,
        0,
        {
            "Hue": t.math("ADD", spread[0], 0.5, x=5, y=0),
            "Saturation": t.math(
                "ADD",
                spread[1],
                t.math("MULTIPLY_ADD", dry, -DRY_FADE, 1.0, x=4.5, y=-1.5),
                x=5,
                y=-1,
            ),
            "Value": t.math(
                "ADD",
                t.math("ADD", spread[2], spread[3], x=5, y=-2),
                t.math("MULTIPLY_ADD", dry, DRY_LIGHT, 1.0, x=4.5, y=-2.5),
                x=5.5,
                y=-2,
            ),
            "Color": inputs["Color"],
        },
    ).outputs[0]
    # Darker and glossier where wet, the thick dirt holding more water, deep in the cracks
    wet = t.math(
        "MULTIPLY",
        moisture,
        t.math("MULTIPLY_ADD", crust, 0.5, 0.5, x=6, y=-4),
        x=7,
        y=-4,
    )
    color = t.node(
        "ShaderNodeMix",
        8,
        0,
        {
            "Factor": t.math("MULTIPLY", wet, WET_DARKEN, x=7.5, y=-3),
            "A": color,
            "B": (0.0, 0.0, 0.0, 1.0),
        },
        data_type="RGBA",
    ).outputs[2]
    color = t.node(
        "ShaderNodeMix",
        8.5,
        0,
        {
            "Factor": t.math("MULTIPLY", crack, CRACK_SHADOW, x=8, y=-1),
            "A": color,
            "B": (0.0, 0.0, 0.0, 1.0),
        },
        data_type="RGBA",
    ).outputs[2]
    roughness = t.node(
        "ShaderNodeMix", 8, -5, {"Factor": wet, "A": inputs["Roughness"], "B": WET_ROUGHNESS}
    ).outputs[0]
    dirt_bsdf = t.node(
        "ShaderNodeBsdfPrincipled",
        10,
        0,
        {
            "Base Color": color,
            "Roughness": roughness,
            "Specular IOR Level": 0.25,
            "Normal": normal,
            "Coat Weight": t.math("MULTIPLY", wet, WET_COAT, x=9, y=-6),
            "Coat Roughness": t.math("MULTIPLY_ADD", wet, -0.3, 0.35, x=9, y=-7),
            "Coat IOR": 1.33,
            "Coat Normal": normal,
        },
    ).outputs[0]
    shader = t.node(
        "ShaderNodeMixShader", 11, 0, {0: opacity, 1: inputs["Shader"], 2: dirt_bsdf}
    ).outputs[0]
    t.node("NodeGroupOutput", 12, 0, {"Shader": shader})
    t.arrange()
    return ng


def build_material():
    """Grains under the dirt of the film, wrapped around it by the operator"""
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree)
    bsdf = t.node(
        "ShaderNodeBsdfPrincipled",
        0,
        0,
        {"Base Color": (0.08, 0.06, 0.04, 1.0), "Roughness": 0.9},
    ).outputs[0]
    t.node("ShaderNodeOutputMaterial", 1, 0, {"Surface": bsdf})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_film(), build_material()), fake_user=True)
