# Build aura.blend: the Aura node group, its glow shader node group and sparks material
# Usage: Blender --background --factory-startup --python aura_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, socket, write

RESOURCE = "aura.blend"
NODE_GROUP = "MustardUI Aura"
GLOW = "MustardUI Aura Glow"
SPARKS = "MustardUI Aura Sparks"
COLOR = (1.0, 0.12, 0.35, 1.0)
# Size of the shimmer patches, in m, and how fast they flow, per second
SHIMMER_SIZE = 0.15
SHIMMER_RATE = 0.6
# Sideways speed of the sparks, relative to their rise, and their fade in, of their life
SPREAD = 0.35
FADE_IN = 0.15
# Most sparks thrown in a frame, not to run out of memory on a large mesh, and the share of the
# sparks thrown off the Hot Spots without Body Glow
MAX_SPAWN = 5000
OFF_SPARKS = 0.2


def build_inputs(ng):
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Control",
        "NodeSocketObject",
        description="Empty at the feet of the model, its Glow property driving the glow",
    )
    add_input(
        ng,
        "Glow",
        "NodeSocketFloat",
        default_value=0.0,
        min_value=0.0,
        description="How much the mesh glows, driven by the Glow of the Control",
    )
    add_input(
        ng,
        "Shimmer",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Glow flowing over the surface in brighter and darker patches",
    )
    add_input(
        ng,
        "Hot Spots",
        "NodeSocketCollection",
        description="Empties glowing on the meshes inside their spheres and throwing more sparks, "
        "e.g. on the hands and feet. Without them, the meshes glow evenly",
    )
    add_input(
        ng,
        "Softness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Width of the fade of the glow across the border of the Hot Spots, of their "
        "radius",
    )
    add_input(
        ng,
        "Hot Spot Glow",
        "NodeSocketFloat",
        default_value=3.0,
        min_value=0.0,
        description="Outline glow and sparks of the Hot Spots, times the Glow",
    )
    add_input(
        ng,
        "Body Glow",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Outline glow outside the Hot Spots, times the Glow, 0 for the Hot Spots only",
    )
    add_input(ng, "Sparks", "NodeSocketBool", default_value=True)
    add_input(
        ng,
        "Amount",
        "NodeSocketFloat",
        default_value=80.0,
        min_value=0.0,
        description="Sparks thrown per square meter per second at full glow",
    )
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.004,
        min_value=0.0,
        description="Thickness of the spark streaks, in average, scaled with the model",
    )
    add_input(
        ng,
        "Length",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.05,
        min_value=0.0,
        description="Length of the spark streaks along their flight, scaled with the model",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        default_value=2.0,
        min_value=0.01,
        description="Seconds the sparks fly for",
    )
    add_input(
        ng,
        "Rise Speed",
        "NodeSocketFloat",
        default_value=0.3,
        description="Speed of the sparks up the Control, in m/s, scaled with the model",
    )
    add_input(ng, "Color", "NodeSocketColor", default_value=(1.0, 0.3, 0.55, 1.0))
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        default_value=30.0,
        min_value=0.0,
        description="Emission strength of the sparks",
    )
    add_input(ng, "Seed", "NodeSocketInt")
    add_input(
        ng, "Sparks Material", "NodeSocketMaterial", description="Material of the sparks"
    ).default_value = bpy.data.materials.get(SPARKS)
    add_output(ng, "Geometry", "NodeSocketGeometry")
    arrange_interface(
        ng,
        (
            (
                None,
                "Glow",
                False,
                None,
                ("Shimmer", "Hot Spots", "Softness", "Hot Spot Glow", "Body Glow"),
            ),
            (
                None,
                "Sparks",
                False,
                "Sparks",
                ("Amount", "Size", "Length", "Lifetime", "Rise Speed", "Color", "Strength", "Seed"),
            ),
            (None, "Materials", True, None, ("Sparks Material",)),
        ),
    )


def random(t, low, high, index, seed, x, y, data_type="FLOAT"):
    node = t.node(
        "FunctionNodeRandomValue",
        x,
        y,
        {"Min": low, "Max": high, "ID": index, "Seed": seed},
        data_type=data_type,
    )
    return socket(node.outputs, "Value")


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = "Glow and rising sparks, driven by the Glow of the Control"
    build_inputs(ng)
    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -10, 0).outputs

    t.section("Model: meters of the model per unit, at the scale of its Control", row=True)
    info = t.node(
        "GeometryNodeObjectInfo", 0, 0, {"Object": inputs["Control"]}, transform_space="RELATIVE"
    )
    scale = t.node("ShaderNodeSeparateXYZ", 1, 0, {0: info.outputs["Scale"]}).outputs["X"]
    meters = t.math("DIVIDE", 1.0, t.math("ABSOLUTE", scale, x=2, y=0), x=3, y=0)
    time = t.node("GeometryNodeInputSceneTime", 0, -4).outputs["Seconds"]
    rest = t.node(
        "GeometryNodeInputNamedAttribute",
        0,
        -6,
        {"Name": "rest_position"},
        data_type="FLOAT_VECTOR",
    )
    rest = t.node(
        "GeometryNodeSwitch",
        1,
        -6,
        {
            "Switch": rest.outputs["Exists"],
            "False": t.node("GeometryNodeInputPosition", 0, -7).outputs[0],
            "True": socket(rest.outputs, "Attribute"),
        },
        input_type="VECTOR",
    ).outputs[0]
    t.section("Hot Spots: in the spheres of the Empties, fading out across their border")
    spots = t.node(
        "GeometryNodeCollectionInfo",
        0,
        0,
        {"Collection": inputs["Hot Spots"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    centers = t.node(
        "GeometryNodeInstancesToPoints",
        1,
        0,
        {
            "Instances": spots,
            "Radius": t.vmath(
                "DOT_PRODUCT",
                t.node("GeometryNodeInputInstanceScale", 0, -2).outputs[0],
                (1 / 3, 1 / 3, 1 / 3),
                x=1,
                y=-2,
            ),
        },
    ).outputs[0]
    nearest = t.node("GeometryNodeSampleNearest", 2, -2, {"Geometry": centers}, domain="POINT")

    def nearest_value(value, data_type, y):
        return t.node(
            "GeometryNodeSampleIndex",
            3,
            y,
            {"Geometry": centers, "Value": value, "Index": nearest.outputs[0]},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]

    distance = t.math(
        "DIVIDE",
        t.vmath(
            "DISTANCE",
            t.node("GeometryNodeInputPosition", 3, -6).outputs[0],
            nearest_value(
                t.node("GeometryNodeInputPosition", 2, -4).outputs[0], "FLOAT_VECTOR", -4
            ),
            x=4,
            y=-4,
        ),
        nearest_value(t.node("GeometryNodeInputRadius", 2, -5).outputs[0], "FLOAT", -5),
        x=5,
        y=-4,
    )
    hot = t.node(
        "ShaderNodeMapRange",
        6,
        -4,
        {
            "Value": distance,
            "From Min": t.math("MULTIPLY_ADD", inputs["Softness"], 0.5, 1.0, x=5, y=-7),
            "From Max": t.math("MULTIPLY_ADD", inputs["Softness"], -0.5, 0.999, x=5, y=-8),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs["Result"]
    hot = t.node(
        "GeometryNodeSwitch",
        7,
        -4,
        {
            "Switch": t.math(
                "GREATER_THAN",
                t.node(
                    "GeometryNodeAttributeDomainSize",
                    6,
                    -6,
                    {"Geometry": spots},
                    component="INSTANCES",
                ).outputs["Instance Count"],
                0.0,
                x=7,
                y=-6,
            ),
            "True": hot,
        },
        input_type="FLOAT",
    ).outputs[0]

    # Outline glow from the Body Glow to the Hot Spot Glow
    outline = t.node(
        "ShaderNodeMix",
        1,
        -9,
        {"Factor": hot, "A": inputs["Body Glow"], "B": inputs["Hot Spot Glow"]},
    ).outputs[0]

    t.section("Glow: shimmering patches on the rest mesh, brighter on the Hot Spots")
    noise = t.node(
        "ShaderNodeTexNoise",
        10,
        -1,
        {
            "Vector": t.vmath("SCALE", rest, meters, x=9, y=-1),
            "W": t.math(
                "MULTIPLY_ADD",
                time,
                SHIMMER_RATE,
                t.math("MULTIPLY", inputs["Seed"], 7.31, x=8, y=-3),
                x=9,
                y=-3,
            ),
            "Scale": 1 / SHIMMER_SIZE,
            "Detail": 2.0,
        },
        noise_dimensions="4D",
    ).outputs["Factor"]
    # 0 to 2 times the Glow, 1 in average
    shimmer = t.node(
        "ShaderNodeMapRange",
        11,
        -1,
        {"Value": noise, "From Min": 0.3, "From Max": 0.7, "To Min": 0.0, "To Max": 2.0},
    ).outputs["Result"]
    shimmer = t.node(
        "ShaderNodeMix", 12, -1, {"Factor": inputs["Shimmer"], "A": 1.0, "B": shimmer}
    ).outputs[0]
    glow = t.math("MULTIPLY", shimmer, inputs["Glow"], x=13, y=-1)
    # The outline glow, and the Hot Spots blazing all over
    glow = t.node(
        "ShaderNodeCombineXYZ",
        14,
        -1,
        {
            "X": t.math("MULTIPLY", glow, outline, x=14, y=-2),
            "Y": t.math("MULTIPLY", glow, hot, x=14, y=-3),
        },
    ).outputs[0]
    glowing = t.math("GREATER_THAN", inputs["Glow"], 0.0, x=13, y=-3)
    stored = t.store(inputs["Geometry"], "aura_glow", "FLOAT_VECTOR", glow, 15, 0)
    geometry = t.node(
        "GeometryNodeSwitch",
        16,
        0,
        {"Switch": glowing, "False": inputs["Geometry"], "True": stored},
        input_type="GEOMETRY",
    ).outputs[0]

    t.section("World: the sparks fly in world space, sized by the Control", row=True)
    world = t.node(
        "GeometryNodeObjectInfo",
        0,
        0,
        {"Object": t.node("GeometryNodeSelfObject", -1, 0).outputs[0]},
        transform_space="ORIGINAL",
    ).outputs
    inverse = t.node("FunctionNodeInvertMatrix", 1, 0, {"Matrix": world["Transform"]}).outputs[0]
    unit = t.math(
        "ABSOLUTE",
        t.node("ShaderNodeSeparateXYZ", 1, -1, {0: world["Scale"]}).outputs["X"],
        x=2,
        y=-1,
    )
    # World meters per meter of the model, scaled with the Control
    scaled = t.math("DIVIDE", unit, meters, x=3, y=-1)
    control = t.node(
        "GeometryNodeObjectInfo", 0, -3, {"Object": inputs["Control"]}, transform_space="ORIGINAL"
    ).outputs
    up = t.node(
        "FunctionNodeTransformDirection",
        1,
        -3,
        {"Direction": (0.0, 0.0, 1.0), "Transform": control["Transform"]},
    ).outputs[0]
    up = t.vmath("NORMALIZE", up, x=2, y=-3)
    sim_in = t.node("GeometryNodeSimulationInput", 0, -6)
    sim_out = t.node("GeometryNodeSimulationOutput", 30, -6)
    sim_in.pair_with_output(sim_out)
    dt = sim_in.outputs["Delta Time"]
    frame = t.node("GeometryNodeInputSceneTime", 0, -8).outputs["Frame"]

    t.section("Spawn: sparks on the rest mesh by the Glow each frame, fewer off the Hot Spots")
    captured = t.node("GeometryNodeCaptureAttribute", 0, 0, {"Geometry": inputs["Geometry"]})
    for name, value in (
        ("Posed", t.node("GeometryNodeInputPosition", -1, -1).outputs[0]),
        ("Normal", t.node("GeometryNodeInputNormal", -1, -2).outputs[0]),
    ):
        captured.capture_items.new("VECTOR", name)
        t.connect(value, captured.inputs[name])
    # Hot on the posed mesh, the sparks distributed on the rest one
    captured.capture_items.new("FLOAT", "Hot")
    t.connect(hot, captured.inputs["Hot"])
    at_rest = t.node(
        "GeometryNodeSetPosition",
        1,
        0,
        {"Geometry": captured.outputs["Geometry"], "Position": rest},
    ).outputs[0]
    area = t.node(
        "GeometryNodeAttributeStatistic",
        2,
        -2,
        {
            "Geometry": at_rest,
            "Attribute": t.node("GeometryNodeInputMeshFaceArea", 1, -3).outputs[0],
        },
        domain="FACE",
    ).outputs["Sum"]
    # Sparks of this frame, per unit of the rest mesh
    density = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            inputs["Amount"],
            t.math("MULTIPLY", inputs["Glow"], dt, x=1, y=-5),
            x=2,
            y=-4,
        ),
        t.math("MULTIPLY", meters, meters, x=2, y=-5),
        x=3,
        y=-4,
    )
    density = t.math("MINIMUM", density, t.math("DIVIDE", MAX_SPAWN, area, x=3, y=-2), x=4, y=-4)
    # Off the Hot Spots by the Body Glow, at least OFF_SPARKS
    off = t.math("MULTIPLY_ADD", inputs["Body Glow"], 1.0 - OFF_SPARKS, OFF_SPARKS, x=3, y=-7)
    weight = t.node(
        "ShaderNodeMix",
        4,
        -7,
        {"Factor": captured.outputs["Hot"], "A": off, "B": inputs["Hot Spot Glow"]},
    ).outputs[0]
    seed = t.math("MULTIPLY_ADD", inputs["Seed"], 7919.0, frame, x=4, y=-9)
    spawned = t.node(
        "GeometryNodeDistributePointsOnFaces",
        5,
        0,
        {
            "Mesh": at_rest,
            "Density": t.math("MULTIPLY", density, weight, x=5, y=-4),
            "Seed": seed,
        },
        distribute_method="RANDOM",
    ).outputs["Points"]
    index = t.node("GeometryNodeInputIndex", 6, -2).outputs[0]
    offset = t.math("DIVIDE", inputs["Size"], meters, x=6, y=-4)
    start = t.node(
        "FunctionNodeTransformPoint",
        8,
        -3,
        {
            "Vector": t.vmath(
                "ADD",
                captured.outputs["Posed"],
                t.vmath("SCALE", captured.outputs["Normal"], offset, x=7, y=-4),
                x=7,
                y=-3,
            ),
            "Transform": world["Transform"],
        },
    ).outputs[0]
    rise = t.vmath(
        "SCALE",
        up,
        t.math(
            "MULTIPLY",
            inputs["Rise Speed"],
            random(t, 0.6, 1.4, index, t.math("ADD", seed, 1, x=6, y=-6), 7, -6),
            x=8,
            y=-6,
        ),
        x=9,
        y=-6,
    )
    spread = t.vmath(
        "SCALE",
        random(
            t,
            (-1, -1, -1),
            (1, 1, 1),
            index,
            t.math("ADD", seed, 2, x=6, y=-8),
            7,
            -8,
            "FLOAT_VECTOR",
        ),
        t.math("MULTIPLY", inputs["Rise Speed"], SPREAD, x=7, y=-9),
        x=8,
        y=-8,
    )
    velocity = t.vmath("SCALE", t.vmath("ADD", rise, spread, x=9, y=-7), scaled, x=10, y=-7)
    size = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Size"], 0.5, x=7, y=-11),
        t.math(
            "MULTIPLY",
            random(t, 0.5, 1.5, index, t.math("ADD", seed, 3, x=6, y=-12), 7, -12),
            scaled,
            x=8,
            y=-12,
        ),
        x=9,
        y=-11,
    )
    life = t.math(
        "MULTIPLY",
        inputs["Lifetime"],
        random(t, 0.7, 1.3, index, t.math("ADD", seed, 4, x=6, y=-14), 7, -14),
        x=8,
        y=-14,
    )
    # New points, without the mesh attributes
    thrown = t.node("GeometryNodeCaptureAttribute", 11, 0, {"Geometry": spawned})
    for data_type, name, value in (
        ("VECTOR", "Start", start),
        ("VECTOR", "Velocity", velocity),
        ("FLOAT", "Size", size),
        ("FLOAT", "Life", life),
    ):
        thrown.capture_items.new(data_type, name)
        t.connect(value, thrown.inputs[name])
    new = t.node(
        "GeometryNodeAttributeDomainSize",
        12,
        -1,
        {"Geometry": thrown.outputs["Geometry"]},
        component="POINTCLOUD",
    ).outputs["Point Count"]
    new_index = t.node("GeometryNodeInputIndex", 12, -3).outputs[0]

    def taken(name, data_type, y):
        return t.node(
            "GeometryNodeSampleIndex",
            13,
            y,
            {
                "Geometry": thrown.outputs["Geometry"],
                "Value": thrown.outputs[name],
                "Index": new_index,
            },
            data_type=data_type,
            domain="POINT",
        ).outputs[0]

    points = t.node(
        "GeometryNodePoints", 14, 0, {"Count": new, "Position": taken("Start", "FLOAT_VECTOR", -2)}
    ).outputs[0]
    for x, (name, attribute, data_type) in enumerate(
        (
            ("Velocity", ".aura_velocity", "FLOAT_VECTOR"),
            ("Size", ".aura_size", "FLOAT"),
            ("Life", ".aura_life", "FLOAT"),
        )
    ):
        sampled_type = "FLOAT_VECTOR" if data_type == "FLOAT_VECTOR" else "FLOAT"
        points = t.store(
            points, attribute, data_type, taken(name, sampled_type, -4 - 2 * x), 15 + x, 0
        )
    spawning = t.node(
        "FunctionNodeBooleanMath", 17, -2, {0: inputs["Sparks"], 1: glowing}, operation="AND"
    ).outputs[0]
    points = t.node(
        "GeometryNodeSwitch", 18, 0, {"Switch": spawning, "True": points}, input_type="GEOMETRY"
    ).outputs[0]

    t.section("Flight: the sparks fly on, also after the Glow, until their life ends")
    state = sim_in.outputs["Geometry"]
    flown = t.node(
        "GeometryNodeSetPosition",
        1,
        0,
        {
            "Geometry": state,
            "Offset": t.vmath(
                "SCALE", t.attribute(".aura_velocity", "FLOAT_VECTOR", 0, -2), dt, x=1, y=-2
            ),
        },
    ).outputs[0]
    age = t.math("ADD", t.attribute(".aura_age", "FLOAT", 1, -4), dt, x=2, y=-4)
    flown = t.store(flown, ".aura_age", "FLOAT", age, 3, 0)
    flown = t.node(
        "GeometryNodeDeleteGeometry",
        4,
        0,
        {
            "Geometry": flown,
            "Selection": t.math(
                "GREATER_THAN",
                t.attribute(".aura_age", "FLOAT", 3, -3),
                t.attribute(".aura_life", "FLOAT", 3, -4),
                x=4,
                y=-3,
            ),
        },
        domain="POINT",
    ).outputs[0]
    flying = t.node("GeometryNodeJoinGeometry", 5, 0)
    for value in (points, flown):
        t.connect(value, flying.inputs[0])
    t.connect(flying.outputs[0], sim_out.inputs["Geometry"])
    state = sim_out.outputs["Geometry"]

    t.section(
        "Output: the sparks as streaks, a head and a tail, back in the object space", row=True
    )
    count = t.node(
        "GeometryNodeAttributeDomainSize", 0, -1, {"Geometry": state}, component="POINTCLOUD"
    ).outputs["Point Count"]
    point = t.node("GeometryNodeInputIndex", 0, -3).outputs[0]
    spark = t.math("FLOOR", t.math("DIVIDE", point, 2.0, x=1, y=-3), x=2, y=-3)
    tail = t.math("FLOORED_MODULO", point, 2.0, x=2, y=-4)

    def sampled(value, data_type, y):
        return t.node(
            "GeometryNodeSampleIndex",
            3,
            y,
            {"Geometry": state, "Value": value, "Index": spark},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]

    age = t.math(
        "DIVIDE",
        sampled(t.attribute(".aura_age", "FLOAT", 2, -10), "FLOAT", -10),
        sampled(t.attribute(".aura_life", "FLOAT", 2, -11), "FLOAT", -11),
        x=4,
        y=-10,
    )
    fade_in = t.node(
        "ShaderNodeMapRange",
        5,
        -11,
        {"Value": age, "From Max": FADE_IN},
        interpolation_type="SMOOTHSTEP",
    ).outputs["Result"]
    fade = t.math("MULTIPLY", fade_in, t.math("SUBTRACT", 1.0, age, x=5, y=-12), x=6, y=-11)
    # The tail behind the head along the flight, thinner and dark
    direction = t.vmath(
        "NORMALIZE",
        sampled(t.attribute(".aura_velocity", "FLOAT_VECTOR", 2, -8), "FLOAT_VECTOR", -8),
        x=4,
        y=-8,
    )
    behind = t.math(
        "MULTIPLY",
        tail,
        t.math("MULTIPLY", inputs["Length"], scaled, x=3, y=-13),
        x=4,
        y=-13,
    )
    position = t.vmath(
        "SUBTRACT",
        sampled(t.node("GeometryNodeInputPosition", 2, -2).outputs[0], "FLOAT_VECTOR", -2),
        t.vmath("SCALE", direction, behind, x=5, y=-8),
        x=6,
        y=-2,
    )
    position = t.node(
        "FunctionNodeTransformPoint", 7, -2, {"Vector": position, "Transform": inverse}
    ).outputs[0]
    radius = t.math(
        "DIVIDE",
        t.math(
            "MULTIPLY",
            sampled(t.attribute(".aura_size", "FLOAT", 2, -6), "FLOAT", -6),
            t.math(
                "MULTIPLY",
                t.math("SQRT", fade, x=7, y=-11),
                t.math("MULTIPLY_ADD", tail, -0.7, 1.0, x=4, y=-5),
                x=8,
                y=-11,
            ),
            x=8,
            y=-6,
        ),
        unit,
        x=9,
        y=-6,
    )
    streaks = t.node(
        "GeometryNodePoints",
        10,
        0,
        {
            "Count": t.math("MULTIPLY", count, 2.0, x=1, y=-1),
            "Position": position,
            "Radius": radius,
        },
    ).outputs[0]
    light = t.vmath(
        "SCALE",
        inputs["Color"],
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", fade, inputs["Strength"], x=7, y=-13),
            t.math("SUBTRACT", 1.0, tail, x=7, y=-14),
            x=8,
            y=-13,
        ),
        x=9,
        y=-13,
    )
    streaks = t.store(streaks, "aura_spark", "FLOAT_VECTOR", light, 11, 0)
    curves = t.node(
        "GeometryNodePointsToCurves",
        12,
        0,
        {"Points": streaks, "Curve Group ID": spark, "Weight": tail},
    ).outputs[0]
    # Thin tubes, curves of a mesh object not being rendered, as an instance past the Subdivision
    tubes = t.node(
        "GeometryNodeCurveToMesh",
        13,
        0,
        {
            "Curve": curves,
            "Profile Curve": t.node(
                "GeometryNodeCurvePrimitiveCircle", 12, -2, {"Resolution": 4}
            ).outputs[0],
            "Scale": t.node("GeometryNodeInputRadius", 12, -3).outputs[0],
        },
    ).outputs[0]
    tubes = t.node("GeometryNodeSetShadeSmooth", 14, 0, {"Mesh": tubes}).outputs[0]
    tubes = t.node(
        "GeometryNodeSetMaterial", 15, 0, {"Geometry": tubes, "Material": inputs["Sparks Material"]}
    ).outputs[0]
    tubes = t.node("GeometryNodeGeometryToInstance", 16, 0, {0: tubes}).outputs[0]
    tubes = t.node(
        "GeometryNodeSwitch",
        17,
        0,
        {"Switch": t.math("GREATER_THAN", count, 0.0, x=16, y=-2), "True": tubes},
        input_type="GEOMETRY",
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 18, 0)
    for value in (tubes, geometry):
        t.connect(value, joined.inputs[0])
    t.node("NodeGroupOutput", 19, 0, {0: joined.outputs[0]})
    t.arrange()
    return ng


def build_glow():
    """The shader with a glow added, brighter on the rim, read from the mesh"""
    ng = bpy.data.node_groups.new(GLOW, "ShaderNodeTree")
    add_input(ng, "Shader", "NodeSocketShader")
    add_input(
        ng,
        "Opacity",
        "NodeSocketFloat",
        default_value=1.0,
        hide_value=True,
        description="Alpha of the shader, not to glow where it is transparent",
    )
    add_input(ng, "Color", "NodeSocketColor", default_value=COLOR)
    add_input(
        ng,
        "Rim",
        "NodeSocketFloat",
        default_value=8.0,
        min_value=0.0,
        description="Emission strength of the glow on the outline",
    )
    add_input(
        ng,
        "Rim Width",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Width of the glowing outline",
    )
    add_input(
        ng,
        "Flush",
        "NodeSocketFloat",
        min_value=0.0,
        description="Emission strength of the glow all over the Hot Spots, 0 for the outline only",
    )
    add_output(ng, "Shader", "NodeSocketShader")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    glow = t.node(
        "ShaderNodeAttribute", 1, -2, attribute_type="GEOMETRY", attribute_name="aura_glow"
    ).outputs["Vector"]
    glow = t.node("ShaderNodeSeparateXYZ", 2, -2, {0: glow}).outputs
    facing = t.node("ShaderNodeLayerWeight", 1, -4, {"Blend": 0.5}).outputs["Facing"]
    sharpness = t.math(
        "DIVIDE", 1.0, t.math("MAXIMUM", inputs["Rim Width"], 0.01, x=1, y=-6), x=2, y=-6
    )
    facing = t.math("POWER", facing, sharpness, x=2, y=-4)
    strength = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", facing, inputs["Rim"], x=3, y=-4),
        glow["X"],
        t.math("MULTIPLY", glow["Y"], inputs["Flush"], x=3, y=-2),
        x=4,
        y=-3,
    )
    strength = t.math("MULTIPLY", strength, inputs["Opacity"], x=4, y=-2)
    emission = t.node(
        "ShaderNodeEmission", 5, -1, {"Color": inputs["Color"], "Strength": strength}
    ).outputs[0]
    shader = t.node("ShaderNodeAddShader", 6, 0, {0: inputs["Shader"], 1: emission}).outputs[0]
    t.node("NodeGroupOutput", 7, 0, {"Shader": shader})
    return ng


def build_sparks_material():
    """Glowing spark streaks, casting no shadows"""
    material = bpy.data.materials.new(SPARKS)
    material.use_transparent_shadow = True
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))
    light = t.node("ShaderNodeAttribute", -400, 100, attribute_name="aura_spark")
    emission = t.node(
        "ShaderNodeEmission", -200, 100, {"Color": light.outputs["Vector"], "Strength": 1.0}
    )
    transparent = t.node("ShaderNodeBsdfTransparent", 0, -50).outputs[0]
    shadow = t.node("ShaderNodeLightPath", 0, 300).outputs["Is Shadow Ray"]
    shader = t.node(
        "ShaderNodeMixShader", 200, 0, {0: shadow, 1: emission.outputs[0], 2: transparent}
    )
    t.node("ShaderNodeOutputMaterial", 400, 0, {"Surface": shader.outputs[0]})
    return material


if __name__ == "__main__":
    sparks = build_sparks_material()
    write(RESOURCE, (build_node_group(), build_glow(), sparks), fake_user=True)
