# Build imprints.blend: the Imprints node group and the Imprints Tint shader group
# Usage: Blender --background --factory-startup --python imprints_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "imprints.blend"
NODE_GROUP = "MustardUI Imprints"
TINT = "MustardUI Imprints Tint"
# Depths below the surface the Colliders are looked for, not to imprint parts far under it
REACH = 3.0
# Distance out of the surface a Collider covering a point is looked for
OUTSIDE = 10.0
# Start of the rays through the mesh, inside it not to hit the faces of the point
SELF_OFFSET = 0.001
# Blur iterations of the rim, at most
RIM_ITERATIONS = 200
# Rounds of the soft imprints spreading them keeping the pressed points as deep, on a copy of
# the mesh merged to a fraction of the Softness, then pushing out of the Colliders the points
# moved into them
SOFT_ROUNDS = 128
COARSE = 12.0
# Blur iterations of the soft imprints back on the mesh, at most
SMOOTH_ITERATIONS = 64
# Fading of the soft imprints away from the pressed points, by round
FADE = 2.0
PUSH_ROUNDS = 2
# Depth of the imprints tinted fully, relative to the Depth
TINT_DEPTH = 0.4
# Depth of the imprints the rim fades out to, relative to the Depth, not to rise inside them
RIM_DEPTH = 0.1


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Imprint the Colliders in the mesh, as in snow, sand or a cushion, storing the "
        "imprint attribute read by the Imprints Tint shader"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects pressing into the mesh, e.g. the body and the shoes",
    )
    add_input(
        ng,
        "Depth",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.05,
        min_value=0.0,
        description="Deepest imprint, as thick as the soft layer",
    )
    add_input(
        ng,
        "Subdivisions",
        "NodeSocketInt",
        default_value=0,
        min_value=0,
        max_value=8,
        description="Subdivisions of the mesh before the imprints, for detailed ones",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        default_value=1,
        min_value=0,
        max_value=50,
        description="Iterations smoothing the imprints over the mesh",
    )
    add_input(
        ng,
        "Rim",
        "NodeSocketFloat",
        default_value=0.5,
        min_value=-2.0,
        max_value=2.0,
        description="Height of the rim pushed up around the imprints, or of the bulge around "
        "the soft ones, relative to their depth, negative to sink the surface around them",
    )
    add_input(
        ng,
        "Rim Width",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.03,
        min_value=0.0,
        description="Width of the rim around the imprints",
    )
    add_input(
        ng,
        "Noise",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Uneven depth of the imprints and the rim",
    )
    add_input(
        ng,
        "Noise Scale",
        "NodeSocketFloat",
        default_value=40.0,
        min_value=0.0,
        description="Number of bumps of the Noise per meter",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(0.8, 0.8, 0.8, 1.0),
        description="Color multiplying the base color of the materials in the imprints",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the imprints, e.g. to the soft parts",
    )
    add_input(
        ng,
        "Lasting",
        "NodeSocketBool",
        default_value=True,
        description="Keep the imprints where the Colliders were, simulated from the Start Frame",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    add_input(
        ng,
        "Recovery",
        "NodeSocketFloat",
        default_value=0.0,
        min_value=0.0,
        description="Seconds for the deepest imprints to fill back, 0 to keep them",
    )
    softness = add_input(
        ng,
        "Softness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0,
        min_value=0.0,
        description="Distance the imprints spread over, the soft surface wrapping around the "
        "Colliders as a cushion, 0 for crisp imprints as footprints",
    )
    # After Smooth, added last to keep the identifiers of the inputs before it
    ng.interface.move(
        softness, list(ng.interface.items_tree).index(ng.interface.items_tree["Smooth"]) + 1
    )
    arrange_interface(ng, [(None, "Lasting", False, "Lasting", ["Start Frame", "Recovery"])])

    t = Tree(ng)
    t.section("Colliders")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    geometry = t.node(
        "GeometryNodeSubdivideMesh",
        -1,
        0,
        {"Mesh": inputs["Geometry"], "Level": inputs["Subdivisions"]},
    ).outputs[0]
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

    t.section("Imprint")
    reach = t.math("MULTIPLY", inputs["Depth"], REACH, x=3, y=-6)
    # Within half the thickness of the mesh, pressed at most to its middle from either side
    mesh = t.node(
        "GeometryNodeTransform",
        2,
        -11,
        {"Geometry": inputs["Geometry"], "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    through = t.node(
        "GeometryNodeRaycast",
        3,
        -11,
        {
            "Target Geometry": mesh,
            "Source Position": t.vmath(
                "SUBTRACT", world, t.vmath("SCALE", normal, SELF_OFFSET, x=2, y=-12), x=2.5, y=-12
            ),
            "Ray Direction": t.vmath("SCALE", normal, -1.0, x=2, y=-13),
            "Ray Length": t.math("MULTIPLY", reach, 2.0, x=2, y=-14),
        },
    ).outputs
    half = t.math(
        "MULTIPLY",
        t.math("ADD", through["Hit Distance"], SELF_OFFSET, x=4, y=-11),
        0.5,
        x=4.5,
        y=-11,
    )
    reach = t.node(
        "GeometryNodeSwitch",
        5,
        -10,
        {
            "Switch": through["Is Hit"],
            "False": reach,
            "True": t.math("MINIMUM", reach, half, x=5, y=-11),
        },
        input_type="FLOAT",
    ).outputs[0]
    geometry = t.store(geometry, ".imprint_reach", "FLOAT", reach, 5.5, 0)
    reach = t.attribute(".imprint_reach", "FLOAT", 6, -10)
    # Only the points near the Colliders cast a ray
    box = t.node("GeometryNodeBoundBox", 3, -8, {"Geometry": colliders}).outputs
    near = in_box(t, box, world, reach, 4, -9)
    depth = pressed_depth(t, colliders, world, normal, reach, inputs["Depth"], 4, -5)
    depth = t.math("MULTIPLY", depth, inputs["Mask"], x=9, y=-5)
    store = t.node(
        "GeometryNodeStoreNamedAttribute",
        10,
        0,
        {"Geometry": geometry, "Name": ".imprint_live", "Value": depth, "Selection": near},
        data_type="FLOAT",
        domain="POINT",
    )
    geometry = store.outputs["Geometry"]
    live = t.attribute(".imprint_live", "FLOAT", 11, -2)

    t.section("Lasting", row=True)
    depth = build_lasting(t, inputs, geometry, live)

    t.section("Displacement", row=True)
    geometry = t.store(geometry, ".imprint_depth", "FLOAT", depth, -2, 0)
    depth = t.attribute(".imprint_depth", "FLOAT", -2, -2)
    depth = t.math("MAXIMUM", depth, shallowest_neighbor(t, depth, -2, -4), x=-1, y=-2)
    depth = t.node(
        "GeometryNodeBlurAttribute",
        0,
        -2,
        {"Value": depth, "Iterations": inputs["Smooth"]},
        data_type="FLOAT",
    ).outputs[0]
    geometry = t.store(geometry, ".imprint_depth", "FLOAT", depth, 1, 0)
    depth = t.attribute(".imprint_depth", "FLOAT", 2, -2)

    # The rim from the imprints blurred over its width, outside of them, by their edge length
    edges = t.node("GeometryNodeInputMeshEdgeVertices", 2, -6).outputs
    length = t.vmath(
        "DISTANCE",
        *(
            t.node(
                "FunctionNodeTransformPoint",
                3,
                -6 - i,
                {"Vector": edges[f"Position {i + 1}"], "Transform": to_world},
            ).outputs[0]
            for i in range(2)
        ),
        x=4,
        y=-6,
    )
    length = t.node(
        "GeometryNodeAttributeStatistic",
        5,
        -6,
        {
            "Geometry": geometry,
            "Selection": t.math("GREATER_THAN", depth, 0.0, x=4, y=-8),
            "Attribute": length,
        },
        domain="EDGE",
    ).outputs["Mean"]
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        10,
        -5,
        {
            "Value": depth,
            "Iterations": blur_iterations(t, inputs["Rim Width"], length, RIM_ITERATIONS, 6, -6),
        },
        data_type="FLOAT",
    ).outputs[0]
    rim = t.math(
        "MULTIPLY",
        t.math("MAXIMUM", t.math("SUBTRACT", blurred, depth, x=11, y=-5), 0.0, x=12, y=-5),
        inputs["Rim"],
        x=13,
        y=-5,
    )
    outside = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "DIVIDE",
            depth,
            t.math("MULTIPLY", inputs["Depth"], RIM_DEPTH, x=11, y=-7),
            x=12,
            y=-7,
        ),
        x=13,
        y=-7,
        clamp=True,
    )
    rim = t.math("MULTIPLY", rim, outside, x=13.5, y=-5)
    height = t.math("SUBTRACT", rim, depth, x=14, y=-4)

    noise = t.node(
        "ShaderNodeTexNoise",
        10,
        -9,
        {"Vector": world, "Scale": inputs["Noise Scale"], "Detail": 0.0},
    ).outputs["Fac"]
    noise = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", noise, 0.5, x=11, y=-9),
        t.math("MULTIPLY", inputs["Noise"], 2.0, x=11, y=-10),
        1.0,
        x=12,
        y=-9,
    )
    noise = t.math("MAXIMUM", noise, 0.0, x=13, y=-9)
    crisp = t.store(
        geometry,
        ".imprint_offset",
        "FLOAT_VECTOR",
        t.vmath("SCALE", normal, t.math("MULTIPLY", height, noise, x=14, y=-5), x=15, y=-4),
        15,
        -1,
    )
    soft = build_soft(t, inputs, geometry, colliders, box, world, normal, reach, depth, length)
    soft = t.store(
        soft,
        ".imprint_offset",
        "FLOAT_VECTOR",
        t.vmath(
            "SCALE", t.attribute(".imprint_offset", "FLOAT_VECTOR", 15, -7), noise, x=15.5, y=-6
        ),
        16,
        -6,
    )
    geometry = t.node(
        "GeometryNodeSwitch",
        16.5,
        0,
        {
            "Switch": t.math("GREATER_THAN", inputs["Softness"], 0.0, x=16, y=-2),
            "False": crisp,
            "True": soft,
        },
        input_type="GEOMETRY",
    ).outputs[0]
    offset = t.attribute(".imprint_offset", "FLOAT_VECTOR", 17, -2)

    # Smooth where displaced, not to show the faces of the imprints
    geometry = t.node(
        "GeometryNodeSetShadeSmooth",
        16,
        0,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "GREATER_THAN", t.vmath("LENGTH", offset, x=17, y=-3), 1e-6, x=17.5, y=-3
            ),
        },
        domain="FACE",
    ).outputs[0]
    offset = t.node(
        "FunctionNodeTransformDirection",
        16,
        -4,
        {"Direction": offset, "Transform": to_local},
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSetPosition", 17, 0, {"Geometry": geometry, "Offset": offset}
    ).outputs[0]

    t.section("Attributes", row=True)
    # The amount left untinted in the alpha, 1 as read by the shaders without the attribute
    amount = t.math(
        "DIVIDE",
        depth,
        t.math("MULTIPLY", inputs["Depth"], TINT_DEPTH, x=0, y=-3),
        x=1,
        y=-2,
        clamp=True,
    )
    rgb = t.node("FunctionNodeSeparateColor", 1, -4, {0: inputs["Color"]}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        2,
        -2,
        {
            "Red": rgb["Red"],
            "Green": rgb["Green"],
            "Blue": rgb["Blue"],
            "Alpha": t.math("SUBTRACT", 1.0, amount, x=2, y=-4),
        },
    ).outputs[0]
    geometry = t.store(geometry, "imprint", "FLOAT_COLOR", color, 3, 0)
    geometry = t.node(
        "GeometryNodeRemoveAttribute",
        4,
        0,
        {"Geometry": geometry, "Pattern Mode": "Wildcard", "Name": ".imprint_*"},
    ).outputs[0]
    t.node("NodeGroupOutput", 5, 0, {"Geometry": geometry})
    t.arrange()
    return ng


def pressed_depth(t, colliders, position, normal, reach, limit, x, y):
    """Depth the Colliders press the surface at the position, up from under it to their lowest
    surface, only where they cover it"""
    ray = t.node(
        "GeometryNodeRaycast",
        x + 1,
        y,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath(
                "SUBTRACT", position, t.vmath("SCALE", normal, reach, x=x, y=y), x=x + 0.5, y=y
            ),
            "Ray Direction": normal,
            "Ray Length": reach,
        },
    ).outputs
    depth = t.math(
        "MINIMUM",
        t.math("SUBTRACT", reach, ray["Hit Distance"], x=x + 2, y=y),
        limit,
        x=x + 3,
        y=y,
    )
    depth = t.math("MULTIPLY", depth, ray["Is Hit"], x=x + 4, y=y)
    # Not seen through a mesh thinner than the reach
    covered = t.node(
        "GeometryNodeRaycast",
        x + 1,
        y - 2,
        {
            "Target Geometry": colliders,
            "Source Position": position,
            "Ray Direction": normal,
            "Ray Length": OUTSIDE,
        },
    ).outputs["Is Hit"]
    return t.math("MULTIPLY", depth, covered, x=x + 4.5, y=y)


def blur_iterations(t, distance, length, limit, x, y):
    """Blur iterations spreading a value over the distance, the edges being that long"""
    spread = t.math("DIVIDE", distance, length, x=x, y=y)
    iterations = t.math(
        "MINIMUM",
        t.math("MULTIPLY", t.math("MULTIPLY", spread, spread, x=x + 1, y=y), 2.0, x=x + 2, y=y),
        limit,
        x=x + 3,
        y=y,
    )
    return t.math("ROUND", iterations, x=x + 3.5, y=y)


def build_soft(t, inputs, geometry, colliders, box, world, normal, reach, depth, spacing):
    """Geometry with the offsets of the soft imprints: spread over the Softness keeping the
    pressed points as deep, on a coarser copy of the mesh, then the points moved into the
    Colliders pushed out of them"""
    inward = t.vmath("SCALE", normal, -1.0, x=0, y=-12)
    pressed = t.vmath("SCALE", inward, depth, x=0.5, y=-13)
    geometry = t.store(geometry, ".imprint_inward", "FLOAT_VECTOR", inward, 0.5, -11)
    geometry = t.store(geometry, ".imprint_offset", "FLOAT_VECTOR", pressed, 1, -11)
    # Each part of the mesh brought back from its own, its denser edges merged further away
    island = t.node("GeometryNodeInputMeshIsland", 0.5, -15).outputs["Island Index"]
    geometry = t.store(geometry, ".imprint_island", "INT", island, 1, -10)

    # Around the Colliders in world space, its points about a seventh of the Softness apart
    near = in_box(t, box, world, t.math("ADD", reach, inputs["Softness"], x=0, y=-16), 0.5, -16)
    coarse = t.node(
        "GeometryNodeDeleteGeometry",
        1,
        -12,
        {"Geometry": geometry, "Selection": t.math("SUBTRACT", 1.0, near, x=1, y=-15)},
        domain="POINT",
    ).outputs[0]
    coarse = t.node(
        "GeometryNodeSetPosition", 1.5, -12, {"Geometry": coarse, "Position": world}
    ).outputs[0]
    coarse = t.node(
        "GeometryNodeMergeByDistance",
        2,
        -12,
        {
            "Geometry": coarse,
            "Mode": "Connected",
            "Distance": t.math("DIVIDE", inputs["Softness"], COARSE, x=1.5, y=-14),
        },
    ).outputs[0]
    edges = t.node("GeometryNodeInputMeshEdgeVertices", 2, -16).outputs
    length = t.node(
        "GeometryNodeAttributeStatistic",
        2.5,
        -15,
        {
            "Geometry": coarse,
            "Attribute": t.vmath(
                "DISTANCE", edges["Position 1"], edges["Position 2"], x=2.5, y=-16
            ),
        },
        domain="EDGE",
    ).outputs["Mean"]
    rounds_in = t.node(
        "GeometryNodeRepeatInput",
        3,
        -12,
        {"Iterations": blur_iterations(t, inputs["Softness"], length, SOFT_ROUNDS, 2.5, -17)},
    )
    rounds_out = t.node("GeometryNodeRepeatOutput", 7, -12)
    rounds_in.pair_with_output(rounds_out)
    t.connect(coarse, rounds_in.inputs["Geometry"])
    coarse_inward = t.vmath(
        "NORMALIZE", t.attribute(".imprint_inward", "FLOAT_VECTOR", 3, -14), x=3.5, y=-14
    )
    # Sinking less and less away from the pressed points, as on an elastic foundation
    ratio = t.math("DIVIDE", length, inputs["Softness"], x=3, y=-18)
    keep = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", t.math("MULTIPLY", ratio, ratio, x=3.5, y=-18), FADE, x=4, y=-18),
        x=4.5,
        y=-18,
        clamp=True,
    )
    kept = keep_pressed(
        t,
        t.vmath(
            "SCALE",
            t.node(
                "GeometryNodeBlurAttribute",
                4,
                -13,
                {"Value": t.attribute(".imprint_offset", "FLOAT_VECTOR", 3, -13), "Iterations": 1},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
            keep,
            x=4.5,
            y=-13,
        ),
        coarse_inward,
        t.attribute(".imprint_depth", "FLOAT", 3, -15),
        5,
        -13,
    )
    t.connect(
        t.store(rounds_in.outputs["Geometry"], ".imprint_offset", "FLOAT_VECTOR", kept, 6, -12),
        rounds_out.inputs["Geometry"],
    )

    # Back on the mesh, the pressed points as deep
    spread = t.node(
        "GeometryNodeSampleNearestSurface",
        8,
        -13,
        {
            "Mesh": rounds_out.outputs["Geometry"],
            "Value": t.attribute(".imprint_offset", "FLOAT_VECTOR", 7, -14),
            "Group ID": t.attribute(".imprint_island", "INT", 7, -15),
            "Sample Position": world,
            "Sample Group ID": t.attribute(".imprint_island", "INT", 7, -16),
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    geometry = t.node(
        "GeometryNodeStoreNamedAttribute",
        10,
        -11,
        {
            "Geometry": geometry,
            "Name": ".imprint_offset",
            "Value": spread,
            "Selection": near,
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]

    # Smoothed over the size of the faces of the copy, not to show them, the pressed points as deep
    # along the normals smoothed as much, not to tear apart the finer details as the piping
    iterations = blur_iterations(t, length, spacing, SMOOTH_ITERATIONS, 9.5, -15)
    geometry = t.store(
        geometry,
        ".imprint_smooth",
        "FLOAT_VECTOR",
        t.vmath(
            "NORMALIZE",
            t.node(
                "GeometryNodeBlurAttribute",
                10,
                -16,
                {"Value": inward, "Iterations": iterations},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
            x=10.5,
            y=-16,
        ),
        10.5,
        -11,
    )
    smooth = t.attribute(".imprint_smooth", "FLOAT_VECTOR", 11, -16)
    smoothed = t.node(
        "GeometryNodeBlurAttribute",
        10.5,
        -12,
        {
            "Value": t.attribute(".imprint_offset", "FLOAT_VECTOR", 10, -13),
            "Iterations": iterations,
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    geometry = t.store(
        geometry,
        ".imprint_offset",
        "FLOAT_VECTOR",
        keep_pressed(t, smoothed, smooth, depth, 11, -13),
        12,
        -11,
    )

    for i in range(PUSH_ROUNDS):
        offset = t.attribute(".imprint_offset", "FLOAT_VECTOR", 7 + 3 * i, -13)
        # In all at most as deep as the Depth
        left = t.math(
            "MAXIMUM",
            t.math(
                "SUBTRACT",
                inputs["Depth"],
                t.vmath("DOT_PRODUCT", offset, smooth, x=7 + 3 * i, y=-18),
                x=7.5 + 3 * i,
                y=-18,
            ),
            0.0,
            x=8 + 3 * i,
            y=-18,
        )
        deeper = pressed_depth(
            t,
            colliders,
            t.vmath("ADD", world, offset, x=7 + 3 * i, y=-14),
            t.vmath("SCALE", smooth, -1.0, x=7 + 3 * i, y=-17),
            reach,
            left,
            7 + 3 * i,
            -16,
        )
        geometry = t.store(
            geometry,
            ".imprint_offset",
            "FLOAT_VECTOR",
            t.vmath(
                "ADD",
                offset,
                t.vmath("SCALE", smooth, deeper, x=8 + 3 * i, y=-13),
                x=9 + 3 * i,
                y=-12,
            ),
            9 + 3 * i,
            -11,
        )
    # Bulging around the pressed points over the Rim Width, the Rim being the share of the pressed
    # volume moved into the ring around them
    offset = t.attribute(".imprint_offset", "FLOAT_VECTOR", 13, -13)
    iterations = blur_iterations(t, inputs["Rim Width"], spacing, RIM_ITERATIONS, 13, -18)
    pressed = t.math("GREATER_THAN", depth, 0.0, x=13, y=-17)

    def blur(value, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            14,
            y,
            {"Value": value, "Iterations": iterations},
            data_type="FLOAT",
        ).outputs[0]

    # Rising from the pressed points, peaking at a third of the Rim Width: the pressed share of the
    # points around, a half next to them, from 1 there to 0 at the Rim Width
    out = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", blur(pressed, -17), 2.0, x=14.5, y=-17),
        x=15,
        y=-17,
        clamp=True,
    )
    ring = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            out,
            t.math("POWER", t.math("SUBTRACT", 1.0, out, x=15, y=-19), 2.0, x=15.5, y=-19),
            x=16,
            y=-18,
        ),
        t.math("MULTIPLY", t.math("SUBTRACT", 1.0, pressed, x=14, y=-20), 6.75, x=15, y=-20),
        x=16.5,
        y=-17,
    )
    geometry = t.store(geometry, ".imprint_ring", "FLOAT", ring, 15, -11)
    ring = t.attribute(".imprint_ring", "FLOAT", 15.5, -17)
    bulge = t.math(
        "MULTIPLY",
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", ring, blur(depth, -14), x=15, y=-14),
            t.math("MAXIMUM", blur(ring, -15), 1e-6, x=15, y=-15),
            x=15.5,
            y=-14,
        ),
        inputs["Rim"],
        x=16,
        y=-14,
    )
    # Smoothed not to rise all at once next to the pressed points, then up to the Colliders above,
    # as against the body
    bulge = t.math(
        "MULTIPLY", blur(bulge, -16), t.math("SUBTRACT", 1.0, pressed, x=15, y=-21), x=16, y=-16
    )
    outward = t.vmath("SCALE", smooth, -1.0, x=16, y=-16)
    hit = t.node(
        "GeometryNodeRaycast",
        16.5,
        -16,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath("ADD", world, offset, x=16, y=-15),
            "Ray Direction": outward,
            "Ray Length": bulge,
        },
    ).outputs
    bulge = t.node(
        "GeometryNodeSwitch",
        17,
        -14,
        {"Switch": hit["Is Hit"], "False": bulge, "True": hit["Hit Distance"]},
        input_type="FLOAT",
    ).outputs[0]
    bulged = t.vmath("ADD", offset, t.vmath("SCALE", outward, bulge, x=17, y=-15), x=17.5, y=-13)
    return t.store(geometry, ".imprint_offset", "FLOAT_VECTOR", bulged, 18, -11)


def in_box(t, box, position, margin, x, y):
    """Whether the position is in the bounding box grown by the margin"""
    low = t.vmath(
        "SUBTRACT", position, t.vmath("SUBTRACT", box["Min"], margin, x=x, y=y), x=x + 1, y=y
    )
    high = t.vmath(
        "SUBTRACT", t.vmath("ADD", box["Max"], margin, x=x, y=y - 1), position, x=x + 1, y=y - 1
    )
    xyz = t.node(
        "ShaderNodeSeparateXYZ", x + 2, y, {0: t.vmath("MINIMUM", low, high, x=x + 1.5, y=y)}
    ).outputs
    return t.math(
        "GREATER_THAN",
        t.math(
            "MINIMUM",
            t.math("MINIMUM", xyz["X"], xyz["Y"], x=x + 3, y=y),
            xyz["Z"],
            x=x + 4,
            y=y,
        ),
        0.0,
        x=x + 5,
        y=y,
    )


def keep_pressed(t, offset, inward, depth, x, y):
    """Offset moving the pressed points at least as deep along their inward normal"""
    short = t.math(
        "MAXIMUM",
        t.math("SUBTRACT", depth, t.vmath("DOT_PRODUCT", offset, inward, x=x, y=y), x=x + 0.5, y=y),
        0.0,
        x=x + 1,
        y=y,
    )
    return t.vmath("ADD", offset, t.vmath("SCALE", inward, short, x=x + 1, y=y - 1), x=x + 1.5, y=y)


def shallowest_neighbor(t, value, x, y):
    """Smallest value of the points next to each point, to fill the single points the rays pass
    by, as between the toes"""
    neighbor = t.node(
        "GeometryNodeFieldAtIndex",
        x + 2,
        y,
        {
            "Value": value,
            "Index": t.node(
                "GeometryNodeVertexOfCorner",
                x + 1,
                y - 1,
                {
                    "Corner Index": t.node(
                        "GeometryNodeOffsetCornerInFace", x, y - 1, {"Offset": 1}
                    ).outputs[0]
                },
            ).outputs[0],
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    smallest = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 3,
        y,
        {
            "Value": neighbor,
            "Group ID": t.node("GeometryNodeVertexOfCorner", x + 2, y - 2).outputs[0],
        },
        data_type="FLOAT",
        domain="CORNER",
    ).outputs["Min"]
    return t.node(
        "GeometryNodeFieldOnDomain",
        x + 4,
        y,
        {"Value": smallest},
        data_type="FLOAT",
        domain="CORNER",
    ).outputs[0]


def build_lasting(t, inputs, geometry, live):
    """Depth of each point, the deepest since the Start Frame filling back, simulated on points
    by index"""
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    count = t.node("GeometryNodeAttributeDomainSize", 0, 0, {0: geometry}).outputs["Point Count"]
    points = t.node("GeometryNodePoints", 1, 0, {"Count": count}).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 6, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(points, sim_in.inputs["Geometry"])
    state = t.node(
        "GeometryNodeSwitch",
        3,
        0,
        {"Switch": started, "False": points, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 3, -2).outputs[0]
    current = t.node(
        "GeometryNodeSampleIndex",
        4,
        -2,
        {"Geometry": geometry, "Value": live, "Index": index},
        data_type="FLOAT",
    ).outputs[0]
    # Filling back by the Depth in the Recovery, none without it
    fill = t.math(
        "DIVIDE",
        t.math("MULTIPLY", sim_in.outputs["Delta Time"], inputs["Depth"], x=3, y=-4),
        inputs["Recovery"],
        x=4,
        y=-4,
    )
    kept = t.math(
        "SUBTRACT",
        t.attribute(".imprint_kept", "FLOAT", 3, -3),
        t.math("MULTIPLY", fill, started, x=4.5, y=-4),
        x=5,
        y=-3,
        clamp=True,
    )
    state = t.store(
        state, ".imprint_kept", "FLOAT", t.math("MAXIMUM", current, kept, x=5.5, y=-2), 5, 0
    )
    t.connect(state, sim_out.inputs["Geometry"])

    # Back on the mesh by index, without Lasting the live depth
    result = t.node(
        "GeometryNodeSampleIndex",
        8,
        -2,
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Value": t.attribute(".imprint_kept", "FLOAT", 7, -3),
            "Index": t.node("GeometryNodeInputIndex", 7, -4).outputs[0],
        },
        data_type="FLOAT",
    ).outputs[0]
    return t.node(
        "GeometryNodeSwitch",
        9,
        -2,
        {"Switch": inputs["Lasting"], "False": live, "True": result},
        input_type="FLOAT",
    ).outputs[0]


def build_tint():
    """The color multiplied by the color of the imprints, from the attribute of the modifier"""
    ng = bpy.data.node_groups.new(TINT, "ShaderNodeTree")
    add_input(ng, "Color", "NodeSocketColor", default_value=(0.8, 0.8, 0.8, 1.0))
    add_output(ng, "Color", "NodeSocketColor")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    imprint = t.node(
        "ShaderNodeAttribute", 0, -2, attribute_type="GEOMETRY", attribute_name="imprint"
    ).outputs
    tinted = t.node(
        "ShaderNodeMix",
        2,
        0,
        {
            "Factor": t.math("SUBTRACT", 1.0, imprint["Alpha"], x=1, y=-3, clamp=True),
            "A": inputs["Color"],
            "B": imprint["Color"],
        },
        data_type="RGBA",
        blend_type="MULTIPLY",
    ).outputs
    t.node("NodeGroupOutput", 3, 0, {"Color": next(s for s in tinted if s.type == "RGBA")})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_tint()), fake_user=True)
