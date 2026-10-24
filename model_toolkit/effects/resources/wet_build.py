# Build wet.blend: the Wet node group, the Wet Film shader group and the drops material
# Usage: Blender --background --factory-startup --python wet_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "wet.blend"
NODE_GROUP = "MustardUI Wet"
FILM = "MustardUI Wet Film"
MIST = "MustardUI Wet Mist"
MATERIAL = "MustardUI Wet Drops"
# Share of the drop sphere below the surface
SINK = 0.2
# Clusters of drops and of tiny drops per meter
CLUSTER = 20.0
# Longest drops, relative to their width
MAX_STRETCH = 2.5
# Stretch of the running drops at full Speed
RUN_STRETCH = 1.0
# Size of the trail drops and the radius lost by the running drops for each, relative to them
TRAIL_SIZE = 0.6
TRAIL_LOSS = 0.08
# Run between the trail points, relative to the radius of the running drop
TRAIL_SPACING = 2.0
# Water of the film taken by the running drops with dripping, in meters of depth
FILM_DEPTH = 0.00005
# Radius the drops hanging on the overhangs grow to before dripping, relative to Drip Radius
HANG = 1.6
# Seconds between the drops dripping from a hanging drop
DRIP_INTERVAL = 0.25
# Largest running drops, relative to the largest drops
MAX_RUN = 1.2
# Downward share of the normal of the overhangs, where the large drops drip
OVERHANG = 0.4
# Gravity in meters per second squared, air drag of the falling drops per second
GRAVITY = 9.81
DRAG = 0.5
# Seconds before the dripping drops can land on the mesh, not to land where they left
LAUNCH = 0.1
# Radius kept by the drops landing on the mesh, and the size of the splashes on the floor
LANDING = 0.8
SPLASH = 1.8
# Stretch of the falling drops per meter per second
FALL_STRETCH = 0.5
# Speed under which the running drops dry, in meters per second
STILL = 0.003
# Height of the lines of water along the trails, relative to the drops
LINE_HEIGHT = 0.25
# Grip and wobble patterns per meter
GRIP = 40.0
WOBBLE = 30.0
# Ripples of the film per meter, and their height in meters
RIPPLE = 120.0
RIPPLE_HEIGHT = 0.001
# Reflectance of water seen face on, and its share at grazing angles, the film being thin
WATER_F0 = 0.02
EDGE_FRESNEL = 0.5
# Most of the surface under the film hidden by its reflection, at grazing angles
MAX_COVER = 0.6
# Roughness, reflection and tiny drops of the damp skin between the patches of film
DAMP_ROUGHNESS = 0.4
DAMP_COAT = 0.35
DAMP_MIST = 0.4
# Half width of the transition from the damp skin to the film, in the noise of the patches
FILM_EDGE = 0.12
# Share of the normal smoothed by the water in the pools
FILL = 0.2
# Scale of the layers of tiny drops relative to Mist Scale, and their share of Mist
MIST_LAYERS = ((0.4, 0.3), (1.0, 1.0), (2.3, 1.0), (5.0, 1.0))
# Smallest tiny drops, relative to Mist Size
MIST_SMALLEST = 0.2
# Height of the sheets of film in meters at full Bump, at their edges and in the pools, and the
# swells on them per meter
SHEET = 0.001
POOL = 0.0012
SWELL = 45.0
# Reflection of the tiny drops, relative to the film
DROP_SHINE = 6.0
# Light of the surface under the drops lost on their rim, in EEVEE
DROP_RING = 0.3
# Glints of the film per meter
SPARKLE = 150.0
# Streaks per meter, across and along the vertical
STREAK = (60.0, 60.0, 4.0)


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Wet the mesh inside the sphere of the Control, storing the wetness attribute read by the "
        "Wet Film shader, with water drops on it"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng, "Control", "NodeSocketObject", description="Empty whose sphere defines the wet area"
    )
    add_input(
        ng,
        "Wetness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Amount of wetness, animate it to dry the mesh",
    )
    add_input(
        ng,
        "Falloff",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Width of the ragged border of the wet area, relative to the Control radius",
    )
    add_input(
        ng,
        "Patches",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.25,
        min_value=0.0,
        max_value=1.0,
        description="Drier patches in the wet area",
    )
    add_input(
        ng,
        "Patch Scale",
        "NodeSocketFloat",
        default_value=8.0,
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
        description="Vertex Group limiting the wet area",
    )
    panel = ng.interface.new_panel("Drops")
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        panel,
        default_value=20000.0,
        min_value=0.0,
        max_value=100000.0,
        description="Drops per square meter",
    )
    add_input(
        ng,
        "Min Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0004,
        min_value=0.0,
        description="Radius of the smallest drops",
    )
    add_input(
        ng,
        "Max Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0025,
        min_value=0.0,
        description="Radius of the largest drops, fewer than the small ones",
    )
    add_input(
        ng,
        "Height",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.7,
        min_value=0.0,
        max_value=1.0,
        description="Height of the drops, relative to their radius",
    )
    add_input(
        ng,
        "Stretch",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Stretch of the larger drops downward on slopes",
    )
    add_input(
        ng,
        "Clusters",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Drops gathered in clusters, sparser between them",
    )
    add_input(ng, "Seed", "NodeSocketInt", panel, description="Seed of the drops placement")
    add_input(ng, "Material", "NodeSocketMaterial", panel, description="Material of the drops")
    panel = ng.interface.new_panel("Physics", default_closed=True)
    # In the panel header
    add_input(
        ng,
        "Physics",
        "NodeSocketBool",
        panel,
        default_value=False,
        description="The large drops running down, leaving trails of small drops and sweeping "
        "the drops on their way. Simulated from the Start Frame",
    ).is_panel_toggle = True
    add_input(ng, "Start Frame", "NodeSocketInt", panel, description="First simulated frame")
    add_input(
        ng,
        "Run Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0018,
        min_value=0.0,
        description="Radius of the smallest drops running down",
    )
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        panel,
        default_value=0.08,
        min_value=0.0,
        description="Speed of the running drops on a vertical surface, in meters per second",
    )
    add_input(
        ng,
        "Stickiness",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Grip of the surface, stopping the smaller drops and the ones on gentle slopes",
    )
    add_input(
        ng,
        "Wobble",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="Sideways wobble of the running drops",
    )
    add_input(
        ng,
        "Trail",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Water left behind in small drops, shrinking the running drops until they stop",
    )
    add_input(
        ng,
        "Line Life",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=6.0,
        min_value=0.1,
        description="Seconds the lines of water left by the running drops last, fading from where "
        "they started over the second half",
    )
    add_input(
        ng,
        "Run Rate",
        "NodeSocketFloat",
        panel,
        default_value=0.04,
        min_value=0.0,
        description="Chance per second of each large drop to start running",
    )
    add_input(
        ng,
        "Regrow",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=3.0,
        min_value=0.1,
        description="Seconds for the drops to form again where a running drop passed",
    )
    panel = ng.interface.new_panel("Dripping", default_closed=True)
    ng.interface.move_to_parent(
        panel,
        next(x for x in ng.interface.items_tree if x.name == "Physics" and x.item_type == "PANEL"),
        100,
    )
    add_input(
        ng,
        "Dripping",
        "NodeSocketBool",
        panel,
        default_value=False,
        description="The running drops merging and taking the drops on their way, dripping from "
        "below the chin, the arms and other overhangs once large, landing on the mesh or the Floor",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Drip Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.002,
        min_value=0.0,
        description="Radius of the drops dripping from the overhangs, one at a time from the "
        "larger drops hanging there",
    )
    add_input(
        ng,
        "Floor",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0,
        description="Height of the floor where the dripping drops splash, in world space",
    )

    t = Tree(ng, spacing=(200, 160))
    t.section("Wetness")
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
    distance = t.vmath("LENGTH", local, x=2, y=-2)
    edge_noise = t.node(
        "ShaderNodeTexNoise",
        1,
        -4,
        {"Vector": rest, "Scale": t.math("MULTIPLY", inputs["Patch Scale"], 4.0, x=0, y=-5)},
    ).outputs["Fac"]
    falloff = t.math("MAXIMUM", inputs["Falloff"], 0.001, x=2, y=-5)
    distance = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", edge_noise, 0.5, x=2, y=-4), falloff, distance, x=3, y=-3
    )
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

    # Drier patches, and the wetness of the previous Wet modifiers kept
    patch_noise = t.node(
        "ShaderNodeTexNoise", 1, -7, {"Vector": rest, "Scale": inputs["Patch Scale"], "Detail": 3.0}
    ).outputs["Fac"]
    patch = t.node(
        "ShaderNodeMapRange",
        2,
        -7,
        {"Value": patch_noise, "From Min": 0.35, "From Max": 0.6},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    patch = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", patch, 1.0, x=3, y=-7), inputs["Patches"], 1.0, x=4, y=-7
    )
    wet = t.math("MULTIPLY", sphere, patch, x=5, y=-4)
    wet = t.math("MULTIPLY", wet, inputs["Wetness"], x=6, y=-4)
    wet = t.math("MULTIPLY", wet, inputs["Mask"], x=7, y=-4)
    previous = t.attribute("wetness", "FLOAT", 7, -6)
    total = t.math("MAXIMUM", wet, previous, x=8, y=-5)

    # Only the mesh, not to wet the drops of the previous Wet modifiers
    components = t.node("GeometryNodeSeparateComponents", 0, 1, {0: inputs["Geometry"]}).outputs
    mesh = t.store(components["Mesh"], "wetness", "FLOAT", total, 9, 1)
    # For the shader in a single attribute, EEVEE reading few of them: rest position and wetness
    packed = t.node(
        "FunctionNodeCombineColor",
        9,
        -1,
        {
            "Red": t.node("ShaderNodeSeparateXYZ", 8, -1, {0: rest}).outputs["X"],
            "Alpha": total,
        },
    )
    rest_xyz = t.node("ShaderNodeSeparateXYZ", 8, -1.5, {0: rest}).outputs
    t.connect(rest_xyz["Y"], packed.inputs["Green"])
    t.connect(rest_xyz["Z"], packed.inputs["Blue"])
    mesh = t.store(mesh, "wet", "FLOAT_COLOR", packed.outputs[0], 10, 1)

    t.section("Drops", row=True)
    # Placed on the rest mesh, not to move on the deformed one, without its attributes
    captured = t.node("GeometryNodeCaptureAttribute", 0, -10, {"Geometry": components["Mesh"]})
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
    drops = t.strip(at_rest, 2, -10)
    drops = t.node(
        "GeometryNodeDistributePointsOnFaces",
        3,
        -10,
        {
            "Mesh": drops,
            "Selection": t.math(
                "GREATER_THAN", captured["Total"], captured["Previous"], x=2, y=-12
            ),
            "Density": inputs["Density"],
            "Seed": inputs["Seed"],
        },
        distribute_method="RANDOM",
    ).outputs["Points"]

    # Random values from the rest position, the same for the drops of every Wet modifier, each one
    # keeping the drops between the previous wetness and its own
    rest_point = t.node("GeometryNodeInputPosition", 3, -12).outputs[0]
    random = t.node(
        "ShaderNodeTexWhiteNoise", 4, -12, {"Vector": rest_point}, noise_dimensions="3D"
    )
    value = random.outputs["Value"]
    dry = t.math(
        "MAXIMUM",
        t.math("LESS_THAN", value, captured["Previous"], x=5, y=-13),
        t.math("GREATER_THAN", value, captured["Total"], x=5, y=-14),
        x=6,
        y=-13,
    )
    # Fewer drops between the clusters
    cluster = t.node(
        "ShaderNodeTexNoise", 4, -15, {"Vector": rest_point, "Scale": CLUSTER, "Detail": 2.0}
    ).outputs["Fac"]
    cluster = t.node(
        "ShaderNodeMapRange",
        5,
        -15,
        {"Value": cluster, "From Min": 0.4, "From Max": 0.65},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    cluster = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", cluster, 1.0, x=6, y=-15),
        inputs["Clusters"],
        1.0,
        x=7,
        y=-15,
    )
    spread = t.node("ShaderNodeSeparateXYZ", 5, -17, {0: random.outputs["Color"]}).outputs["Y"]
    dry = t.math("MAXIMUM", dry, t.math("GREATER_THAN", spread, cluster, x=7, y=-16), x=8, y=-13)
    drops = t.node("GeometryNodeDeleteGeometry", 7, -10, {"Geometry": drops, "Selection": dry})
    drops = drops.outputs[0]

    # Mostly small drops
    share = t.node("ShaderNodeSeparateXYZ", 5, -16, {0: random.outputs["Color"]}).outputs["X"]
    share = t.math("POWER", share, 3.0, x=6, y=-16)
    radius = t.node(
        "ShaderNodeMapRange",
        7,
        -16,
        {"Value": share, "To Min": inputs["Min Radius"], "To Max": inputs["Max Radius"]},
    ).outputs[0]
    drops = t.store(drops, ".wet_radius", "FLOAT", radius, 8, -10)

    self_object = t.node("GeometryNodeSelfObject", 3, -19).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", 4, -19, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    down = t.node(
        "FunctionNodeTransformDirection",
        6,
        -19,
        {
            "Transform": t.node("FunctionNodeInvertMatrix", 5, -19, {0: to_world}).outputs[0],
            "Direction": (0.0, 0.0, -1.0),
        },
    ).outputs[0]
    runners, trail, falling = build_runners(t, inputs, captured, at_rest, drops, down)

    t.section("Placement", row=True)
    # The large drops running with physics, and the drops their trails pass swept away
    started = t.math(
        "MULTIPLY",
        inputs["Physics"],
        t.math(
            "GREATER_THAN",
            t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"],
            inputs["Start Frame"],
            x=1,
            y=-2,
        ),
        x=2,
        y=-2,
    )
    drop_radius = t.attribute(".wet_radius", "FLOAT", 0, -4)
    position = t.node("GeometryNodeInputPosition", 0, -5).outputs[0]
    growth = regrowth(t, inputs, trail, drop_radius, position, 1, -5)
    # Hidden where a trail just passed, as where a drop started running
    hidden = t.math("LESS_THAN", growth, 0.05, x=4, y=-5)
    drops = t.node(
        "GeometryNodeDeleteGeometry",
        6,
        0,
        {"Geometry": drops, "Selection": t.math("MULTIPLY", hidden, started, x=6, y=-3)},
    ).outputs[0]
    drops = t.store(
        drops,
        ".wet_radius",
        "FLOAT",
        t.math(
            "MULTIPLY",
            drop_radius,
            t.node(
                "GeometryNodeSwitch", 6, -5, {"Switch": started, "False": 1.0, "True": growth}
            ).outputs[0],
            x=7,
            y=-4,
        ),
        6.5,
        0,
    )
    # On the deformed mesh, interpolated from where they were placed, the moved runners from their
    # nearest rest position
    for i, name in enumerate(("Posed", "Normal")):
        drops = t.store(drops, f".wet_{name.lower()}", "FLOAT_VECTOR", captured[name], 6.8, -i)
        sample = t.node(
            "GeometryNodeSampleNearestSurface",
            6,
            2 + i,
            {"Mesh": at_rest, "Value": captured[name]},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        runners = t.store(runners, f".wet_{name.lower()}", "FLOAT_VECTOR", sample, 6.8, 2 + i)
    joined = t.node("GeometryNodeJoinGeometry", 7, 0)
    for points in (runners, drops):
        t.connect(points, joined.inputs[0])
    drops = joined.outputs[0]

    # The larger and faster ones stretched down
    posed = t.attribute(".wet_posed", "FLOAT_VECTOR", 8, -2)
    normal = t.vmath("NORMALIZE", t.attribute(".wet_normal", "FLOAT_VECTOR", 8, -4), x=9, y=-4)
    slope = t.vmath("SUBTRACT", down, t.vmath("PROJECT", down, normal, x=9, y=-6), x=10, y=-6)
    size = t.math("DIVIDE", drop_radius, inputs["Max Radius"], x=9, y=-8, clamp=True)
    stretch = t.math("MULTIPLY", t.vmath("LENGTH", slope, x=10, y=-7), size, x=11, y=-7)
    stretch = t.math("MULTIPLY_ADD", stretch, inputs["Stretch"], 1.0, x=12, y=-7)
    speed = t.math(
        "DIVIDE",
        t.attribute(".wet_speed", "FLOAT", 10, -9),
        inputs["Speed"],
        x=11,
        y=-9,
        clamp=True,
    )
    stretch = t.math("MULTIPLY_ADD", speed, RUN_STRETCH, stretch, x=13, y=-8)
    stretch = t.math("MINIMUM", stretch, MAX_STRETCH, x=13.5, y=-8)
    scale = t.node(
        "ShaderNodeCombineXYZ",
        14,
        -6,
        {
            "X": t.math("MULTIPLY", drop_radius, stretch, x=13, y=-6),
            "Y": drop_radius,
            "Z": t.math("MULTIPLY", drop_radius, inputs["Height"], x=13, y=-7),
        },
    ).outputs[0]
    rotation = t.node(
        "FunctionNodeAlignRotationToVector", 11, -10, {"Vector": normal}, axis="Z"
    ).outputs[0]
    rotation = t.node(
        "FunctionNodeAlignRotationToVector",
        14,
        -9,
        {"Rotation": rotation, "Vector": slope},
        axis="X",
        pivot_axis="Z",
    ).outputs[0]
    drops = t.node(
        "GeometryNodeSetPosition", 15, 0, {"Geometry": drops, "Position": posed}
    ).outputs[0]

    # Domes of water, a bit sunk in the surface
    dome = t.node("GeometryNodeMeshUVSphere", 14, -12, {"Segments": 12, "Rings": 6, "Radius": 1.0})
    dome_z = t.node(
        "ShaderNodeSeparateXYZ",
        14,
        -14,
        {0: t.node("GeometryNodeInputPosition", 13, -14).outputs[0]},
    ).outputs["Z"]
    dome = t.node(
        "GeometryNodeDeleteGeometry",
        15,
        -12,
        {
            "Geometry": dome.outputs["Mesh"],
            "Selection": t.math("LESS_THAN", dome_z, -0.01, x=15, y=-14),
        },
    ).outputs[0]
    dome = t.node(
        "GeometryNodeTransform", 16, -12, {"Geometry": dome, "Translation": (0.0, 0.0, -SINK)}
    ).outputs[0]
    dome = t.node("GeometryNodeSetShadeSmooth", 17, -12, {"Geometry": dome}).outputs[0]
    dome = t.node(
        "GeometryNodeSetMaterial", 18, -12, {"Geometry": dome, "Material": inputs["Material"]}
    ).outputs[0]
    drops = t.node(
        "GeometryNodeInstanceOnPoints",
        19,
        0,
        {"Points": drops, "Instance": dome, "Rotation": rotation, "Scale": scale},
    ).outputs[0]

    # The mesh first, the drops as instances not to be subdivided by the next modifiers
    output = t.node("GeometryNodeJoinGeometry", 20, 2)
    for name in ("Instances", "Volume", "Point Cloud", "Grease Pencil", "Curve"):
        t.connect(components[name], output.inputs[0])
    t.connect(build_falling(t, inputs, falling, down), output.inputs[0])
    t.connect(build_lines(t, inputs, captured, at_rest, runners, trail), output.inputs[0])
    t.connect(drops, output.inputs[0])
    t.connect(mesh, output.inputs[0])
    t.node("NodeGroupOutput", 21, 2, {0: output.outputs[0]})
    t.arrange()
    return ng


def regrowth(t, inputs, trail, radius, position, x, y):
    """Growth of the drops back where a trail passed, from 0 when it passed to 1 after Regrow"""
    seconds = t.node("GeometryNodeInputSceneTime", x, y - 1).outputs["Seconds"]
    nearest = t.node(
        "GeometryNodeSampleNearest", x, y, {"Geometry": trail}, domain="POINT"
    ).outputs[0]
    found, time = (
        t.node(
            "GeometryNodeSampleIndex",
            x + 1,
            y - i,
            {"Geometry": trail, "Value": value, "Index": nearest},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
        for i, (value, data_type) in enumerate(
            (
                (position, "FLOAT_VECTOR"),
                (t.attribute(".wet_time", "FLOAT", x, y - 2), "FLOAT"),
            )
        )
    )
    near = t.math(
        "LESS_THAN",
        t.vmath("DISTANCE", found, position, x=x + 2, y=y),
        t.math("ADD", inputs["Run Radius"], radius, x=x + 2, y=y - 1),
        x=x + 3,
        y=y,
    )
    # None without trails
    count = t.node(
        "GeometryNodeAttributeDomainSize", x + 2, y - 2, {0: trail}, component="POINTCLOUD"
    ).outputs["Point Count"]
    near = t.math(
        "MULTIPLY", near, t.math("GREATER_THAN", count, 0.0, x=x + 3, y=y - 2), x=x + 4, y=y
    )
    grown = t.node(
        "ShaderNodeMapRange",
        x + 3,
        y - 3,
        {
            "Value": t.math("SUBTRACT", seconds, time, x=x + 2, y=y - 3),
            "From Min": inputs["Regrow"],
            "From Max": t.math("MULTIPLY", inputs["Regrow"], 1.5, x=x + 2, y=y - 4),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    return t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", near, t.math("SUBTRACT", 1.0, grown, x=x + 4, y=y - 3), x=x + 5, y=y),
        x=x + 6,
        y=y,
    )


def merge(t, runners, radius, x, y):
    """Touching running drops merged, the water of the smaller ones in the larger ones"""
    index = t.node("GeometryNodeInputIndex", x, y - 1).outputs[0]
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    nearest = t.node("GeometryNodeIndexOfNearest", x, y - 3).outputs

    def other(value, data_type, i):
        return t.node(
            "GeometryNodeSampleIndex",
            x + 1,
            y - i,
            {"Geometry": runners, "Value": value, "Index": nearest["Index"]},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]

    touching = t.math(
        "MULTIPLY",
        nearest["Has Neighbor"],
        t.math(
            "LESS_THAN",
            t.vmath("DISTANCE", position, other(position, "FLOAT_VECTOR", 1), x=x + 2, y=y - 1),
            t.math("ADD", radius, other(radius, "FLOAT", 2), x=x + 2, y=y - 2),
            x=x + 3,
            y=y - 1,
        ),
        x=x + 4,
        y=y - 1,
    )
    # The smaller one, or the later one of equal ones
    smaller = t.math(
        "ADD",
        t.math("LESS_THAN", radius, other(radius, "FLOAT", 3), x=x + 2, y=y - 3),
        t.math(
            "MULTIPLY",
            t.math("COMPARE", radius, other(radius, "FLOAT", 4), 1e-9, x=x + 2, y=y - 4),
            t.math("GREATER_THAN", index, nearest["Index"], x=x + 2, y=y - 5),
            x=x + 3,
            y=y - 4,
        ),
        x=x + 4,
        y=y - 3,
    )
    donor = t.math("MULTIPLY", touching, smaller, x=x + 5, y=y - 1)
    captured = t.node("GeometryNodeCaptureAttribute", x + 6, y, {"Geometry": runners})
    captured.capture_items.new("FLOAT", "Donor")
    t.connect(donor, captured.inputs["Donor"])
    runners, donor = captured.outputs["Geometry"], captured.outputs["Donor"]
    # Not giving the water to a drop giving its own
    donor = t.math(
        "MULTIPLY",
        donor,
        t.math("SUBTRACT", 1.0, other(donor, "FLOAT", 6), x=x + 7, y=y - 6),
        x=x + 8,
        y=y - 6,
    )
    total = t.node(
        "GeometryNodeAccumulateField",
        x + 9,
        y - 4,
        {
            "Value": t.math(
                "MULTIPLY", t.math("POWER", radius, 3.0, x=x + 8, y=y - 4), donor, x=x + 9, y=y - 5
            ),
            "Group ID": t.node(
                "GeometryNodeSwitch",
                x + 9,
                y - 7,
                {"Switch": donor, "False": index, "True": nearest["Index"]},
                input_type="INT",
            ).outputs[0],
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs["Total"]
    grown = t.math(
        "POWER",
        t.math("ADD", t.math("POWER", radius, 3.0, x=x + 10, y=y - 3), total, x=x + 11, y=y - 3),
        1.0 / 3.0,
        x=x + 12,
        y=y - 3,
    )
    state = t.node("GeometryNodeCaptureAttribute", x + 12, y, {"Geometry": runners})
    for name, value in (("Donor", donor), ("Grown", grown)):
        state.capture_items.new("FLOAT", name)
        t.connect(value, state.inputs[name])
    merged = t.store(
        state.outputs["Geometry"], ".wet_radius", "FLOAT", state.outputs["Grown"], x + 13, y
    )
    return t.node(
        "GeometryNodeDeleteGeometry",
        x + 14,
        y,
        {
            "Geometry": merged,
            "Selection": t.math("GREATER_THAN", state.outputs["Donor"], 0.5, x=x + 13, y=y - 2),
        },
    ).outputs[0]


def absorb(t, inputs, drops, trail, left, runner, x, y):
    """The drops on the way of the running ones where they leave trail points, as points giving
    their water to the running drop"""
    radius = t.attribute(".wet_radius", "FLOAT", x, y - 1)
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    nearest = t.node("GeometryNodeSampleNearest", x, y, {"Geometry": left}, domain="POINT").outputs[
        0
    ]
    found, target = (
        t.node(
            "GeometryNodeSampleIndex",
            x + 1,
            y - i,
            {"Geometry": left, "Value": value, "Index": nearest},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
        for i, (value, data_type) in enumerate(((position, "FLOAT_VECTOR"), (runner, "INT")))
    )
    growth = regrowth(t, inputs, trail, radius, position, x, y - 6)
    taken = t.math(
        "MULTIPLY",
        t.math(
            "LESS_THAN",
            t.vmath("DISTANCE", found, position, x=x + 2, y=y),
            t.math("ADD", inputs["Run Radius"], radius, x=x + 2, y=y - 1),
            x=x + 3,
            y=y,
        ),
        t.math("GREATER_THAN", growth, 0.05, x=x + 3, y=y - 2),
        x=x + 4,
        y=y,
    )
    count = t.node(
        "GeometryNodeAttributeDomainSize", x + 3, y - 3, {0: left}, component="POINTCLOUD"
    ).outputs["Point Count"]
    taken = t.math(
        "MULTIPLY", taken, t.math("GREATER_THAN", count, 0.0, x=x + 4, y=y - 3), x=x + 5, y=y
    )
    givers = t.node(
        "GeometryNodeDeleteGeometry",
        x + 5,
        y,
        {"Geometry": drops, "Selection": t.math("LESS_THAN", taken, 0.5, x=x + 5, y=y - 1)},
    ).outputs[0]
    givers = t.store(givers, ".wet_target", "INT", target, x + 6, y)
    givers = t.store(
        givers,
        ".wet_gain",
        "FLOAT",
        t.math(
            "POWER", t.math("MULTIPLY", radius, growth, x=x + 6, y=y - 2), 3.0, x=x + 7, y=y - 2
        ),
        x + 7,
        y,
    )
    return t.store(givers, ".wet_donor", "BOOLEAN", True, x + 8, y)


def fall(t, inputs, captured, falling, down, dt, seconds, frame, x, y):
    """Falling drops in the space of the object, the ones landing on the mesh at their rest
    position to run again, and the falling ones with the splashes on the floor"""
    position = t.node("GeometryNodeInputPosition", x, y - 1).outputs[0]
    radius = t.attribute(".wet_radius", "FLOAT", x, y - 2)
    landed = t.attribute(".wet_landed", "FLOAT", x, y - 3)
    flying = t.math("SUBTRACT", 1.0, landed, x=x + 1, y=y - 3)
    velocity = t.vmath(
        "MULTIPLY_ADD",
        down,
        t.math("MULTIPLY", dt, GRAVITY, x=x, y=y - 5),
        t.attribute(".wet_velocity", "FLOAT_VECTOR", x, y - 4),
        x=x + 1,
        y=y - 4,
    )
    velocity = t.vmath(
        "SCALE",
        velocity,
        t.math(
            "DIVIDE",
            flying,
            t.math("MULTIPLY_ADD", dt, DRAG, 1.0, x=x + 1, y=y - 6),
            x=x + 2,
            y=y - 5,
        ),
        x=x + 3,
        y=y - 4,
    )
    moved = t.vmath(
        "ADD", t.vmath("SCALE", velocity, dt, x=x + 4, y=y - 5), position, x=x + 4, y=y - 4
    )

    # Hitting the mesh, after leaving it
    ray = t.node(
        "GeometryNodeRaycast",
        x + 4,
        y - 7,
        {
            "Target Geometry": captured["Geometry"],
            "Ray Direction": velocity,
            "Ray Length": t.math(
                "MULTIPLY_ADD",
                t.vmath("LENGTH", velocity, x=x + 3, y=y - 8),
                dt,
                radius,
                x=x + 4,
                y=y - 8,
            ),
        },
    ).outputs
    old = t.math(
        "GREATER_THAN",
        t.math(
            "SUBTRACT", seconds, t.attribute(".wet_time", "FLOAT", x + 4, y - 10), x=x + 5, y=y - 10
        ),
        LAUNCH,
        x=x + 6,
        y=y - 10,
    )
    hit = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", ray["Is Hit"], old, x=x + 6, y=y - 9),
        flying,
        x=x + 7,
        y=y - 9,
    )

    # On the floor, in world space
    self_object = t.node("GeometryNodeSelfObject", x + 4, y - 12).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", x + 5, y - 12, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    world = t.node(
        "FunctionNodeTransformPoint", x + 6, y - 12, {"Vector": moved, "Transform": to_world}
    ).outputs[0]
    world = t.node("ShaderNodeSeparateXYZ", x + 7, y - 12, {0: world}).outputs
    below = t.math("LESS_THAN", world["Z"], inputs["Floor"], x=x + 8, y=y - 12)
    floor = t.node(
        "FunctionNodeTransformPoint",
        x + 9,
        y - 12,
        {
            "Vector": t.node(
                "ShaderNodeCombineXYZ",
                x + 8,
                y - 13,
                {"X": world["X"], "Y": world["Y"], "Z": inputs["Floor"]},
            ).outputs[0],
            "Transform": t.node("FunctionNodeInvertMatrix", x + 8, y - 14, {0: to_world}).outputs[
                0
            ],
        },
    ).outputs[0]
    splash = t.math("MULTIPLY", below, flying, x=x + 9, y=y - 11)

    state = t.node("GeometryNodeCaptureAttribute", x + 10, y, {"Geometry": falling})
    for data_type, name, value in (
        ("FLOAT", "Hit", hit),
        ("VECTOR", "Hit Position", ray["Hit Position"]),
        ("FLOAT", "Splash", splash),
        (
            "VECTOR",
            "Moved",
            t.node(
                "GeometryNodeSwitch",
                x + 10,
                y - 12,
                {"Switch": below, "False": moved, "True": floor},
                input_type="VECTOR",
            ).outputs[0],
        ),
        ("VECTOR", "Velocity", velocity),
    ):
        state.capture_items.new(data_type, name)
        t.connect(value, state.inputs[name])
    state = state.outputs
    split = t.node(
        "GeometryNodeSeparateGeometry",
        x + 11,
        y,
        {
            "Geometry": state["Geometry"],
            "Selection": t.math("GREATER_THAN", state["Hit"], 0.5, x=x + 11, y=y - 2),
        },
    ).outputs

    # Running again from where they land, with a new trail
    hits = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 12,
        y + 2,
        {
            "Mesh": captured["Geometry"],
            "Value": captured["Rest"],
            "Sample Position": state["Hit Position"],
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    runners = t.node(
        "GeometryNodeSetPosition", x + 13, y + 1, {"Geometry": split["Selection"], "Position": hits}
    ).outputs[0]
    runners = t.store(
        runners,
        ".wet_radius",
        "FLOAT",
        t.math("MULTIPLY", radius, LANDING, x=x + 13, y=y + 3),
        x + 14,
        y + 1,
    )
    runners = t.store(
        runners,
        ".wet_id",
        "INT",
        t.node(
            "FunctionNodeHashValue",
            x + 14,
            y + 3,
            {"Value": hits, "Seed": frame},
            data_type="VECTOR",
        ).outputs[0],
        x + 15,
        y + 1,
    )
    for i, name in enumerate((".wet_travel", ".wet_speed")):
        runners = t.store(runners, name, "FLOAT", 0.0, x + 16 + i, y + 1)

    # Splashes kept until dry
    falling = t.node(
        "GeometryNodeSetPosition",
        x + 12,
        y,
        {"Geometry": split["Inverted"], "Position": state["Moved"]},
    ).outputs[0]
    falling = t.store(falling, ".wet_velocity", "FLOAT_VECTOR", state["Velocity"], x + 13, y)
    falling = t.store(
        falling,
        ".wet_landed",
        "FLOAT",
        t.math("MAXIMUM", landed, state["Splash"], x=x + 13, y=y - 2),
        x + 14,
        y,
    )
    falling = t.store(
        falling,
        ".wet_time",
        "FLOAT",
        t.node(
            "GeometryNodeSwitch",
            x + 14,
            y - 2,
            {
                "Switch": t.math("GREATER_THAN", state["Splash"], 0.5, x=x + 14, y=y - 3),
                "False": t.attribute(".wet_time", "FLOAT", x + 13, y - 3),
                "True": seconds,
            },
        ).outputs[0],
        x + 15,
        y,
    )
    age = t.math(
        "SUBTRACT", seconds, t.attribute(".wet_time", "FLOAT", x + 15, y - 2), x=x + 16, y=y - 2
    )
    gone = t.math(
        "GREATER_THAN",
        age,
        t.math("MULTIPLY", inputs["Regrow"], 2.0, x=x + 16, y=y - 3),
        x=x + 17,
        y=y - 2,
    )
    # Not falling for ever without a floor under them
    gone = t.math(
        "MAXIMUM", gone, t.math("GREATER_THAN", age, 10.0, x=x + 17, y=y - 3), x=x + 18, y=y - 2
    )
    falling = t.node(
        "GeometryNodeDeleteGeometry", x + 18, y, {"Geometry": falling, "Selection": gone}
    ).outputs[0]
    return runners, falling


def build_runners(t, inputs, captured, at_rest, drops, down):
    """Running drops and their trails, points at their rest position, from the large drops"""
    t.section("Physics", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    sim_in = t.node("GeometryNodeSimulationInput", 1, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 16, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("GEOMETRY", "Trail")
    sim_out.state_items.new("GEOMETRY", "Falling")
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=2, y=-2)
    runners, trail, falling = (
        t.node(
            "GeometryNodeSwitch",
            2,
            -i,
            {"Switch": started, "True": sim_in.outputs[name]},
            input_type="GEOMETRY",
        ).outputs[0]
        for i, name in enumerate(("Geometry", "Trail", "Falling"))
    )
    previous = trail
    radius = t.attribute(".wet_radius", "FLOAT", 2, -4)
    position = t.node("GeometryNodeInputPosition", 2, -5).outputs[0]

    # The large drops start running by chance, where grown again after a trail
    seconds = t.node("GeometryNodeInputSceneTime", 0, -3).outputs["Seconds"]
    reached = t.math(
        "LESS_THAN", regrowth(t, inputs, trail, radius, position, 3, -3), 0.999, x=4, y=-4
    )
    waiting = t.math(
        "MAXIMUM",
        t.math("LESS_THAN", radius, inputs["Run Radius"], x=3, y=-6),
        t.math("SUBTRACT", 1.0, started, x=3, y=-7),
        x=4,
        y=-6,
    )
    chance = t.node(
        "ShaderNodeTexWhiteNoise", 3, -9, {"Vector": position, "W": frame}, noise_dimensions="4D"
    ).outputs["Value"]
    unlucky = t.math(
        "GREATER_THAN", chance, t.math("MULTIPLY", inputs["Run Rate"], dt, x=4, y=-11), x=5, y=-9
    )
    waiting = t.math("MAXIMUM", waiting, unlucky, x=6, y=-7)
    spawned = t.node(
        "GeometryNodeDeleteGeometry",
        5,
        -3,
        {"Geometry": drops, "Selection": t.math("MAXIMUM", reached, waiting, x=5, y=-5)},
    ).outputs[0]
    # Each with its trail, in order
    spawned = t.store(
        spawned,
        ".wet_id",
        "INT",
        t.node(
            "FunctionNodeHashValue", 5, -8, {"Value": position, "Seed": frame}, data_type="VECTOR"
        ).outputs[0],
        5.5,
        -3,
    )
    joined = t.node("GeometryNodeJoinGeometry", 6, 0)
    t.connect(spawned, joined.inputs[0])
    t.connect(runners, joined.inputs[0])
    runners = t.node(
        "GeometryNodeSwitch",
        6.5,
        0,
        {
            "Switch": inputs["Dripping"],
            "False": joined.outputs[0],
            "True": merge(t, joined.outputs[0], radius, 6, 2),
        },
        input_type="GEOMETRY",
    ).outputs[0]
    # A small drop left where they start, not to start again
    origins = t.store(
        spawned, ".wet_radius", "FLOAT", t.math("MULTIPLY", radius, TRAIL_SIZE, x=5, y=-7), 6, -3
    )
    origins = t.store(
        origins, ".wet_time", "FLOAT", t.math("SUBTRACT", seconds, 0.01, x=6, y=-5), 6.5, -3
    )

    # Sliding down the deformed mesh, gripped by the surface, the smaller ones less
    posed, normal = (
        t.node(
            "GeometryNodeSampleNearestSurface",
            6,
            -2 - 2 * i,
            {"Mesh": at_rest, "Value": captured[name]},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, name in enumerate(("Posed", "Normal"))
    )
    normal = t.vmath("NORMALIZE", normal, x=7, y=-4)
    slope = t.vmath("SUBTRACT", down, t.vmath("PROJECT", down, normal, x=7, y=-6), x=8, y=-6)
    grip = t.node(
        "ShaderNodeTexNoise", 6, -8, {"Vector": position, "Scale": GRIP, "Detail": 2.0}
    ).outputs["Fac"]
    grip = t.node(
        "ShaderNodeMapRange",
        7,
        -8,
        {"Value": grip, "From Min": 0.3, "From Max": 0.7},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    drive = t.math(
        "MULTIPLY",
        t.vmath("LENGTH", slope, x=8, y=-7),
        t.math("DIVIDE", radius, inputs["Run Radius"], x=8, y=-8),
        x=9,
        y=-7,
    )
    drive = t.math(
        "SUBTRACT", drive, t.math("MULTIPLY", grip, inputs["Stickiness"], x=8, y=-9), x=10, y=-7
    )
    speed = t.math(
        "MULTIPLY",
        t.math("MAXIMUM", drive, 0.0, x=11, y=-7),
        inputs["Speed"],
        x=12,
        y=-7,
    )
    wobble = t.node("ShaderNodeTexNoise", 7, -11, {"Vector": position, "Scale": WOBBLE}).outputs[
        "Color"
    ]
    wobble = t.vmath("MULTIPLY_ADD", wobble, (2.0,) * 3, (-1.0,) * 3, x=8, y=-11)
    wobble = t.vmath(
        "SUBTRACT", wobble, t.vmath("PROJECT", wobble, normal, x=9, y=-12), x=10, y=-11
    )
    direction = t.vmath(
        "MULTIPLY_ADD",
        wobble,
        inputs["Wobble"],
        t.vmath("NORMALIZE", slope, x=9, y=-6),
        x=11,
        y=-10,
    )
    direction = t.vmath("NORMALIZE", direction, x=12, y=-10)
    step = t.math("MULTIPLY", speed, dt, x=13, y=-7)
    moved = t.vmath("MULTIPLY_ADD", direction, step, posed, x=13, y=-10)
    moved = t.node(
        "GeometryNodeSampleNearestSurface",
        14,
        -10,
        {"Mesh": captured["Geometry"], "Value": captured["Rest"], "Sample Position": moved},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]

    # Hanging on the overhangs until large, then dripping a drop of Drip Radius at a time
    ready = t.math(
        "GREATER_THAN",
        t.math("SUBTRACT", seconds, t.attribute(".wet_dripped", "FLOAT", 8, -17), x=9, y=-17),
        DRIP_INTERVAL,
        x=10,
        y=-17,
    )
    hanging = t.math(
        "MULTIPLY",
        t.math(
            "GREATER_THAN", t.vmath("DOT_PRODUCT", normal, down, x=8, y=-14), OVERHANG, x=9, y=-14
        ),
        t.math(
            "GREATER_THAN",
            radius,
            t.math("MULTIPLY", inputs["Drip Radius"], HANG, x=8, y=-16),
            x=9,
            y=-15,
        ),
        x=10,
        y=-14,
    )
    hanging = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", hanging, ready, x=11, y=-15),
        inputs["Dripping"],
        x=11,
        y=-14,
    )
    marked = t.node("GeometryNodeCaptureAttribute", 12, 1, {"Geometry": runners})
    marked.capture_items.new("FLOAT", "Hanging")
    t.connect(hanging, marked.inputs["Hanging"])
    hanging = t.math("GREATER_THAN", marked.outputs["Hanging"], 0.5, x=12, y=-14)
    detached = t.node(
        "GeometryNodeDeleteGeometry",
        13,
        2,
        {
            "Geometry": marked.outputs["Geometry"],
            "Selection": t.math("SUBTRACT", 1.0, hanging, x=13, y=-14),
        },
    ).outputs[0]
    detached = t.node(
        "GeometryNodeSetPosition",
        14,
        2,
        {
            "Geometry": detached,
            "Position": t.vmath("MULTIPLY_ADD", normal, inputs["Drip Radius"], posed, x=13, y=-15),
        },
    ).outputs[0]
    detached = t.store(detached, ".wet_radius", "FLOAT", inputs["Drip Radius"], 15, 2)
    detached = t.store(detached, ".wet_time", "FLOAT", seconds, 16, 2)
    detached = t.store(detached, ".wet_velocity", "FLOAT_VECTOR", (0.0, 0.0, 0.0), 17, 2)
    left = t.math(
        "POWER",
        t.math(
            "MAXIMUM",
            t.math(
                "SUBTRACT",
                t.math("POWER", radius, 3.0, x=13, y=-16),
                t.math("POWER", inputs["Drip Radius"], 3.0, x=13, y=-17),
                x=14,
                y=-16,
            ),
            0.0,
            x=15,
            y=-16,
        ),
        1.0 / 3.0,
        x=16,
        y=-16,
    )
    runners = t.store(
        marked.outputs["Geometry"],
        ".wet_radius",
        "FLOAT",
        t.node(
            "GeometryNodeSwitch",
            16,
            -14,
            {"Switch": hanging, "False": radius, "True": left},
        ).outputs[0],
        17,
        1,
    )
    runners = t.store(
        runners,
        ".wet_dripped",
        "FLOAT",
        t.node(
            "GeometryNodeSwitch",
            17,
            -14,
            {
                "Switch": hanging,
                "False": t.attribute(".wet_dripped", "FLOAT", 16, -15),
                "True": seconds,
            },
        ).outputs[0],
        18,
        1,
    )

    # A trail point left behind every few radii, the water left shrinking it
    travel = t.math("ADD", t.attribute(".wet_travel", "FLOAT", 13, -12), step, x=14, y=-12)
    deposit = t.math(
        "GREATER_THAN",
        travel,
        t.math("MULTIPLY", radius, TRAIL_SPACING, x=14, y=-13),
        x=15,
        y=-12,
    )
    state = t.node("GeometryNodeCaptureAttribute", 15, 0, {"Geometry": runners})
    for data_type, name, value in (
        ("VECTOR", "Moved", moved),
        ("FLOAT", "Speed", speed),
        ("FLOAT", "Travel", travel),
        ("FLOAT", "Deposit", deposit),
        ("INT", "Index", t.node("GeometryNodeInputIndex", 14, -14).outputs[0]),
    ):
        state.capture_items.new(data_type, name)
        t.connect(value, state.inputs[name])
    state = state.outputs
    left = t.node(
        "GeometryNodeDeleteGeometry",
        16,
        -3,
        {
            "Geometry": state["Geometry"],
            "Selection": t.math("LESS_THAN", state["Deposit"], 0.5, x=16, y=-4),
        },
    ).outputs[0]
    size = t.node("ShaderNodeTexWhiteNoise", 16, -5, {"Vector": position}).outputs["Value"]
    size = t.math("MULTIPLY_ADD", size, 0.8, 0.6, x=17, y=-5)
    size = t.math("MULTIPLY", t.math("MULTIPLY", size, radius, x=18, y=-5), TRAIL_SIZE, x=19, y=-5)
    size = t.math(
        "MULTIPLY", size, t.math("MULTIPLY", inputs["Trail"], 2.0, x=18, y=-6), x=20, y=-5
    )
    left = t.store(left, ".wet_radius", "FLOAT", size, 20, -3)
    left = t.store(left, ".wet_time", "FLOAT", seconds, 21, -3)
    joined = t.node("GeometryNodeJoinGeometry", 22, -1)
    for points in (origins, left, trail):
        t.connect(points, joined.inputs[0])
    # Dried
    age = t.math("SUBTRACT", seconds, t.attribute(".wet_time", "FLOAT", 22, -3), x=23, y=-3)
    trail = t.node(
        "GeometryNodeDeleteGeometry",
        23,
        -1,
        {
            "Geometry": joined.outputs[0],
            # Once faded, and not needed by the drops growing again
            "Selection": t.math(
                "GREATER_THAN",
                age,
                t.math(
                    "MAXIMUM",
                    inputs["Line Life"],
                    t.math("MULTIPLY", inputs["Regrow"], 1.5, x=23, y=-5),
                    x=23,
                    y=-4,
                ),
                x=24,
                y=-3,
            ),
        },
    ).outputs[0]

    loss = t.math("MULTIPLY", state["Deposit"], inputs["Trail"], x=16, y=-1)
    loss = t.math("MULTIPLY_ADD", loss, -TRAIL_LOSS, 1.0, x=17, y=-1)
    # Drying once stopped, over Regrow
    still = t.math("LESS_THAN", state["Speed"], STILL, x=16, y=-2)
    dry = t.math("DIVIDE", t.math("MULTIPLY", still, dt, x=17, y=-2), inputs["Regrow"], x=18, y=-2)
    loss = t.math("MULTIPLY", loss, t.math("SUBTRACT", 1.0, dry, x=19, y=-2), x=19, y=-1)
    # With dripping, the water of the drops on the way taken where trail points are left
    gained = t.node(
        "GeometryNodeSwitch",
        17,
        -6,
        {
            "Switch": inputs["Dripping"],
            "True": absorb(t, inputs, drops, previous, left, state["Index"], 16, -8),
        },
        input_type="GEOMETRY",
    ).outputs[0]
    gained = t.node("GeometryNodeJoinGeometry", 18, 0, {0: gained})
    t.connect(state["Geometry"], gained.inputs[0])
    gain = t.node(
        "GeometryNodeAccumulateField",
        18,
        -7,
        {
            "Value": t.attribute(".wet_gain", "FLOAT", 17, -8),
            "Group ID": t.node(
                "GeometryNodeSwitch",
                17,
                -9,
                {
                    "Switch": t.attribute(".wet_donor", "BOOLEAN", 16, -10),
                    "False": state["Index"],
                    "True": t.attribute(".wet_target", "INT", 16, -11),
                },
                input_type="INT",
            ).outputs[0],
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs["Total"]
    # and of the film under them as they run
    film = t.node(
        "GeometryNodeSampleNearestSurface",
        17,
        -12,
        {"Mesh": at_rest, "Value": captured["Total"]},
        data_type="FLOAT",
    ).outputs["Value"]
    film = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", film, FILM_DEPTH * 2.0, x=18, y=-12),
        t.math("MULTIPLY", radius, state["Speed"], x=18, y=-13),
        x=19,
        y=-12,
    )
    film = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", film, dt, x=20, y=-12),
        inputs["Dripping"],
        x=21,
        y=-12,
    )
    volume = t.math(
        "ADD",
        t.math("POWER", t.math("MULTIPLY", radius, loss, x=18, y=-1), 3.0, x=19, y=-1),
        t.math("ADD", gain, film, x=20, y=-4),
        x=19,
        y=-3,
    )
    # Not much larger than the largest drops, the rest left on the way
    runners = t.store(
        gained.outputs[0],
        ".wet_radius",
        "FLOAT",
        t.math(
            "MINIMUM",
            t.math("POWER", volume, 1.0 / 3.0, x=20, y=-3),
            t.node(
                "GeometryNodeSwitch",
                20,
                -5,
                {
                    "Switch": inputs["Dripping"],
                    "False": 1.0,
                    "True": t.math(
                        "MULTIPLY",
                        t.math(
                            "MAXIMUM",
                            inputs["Max Radius"],
                            t.math("MULTIPLY", inputs["Drip Radius"], HANG, x=18, y=-7),
                            x=19,
                            y=-6,
                        ),
                        MAX_RUN,
                        x=20,
                        y=-6,
                    ),
                },
            ).outputs[0],
            x=21,
            y=-3,
        ),
        19,
        0,
    )
    runners = t.node(
        "GeometryNodeDeleteGeometry",
        19.5,
        0,
        {"Geometry": runners, "Selection": t.attribute(".wet_donor", "BOOLEAN", 19, -4)},
    ).outputs[0]
    runners = t.store(
        runners,
        ".wet_travel",
        "FLOAT",
        t.math(
            "MULTIPLY",
            state["Travel"],
            t.math("SUBTRACT", 1.0, state["Deposit"], x=19, y=-2),
            x=20,
            y=-2,
        ),
        20,
        0,
    )
    runners = t.store(runners, ".wet_speed", "FLOAT", state["Speed"], 21, 0)
    runners = t.node(
        "GeometryNodeSetPosition", 22, 0, {"Geometry": runners, "Position": state["Moved"]}
    ).outputs[0]
    runners = t.node(
        "GeometryNodeDeleteGeometry",
        23,
        0,
        {
            "Geometry": runners,
            "Selection": t.math("LESS_THAN", radius, inputs["Min Radius"], x=23, y=-2),
        },
    ).outputs[0]
    # Falling, landing on the mesh to run again or on the floor
    joined = t.node("GeometryNodeJoinGeometry", 24, 3)
    t.connect(detached, joined.inputs[0])
    t.connect(falling, joined.inputs[0])
    landed, falling = (
        t.node(
            "GeometryNodeSwitch",
            25,
            3 - i,
            {"Switch": inputs["Dripping"], "True": output},
            input_type="GEOMETRY",
        ).outputs[0]
        for i, output in enumerate(
            fall(t, inputs, captured, joined.outputs[0], down, dt, seconds, frame, 24, 6)
        )
    )
    joined = t.node("GeometryNodeJoinGeometry", 25, 0)
    t.connect(landed, joined.inputs[0])
    t.connect(runners, joined.inputs[0])
    t.connect(joined.outputs[0], sim_out.inputs["Geometry"])
    t.connect(trail, sim_out.inputs["Trail"])
    t.connect(falling, sim_out.inputs["Falling"])

    # Not simulated without physics
    return (
        t.node(
            "GeometryNodeSwitch",
            23,
            -i,
            {"Switch": inputs["Physics"], "True": sim_out.outputs[name]},
            input_type="GEOMETRY",
        ).outputs[0]
        for i, name in enumerate(("Geometry", "Trail", "Falling"))
    )


def build_falling(t, inputs, falling, down):
    """Falling drops stretched along their motion, and splashes on the floor drying, as instances"""
    t.section("Falling", row=True)
    seconds = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Seconds"]
    radius = t.attribute(".wet_radius", "FLOAT", 0, -3)
    landed = t.math("GREATER_THAN", t.attribute(".wet_landed", "FLOAT", 0, -4), 0.5, x=1, y=-4)
    velocity = t.attribute(".wet_velocity", "FLOAT_VECTOR", 0, -5)
    split = t.node(
        "GeometryNodeSeparateGeometry", 2, 0, {"Geometry": falling, "Selection": landed}
    ).outputs

    drop = t.node("GeometryNodeMeshUVSphere", 2, -6, {"Segments": 12, "Rings": 6, "Radius": 1.0})
    drop = t.node("GeometryNodeSetShadeSmooth", 3, -6, {"Geometry": drop.outputs["Mesh"]})
    drop = t.node(
        "GeometryNodeSetMaterial",
        4,
        -6,
        {"Geometry": drop.outputs[0], "Material": inputs["Material"]},
    ).outputs[0]
    stretch = t.math(
        "MINIMUM",
        t.math(
            "MULTIPLY_ADD", t.vmath("LENGTH", velocity, x=2, y=-8), FALL_STRETCH, 1.0, x=3, y=-8
        ),
        3.0,
        x=4,
        y=-8,
    )
    drops = t.node(
        "GeometryNodeInstanceOnPoints",
        5,
        -1,
        {
            "Points": split["Inverted"],
            "Instance": drop,
            "Rotation": t.node(
                "FunctionNodeAlignRotationToVector", 4, -9, {"Vector": velocity}, axis="Z"
            ).outputs[0],
            "Scale": t.node(
                "ShaderNodeCombineXYZ",
                4,
                -10,
                {"X": radius, "Y": radius, "Z": t.math("MULTIPLY", radius, stretch, x=3, y=-10)},
            ).outputs[0],
        },
    ).outputs[0]

    # Flat, shrinking from Regrow to twice that
    dry = t.node(
        "ShaderNodeMapRange",
        3,
        -12,
        {
            "Value": t.math(
                "SUBTRACT", seconds, t.attribute(".wet_time", "FLOAT", 2, -13), x=2.5, y=-12
            ),
            "From Min": t.math("MULTIPLY", inputs["Regrow"], 2.0, x=2, y=-14),
            "From Max": inputs["Regrow"],
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    size = t.math("MULTIPLY", t.math("MULTIPLY", radius, SPLASH, x=3, y=-15), dry, x=4, y=-15)
    splash = t.node(
        "GeometryNodeInstanceOnPoints",
        5,
        -3,
        {
            "Points": split["Selection"],
            "Instance": drop,
            "Rotation": t.node(
                "FunctionNodeAlignRotationToVector",
                4,
                -16,
                {"Vector": t.vmath("SCALE", down, -1.0, x=3, y=-16)},
                axis="Z",
            ).outputs[0],
            "Scale": t.node(
                "ShaderNodeCombineXYZ",
                5,
                -15,
                {"X": size, "Y": size, "Z": t.math("MULTIPLY", size, 0.15, x=4, y=-16)},
            ).outputs[0],
        },
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 6, 0)
    t.connect(drops, joined.inputs[0])
    t.connect(splash, joined.inputs[0])
    return joined.outputs[0]


def build_lines(t, inputs, captured, at_rest, runners, trail):
    """Thin lines of water along the trails, up to the running drops, as an instance"""
    t.section("Lines", row=True)
    seconds = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Seconds"]
    heads = t.store(runners, ".wet_time", "FLOAT", t.math("ADD", seconds, 1.0, x=1, y=-2), 1, 0)
    joined = t.node("GeometryNodeJoinGeometry", 2, 0)
    t.connect(heads, joined.inputs[0])
    t.connect(trail, joined.inputs[0])
    lines = t.node(
        "GeometryNodePointsToCurves",
        3,
        0,
        {
            "Points": joined.outputs[0],
            "Curve Group ID": t.attribute(".wet_id", "INT", 2, -2),
            "Weight": t.attribute(".wet_time", "FLOAT", 2, -3),
        },
    ).outputs[0]

    # On the deformed mesh from their rest position, the profile standing on the surface
    posed, normal = (
        t.node(
            "GeometryNodeSampleNearestSurface",
            3,
            -2 - 2 * i,
            {"Mesh": at_rest, "Value": captured[name]},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, name in enumerate(("Posed", "Normal"))
    )
    lines = t.node(
        "GeometryNodeSetCurveNormal",
        4,
        0,
        {"Curve": lines, "Mode": "Free", "Normal": t.vmath("NORMALIZE", normal, x=4, y=-4)},
    ).outputs[0]
    lines = t.node("GeometryNodeSetPosition", 5, 0, {"Geometry": lines, "Position": posed})
    lines = t.node(
        "GeometryNodeCurveSplineType", 6, 0, {"Curve": lines.outputs[0]}, spline_type="CATMULL_ROM"
    ).outputs[0]
    lines = t.node(
        "GeometryNodeSetSplineResolution", 7, 0, {"Geometry": lines, "Resolution": 2}
    ).outputs[0]
    profile = t.node(
        "GeometryNodeCurveArc",
        6,
        -3,
        {"Resolution": 4, "Radius": 1.0, "Start Angle": -math.pi / 2, "Sweep Angle": math.pi},
        mode="RADIUS",
    ).outputs["Curve"]
    profile = t.node(
        "GeometryNodeTransform",
        7,
        -3,
        {
            "Geometry": profile,
            "Scale": t.node(
                "ShaderNodeCombineXYZ",
                6,
                -5,
                {
                    "X": t.math("MULTIPLY", inputs["Height"], LINE_HEIGHT, x=5, y=-5),
                    "Y": 1.0,
                    "Z": 1.0,
                },
            ).outputs[0],
        },
    ).outputs[0]
    lines = t.node(
        "GeometryNodeCurveToMesh",
        8,
        0,
        {
            "Curve": lines,
            "Profile Curve": profile,
            "Scale": t.math(
                "MULTIPLY",
                t.attribute(".wet_radius", "FLOAT", 7, -1),
                t.node(
                    "ShaderNodeMapRange",
                    7,
                    -2,
                    {
                        "Value": t.math(
                            "SUBTRACT",
                            seconds,
                            t.attribute(".wet_time", "FLOAT", 6, -2),
                            x=6.5,
                            y=-2,
                        ),
                        "From Min": inputs["Line Life"],
                        "From Max": t.math("MULTIPLY", inputs["Line Life"], 0.5, x=6, y=-6),
                    },
                    interpolation_type="SMOOTHSTEP",
                ).outputs[0],
                x=7.5,
                y=-1,
            ),
        },
    ).outputs[0]
    lines = t.node("GeometryNodeSetShadeSmooth", 9, 0, {"Geometry": lines}).outputs[0]
    lines = t.store(lines, "wet_line", "FLOAT", 1.0, 9.5, 0)
    lines = t.node(
        "GeometryNodeSetMaterial", 10, 0, {"Geometry": lines, "Material": inputs["Material"]}
    ).outputs[0]
    return t.node("GeometryNodeGeometryToInstance", 11, 0, {0: lines}).outputs[0]


def build_mist():
    """Height of tiny drops in the cells of a Voronoi texture, some of them empty"""
    ng = bpy.data.node_groups.new(MIST, "ShaderNodeTree")
    add_input(ng, "Vector", "NodeSocketVector", hide_value=True)
    add_input(ng, "Scale", "NodeSocketFloat", default_value=500.0)
    add_input(ng, "Size", "NodeSocketFloat", default_value=0.35)
    add_input(ng, "Amount", "NodeSocketFloat", default_value=0.5)
    add_output(ng, "Height", "NodeSocketFloat")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    voronoi = t.node(
        "ShaderNodeTexVoronoi", 1, 0, {"Vector": inputs["Vector"], "Scale": inputs["Scale"]}
    ).outputs
    random = t.node("ShaderNodeSeparateColor", 2, -2, {0: voronoi["Color"]}).outputs
    # Mostly small, a few up to the full size
    radius = t.math("MULTIPLY", random["Red"], random["Red"], x=2.5, y=-1)
    radius = t.math("MULTIPLY_ADD", radius, 1.0 - MIST_SMALLEST, MIST_SMALLEST, x=3, y=-1)
    radius = t.math("MULTIPLY", radius, inputs["Size"], x=4, y=-1)
    # Dome over each drop, in meters
    inside = t.math("DIVIDE", voronoi["Distance"], radius, x=5, y=0)
    inside = t.math(
        "MULTIPLY_ADD", inside, t.math("MULTIPLY", inside, -1.0, x=5, y=1), 1.0, x=6, y=0
    )
    height = t.math("SQRT", t.math("MAXIMUM", inside, 0.0, x=7, y=0), x=8, y=0)
    height = t.math("MULTIPLY", height, radius, x=9, y=0)
    height = t.math("DIVIDE", height, inputs["Scale"], x=10, y=0)
    present = t.math("LESS_THAN", random["Green"], inputs["Amount"], x=9, y=-2)
    height = t.math("MULTIPLY", height, present, x=11, y=0)
    t.node("NodeGroupOutput", 12, 0, {"Height": height})
    return ng


def build_film(mist):
    """The shader under a glossy wet film with tiny drops, darker, by the wetness attribute"""
    ng = bpy.data.node_groups.new(FILM, "ShaderNodeTree")
    add_input(ng, "Shader", "NodeSocketShader")
    add_input(
        ng,
        "Normal",
        "NodeSocketVector",
        hide_value=True,
        description="Normal of the surface under the film, from its normal map",
    )
    add_input(
        ng,
        "Roughness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.15,
        min_value=0.0,
        max_value=1.0,
        description="Roughness of the wet film",
    )
    add_input(
        ng,
        "Darken",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Darkening of the wet surface, higher for cloth",
    )
    add_input(
        ng,
        "Mist",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.8,
        min_value=0.0,
        max_value=1.0,
        description="Amount of tiny drops in the film",
    )
    add_input(
        ng,
        "Mist Scale",
        "NodeSocketFloat",
        default_value=500.0,
        min_value=0.0,
        description="Number of tiny drops per meter",
    )
    add_input(
        ng,
        "Mist Size",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.35,
        min_value=0.0,
        max_value=0.5,
        description="Size of the tiny drops, relative to their spacing",
    )
    add_input(
        ng,
        "Mist Patches",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        description="Tiny drops gathered in patches, fewer between them",
    )
    add_input(
        ng,
        "Variation",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Glossier and duller patches of the film",
    )
    add_input(
        ng,
        "Streaks",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="Glossier streaks running down, along the vertical of the rest pose",
    )
    add_input(
        ng,
        "Ripples",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.1,
        min_value=0.0,
        max_value=1.0,
        description="Uneven thickness of the film, rippling its reflections",
    )
    add_input(
        ng,
        "Bump",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.1,
        min_value=0.0,
        max_value=1.0,
        description="Relief of the water, raised in sheets and pools whose edges catch the light",
    )
    add_input(
        ng,
        "Sparkle",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Fine variation of the film roughness, breaking its sheen into glints",
    )
    add_input(
        ng,
        "Shine",
        "NodeSocketFloat",
        default_value=1.2,
        min_value=0.0,
        max_value=5.0,
        description="Strength of the film reflections, 1 for clear water",
    )
    add_input(
        ng,
        "Coverage",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        description="Share of the wet surface under a glossy film, the rest only damp",
    )
    add_input(
        ng,
        "Patch Scale",
        "NodeSocketFloat",
        default_value=25.0,
        min_value=0.0,
        description="Number of glossy and damp patches per meter",
    )
    add_output(ng, "Shader", "NodeSocketShader")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    # Rest position and wetness, stored by the Wet modifier
    wet = t.node(
        "ShaderNodeAttribute", 1, 2, attribute_type="GEOMETRY", attribute_name="wet"
    ).outputs
    wetness, rest = wet["Alpha"], wet["Vector"]

    # Glossy patches of film, thicker in pools, and damp skin around them
    cover = t.node(
        "ShaderNodeTexNoise",
        1,
        6,
        {
            "Vector": rest,
            "Scale": inputs["Patch Scale"],
            "Detail": 6.0,
            "Roughness": 0.65,
            "Distortion": 0.4,
        },
    ).outputs["Fac"]
    edge = t.math("MULTIPLY_ADD", inputs["Coverage"], -0.5, 0.75, x=1, y=4)
    film = t.node(
        "ShaderNodeMapRange",
        2,
        5,
        {
            "Value": cover,
            "From Min": t.math("SUBTRACT", edge, FILM_EDGE, x=2, y=4),
            "From Max": t.math("ADD", edge, FILM_EDGE, x=2, y=3),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    streaks = t.node(
        "ShaderNodeTexNoise",
        1,
        9,
        {"Vector": t.vmath("MULTIPLY", rest, STREAK, x=0, y=9), "Scale": 1.0, "Detail": 2.0},
    ).outputs["Fac"]
    streaks = t.node(
        "ShaderNodeMapRange",
        2,
        9,
        {"Value": streaks, "From Min": 0.55, "From Max": 0.7},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Water running down in the streaks
    streaks = t.math("MULTIPLY", streaks, inputs["Streaks"], x=3, y=9)
    film = t.math("MAXIMUM", film, streaks, x=3, y=5)
    pools = t.node(
        "ShaderNodeTexNoise",
        2,
        7,
        {"Vector": rest, "Scale": t.math("MULTIPLY", inputs["Patch Scale"], 0.4, x=1, y=8)},
    ).outputs["Fac"]
    pools = t.node(
        "ShaderNodeMapRange",
        3,
        7,
        {"Value": pools, "From Min": 0.4, "From Max": 0.7},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    thick = t.math("MULTIPLY", film, pools, x=4, y=6)

    # Three sizes of tiny drops, fewer where drier
    patches = t.node(
        "ShaderNodeTexNoise", 1, -7, {"Vector": rest, "Scale": CLUSTER, "Detail": 2.0}
    ).outputs["Fac"]
    patches = t.node(
        "ShaderNodeMapRange",
        2,
        -7,
        {"Value": patches, "From Min": 0.4, "From Max": 0.65},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    patches = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", patches, 1.0, x=3, y=-7),
        inputs["Mist Patches"],
        1.0,
        x=4,
        y=-7,
    )
    amount = t.math("MULTIPLY", inputs["Mist"], wetness, x=2, y=-5)
    amount = t.math("MULTIPLY", amount, patches, x=3, y=-6)
    amount = t.math(
        "MULTIPLY",
        amount,
        t.math("MULTIPLY_ADD", film, 1.0 - DAMP_MIST, DAMP_MIST, x=3, y=-8),
        x=4,
        y=-6,
    )
    height, *layers = (
        t.node(
            "ShaderNodeGroup",
            3,
            -3 - i,
            {
                0: rest,
                1: t.math("MULTIPLY", inputs["Mist Scale"], scale, x=2.5, y=-3 - i),
                2: inputs["Mist Size"],
                3: t.math("MULTIPLY", amount, share, x=2.5, y=-3.5 - i),
            },
            node_tree=mist,
        ).outputs[0]
        for i, (scale, share) in enumerate(MIST_LAYERS)
    )
    for i, layer in enumerate(layers):
        height = t.math("MAXIMUM", height, layer, x=4 + 0.2 * i, y=-4)
    # The tiny drops smooth, their small glints not to blur away
    in_drop = t.math("GREATER_THAN", height, 0.0, x=5, y=-6)
    # On a film of uneven thickness
    ripples = t.node(
        "ShaderNodeTexNoise",
        3,
        -10,
        {"Vector": rest, "Scale": RIPPLE, "Detail": 4.0, "Roughness": 0.6},
    ).outputs["Fac"]
    ripples = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", ripples, 0.5, x=4, y=-10),
        t.math(
            "MULTIPLY",
            inputs["Ripples"],
            t.math(
                "MULTIPLY",
                t.math("MULTIPLY", wetness, RIPPLE_HEIGHT, x=2, y=-12),
                t.math("ADD", thick, 0.3, x=2, y=-13),
                x=3,
                y=-12,
            ),
            x=4,
            y=-11,
        ),
        x=5,
        y=-10,
    )
    height = t.math("ADD", height, ripples, x=5, y=-5)
    # Raised in sheets, swelling and thicker in the pools
    swell = t.node(
        "ShaderNodeTexNoise",
        3,
        -16,
        {"Vector": rest, "Scale": SWELL, "Detail": 2.0, "Distortion": 0.5},
    ).outputs["Fac"]
    relief = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", film, swell, x=4, y=-15),
        2.0 * SHEET,
        t.math("MULTIPLY", thick, POOL, x=4, y=-16),
        x=5,
        y=-15,
    )
    relief = t.math(
        "MULTIPLY",
        relief,
        t.math("MULTIPLY", inputs["Bump"], wetness, x=5, y=-16),
        x=6,
        y=-15,
    )
    height = t.math("ADD", height, relief, x=6, y=-5)
    # The normal of the surface, or of the mesh without one
    surface = inputs["Normal"]
    linked = t.math("GREATER_THAN", t.vmath("LENGTH", surface, x=3, y=-8), 0.5, x=4, y=-8)
    surface = t.node(
        "ShaderNodeMix",
        5,
        -8,
        {
            "Factor": linked,
            "A": t.node("ShaderNodeNewGeometry", 4, -9).outputs["Normal"],
            "B": surface,
        },
        data_type="VECTOR",
    ).outputs[1]
    # Smoothed by the water filling the pores where thick
    surface = t.node(
        "ShaderNodeMix",
        5.5,
        -8,
        {
            "Factor": t.math("MULTIPLY", thick, FILL, x=5, y=-9),
            "A": surface,
            "B": t.node("ShaderNodeNewGeometry", 5, -10).outputs["Normal"],
        },
        data_type="VECTOR",
    ).outputs[1]
    # The height in meters, not scaled down by the default Distance
    normal = t.node(
        "ShaderNodeBump", 5, -4, {"Distance": 1.0, "Height": height, "Normal": surface}
    ).outputs[0]
    roughness = t.node(
        "ShaderNodeMix", 5, -6, {"Factor": film, "A": DAMP_ROUGHNESS, "B": inputs["Roughness"]}
    ).outputs[0]
    film_roughness = roughness
    roughness = t.math(
        "MULTIPLY", roughness, t.math("SUBTRACT", 1.0, in_drop, x=6, y=-6), x=6, y=-5
    )
    # Glinting where smoother
    sparkle = t.node(
        "ShaderNodeTexNoise", 5, -12, {"Vector": rest, "Scale": SPARKLE, "Detail": 2.0}
    ).outputs["Fac"]
    sparkle = t.node(
        "ShaderNodeMapRange",
        6,
        -12,
        {"Value": sparkle, "From Min": 0.55, "From Max": 0.7},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    sparkle = t.math("MULTIPLY", sparkle, inputs["Sparkle"], x=7, y=-12)
    roughness = t.math(
        "MULTIPLY", roughness, t.math("SUBTRACT", 1.0, sparkle, x=7.5, y=-12), x=7, y=-5
    )

    # Glossier patches and streaks, smoother and stronger
    variation = t.node(
        "ShaderNodeTexNoise", 1, -9, {"Vector": rest, "Scale": 6.0, "Detail": 4.0}
    ).outputs["Fac"]
    variation = t.math(
        "MULTIPLY",
        t.math("MULTIPLY_ADD", variation, 2.0, -1.0, x=2, y=-9),
        inputs["Variation"],
        x=3,
        y=-9,
    )
    gloss = t.math("ADD", variation, streaks, x=5, y=-10)
    roughness = t.math(
        "MULTIPLY", roughness, t.math("SUBTRACT", 1.0, gloss, x=6, y=-8, clamp=True), x=7, y=-6
    )

    # Darker under the film, a black emission scaling the shader
    black = t.node("ShaderNodeEmission", 5, 1, {"Color": (0.0, 0.0, 0.0, 1.0), "Strength": 0.0})
    # Darker in the glossier patches and streaks, the water thicker there
    darken = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Darken"], wetness, x=5, y=2),
        t.math("ADD", gloss, 1.0, x=5, y=3),
        x=5.5,
        y=2,
        clamp=True,
    )
    shader = t.node(
        "ShaderNodeMixShader", 6, 0, {0: darken, 1: inputs["Shader"], 2: black.outputs[0]}
    ).outputs[0]
    # Fresnel of water, lower at grazing angles where rougher, on the smooth normal not to
    # outline the edges with the tiny drops
    facing = t.node("ShaderNodeLayerWeight", 6, -4, {"Blend": 0.5, "Normal": surface}).outputs[
        "Facing"
    ]
    edge = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", 1.0, film_roughness, x=6, y=-6),
        EDGE_FRESNEL,
        x=6.5,
        y=-6,
    )
    fresnel = t.math(
        "MULTIPLY_ADD",
        t.math("POWER", facing, 5.0, x=6.5, y=-4),
        t.math("SUBTRACT", t.math("MAXIMUM", edge, WATER_F0, x=7, y=-6), WATER_F0, x=7, y=-5),
        WATER_F0,
        x=7,
        y=-4,
    )
    wet = t.math(
        "MULTIPLY",
        wetness,
        t.math("MULTIPLY_ADD", film, 1.0 - DAMP_COAT, DAMP_COAT, x=7, y=-7),
        x=7.5,
        y=-7,
    )
    coat = t.math("MULTIPLY", fresnel, wet, x=7.5, y=-3)
    # The surface under the film dimmed by the reflected light, never hidden at grazing angles
    shader = t.node(
        "ShaderNodeMixShader",
        8,
        0,
        {
            0: t.math(
                "MINIMUM",
                t.math(
                    "MULTIPLY",
                    coat,
                    t.math("MINIMUM", inputs["Shine"], 1.0, x=7.5, y=-2),
                    x=7.8,
                    y=-1,
                ),
                MAX_COVER,
                x=8,
                y=-1,
            ),
            1: shader,
            2: black.outputs[0],
        },
    ).outputs[0]
    # The reflection added, Shine and the glossier parts raising it where seen face on
    boost = t.math(
        "SUBTRACT",
        t.math("MULTIPLY", inputs["Shine"], t.math("ADD", gloss, 1.0, x=7, y=-9), x=7.5, y=-9),
        1.0,
        x=8,
        y=-9,
    )
    reflection = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", wet, WATER_F0, x=8, y=-8),
        boost,
        t.math("MULTIPLY", coat, t.math("MINIMUM", inputs["Shine"], 1.0, x=7.5, y=-10), x=8, y=-10),
        x=8.5,
        y=-4,
        clamp=True,
    )
    # Brighter in the tiny drops, gathering the light like the refracting ones, and in the glints
    reflection = t.math(
        "MULTIPLY",
        reflection,
        t.math(
            "MULTIPLY_ADD",
            t.math("MAXIMUM", in_drop, sparkle, x=8.2, y=-6),
            DROP_SHINE - 1.0,
            1.0,
            x=8.5,
            y=-6,
        ),
        x=8.8,
        y=-4,
        clamp=True,
    )
    glossy = t.node(
        "ShaderNodeBsdfGlossy",
        9,
        -2,
        {
            "Color": t.node(
                "ShaderNodeCombineColor",
                8.5,
                -5,
                {"Red": reflection, "Green": reflection, "Blue": reflection},
            ).outputs[0],
            "Roughness": roughness,
            "Normal": normal,
        },
    ).outputs[0]
    shader = t.node("ShaderNodeAddShader", 10, 0, {0: shader, 1: glossy}).outputs[0]
    t.node("NodeGroupOutput", 11, 0, {"Shader": shader})
    return ng


def build_material():
    """Clear water, letting the light through to the surface under it without caustics"""
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    material.use_transparent_shadow = True
    t = Tree(material.node_tree)
    water = t.node(
        "ShaderNodeBsdfPrincipled",
        0,
        0,
        {
            "Base Color": (1.0, 1.0, 1.0, 1.0),
            "Roughness": 0.02,
            "IOR": 1.33,
            "Transmission Weight": 1.0,
        },
    ).outputs[0]
    # In Cycles reflecting the surroundings on the rim, as the light inside is reflected back there
    # but on the flat lines of water
    facing = t.node("ShaderNodeLayerWeight", -1, -3).outputs["Facing"]
    drop = t.math(
        "SUBTRACT",
        1.0,
        t.node(
            "ShaderNodeAttribute", -2, -5, attribute_type="GEOMETRY", attribute_name="wet_line"
        ).outputs["Fac"],
        x=-1,
        y=-5,
    )
    rim = t.node(
        "ShaderNodeMapRange",
        0,
        -3,
        {"Value": facing, "From Min": 0.5, "From Max": 0.8},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    rim = t.math("MULTIPLY", rim, drop, x=0.5, y=-3)
    mirror = t.node(
        "ShaderNodeBsdfGlossy", 0, -4, {"Color": (1.0, 1.0, 1.0, 1.0), "Roughness": 0.02}
    ).outputs[0]
    water = t.node("ShaderNodeMixShader", 1, -1, {0: rim, 1: water, 2: mirror}).outputs[0]
    # Transparent to the light and the bounces of the surface under it, lit once
    # but for a ring around the light passing through its center, as when refracted
    path = t.node("ShaderNodeLightPath", -1, 2).outputs
    lit = t.node(
        "ShaderNodeMapRange",
        0,
        3,
        {"Value": facing, "From Min": 0.6, "From Max": 0.3},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    lit = t.math("MAXIMUM", lit, t.math("SUBTRACT", 1.0, drop, x=0.5, y=4), x=0.8, y=3)
    lit = t.math("MULTIPLY", path["Is Shadow Ray"], lit, x=1, y=3)
    through = t.math("MAXIMUM", lit, path["Is Diffuse Ray"], x=1, y=2)
    transparent = t.node("ShaderNodeBsdfTransparent", 0, -2).outputs[0]
    # The lines a thin film, reflecting without refraction
    film = t.node(
        "ShaderNodeMixShader",
        1,
        -6,
        {
            0: t.node("ShaderNodeFresnel", 0, -6, {"IOR": 1.33}).outputs[0],
            1: transparent,
            2: mirror,
        },
    ).outputs[0]
    water = t.node("ShaderNodeMixShader", 1.5, -1, {0: drop, 1: film, 2: water}).outputs[0]
    surface = t.node("ShaderNodeMixShader", 1, 0, {0: through, 1: water, 2: transparent})
    t.node("ShaderNodeOutputMaterial", 2, 0, {"Surface": surface.outputs[0]}, target="CYCLES")
    # EEVEE showing the surface under the drops, darker on the rim refracting it from around, as
    # its refraction shows the world where the rays miss the screen, black in dark scenes
    see = t.node(
        "ShaderNodeBsdfTransparent",
        0,
        4,
        {
            "Color": t.node(
                "ShaderNodeMapRange",
                -0.5,
                5,
                {
                    "Value": facing,
                    "From Min": 0.5,
                    "From Max": 0.9,
                    "To Min": 1.0,
                    "To Max": 1.0 - DROP_RING,
                },
                interpolation_type="SMOOTHSTEP",
            ).outputs[0]
        },
    ).outputs[0]
    clear = t.node(
        "ShaderNodeMixShader",
        1,
        4,
        {0: t.node("ShaderNodeFresnel", 0, 5, {"IOR": 1.33}).outputs[0], 1: see, 2: mirror},
    ).outputs[0]
    water = t.node("ShaderNodeMixShader", 1.5, 2, {0: drop, 1: film, 2: clear}).outputs[0]
    surface = t.node(
        "ShaderNodeMixShader",
        2,
        2,
        {0: path["Is Shadow Ray"], 1: water, 2: transparent},
    )
    t.node("ShaderNodeOutputMaterial", 3, 2, {"Surface": surface.outputs[0]}, target="EEVEE")
    return material


if __name__ == "__main__":
    write(
        RESOURCE, (build_node_group(), build_film(build_mist()), build_material()), fake_user=True
    )
