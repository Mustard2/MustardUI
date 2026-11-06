# Build footprints.blend: the Footprints node group and the Footprints Film shader group
# Usage: Blender --background --factory-startup --python footprints_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write
from imprints_build import MATCH, OUTSIDE, build_lasting, in_box, refine
from wet_build import build_film, build_mist

RESOURCE = "footprints.blend"
NODE_GROUP = "MustardUI Footprints"
FILM = "MustardUI Footprints Film"
MIST = "MustardUI Footprints Mist"
# Depth under the surface the Colliders are looked for, relative to the Contact
REACH = 25.0
# Height the Colliders leave the surface at, relative to the Contact, not to step again hovering
RELEASE = 2.0
# Height of the Colliders off the surface past its edges
FAR = 1000.0
# Water over the patch threshold the prints are fully wet at, blur iterations of the wetness
# smoothing their outline over the faces, and its width sharpened by the shader
EDGE = 0.1
BLUR = 2
OUTLINE = 0.1
# Ragged border of the Puddle, relative to the Control radius, and the points across it the mesh
# is subdivided around at most
PUDDLE_EDGE = 0.15
PUDDLE_POINTS = 300
# Wetness from the half of the puddle border the mesh is subdivided within
PUDDLE_BAND = 0.4
# Bays and capes along the border of the Puddle
PUDDLE_WIGGLE = 1.5


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Wet prints of the Colliders stepping on the mesh, fainter at each step and drying, "
        "storing the footprint attribute read by the Footprints Film shader"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects leaving the prints, e.g. the body and the shoes",
    )
    add_input(
        ng,
        "Wetness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Wetness of the Colliders, animate it to wet or dry them",
    )
    add_input(
        ng,
        "Steps",
        "NodeSocketFloat",
        default_value=6.0,
        min_value=0.0,
        description="Steps the Colliders leave prints for, each fainter, 0 to leave them as wet "
        "at every step",
    )
    add_input(
        ng,
        "Drying",
        "NodeSocketFloat",
        default_value=30.0,
        min_value=0.0,
        description="Seconds for the wettest prints to dry, 0 to keep them",
    )
    add_input(
        ng,
        "Contact",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.01,
        min_value=0.0001,
        description="Distance off the surface the Colliders touch it within, as soft soles do",
    )
    add_input(
        ng,
        "Patches",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        description="Prints breaking into patches as they get drier",
    )
    add_input(
        ng,
        "Patch Scale",
        "NodeSocketFloat",
        default_value=40.0,
        min_value=0.0,
        description="Number of patches per meter",
    )
    add_input(
        ng,
        "Subdivisions",
        "NodeSocketInt",
        default_value=0,
        min_value=0,
        max_value=16,
        description="Subdivisions of the mesh near the Colliders and the prints",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    add_input(
        ng,
        "Puddle",
        "NodeSocketBool",
        default_value=False,
        description="Wet the surface inside the sphere of the Control, wetting again the "
        "Colliders stepping in it",
    )
    add_input(ng, "Control", "NodeSocketObject", description="Empty with the puddle in its sphere")
    arrange_interface(ng, [(None, "Puddle", False, "Puddle", ["Control"])])

    t = Tree(ng)
    t.section("Colliders")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    # Only the mesh, not the drops of a Wet before, the other components joined back as they are
    components = t.node("GeometryNodeSeparateComponents", -1, 1, {0: inputs["Geometry"]}).outputs
    self_object = t.node("GeometryNodeSelfObject", -2, -2).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -1, -2, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", 0, -2, {0: to_world}).outputs[0]
    position = t.node("GeometryNodeInputPosition", 0, -3).outputs[0]
    world = t.node(
        "FunctionNodeTransformPoint", 1, -3, {"Vector": position, "Transform": to_world}
    ).outputs[0]
    # Normals by the inverse transpose, the mesh being scaled unevenly
    normal = t.node(
        "FunctionNodeTransformDirection",
        2,
        -4,
        {
            "Direction": t.node("GeometryNodeInputNormal", 1, -4).outputs["Normal"],
            "Transform": t.node("FunctionNodeTransposeMatrix", 1, -5, {0: to_local}).outputs[0],
        },
    ).outputs[0]
    normal = t.vmath("NORMALIZE", normal, x=3, y=-4)
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        0,
        -7,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", 1, -7, {"Geometry": colliders}).outputs[0]
    colliders = t.node(
        "GeometryNodeTransform",
        2,
        -7,
        {"Geometry": colliders, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    mesh = t.node(
        "GeometryNodeTransform",
        2,
        -11,
        {"Geometry": components["Mesh"], "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    reach = t.math("MULTIPLY", inputs["Contact"], REACH, x=3, y=-12)
    release = t.math("MULTIPLY", inputs["Contact"], RELEASE, x=3, y=-13)

    t.section("Contact", row=True)
    # Height of the Collider points over the nearest face of the surface, far past its edges
    near = t.node(
        "GeometryNodeProximity",
        1,
        -2,
        {"Geometry": mesh, "Sample Position": position},
        target_element="FACES",
    ).outputs
    up = t.node(
        "GeometryNodeSampleNearestSurface",
        1,
        -4,
        {
            "Mesh": mesh,
            "Value": t.node("GeometryNodeInputNormal", 0, -5).outputs["Normal"],
            "Sample Position": position,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    offset = t.vmath("SUBTRACT", position, near["Position"], x=2, y=-2)
    height = t.vmath("DOT_PRODUCT", offset, up, x=3, y=-2)
    aside = t.vmath(
        "LENGTH",
        t.vmath("SUBTRACT", offset, t.vmath("SCALE", up, height, x=3, y=-4), x=4, y=-4),
        x=5,
        y=-4,
    )
    over = t.math(
        "MULTIPLY",
        near["Is Valid"],
        t.math("LESS_THAN", aside, inputs["Contact"], x=6, y=-4),
        x=7,
        y=-4,
    )
    height = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", 1.0, over, x=7, y=-3), FAR, height, x=8, y=-2
    )
    colliders = t.store(colliders, ".footprint_height", "FLOAT", height, 9, 0)
    # Box of the Collider points near the surface, far away without them
    low = t.math("LESS_THAN", t.attribute(".footprint_height", "FLOAT", 9, -8), release, x=10, y=-8)
    soles = t.node(
        "GeometryNodeAttributeStatistic",
        11,
        -8,
        {"Geometry": colliders, "Selection": low, "Attribute": position},
        data_type="FLOAT_VECTOR",
    ).outputs
    count = t.node(
        "GeometryNodeAttributeStatistic",
        11,
        -11,
        {"Geometry": colliders, "Selection": low, "Attribute": 1.0},
    ).outputs["Sum"]
    box = {
        key: t.node(
            "GeometryNodeSwitch",
            12,
            -8 - i,
            {"Switch": count, "False": (FAR, FAR, FAR), "True": soles[key]},
            input_type="VECTOR",
        ).outputs[0]
        for i, key in enumerate(("Min", "Max"))
    }
    colliders = t.store(
        colliders, ".footprint_puddle", "FLOAT", puddle(t, inputs, position, 8, -6), 10, 0
    )

    t.section("Steps", row=True)
    # Water used by each Collider point stepping, kept for the points that stepped
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    sim_in = t.node("GeometryNodeSimulationInput", 1, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 12, 0)
    sim_in.pair_with_output(sim_out)
    state = t.node(
        "GeometryNodeSwitch",
        2,
        0,
        {"Switch": started, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 2, -3).outputs[0]
    points = t.node(
        "GeometryNodePoints",
        3,
        -1,
        {
            "Count": t.node("GeometryNodeAttributeDomainSize", 2, -1, {0: colliders}).outputs[0],
            "Position": t.node("ShaderNodeCombineXYZ", 2.5, -3, {"X": index}).outputs[0],
        },
    ).outputs[0]
    key = t.node("GeometryNodeInputPosition", 3, -5).outputs[0]
    dry, touched = keyed(t, state, key, (".footprint_dry", ".footprint_touch"), 4, -5)

    def collider(name, y):
        return t.node(
            "GeometryNodeSampleIndex",
            5,
            y,
            {
                "Geometry": colliders,
                "Value": t.attribute(name, "FLOAT", 4.5, y - 1),
                "Index": index,
            },
            data_type="FLOAT",
        ).outputs[0]

    height = collider(".footprint_height", -9)
    # Down within the Contact, up past the release height, not deeper than the reach
    touch = t.math(
        "MAXIMUM",
        t.math("LESS_THAN", height, inputs["Contact"], x=6, y=-9),
        t.math(
            "MULTIPLY",
            touched,
            t.math("LESS_THAN", height, release, x=6, y=-10),
            x=6.5,
            y=-10,
        ),
        x=7,
        y=-9,
    )
    touch = t.math(
        "MULTIPLY",
        touch,
        t.math("GREATER_THAN", height, t.math("MULTIPLY", reach, -1.0, x=6, y=-12), x=6.5, y=-12),
        x=7.5,
        y=-9,
    )
    # Wet again in the puddle, drier after each step down
    before = t.math(
        "MINIMUM",
        dry,
        t.math(
            "SUBTRACT",
            1.0,
            t.math("MULTIPLY", collider(".footprint_puddle", -13), touch, x=6, y=-13),
            x=7,
            y=-13,
        ),
        x=8,
        y=-7,
    )
    step = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", touch, t.math("SUBTRACT", 1.0, touched, x=7, y=-11), x=7.5, y=-11),
        t.math("DIVIDE", 1.0, inputs["Steps"], x=7.5, y=-12),
        x=8,
        y=-11,
    )
    dry = t.math("MINIMUM", t.math("ADD", before, step, x=8.5, y=-8), 1.0, x=9, y=-8)
    for i, (name, value) in enumerate(
        ((".footprint_dry", dry), (".footprint_touch", touch), (".footprint_before", before))
    ):
        points = t.store(points, name, "FLOAT", value, 9.5 + i * 0.5, 0)
    points = t.node(
        "GeometryNodeDeleteGeometry",
        11,
        0,
        {
            "Geometry": points,
            "Selection": t.math(
                "LESS_THAN",
                t.math(
                    "MAXIMUM",
                    t.attribute(".footprint_dry", "FLOAT", 10, -3),
                    t.attribute(".footprint_touch", "FLOAT", 10, -4),
                    x=10.5,
                    y=-3,
                ),
                1e-6,
                x=11,
                y=-3,
            ),
        },
        domain="POINT",
    ).outputs[0]
    t.connect(points, sim_out.inputs["Geometry"])
    # The water of the Collider points before stepping now
    (before,) = keyed(
        t,
        sim_out.outputs["Geometry"],
        t.node(
            "ShaderNodeCombineXYZ",
            12,
            -3,
            {"X": t.node("GeometryNodeInputIndex", 11.5, -3).outputs[0]},
        ).outputs[0],
        (".footprint_before",),
        12.5,
        -3,
    )
    water = t.math(
        "MULTIPLY",
        inputs["Wetness"],
        t.math("SUBTRACT", 1.0, before, x=14, y=-3),
        x=14.5,
        y=-2,
    )
    colliders = t.store(colliders, ".footprint_water", "FLOAT", water, 15, 0)

    t.section("Prints", row=True)
    # Subdivided where the Colliders may step, the same at each frame, without the attributes not
    # to keep them in the simulation
    geometry = refine(
        t,
        t.strip(components["Mesh"], -6, 0),
        inputs["Subdivisions"],
        to_world,
        box,
        release,
        None,
        None,
        0,
        0,
    )
    # Up from under the surface to the lowest Collider surface, only where they cover it
    ray = t.node(
        "GeometryNodeRaycast",
        8,
        -4,
        {
            "Target Geometry": colliders,
            "Attribute": t.attribute(".footprint_water", "FLOAT", 7, -3),
            "Source Position": t.vmath(
                "SUBTRACT", world, t.vmath("SCALE", normal, reach, x=7, y=-5), x=7.5, y=-5
            ),
            "Ray Direction": normal,
            "Ray Length": t.math("ADD", reach, inputs["Contact"], x=7, y=-6),
        },
        data_type="FLOAT",
    ).outputs
    covered = t.node(
        "GeometryNodeRaycast",
        8,
        -8,
        {
            "Target Geometry": colliders,
            "Source Position": world,
            "Ray Direction": normal,
            "Ray Length": OUTSIDE,
        },
    ).outputs["Is Hit"]
    # Wetter where touching closer
    close = t.node(
        "ShaderNodeMapRange",
        9,
        -2,
        {
            "Value": t.math("SUBTRACT", ray["Hit Distance"], reach, x=8.5, y=-2),
            "From Min": 0.0,
            "From Max": inputs["Contact"],
            "To Min": 1.0,
            "To Max": 0.0,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    left = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", close, ray["Attribute"], x=10, y=-2),
        t.math("MULTIPLY", ray["Is Hit"], covered, x=10, y=-4),
        x=11,
        y=-2,
    )
    store = t.node(
        "GeometryNodeStoreNamedAttribute",
        12,
        0,
        {
            "Geometry": geometry,
            "Name": ".imprint_live",
            "Value": left,
            "Selection": in_box(t, box, world, release, 6, -10),
        },
        data_type="FLOAT",
        domain="POINT",
    )

    t.section("Lasting", row=True)
    # The water left, drying by 1 in the Drying
    lasting = {"Start Frame": inputs["Start Frame"], "Depth": 1.0, "Recovery": inputs["Drying"]}
    state = build_lasting(
        t, lasting, store.outputs["Geometry"], t.attribute(".imprint_live", "FLOAT", 0, -4)
    )

    t.section("Subdivision", row=True)
    around = t.node("GeometryNodeJoinGeometry", 2, -2)
    for part in (
        puddle_points(t, inputs, mesh, -2, -6),
        t.node(
            "GeometryNodeTransform",
            1,
            -2,
            {"Geometry": state, "Mode": "Matrix", "Transform": to_world},
        ).outputs[0],
    ):
        t.connect(part, around.inputs[0])
    # Fewer points, as far apart as the faces are subdivided around them
    around = t.node(
        "GeometryNodeMergeByDistance",
        3,
        -2,
        {"Geometry": around.outputs[0], "Distance": inputs["Contact"]},
    ).outputs[0]
    # Around the Colliders, the prints and the puddle, a little past them for the blur
    geometry = refine(
        t,
        components["Mesh"],
        inputs["Subdivisions"],
        to_world,
        box,
        release,
        around,
        inputs["Contact"],
        3,
        0,
    )
    # The water of the state at the same positions
    (water,) = keyed(t, state, position, (".imprint_kept",), 8, -4, MATCH)

    t.section("Wetness", row=True)
    # Drier parts of the patches breaking first, sharp at the edges of the water
    patch = t.node(
        "ShaderNodeTexNoise",
        0,
        -4,
        {"Vector": world, "Scale": inputs["Patch Scale"], "Detail": 2.0},
    ).outputs["Fac"]
    patch = t.node(
        "ShaderNodeMapRange",
        1,
        -4,
        {"Value": patch, "From Min": 0.35, "From Max": 0.65},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Fully wet with all the water
    threshold = t.math(
        "MULTIPLY", patch, t.math("MULTIPLY", inputs["Patches"], 1.0 - EDGE, x=1.5, y=-5), x=2, y=-4
    )
    wet = t.node(
        "ShaderNodeMapRange",
        3,
        -2,
        {
            "Value": water,
            "From Min": threshold,
            "From Max": t.math("ADD", threshold, EDGE, x=2.5, y=-5),
        },
    ).outputs[0]
    wet = t.math("MAXIMUM", wet, puddle(t, inputs, world, 2, -7), x=4, y=-2)
    geometry = t.store(geometry, ".footprint_wet", "FLOAT", wet, 4, 0)
    wet = t.node(
        "GeometryNodeBlurAttribute",
        4.5,
        -2,
        {"Value": t.attribute(".footprint_wet", "FLOAT", 4, -3), "Iterations": BLUR},
        data_type="FLOAT",
    ).outputs[0]
    # World position for the film detail and the dryness, 1 as read by the shaders without it
    xyz = t.node("ShaderNodeSeparateXYZ", 4, -4, {0: world}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        5,
        -2,
        {
            "Red": xyz["X"],
            "Green": xyz["Y"],
            "Blue": xyz["Z"],
            "Alpha": t.math("SUBTRACT", 1.0, wet, x=4.5, y=-2),
        },
    ).outputs[0]
    geometry = t.store(geometry, "footprint", "FLOAT_COLOR", color, 6, 0)
    for i, pattern in enumerate((".imprint_*", ".footprint_*")):
        geometry = t.node(
            "GeometryNodeRemoveAttribute",
            6.5 + i * 0.5,
            0,
            {"Geometry": geometry, "Pattern Mode": "Wildcard", "Name": pattern},
        ).outputs[0]
    output = t.node("GeometryNodeJoinGeometry", 8, 0)
    for name in ("Instances", "Volume", "Point Cloud", "Grease Pencil", "Curve"):
        t.connect(components[name], output.inputs[0])
    t.connect(geometry, output.inputs[0])
    t.node("NodeGroupOutput", 9, 0, {"Geometry": output.outputs[0]})
    t.arrange()
    return ng


def keyed(t, state, key, names, x, y, tolerance=0.5):
    """Values of the state points with the key as position, 0 for the keys not in it"""
    nearest = t.node(
        "GeometryNodeSampleNearest", x, y, {"Geometry": state, "Sample Position": key}
    ).outputs[0]

    def at(value, data_type, row):
        return t.node(
            "GeometryNodeSampleIndex",
            x + 1,
            y - row,
            {"Geometry": state, "Value": value, "Index": nearest},
            data_type=data_type,
        ).outputs[0]

    found = at(t.node("GeometryNodeInputPosition", x + 0.5, y - 1).outputs[0], "FLOAT_VECTOR", 0)
    same = t.math(
        "LESS_THAN", t.vmath("DISTANCE", found, key, x=x + 2, y=y), tolerance, x=x + 2.5, y=y
    )
    return [
        t.math(
            "MULTIPLY",
            at(t.attribute(name, "FLOAT", x + 0.5, y - 2 - i), "FLOAT", 1 + i),
            same,
            x=x + 3,
            y=y - 1 - i,
        )
        for i, name in enumerate(names)
    ]


def puddle_points(t, inputs, mesh, x, y):
    """Points on the mesh in world space covering the puddle, as far apart as the Contact"""
    info = t.node(
        "GeometryNodeObjectInfo", x, y, {"Object": inputs["Control"]}, transform_space="ORIGINAL"
    ).outputs
    size = t.node("ShaderNodeSeparateXYZ", x + 1, y - 2, {0: info["Scale"]}).outputs
    count = t.math(
        "DIVIDE",
        t.math(
            "MULTIPLY",
            t.math("MAXIMUM", size["X"], size["Y"], x=x + 2, y=y - 2),
            2.0 * (1.0 + PUDDLE_EDGE),
            x=x + 3,
            y=y - 2,
        ),
        inputs["Contact"],
        x=x + 4,
        y=y - 2,
    )
    count = t.math(
        "MINIMUM", t.math("CEIL", count, x=x + 5, y=y - 2), PUDDLE_POINTS, x=x + 6, y=y - 2
    )
    grid = t.node(
        "GeometryNodeMeshGrid",
        x + 7,
        y,
        {
            "Size X": 2.0 * (1.0 + PUDDLE_EDGE),
            "Size Y": 2.0 * (1.0 + PUDDLE_EDGE),
            "Vertices X": count,
            "Vertices Y": count,
        },
    ).outputs[0]
    points = t.node(
        "GeometryNodeMeshToPoints",
        x + 8,
        y,
        {
            "Mesh": grid,
            "Selection": t.math(
                "LESS_THAN",
                t.vmath(
                    "LENGTH",
                    t.node("GeometryNodeInputPosition", x + 7, y - 3).outputs[0],
                    x=x + 7.5,
                    y=y - 3,
                ),
                1.0 + PUDDLE_EDGE,
                x=x + 8,
                y=y - 3,
            ),
        },
    ).outputs[0]
    points = t.node(
        "GeometryNodeTransform",
        x + 9,
        y,
        {"Geometry": points, "Mode": "Matrix", "Transform": info["Transform"]},
    ).outputs[0]
    # Onto the mesh, wherever the sphere cuts it
    points = t.node(
        "GeometryNodeSetPosition",
        x + 10,
        y,
        {
            "Geometry": points,
            "Position": t.node(
                "GeometryNodeProximity",
                x + 9,
                y - 2,
                {
                    "Geometry": mesh,
                    "Sample Position": t.node("GeometryNodeInputPosition", x + 8.5, y - 3).outputs[
                        0
                    ],
                },
                target_element="FACES",
            ).outputs["Position"],
        },
    ).outputs[0]
    # Only across its border, the faces inside and out being all wet or dry
    border = puddle(
        t, inputs, t.node("GeometryNodeInputPosition", x + 10, y - 4).outputs[0], x + 10, y - 6
    )
    points = t.node(
        "GeometryNodeDeleteGeometry",
        x + 11,
        y,
        {
            "Geometry": points,
            "Selection": t.math(
                "GREATER_THAN",
                t.math(
                    "ABSOLUTE",
                    t.math("SUBTRACT", border, 0.5, x=x + 15, y=y - 6),
                    x=x + 16,
                    y=y - 6,
                ),
                PUDDLE_BAND,
                x=x + 17,
                y=y - 6,
            ),
        },
        domain="POINT",
    ).outputs[0]
    return t.node(
        "GeometryNodeSwitch",
        x + 11,
        y,
        {"Switch": inputs["Puddle"], "True": points},
        input_type="GEOMETRY",
    ).outputs[0]


def puddle(t, inputs, world, x, y):
    """How far the world position is in the sphere of the Control, with a ragged border"""
    to_control = t.node(
        "FunctionNodeInvertMatrix",
        x + 1,
        y,
        {
            0: t.node(
                "GeometryNodeObjectInfo",
                x,
                y,
                {"Object": inputs["Control"]},
                transform_space="ORIGINAL",
            ).outputs["Transform"]
        },
    ).outputs[0]
    local = t.node(
        "FunctionNodeTransformPoint", x + 2, y, {"Vector": world, "Transform": to_control}
    ).outputs[0]
    distance = t.vmath("LENGTH", local, x=x + 3, y=y)
    # A few bays and capes around it, ragged at smaller scales
    noise = t.node(
        "ShaderNodeTexNoise",
        x + 2,
        y - 2,
        {"Vector": local, "Scale": PUDDLE_WIGGLE, "Detail": 4.0, "Roughness": 0.6},
    ).outputs["Fac"]
    distance = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", noise, 0.5, x=x + 3, y=y - 2),
        PUDDLE_EDGE * 2.0,
        distance,
        x=x + 4,
        y=y,
    )
    inside = t.node(
        "ShaderNodeMapRange",
        x + 5,
        y,
        {"Value": distance, "From Min": 1.0, "From Max": 1.0 - PUDDLE_EDGE},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    return t.math("MULTIPLY", inside, inputs["Puddle"], x=x + 6, y=y)


def build_footprints_film():
    """The Wet film reading the footprint attribute, as on hard floors"""
    film = build_film(build_mist(MIST), FILM, "footprint", OUTLINE)
    for name, value in (("Darken", 0.4), ("Mist", 0.15), ("Sparkle", 0.2), ("Streaks", 0.0)):
        film.interface.items_tree[name].default_value = value
    return film


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_footprints_film()), fake_user=True)
