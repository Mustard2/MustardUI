# Build chain.blend: the Chain node group and material
# Usage: Blender --background --factory-startup --python chain_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "chain.blend"
NODE_GROUP = "MustardUI Chain"
SOLVER = "MustardUI Chain Solver"
# Raised at every change, the add-on replacing older copies in the files
VERSION = 4
# Over-relaxation of the length passes, which converge slowly along a long chain. Up to 1.8 it
# gets unstable with the smaller steps of more substeps
OVER_RELAXATION = 1.5
# Velocity shared with the next points at each substep
VELOCITY_SHARE = 0.2
# Most points of the simulation in a part of the chain, and links in the chain
MAX_POINTS = 2000
MAX_LINKS = 20000
# Steps and damping pushing the chain at rest out of the Colliders, then steps keeping its length,
# as the steps stretch it as much as they are long
RELAX_STEPS = 24
RELAX_SUBSTEPS = 4
RELAX_DAMPING = 30.0
FINISH_TIME = 1.0 / 240.0
FINISH_SUBSTEPS = 8
# Parts of a chain closer than this to taut are straight, not to lose precision
TAUT = 1.0005
# Newton steps finding the shape of the hanging parts of the chain
CATENARY_STEPS = 4
# Deepest points pushed out of the Colliders, the others being behind open meshes
MAX_DEPTH = 0.05
# Least distance of each point from the second next ones, in segments: the sharpest bend is about
# 60 degrees for each Segment Length, a shorter one allows tighter folds. Not at the Anchors
MIN_FOLD = 1.7
# Distance of the points pushed apart by the Self Collision: of the radius of the chain and, to
# skip the next points, of the distance along it
SELF_RADIUS = 3.0
# Points this close along the chain do not collide, as the ones next to a sharp bend at an Anchor
SELF_SKIP = 10.0
SELF_SPACING = 0.9
# Random offset of the points at rest, for the straight parts to buckle on the Colliders
BUCKLING = 0.0002
# Times the parts of a chain at rest inside the Colliders are moved out of them
OUT_ROUNDS = 2
# Space around the chain the faces of the Colliders are kept in
CROP = 0.15


def build_solver():
    """Node group moving the points of the chain along a time step"""
    ng = bpy.data.node_groups.new(SOLVER, "GeometryNodeTree")
    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Anchors", "NodeSocketGeometry")
    add_input(ng, "Colliders", "NodeSocketGeometry")
    add_input(ng, "Time", "NodeSocketFloat")
    add_input(ng, "Substeps", "NodeSocketInt", default_value=1, min_value=1)
    add_input(ng, "Iterations", "NodeSocketInt", default_value=1, min_value=1)
    add_input(ng, "Gravity", "NodeSocketFloat")
    add_input(ng, "Damping", "NodeSocketFloat")
    add_input(ng, "Friction", "NodeSocketFloat")
    add_input(ng, "Radius", "NodeSocketFloat")
    add_input(ng, "Collision", "NodeSocketBool")
    add_input(ng, "Self Collision", "NodeSocketBool")
    add_input(ng, "Keep Length", "NodeSocketBool")
    add_input(ng, "Tip", "NodeSocketVector")
    add_input(ng, "Hold", "NodeSocketFloat")

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    position = t.node("GeometryNodeInputPosition", -2, -3).outputs["Position"]
    index = t.node("GeometryNodeInputIndex", -2, -4).outputs[0]

    def at(i, value, x, y, data_type="FLOAT_VECTOR"):
        """Value at the point of the index"""
        return t.node(
            "GeometryNodeFieldAtIndex",
            x,
            y,
            {"Index": i, "Value": value},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]

    def along(geometry, reach, other, selection, x):
        """Geometry with the points not farther from the point of the index than the reach"""
        offset = t.vmath("SUBTRACT", position, at(other, position, x, -4), x=x, y=-3)
        return t.node(
            "GeometryNodeSetPosition",
            x + 1,
            0,
            {
                "Geometry": geometry,
                "Selection": selection,
                "Offset": t.vmath(
                    "SCALE",
                    t.vmath("NORMALIZE", offset, x=x, y=-5),
                    t.math(
                        "MINIMUM",
                        t.math("SUBTRACT", reach, t.vmath("LENGTH", offset, x=x, y=-6), x=x, y=-7),
                        0.0,
                        x=x,
                        y=-8,
                    ),
                    x=x + 1,
                    y=-5,
                ),
            },
        ).outputs[0]

    t.section("Frame")
    anchor = t.attribute(".chain_anchor", "INT", 0, -2)
    anchors = inputs["Anchors"]
    target = t.node(
        "GeometryNodeSampleIndex",
        1,
        -2,
        {"Geometry": anchors, "Value": position, "Index": anchor},
        data_type="FLOAT_VECTOR",
        domain="POINT",
        clamp=True,
    ).outputs[0]
    next_target = t.node(
        "GeometryNodeSampleIndex",
        1,
        -4,
        {"Geometry": anchors, "Value": position, "Index": t.math("ADD", anchor, 1.0, x=0, y=-4)},
        data_type="FLOAT_VECTOR",
        domain="POINT",
        clamp=True,
    ).outputs[0]
    # Without Keep Length the parts between the Anchors stretch as much as the Anchors move apart.
    # Past taut they stretch anyway, evenly
    start_distance = t.attribute(".chain_distance", "FLOAT", 2, -5)
    distance = t.vmath("DISTANCE", target, next_target, x=2, y=-4)
    ratio = t.math(
        "MAXIMUM",
        t.node(
            "GeometryNodeSwitch",
            4,
            -5,
            {
                "Switch": t.node(
                    "FunctionNodeBooleanMath",
                    3,
                    -6,
                    {
                        0: inputs["Keep Length"],
                        1: t.math("LESS_THAN", start_distance, 1e-6, x=2, y=-6),
                    },
                    operation="OR",
                ).outputs[0],
                "False": t.math("DIVIDE", distance, start_distance, x=3, y=-4),
                "True": 1.0,
            },
            input_type="FLOAT",
        ).outputs[0],
        t.math("DIVIDE", distance, t.attribute(".chain_part", "FLOAT", 3, -7), x=4, y=-7),
        x=5,
        y=-5,
    )
    # The tip moved to the Tip Control as far as the chain reaches, not to stretch it
    tip = t.attribute(".chain_tip", "FLOAT", 6, -2)
    holding = t.math("GREATER_THAN", inputs["Hold"], 0.0, x=6, y=-3)
    tip_held = t.math("MULTIPLY", tip, holding, x=7, y=-3)
    to_tip = t.vmath("SUBTRACT", inputs["Tip"], target, x=6, y=-4)
    goal = t.vmath(
        "ADD",
        target,
        t.vmath(
            "SCALE",
            t.vmath("NORMALIZE", to_tip, x=7, y=-4),
            t.math(
                "MINIMUM",
                t.vmath("LENGTH", to_tip, x=7, y=-5),
                t.attribute(".chain_from_start", "FLOAT", 7, -6),
                x=8,
                y=-5,
            ),
            x=8,
            y=-4,
        ),
        x=9,
        y=-4,
    )
    target = t.node(
        "GeometryNodeSwitch",
        10,
        -3,
        {
            "Switch": t.math("GREATER_THAN", tip_held, 0.5, x=9, y=-3),
            "False": target,
            "True": t.node(
                "ShaderNodeMix",
                9,
                -5,
                {"Factor": inputs["Hold"], "A": position, "B": goal},
                data_type="VECTOR",
            ).outputs["Result"],
        },
        input_type="VECTOR",
    ).outputs[0]
    geometry = inputs["Geometry"]
    for i, (name, data_type, value) in enumerate(
        (
            (".chain_begin", "FLOAT_VECTOR", position),
            (".chain_target", "FLOAT_VECTOR", target),
            (
                ".chain_free",
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    t.attribute(".chain_free_start", "FLOAT", 9, -6),
                    t.math("SUBTRACT", 1.0, tip_held, x=10, y=-6),
                    x=11,
                    y=-6,
                ),
            ),
            *(
                (
                    f".chain_{name}",
                    "FLOAT",
                    t.math(
                        "MULTIPLY",
                        t.attribute(f".chain_{name}_start", "FLOAT", 4, -7 - 2 * i),
                        ratio,
                        x=5,
                        y=-7 - 2 * i,
                    ),
                )
                for i, name in enumerate(("rest", "from", "to"))
            ),
        )
    ):
        geometry = t.store(geometry, name, data_type, value, 12 + i * 0.1, 0)

    t.section("Substeps")
    steps_in = t.node("GeometryNodeRepeatInput", 12, 0, {"Iterations": inputs["Substeps"]})
    steps_out = t.node("GeometryNodeRepeatOutput", 40, 0)
    steps_in.pair_with_output(steps_out)
    t.connect(geometry, steps_in.inputs["Geometry"])
    step = t.math("DIVIDE", inputs["Time"], inputs["Substeps"], x=12, y=-2)
    free = t.attribute(".chain_free", "FLOAT", 12, -3)
    held = t.math("GREATER_THAN", free, 0.5, x=13, y=-3)
    pinned = t.node("FunctionNodeBooleanMath", 14, -3, {0: held}, operation="NOT").outputs[0]
    velocity = t.attribute(".chain_velocity", "FLOAT_VECTOR", 13, -4)

    # The velocity damped and with the gravity
    factor = t.math(
        "EXPONENT",
        t.math(
            "MULTIPLY", t.math("MULTIPLY", inputs["Damping"], step, x=13, y=-5), -1.0, x=14, y=-5
        ),
        x=15,
        y=-5,
    )
    gravity = t.node(
        "ShaderNodeCombineXYZ",
        15,
        -6,
        {"Z": t.math("MULTIPLY", inputs["Gravity"], -1.0, x=14, y=-6)},
    ).outputs[0]
    velocity = t.vmath(
        "ADD",
        t.vmath("SCALE", velocity, factor, x=16, y=-4),
        t.vmath("SCALE", gravity, step, x=16, y=-6),
        x=17,
        y=-4,
    )
    geometry = t.store(
        steps_in.outputs["Geometry"], ".chain_previous", "FLOAT_VECTOR", position, 13, 0
    )
    geometry = t.node(
        "GeometryNodeSetPosition",
        18,
        0,
        {
            "Geometry": geometry,
            "Selection": held,
            "Offset": t.vmath("SCALE", velocity, step, x=18, y=-4),
        },
    ).outputs[0]
    # The pinned points moving to the Anchors along the substeps
    geometry = t.node(
        "GeometryNodeSetPosition",
        19,
        0,
        {
            "Geometry": geometry,
            "Selection": pinned,
            "Position": t.node(
                "ShaderNodeMix",
                19,
                -4,
                {
                    "Factor": t.math(
                        "DIVIDE",
                        t.math("ADD", steps_in.outputs["Iteration"], 1.0, x=18, y=-6),
                        inputs["Substeps"],
                        x=19,
                        y=-6,
                    ),
                    "A": t.attribute(".chain_begin", "FLOAT_VECTOR", 18, -7),
                    "B": t.attribute(".chain_target", "FLOAT_VECTOR", 18, -8),
                },
                data_type="VECTOR",
            ).outputs["Result"],
        },
    ).outputs[0]

    # Each link at its length, the odd ones after the even ones to converge along the chain
    iterations_in = t.node("GeometryNodeRepeatInput", 20, 0, {"Iterations": inputs["Iterations"]})
    iterations_out = t.node("GeometryNodeRepeatOutput", 32, 0)
    iterations_in.pair_with_output(iterations_out)
    t.connect(geometry, iterations_in.inputs["Geometry"])
    geometry = iterations_in.outputs["Geometry"]
    last = t.math(
        "SUBTRACT",
        t.node(
            "GeometryNodeAttributeDomainSize",
            20,
            -2,
            {"Geometry": iterations_in.outputs["Geometry"]},
            component="POINTCLOUD",
        ).outputs["Point Count"],
        1.0,
        x=21,
        y=-2,
    )
    rest = t.attribute(".chain_rest", "FLOAT", 20, -3)
    for parity in (0, 1):
        x = 21 + 5 * parity
        forward = t.math(
            "COMPARE",
            t.math("FLOORED_MODULO", index, 2.0, x=x, y=-4),
            float(parity),
            0.1,
            x=x + 1,
            y=-4,
        )
        other = t.math(
            "ADD",
            index,
            t.math("SUBTRACT", t.math("MULTIPLY", forward, 2.0, x=x + 1, y=-5), 1.0, x=x + 2, y=-5),
            x=x + 3,
            y=-4,
        )
        offset = t.vmath("SUBTRACT", position, at(other, position, x + 3, -6), x=x + 4, y=-6)
        length = t.node(
            "GeometryNodeSwitch",
            x + 3,
            -8,
            {
                "Switch": t.math("GREATER_THAN", forward, 0.5, x=x + 2, y=-8),
                "False": at(
                    t.math("SUBTRACT", index, 1.0, x=x + 1, y=-9), rest, x + 2, -9, "FLOAT"
                ),
                "True": rest,
            },
            input_type="FLOAT",
        ).outputs[0]
        share = t.math(
            "DIVIDE",
            free,
            t.math("ADD", free, at(other, free, x + 3, -10, "FLOAT"), x=x + 4, y=-10),
            x=x + 4,
            y=-11,
        )
        valid = t.node(
            "FunctionNodeBooleanMath",
            x + 3,
            -12,
            {
                0: t.math("GREATER_THAN", other, -0.5, x=x + 2, y=-12),
                1: t.math(
                    "LESS_THAN", other, t.math("ADD", last, 0.5, x=x + 1, y=-13), x=x + 2, y=-13
                ),
            },
            operation="AND",
        ).outputs[0]
        geometry = t.node(
            "GeometryNodeSetPosition",
            x + 4,
            0,
            {
                "Geometry": geometry,
                "Selection": t.node(
                    "FunctionNodeBooleanMath", x + 4, -13, {0: valid, 1: held}, operation="AND"
                ).outputs[0],
                "Offset": t.vmath(
                    "SCALE",
                    t.vmath("NORMALIZE", offset, x=x + 5, y=-6),
                    t.math(
                        "MULTIPLY",
                        t.math(
                            "SUBTRACT",
                            length,
                            t.vmath("LENGTH", offset, x=x + 5, y=-8),
                            x=x + 5,
                            y=-9,
                        ),
                        t.math("MULTIPLY", share, OVER_RELAXATION, x=x + 5, y=-11),
                        x=x + 5,
                        y=-10,
                    ),
                    x=x + 5,
                    y=-5,
                ),
            },
        ).outputs[0]
    t.connect(geometry, iterations_out.inputs["Geometry"])

    # Links do not fold on themselves, and link directions flip at hairpins: no point closer to the
    # second next ones than they can get
    count_after = t.node(
        "GeometryNodeAttributeDomainSize",
        32.1,
        -30,
        {"Geometry": iterations_out.outputs["Geometry"]},
        component="POINTCLOUD",
    ).outputs["Point Count"]
    folds = []
    for i, sign in enumerate((1.0, -1.0)):
        y = -32 - 8 * i
        second = t.math("ADD", index, 2.0 * sign, x=32.1, y=y)
        exists = t.math(
            "MULTIPLY",
            t.math("GREATER_THAN", second, -0.5, x=32.1, y=y - 1),
            t.math(
                "LESS_THAN",
                second,
                t.math("SUBTRACT", count_after, 0.5, x=32.1, y=y - 2),
                x=32.1,
                y=y - 3,
            ),
            x=32.1,
            y=y - 4,
        )
        away = t.vmath("SUBTRACT", position, at(second, position, 32.1, y - 5), x=32.2, y=y)
        least = t.math(
            "MULTIPLY",
            t.attribute(".chain_rest", "FLOAT", 32.2, y - 1),
            MIN_FOLD,
            x=32.2,
            y=y - 2,
        )
        folds.append(
            t.vmath(
                "SCALE",
                t.vmath("NORMALIZE", away, x=32.2, y=y - 3),
                t.math(
                    "MULTIPLY",
                    t.math(
                        "MAXIMUM",
                        t.math(
                            "SUBTRACT",
                            least,
                            t.vmath("LENGTH", away, x=32.2, y=y - 4),
                            x=32.2,
                            y=y - 5,
                        ),
                        0.0,
                        x=32.2,
                        y=y - 6,
                    ),
                    t.math(
                        "MULTIPLY",
                        t.math("MULTIPLY", exists, 0.25, x=32.2, y=y - 7),
                        # Not around the Anchors, where the chain pivots
                        at(t.math("ADD", index, sign, x=32.2, y=y - 8), free, 32.3, y - 8, "FLOAT"),
                        x=32.3,
                        y=y - 7,
                    ),
                    x=32.3,
                    y=y - 6,
                ),
                x=32.3,
                y=y - 3,
            )
        )
    unfolded = t.node(
        "GeometryNodeSetPosition",
        32.4,
        0,
        {
            "Geometry": iterations_out.outputs["Geometry"],
            "Selection": held,
            "Offset": t.vmath("ADD", folds[0], folds[1], x=32.4, y=-32),
        },
    ).outputs[0]

    # No point farther from the Anchors than along the chain, for the chain not to stretch
    # under its weight however long it is
    geometry = along(
        unfolded,
        t.attribute(".chain_from", "FLOAT", 32, -2),
        t.attribute(".chain_first", "INT", 32, -3),
        held,
        33,
    )
    end = t.attribute(".chain_end", "INT", 34, -2)
    geometry = along(
        geometry,
        t.attribute(".chain_to", "FLOAT", 34, -3),
        end,
        t.node(
            "FunctionNodeBooleanMath",
            35,
            -9,
            {0: held, 1: t.math("GREATER_THAN", end, -0.5, x=34, y=-9)},
            operation="AND",
        ).outputs[0],
        35,
    )

    # The velocity from the solved points, the pushes out below would make them bounce, as much as
    # the substeps are short. A bit of it shared with the next points, calming the fastest waves
    velocity = t.vmath(
        "SCALE",
        t.vmath(
            "SUBTRACT",
            position,
            t.attribute(".chain_previous", "FLOAT_VECTOR", 35, -10),
            x=35,
            y=-9,
        ),
        t.math(
            "DIVIDE",
            t.math("MAXIMUM", free, t.attribute(".chain_tip", "FLOAT", 34.5, -11), x=34.8, y=-11),
            step,
            x=35,
            y=-11,
        ),
        x=35.1,
        y=-9,
    )
    geometry = t.store(geometry, ".chain_velocity", "FLOAT_VECTOR", velocity, 35.1, 0)
    speed = t.attribute(".chain_velocity", "FLOAT_VECTOR", 35.1, -12)
    last_point = t.math(
        "SUBTRACT",
        t.node(
            "GeometryNodeAttributeDomainSize",
            35.1,
            -13,
            {"Geometry": geometry},
            component="POINTCLOUD",
        ).outputs["Point Count"],
        1.0,
        x=35.2,
        y=-13,
    )
    around = t.vmath(
        "SCALE",
        t.vmath(
            "ADD",
            at(
                t.math(
                    "MAXIMUM", t.math("SUBTRACT", index, 1.0, x=35.2, y=-14), 0.0, x=35.2, y=-15
                ),
                speed,
                35.2,
                -16,
            ),
            at(
                t.math(
                    "MINIMUM", t.math("ADD", index, 1.0, x=35.2, y=-17), last_point, x=35.2, y=-18
                ),
                speed,
                35.2,
                -19,
            ),
            x=35.3,
            y=-16,
        ),
        0.5,
        x=35.3,
        y=-17,
    )
    geometry = t.store(
        geometry,
        ".chain_velocity",
        "FLOAT_VECTOR",
        t.node(
            "ShaderNodeMix",
            35.3,
            -18,
            {"Factor": VELOCITY_SHARE, "A": speed, "B": around},
            data_type="VECTOR",
        ).outputs["Result"],
        35.3,
        0,
        selection=held,
    )

    # Points close to others apart, closer than along the chain not to count their neighbors
    nearest_point = t.node("GeometryNodeIndexOfNearest", 35.5, -9, {"Position": position}).outputs[
        "Index"
    ]
    offset = t.vmath("SUBTRACT", position, at(nearest_point, position, 35.5, -11), x=35.5, y=-13)
    apart = t.math(
        "MINIMUM",
        t.math(
            "MULTIPLY", t.attribute(".chain_rest", "FLOAT", 35, -14), SELF_SPACING, x=35.5, y=-14
        ),
        t.math("MULTIPLY", inputs["Radius"], SELF_RADIUS, x=35.5, y=-15),
        x=35.5,
        y=-16,
    )
    near_distance = t.vmath("LENGTH", offset, x=35.5, y=-17)
    separated = t.node(
        "GeometryNodeSetPosition",
        35.5,
        0,
        {
            "Geometry": geometry,
            "Selection": t.node(
                "FunctionNodeBooleanMath",
                35.5,
                -18,
                {
                    0: t.node(
                        "FunctionNodeBooleanMath",
                        35.4,
                        -18,
                        {
                            0: held,
                            1: t.math(
                                "GREATER_THAN",
                                t.math(
                                    "ABSOLUTE",
                                    t.math("SUBTRACT", nearest_point, index, x=35.3, y=-24),
                                    x=35.4,
                                    y=-24,
                                ),
                                SELF_SKIP,
                                x=35.4,
                                y=-25,
                            ),
                        },
                        operation="AND",
                    ).outputs[0],
                    1: t.math("LESS_THAN", near_distance, apart, x=35.5, y=-19),
                },
                operation="AND",
            ).outputs[0],
            "Offset": t.vmath(
                "SCALE",
                t.vmath("NORMALIZE", offset, x=35.5, y=-20),
                t.math(
                    "MULTIPLY",
                    t.math("SUBTRACT", apart, near_distance, x=35.5, y=-21),
                    0.5,
                    x=35.5,
                    y=-22,
                ),
                x=35.5,
                y=-23,
            ),
        },
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSwitch",
        35.75,
        0,
        {"Switch": inputs["Self Collision"], "False": geometry, "True": separated},
        input_type="GEOMETRY",
    ).outputs[0]

    # Points on the Colliders pushed out and slowed down by the friction
    nearest, normal = (
        t.node(
            "GeometryNodeSampleNearestSurface",
            36,
            -2 - 2 * i,
            {"Mesh": inputs["Colliders"], "Value": value, "Sample Position": position},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, value in enumerate(
            (position, t.node("GeometryNodeInputNormal", 35, -12).outputs["Normal"])
        )
    )
    normal = t.vmath("NORMALIZE", normal, x=37, y=-4)
    side = t.vmath(
        "DOT_PRODUCT", t.vmath("SUBTRACT", position, nearest, x=37, y=-2), normal, x=38, y=-2
    )
    hit = t.node(
        "FunctionNodeBooleanMath",
        39,
        -3,
        {
            0: t.math("LESS_THAN", side, inputs["Radius"], x=39, y=-2),
            1: t.math("GREATER_THAN", side, -MAX_DEPTH, x=39, y=-4),
        },
        operation="AND",
    ).outputs[0]
    hit = t.node("FunctionNodeBooleanMath", 40, -3, {0: hit, 1: held}, operation="AND").outputs[0]
    surface = t.vmath(
        "ADD", nearest, t.vmath("SCALE", normal, inputs["Radius"], x=38, y=-5), x=39, y=-5
    )
    # Not bouncing: the speed going in is lost, slowing the sliding one by the friction
    speed = t.attribute(".chain_velocity", "FLOAT_VECTOR", 38, -7)
    along_normal = t.vmath("DOT_PRODUCT", speed, normal, x=39, y=-7)
    slide = t.vmath(
        "SUBTRACT", speed, t.vmath("SCALE", normal, along_normal, x=40, y=-7), x=40, y=-6
    )
    stop = t.math(
        "MINIMUM",
        t.math(
            "DIVIDE",
            t.math(
                "MULTIPLY",
                inputs["Friction"],
                t.math(
                    "ADD",
                    t.math(
                        "MAXIMUM",
                        t.math("MULTIPLY", along_normal, -1.0, x=40, y=-9),
                        0.0,
                        x=41,
                        y=-9,
                    ),
                    t.math(
                        "DIVIDE",
                        t.math("SUBTRACT", inputs["Radius"], side, x=40, y=-8),
                        step,
                        x=41,
                        y=-8,
                    ),
                    x=42,
                    y=-8,
                ),
                x=43,
                y=-8,
            ),
            t.vmath("LENGTH", slide, x=43, y=-9),
            x=44,
            y=-8,
        ),
        1.0,
        x=45,
        y=-8,
    )
    contact = t.node("GeometryNodeCaptureAttribute", 44, 0, {"Geometry": geometry}, domain="POINT")
    contact.capture_items.new("BOOLEAN", "Hit")
    contact.capture_items.new("VECTOR", "Point")
    contact.capture_items.new("VECTOR", "Speed")
    t.connect(hit, contact.inputs["Hit"])
    t.connect(
        t.vmath(
            "SUBTRACT",
            surface,
            t.vmath("SCALE", slide, t.math("MULTIPLY", stop, step, x=45, y=-7), x=45, y=-6),
            x=46,
            y=-5,
        ),
        contact.inputs["Point"],
    )
    t.connect(
        t.vmath(
            "ADD",
            t.vmath("SCALE", slide, t.math("SUBTRACT", 1.0, stop, x=45, y=-11), x=46, y=-11),
            t.vmath(
                "SCALE", normal, t.math("MAXIMUM", along_normal, 0.0, x=45, y=-12), x=46, y=-12
            ),
            x=47,
            y=-11,
        ),
        contact.inputs["Speed"],
    )
    collided = t.node(
        "GeometryNodeSetPosition",
        44.5,
        0,
        {
            "Geometry": contact.outputs["Geometry"],
            "Selection": contact.outputs["Hit"],
            "Position": contact.outputs["Point"],
        },
    ).outputs[0]
    collided = t.store(
        collided,
        ".chain_velocity",
        "FLOAT_VECTOR",
        contact.outputs["Speed"],
        44.75,
        0,
        selection=contact.outputs["Hit"],
    )
    has_faces = t.math(
        "GREATER_THAN",
        t.node(
            "GeometryNodeAttributeDomainSize", 42, -10, {"Geometry": inputs["Colliders"]}
        ).outputs["Face Count"],
        0.0,
        x=43,
        y=-10,
    )
    geometry = t.node(
        "GeometryNodeSwitch",
        45,
        0,
        {
            "Switch": t.node(
                "FunctionNodeBooleanMath",
                44,
                -10,
                {0: inputs["Collision"], 1: has_faces},
                operation="AND",
            ).outputs[0],
            "False": geometry,
            "True": collided,
        },
        input_type="GEOMETRY",
    ).outputs[0]

    t.connect(geometry, steps_out.inputs["Geometry"])

    t.section("Normals")
    # Normals carried along by the chain, for the links not to spin, kept the same along it
    last = t.math(
        "SUBTRACT",
        t.node(
            "GeometryNodeAttributeDomainSize",
            50,
            -2,
            {"Geometry": steps_out.outputs["Geometry"]},
            component="POINTCLOUD",
        ).outputs["Point Count"],
        1.0,
        x=51,
        y=-2,
    )
    before = t.math("MAXIMUM", t.math("SUBTRACT", index, 1.0, x=51, y=-3), 0.0, x=52, y=-3)
    after = t.math("MINIMUM", t.math("ADD", index, 1.0, x=51, y=-4), last, x=52, y=-4)
    tangent = t.vmath(
        "NORMALIZE",
        t.vmath("SUBTRACT", at(after, position, 53, -5), at(before, position, 53, -7), x=54, y=-5),
        x=55,
        y=-5,
    )
    normal = t.attribute(".chain_normal", "FLOAT_VECTOR", 53, -9)
    around = t.vmath(
        "ADD",
        t.vmath("ADD", at(before, normal, 54, -9), at(after, normal, 54, -11), x=55, y=-9),
        t.vmath("SCALE", normal, 2.0, x=55, y=-11),
        x=56,
        y=-9,
    )
    normal = t.vmath(
        "NORMALIZE",
        t.vmath(
            "SUBTRACT",
            around,
            t.vmath(
                "SCALE", tangent, t.vmath("DOT_PRODUCT", around, tangent, x=56, y=-6), x=57, y=-6
            ),
            x=58,
            y=-6,
        ),
        x=59,
        y=-6,
    )
    geometry = t.store(
        steps_out.outputs["Geometry"], ".chain_normal", "FLOAT_VECTOR", normal, 60, 0
    )
    t.node("NodeGroupOutput", 61, 0, {"Geometry": geometry})
    t.arrange()
    return ng


def crop(t, geometry, around, x, y):
    """Faces of the geometry in the bounding box of the other one, grown by CROP and their size"""
    position = t.node("GeometryNodeInputPosition", x, y - 5).outputs["Position"]
    box = t.node("GeometryNodeBoundBox", x, y - 1, {"Geometry": around}).outputs
    center = t.node(
        "GeometryNodeFieldOnDomain",
        x + 1,
        y - 5,
        {"Value": position},
        data_type="FLOAT_VECTOR",
        domain="FACE",
    ).outputs[0]
    size = t.node(
        "GeometryNodeFieldOnDomain",
        x + 2,
        y - 5,
        {"Value": t.vmath("DISTANCE", position, center, x=x + 2, y=y - 6)},
        domain="CORNER",
    ).outputs[0]
    margin = t.math("MULTIPLY_ADD", size, 2.0, CROP, x=x + 3, y=y - 5)
    inside = [
        t.node(
            "FunctionNodeCompare",
            x + 4,
            y - 2 - i,
            {"A": position, "B": t.vmath(operation, box[corner], margin, x=x + 3, y=y - 2 - i)},
            data_type="VECTOR",
            mode="ELEMENT",
            operation=compare,
        ).outputs[0]
        for i, (corner, operation, compare) in enumerate(
            (("Min", "SUBTRACT", "GREATER_EQUAL"), ("Max", "ADD", "LESS_EQUAL"))
        )
    ]
    outside = t.node(
        "FunctionNodeBooleanMath", x + 5, y - 2, {0: inside[0], 1: inside[1]}, operation="NAND"
    ).outputs[0]
    return t.node(
        "GeometryNodeDeleteGeometry",
        x + 6,
        y,
        {"Geometry": geometry, "Selection": outside},
        domain="FACE",
    ).outputs[0]


def build_node_group(solver):
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng["MustardUI Version"] = VERSION
    ng.description = (
        "Chain through the Anchors in the order of their names, hanging with the gravity, "
        "keeping its length and colliding with the Colliders"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Anchors",
        "NodeSocketCollection",
        description="Empties the chain is attached to, through them in the order of their names. "
        "Parent them to what they follow",
    )
    add_input(
        ng,
        "Length",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=1.0,
        min_value=0.0,
        max_value=1000.0,
        description="Length of the chain from the first to the last Anchor, shared by the parts "
        "between them by how far apart they are at the Start Frame",
    )
    add_input(
        ng,
        "Free Length",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0,
        min_value=0.0,
        max_value=1000.0,
        description="Length of the chain hanging loose after the last Anchor",
    )
    add_input(
        ng,
        "Keep Length",
        "NodeSocketBool",
        default_value=True,
        description="Keep the length of the chain, pulling it taut when the Anchors move apart. "
        "When disabled, the simulated parts between the Anchors stretch as they move apart, "
        "keeping how much they hang",
    )
    add_input(ng, "Material", "NodeSocketMaterial")
    add_input(
        ng,
        "Link Length",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.02,
        min_value=0.001,
        max_value=10.0,
        description="Outer length of the links",
    )
    add_input(
        ng,
        "Link Width",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.012,
        min_value=0.001,
        max_value=10.0,
        description="Outer width of the links",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0025,
        min_value=0.0001,
        max_value=1.0,
        description="Thickness of the wire of the links",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        default_value=16,
        min_value=4,
        max_value=64,
        description="Segments around each link, half of them around its wire",
    )
    add_input(
        ng,
        "Dynamics",
        "NodeSocketBool",
        default_value=True,
        description="Simulate the chain swinging from the Start Frame. When disabled, it is "
        "always at rest in its hanging shape, at any frame without playing the animation",
    )
    add_input(
        ng,
        "Start Frame",
        "NodeSocketInt",
        default_value=1,
        description="Frame the simulation starts from, with the chain at rest",
    )
    add_input(
        ng,
        "Gravity",
        "NodeSocketFloat",
        default_value=9.81,
        min_value=0.0,
        max_value=100.0,
        description="Acceleration pulling the chain down",
    )
    add_input(
        ng,
        "Damping",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        max_value=100.0,
        description="How fast the chain stops swinging",
    )
    add_input(
        ng,
        "Time Scale",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the simulation",
    )
    add_input(
        ng,
        "Segment Length",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.03,
        min_value=0.002,
        max_value=10.0,
        description="Distance between the points of the simulation along the chain, lower for "
        "tighter bends and collisions, slower",
    )
    add_input(
        ng,
        "Substeps",
        "NodeSocketInt",
        default_value=16,
        min_value=1,
        max_value=100,
        description="Steps of the simulation for each frame, higher for a stiffer chain, slower",
    )
    add_input(
        ng,
        "Iterations",
        "NodeSocketInt",
        default_value=4,
        min_value=1,
        max_value=100,
        description="Passes keeping the length for each substep, higher for a stiffer chain, "
        "slower",
    )
    add_input(
        ng,
        "Collision",
        "NodeSocketBool",
        default_value=True,
        description="Collide with the Colliders",
    )
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects the chain collides with",
    )
    add_input(
        ng,
        "Self Collision",
        "NodeSocketBool",
        default_value=True,
        description="Collide with itself, e.g. piling up on the floor, slower",
    )
    add_input(
        ng,
        "Friction",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="How much the Colliders stop the chain sliding on them",
    )
    add_input(
        ng,
        "Distance",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0,
        min_value=0.0,
        max_value=1.0,
        description="Distance kept from the Colliders, besides the width of the links",
    )
    # Added last, as the modifiers keep their values by the identifiers of the inputs, in this order
    add_input(
        ng,
        "Tip Control",
        "NodeSocketObject",
        description="Empty moving the tip of the Free Length, as far as the chain reaches",
    )
    add_input(
        ng,
        "Hold",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="How much the tip follows the Tip Control at each frame, 0 to let it hang "
        "loose. Keyframe it to grab and drop the tip",
    )
    arrange_interface(
        ng,
        (
            (None, "Tip", False, None, ("Tip Control", "Hold")),
            (None, "Links", True, None, ("Link Length", "Link Width", "Thickness", "Resolution")),
            (
                None,
                "Dynamics",
                True,
                "Dynamics",
                (
                    "Start Frame",
                    "Gravity",
                    "Damping",
                    "Time Scale",
                    "Segment Length",
                    "Substeps",
                    "Iterations",
                ),
            ),
            (
                None,
                "Collision",
                True,
                "Collision",
                ("Colliders", "Self Collision", "Friction", "Distance"),
            ),
        ),
    )

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    position = t.node("GeometryNodeInputPosition", -2, -3).outputs["Position"]
    index = t.node("GeometryNodeInputIndex", -2, -4).outputs[0]

    def switch(condition, false, true, x, y, input_type="FLOAT"):
        return t.node(
            "GeometryNodeSwitch",
            x,
            y,
            {"Switch": condition, "False": false, "True": true},
            input_type=input_type,
        ).outputs[0]

    t.section("Anchors")
    # By the name of the objects, as the node sorts them
    anchors = t.node(
        "GeometryNodeCollectionInfo",
        0,
        0,
        {"Collection": inputs["Anchors"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    anchors = t.node("GeometryNodeInstancesToPoints", 1, 0, {"Instances": anchors}).outputs[0]
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        0,
        -3,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", 1, -3, {"Geometry": colliders}).outputs[0]

    # The object is an instance only if there is one
    tip_info = t.node(
        "GeometryNodeObjectInfo",
        0,
        -6,
        {"Object": inputs["Tip Control"], "As Instance": True},
        transform_space="RELATIVE",
    ).outputs
    tip_held = t.node(
        "FunctionNodeBooleanMath",
        2,
        -6,
        {
            0: t.math(
                "GREATER_THAN",
                t.node(
                    "GeometryNodeAttributeDomainSize",
                    1,
                    -7,
                    {"Geometry": tip_info["Geometry"]},
                    component="INSTANCES",
                ).outputs["Instance Count"],
                0.0,
                x=1,
                y=-8,
            ),
            1: t.math("GREATER_THAN", inputs["Free Length"], 0.0, x=1, y=-9),
        },
        operation="AND",
    ).outputs[0]
    hold = switch(tip_held, 0.0, inputs["Hold"], 2, -8)
    held = t.math("GREATER_THAN", hold, 0.0, x=3, y=-8)

    t.section("Parts between the Anchors")
    last = t.math(
        "SUBTRACT",
        t.node(
            "GeometryNodeAttributeDomainSize",
            2,
            -2,
            {"Geometry": anchors},
            component="POINTCLOUD",
        ).outputs["Point Count"],
        1.0,
        x=3,
        y=-2,
    )
    is_last = t.math("GREATER_THAN", index, t.math("SUBTRACT", last, 0.5, x=3, y=-3), x=4, y=-3)
    following = t.node(
        "GeometryNodeFieldAtIndex",
        4,
        -5,
        {
            "Index": t.math("MINIMUM", t.math("ADD", index, 1.0, x=3, y=-5), last, x=4, y=-6),
            "Value": position,
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    distance = t.vmath("DISTANCE", position, following, x=5, y=-5)
    total = t.node(
        "GeometryNodeAccumulateField", 6, -5, {"Value": distance}, data_type="FLOAT"
    ).outputs["Total"]
    # Evenly when the Anchors are all at the same place
    share = switch(
        t.math("GREATER_THAN", total, 1e-6, x=7, y=-6),
        t.math("DIVIDE", 1.0, t.math("MAXIMUM", last, 1.0, x=7, y=-7), x=8, y=-7),
        t.math("DIVIDE", distance, total, x=8, y=-5),
        9,
        -5,
    )
    part = t.math("MULTIPLY", inputs["Length"], share, x=10, y=-5)
    segment = t.math("MAXIMUM", inputs["Segment Length"], 0.002, x=10, y=-7)
    free_points = t.math(
        "MINIMUM",
        t.math("CEIL", t.math("DIVIDE", inputs["Free Length"], segment, x=11, y=-8), x=12, y=-8),
        MAX_POINTS,
        x=13,
        y=-8,
    )
    points = switch(
        is_last,
        t.math(
            "MINIMUM",
            t.math(
                "MAXIMUM",
                t.math("ROUND", t.math("DIVIDE", part, segment, x=11, y=-6), x=12, y=-6),
                1.0,
                x=13,
                y=-6,
            ),
            MAX_POINTS,
            x=14,
            y=-6,
        ),
        t.math("ADD", free_points, 1.0, x=14, y=-8),
        15,
        -6,
    )
    rest = switch(
        is_last,
        t.math("DIVIDE", part, points, x=16, y=-5),
        t.math("DIVIDE", inputs["Free Length"], free_points, x=16, y=-8),
        17,
        -5,
    )
    part_distance = switch(is_last, distance, 0.0, 12, -10)
    part = switch(is_last, part, 0.0, 12, -11)
    # The Free Length hangs like the other parts when the tip is held
    to_tip = t.vmath("SUBTRACT", tip_info["Location"], position, x=13, y=-12)
    tip_goal = t.vmath(
        "ADD",
        position,
        t.vmath(
            "SCALE",
            t.vmath("NORMALIZE", to_tip, x=14, y=-12),
            t.math(
                "MINIMUM",
                t.vmath("LENGTH", to_tip, x=14, y=-13),
                inputs["Free Length"],
                x=15,
                y=-13,
            ),
            x=15,
            y=-12,
        ),
        x=16,
        y=-12,
    )
    tip_part = t.node(
        "FunctionNodeBooleanMath", 16, -14, {0: is_last, 1: held}, operation="AND"
    ).outputs[0]
    following = switch(tip_part, following, tip_goal, 17, -12, "VECTOR")
    shape_length = switch(tip_part, part, inputs["Free Length"], 17, -14)

    t.section("Hanging Shape")
    # Each part between two Anchors is a catenary y = a cosh((x - x0) / a), s = a sinh((x - x0) / a)
    # with x along the ground, as nothing else pulls it. sinh(u) / u = r, with u = h / 2a
    offset = t.vmath("SUBTRACT", following, position, x=0, y=-1)
    flat = t.vmath("MULTIPLY", offset, (1.0, 1.0, 0.0), x=1, y=-1)
    height = t.node("ShaderNodeSeparateXYZ", 1, -3, {0: offset}).outputs["Z"]
    ground = t.math("MAXIMUM", t.vmath("LENGTH", flat, x=2, y=-1), 1e-4, x=3, y=-1)
    across = switch(
        t.math("GREATER_THAN", t.vmath("LENGTH", flat, x=2, y=-2), 1e-4, x=3, y=-2),
        (1.0, 0.0, 0.0),
        t.vmath("NORMALIZE", flat, x=3, y=-3),
        4,
        -2,
        "VECTOR",
    )
    ratio = t.math(
        "MAXIMUM",
        t.math(
            "DIVIDE",
            t.math(
                "SQRT",
                t.math(
                    "MAXIMUM",
                    t.math(
                        "SUBTRACT",
                        t.math("MULTIPLY", shape_length, shape_length, x=1, y=-4),
                        t.math("MULTIPLY", height, height, x=1, y=-5),
                        x=2,
                        y=-4,
                    ),
                    0.0,
                    x=3,
                    y=-4,
                ),
                x=4,
                y=-4,
            ),
            ground,
            x=5,
            y=-4,
        ),
        1.0,
        x=6,
        y=-4,
    )
    # From above the solution, the smallest of the small and of the large r approximations
    double = t.math("MULTIPLY", ratio, 2.0, x=7, y=-5)
    log = t.math("LOGARITHM", double, 2.718281828, x=8, y=-5)
    u = t.math(
        "MINIMUM",
        t.math(
            "SQRT",
            t.math("MULTIPLY", t.math("SUBTRACT", ratio, 1.0, x=7, y=-4), 6.0, x=8, y=-4),
            x=9,
            y=-4,
        ),
        t.math(
            "ADD",
            t.math("ADD", log, t.math("LOGARITHM", log, 2.718281828, x=9, y=-5), x=10, y=-5),
            1.0,
            x=11,
            y=-5,
        ),
        x=12,
        y=-4,
    )
    for i in range(CATENARY_STEPS):
        x = 13 + 3 * i
        u = t.math(
            "SUBTRACT",
            u,
            t.math(
                "DIVIDE",
                t.math(
                    "SUBTRACT",
                    t.math("SINH", u, x=x, y=-5),
                    t.math("MULTIPLY", ratio, u, x=x, y=-6),
                    x=x + 1,
                    y=-5,
                ),
                t.math("SUBTRACT", t.math("COSH", u, x=x, y=-7), ratio, x=x + 1, y=-7),
                x=x + 2,
                y=-5,
            ),
            x=x + 2,
            y=-4,
        )
    size = t.math("DIVIDE", ground, t.math("MULTIPLY", u, 2.0, x=25, y=-5), x=26, y=-4)
    slope = t.math("DIVIDE", height, shape_length, x=25, y=-6)
    # atanh of the slope, the lowest point from the Anchor along the ground and along the chain
    lowest = t.math(
        "SUBTRACT",
        t.math("MULTIPLY", ground, 0.5, x=26, y=-7),
        t.math(
            "MULTIPLY",
            size,
            t.math(
                "MULTIPLY",
                t.math(
                    "LOGARITHM",
                    t.math(
                        "DIVIDE",
                        t.math("ADD", 1.0, slope, x=26, y=-8),
                        t.math("SUBTRACT", 1.0, slope, x=26, y=-9),
                        x=27,
                        y=-8,
                    ),
                    2.718281828,
                    x=28,
                    y=-8,
                ),
                0.5,
                x=29,
                y=-8,
            ),
            x=30,
            y=-8,
        ),
        x=31,
        y=-7,
    )
    arc_start = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", size, -1.0, x=31, y=-9),
        t.math("SINH", t.math("DIVIDE", lowest, size, x=31, y=-10), x=32, y=-10),
        x=33,
        y=-9,
    )
    hanging = t.math(
        "GREATER_THAN",
        shape_length,
        t.math("MULTIPLY", t.vmath("LENGTH", offset, x=30, y=-11), TAUT, x=31, y=-11),
        x=32,
        y=-11,
    )

    geometry = anchors
    for i, (name, data_type, value) in enumerate(
        (
            (".chain_anchor", "INT", index),
            (".chain_points", "INT", points),
            (".chain_rest_start", "FLOAT", rest),
            (".chain_distance", "FLOAT", part_distance),
            (".chain_part", "FLOAT", part),
            (".chain_following", "FLOAT_VECTOR", following),
            (".chain_shape_length", "FLOAT", shape_length),
            (".chain_across", "FLOAT_VECTOR", across),
            (".chain_size", "FLOAT", size),
            (".chain_lowest", "FLOAT", lowest),
            (".chain_arc", "FLOAT", arc_start),
            (".chain_hanging", "FLOAT", hanging),
        )
    ):
        geometry = t.store(geometry, name, data_type, value, 34 + i, 0)
    duplicate = t.node(
        "GeometryNodeDuplicateElements",
        24,
        0,
        {"Geometry": geometry, "Amount": t.attribute(".chain_points", "INT", 23, -2)},
        domain="POINT",
    )
    in_part = t.store(
        duplicate.outputs["Geometry"],
        ".chain_in_part",
        "INT",
        duplicate.outputs["Duplicate Index"],
        25,
        0,
    )

    t.section("Points of the Chain")
    count = t.attribute(".chain_points", "INT", 25, -2)
    rest = t.attribute(".chain_rest_start", "FLOAT", 25, -3)
    in_part_value = t.attribute(".chain_in_part", "INT", 25, -4)
    length = t.attribute(".chain_part", "FLOAT", 25, -6)
    # The last Anchor has no part after it, but the loose one
    tail = t.math("LESS_THAN", length, 1e-9, x=26, y=-6)
    first = t.math("SUBTRACT", index, in_part_value, x=26, y=-4)
    end = switch(tail, t.math("ADD", first, count, x=27, y=-4), -1.0, 28, -4)
    geometry = in_part
    for i, (name, data_type, value) in enumerate(
        (
            (".chain_first", "INT", first),
            (".chain_end", "INT", end),
            (
                ".chain_free_start",
                "FLOAT",
                t.math("GREATER_THAN", in_part_value, 0.5, x=26, y=-7),
            ),
            (
                ".chain_tip",
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    t.math(
                        "MULTIPLY",
                        tail,
                        t.math("GREATER_THAN", in_part_value, 0.5, x=26, y=-30),
                        x=27,
                        y=-30,
                    ),
                    t.math(
                        "COMPARE",
                        in_part_value,
                        t.math("SUBTRACT", count, 1.0, x=26, y=-31),
                        0.1,
                        x=27,
                        y=-31,
                    ),
                    x=28,
                    y=-30,
                ),
            ),
            (".chain_from_start", "FLOAT", t.math("MULTIPLY", in_part_value, rest, x=26, y=-8)),
            (
                ".chain_to_start",
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    t.math("SUBTRACT", count, in_part_value, x=26, y=-9),
                    rest,
                    x=27,
                    y=-9,
                ),
            ),
            (".chain_velocity", "FLOAT_VECTOR", (0.0, 0.0, 0.0)),
        )
    ):
        geometry = t.store(geometry, name, data_type, value, 29 + i, 0)

    # At rest on the catenary, or straight down the loose part, the points by their distance along
    # the chain to keep its length: sinh is the arc, the rest follows from it
    distance_along = t.math("MULTIPLY", in_part_value, rest, x=26, y=-10)
    size = t.attribute(".chain_size", "FLOAT", 26, -11)
    arc_start = t.attribute(".chain_arc", "FLOAT", 26, -12)
    arc = t.math("ADD", arc_start, distance_along, x=27, y=-10)
    ratio = t.math("DIVIDE", arc, size, x=28, y=-10)
    # asinh, of the absolute value not to lose precision
    magnitude = t.math("ABSOLUTE", ratio, x=29, y=-10)
    asinh = t.math(
        "MULTIPLY",
        t.math("SIGN", ratio, x=30, y=-11),
        t.math(
            "LOGARITHM",
            t.math(
                "ADD",
                magnitude,
                t.math(
                    "SQRT",
                    t.math(
                        "ADD",
                        t.math("MULTIPLY", magnitude, magnitude, x=30, y=-12),
                        1.0,
                        x=31,
                        y=-12,
                    ),
                    x=32,
                    y=-12,
                ),
                x=33,
                y=-12,
            ),
            2.718281828,
            x=34,
            y=-12,
        ),
        x=35,
        y=-11,
    )
    along_ground = t.math(
        "ADD",
        t.attribute(".chain_lowest", "FLOAT", 34, -14),
        t.math("MULTIPLY", size, asinh, x=35, y=-13),
        x=36,
        y=-13,
    )
    rise = t.math(
        "SUBTRACT",
        t.math(
            "SQRT",
            t.math(
                "ADD",
                t.math("MULTIPLY", size, size, x=34, y=-16),
                t.math("MULTIPLY", arc, arc, x=34, y=-17),
                x=35,
                y=-16,
            ),
            x=36,
            y=-16,
        ),
        t.math(
            "SQRT",
            t.math(
                "ADD",
                t.math("MULTIPLY", size, size, x=34, y=-18),
                t.math("MULTIPLY", arc_start, arc_start, x=34, y=-19),
                x=35,
                y=-18,
            ),
            x=36,
            y=-18,
        ),
        x=37,
        y=-16,
    )
    catenary = t.vmath(
        "ADD",
        t.vmath(
            "ADD",
            position,
            t.vmath(
                "SCALE",
                t.attribute(".chain_across", "FLOAT_VECTOR", 36, -20),
                along_ground,
                x=37,
                y=-20,
            ),
            x=38,
            y=-20,
        ),
        t.node("ShaderNodeCombineXYZ", 38, -16, {"Z": rise}).outputs[0],
        x=39,
        y=-16,
    )
    straight = t.node(
        "ShaderNodeMix",
        38,
        -22,
        {
            "Factor": t.math(
                "DIVIDE",
                distance_along,
                t.attribute(".chain_shape_length", "FLOAT", 36, -22),
                x=37,
                y=-22,
            ),
            "A": position,
            "B": t.attribute(".chain_following", "FLOAT_VECTOR", 37, -23),
        },
        data_type="VECTOR",
    ).outputs["Result"]
    shape = switch(
        t.math("GREATER_THAN", t.attribute(".chain_hanging", "FLOAT", 38, -24), 0.5, x=39, y=-24),
        straight,
        catenary,
        40,
        -16,
        "VECTOR",
    )
    down = t.vmath(
        "ADD",
        position,
        t.node(
            "ShaderNodeCombineXYZ",
            39,
            -26,
            {"Z": t.math("MULTIPLY", distance_along, -1.0, x=38, y=-26)},
        ).outputs[0],
        x=40,
        y=-26,
    )
    geometry = t.node(
        "GeometryNodeSetPosition",
        41,
        0,
        {
            "Geometry": geometry,
            "Position": switch(
                t.node(
                    "FunctionNodeBooleanMath",
                    40,
                    -28,
                    {
                        0: tail,
                        1: t.math(
                            "LESS_THAN",
                            t.attribute(".chain_shape_length", "FLOAT", 39, -28),
                            1e-9,
                            x=39,
                            y=-29,
                        ),
                    },
                    operation="AND",
                ).outputs[0],
                shape,
                down,
                41,
                -16,
                "VECTOR",
            ),
        },
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSetPosition",
        42,
        0,
        {
            "Geometry": geometry,
            "Selection": t.math("GREATER_THAN", in_part_value, 0.5, x=41, y=-20),
            "Offset": t.node(
                "FunctionNodeRandomValue",
                42,
                -20,
                {0: (-BUCKLING, -BUCKLING, 0.0), 1: (BUCKLING, BUCKLING, 0.0)},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
        },
    ).outputs[0]

    # Normals across the plane of the chain, along Y for a hanging one
    positions = [
        t.node(
            "GeometryNodeSampleIndex",
            36,
            -18 - 2 * i,
            {"Geometry": anchors, "Value": position, "Index": value},
            data_type="FLOAT_VECTOR",
            domain="POINT",
            clamp=True,
        ).outputs[0]
        for i, value in enumerate((0, last))
    ]
    across = t.vmath(
        "CROSS_PRODUCT",
        t.vmath("SUBTRACT", positions[1], positions[0], x=37, y=-18),
        (0.0, 0.0, 1.0),
        x=38,
        y=-18,
    )
    normal = switch(
        t.math("GREATER_THAN", t.vmath("LENGTH", across, x=39, y=-19), 1e-6, x=40, y=-19),
        (0.0, 1.0, 0.0),
        t.vmath("NORMALIZE", across, x=39, y=-18),
        41,
        -18,
        "VECTOR",
    )
    start = t.store(geometry, ".chain_normal", "FLOAT_VECTOR", normal, 42, 0)

    def solve(geometry, anchors, colliders, time, substeps, damping, x, y):
        node = t.node(
            "GeometryNodeGroup",
            x,
            y,
            {
                "Geometry": geometry,
                "Anchors": anchors,
                "Colliders": colliders,
                "Time": time,
                "Substeps": substeps,
                "Iterations": inputs["Iterations"],
                "Gravity": inputs["Gravity"],
                "Damping": damping,
                "Friction": inputs["Friction"],
                "Radius": radius,
                "Collision": inputs["Collision"],
                "Self Collision": inputs["Self Collision"],
                "Keep Length": inputs["Keep Length"],
                "Tip": tip_info["Location"],
                "Hold": hold,
            },
            node_tree=solver,
        )
        return node.outputs[0]

    radius = t.math(
        "ADD",
        t.math("MULTIPLY", inputs["Link Width"], 0.5, x=42, y=-3),
        inputs["Distance"],
        x=43,
        y=-3,
    )

    t.section("At Rest", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 42, -9).outputs["Frame"]
    waiting = t.math(
        "LESS_THAN", frame, t.math("ADD", inputs["Start Frame"], 0.5, x=42, y=-10), x=43, y=-9
    )
    # Out of the Colliders from the hanging shape, when needed: repeat zones always run
    rest_colliders = crop(t, colliders, start, 38, -6)
    needed = t.node(
        "FunctionNodeBooleanMath",
        44,
        -9,
        {
            0: inputs["Collision"],
            1: t.math(
                "GREATER_THAN",
                t.node(
                    "GeometryNodeAttributeDomainSize", 42, -6, {"Geometry": rest_colliders}
                ).outputs["Face Count"],
                0.0,
                x=43,
                y=-6,
            ),
        },
        operation="AND",
    ).outputs[0]
    needed = t.node(
        "FunctionNodeBooleanMath",
        45,
        -9,
        {
            0: needed,
            1: t.node(
                "FunctionNodeBooleanMath",
                44,
                -10,
                {0: inputs["Dynamics"], 1: waiting},
                operation="IMPLY",
            ).outputs[0],
        },
        operation="AND",
    ).outputs[0]
    # Each part inside the Colliders moved out on one side, by the average shortest way out of its
    # points, as they would go out on all sides. Up if there is no such a side
    outside = start
    for i in range(OUT_ROUNDS):
        x, y = 38 + 8 * i, -12
        nearest, normal = (
            t.node(
                "GeometryNodeSampleNearestSurface",
                x,
                y - 2 * j,
                {"Mesh": rest_colliders, "Value": value, "Sample Position": position},
                data_type="FLOAT_VECTOR",
            ).outputs["Value"]
            for j, value in enumerate(
                (position, t.node("GeometryNodeInputNormal", x - 1, y - 2).outputs["Normal"])
            )
        )
        normal = t.vmath("NORMALIZE", normal, x=x + 1, y=y - 2)
        depth = t.math(
            "MULTIPLY",
            t.vmath(
                "DOT_PRODUCT",
                t.vmath("SUBTRACT", position, nearest, x=x + 1, y=y),
                normal,
                x=x + 2,
                y=y,
            ),
            -1.0,
            x=x + 3,
            y=y,
        )
        inside = t.node(
            "FunctionNodeBooleanMath",
            x + 4,
            y,
            {
                0: t.math("GREATER_THAN", depth, 0.0, x=x + 3, y=y - 1),
                1: t.math(
                    "GREATER_THAN",
                    t.attribute(".chain_free_start", "FLOAT", x + 2, y - 2),
                    0.5,
                    x=x + 3,
                    y=y - 2,
                ),
            },
            operation="AND",
        ).outputs[0]
        way = t.node(
            "GeometryNodeAccumulateField",
            x + 5,
            y,
            {
                "Value": t.vmath(
                    "SCALE",
                    normal,
                    switch(inside, 0.0, depth, x + 4, y - 3),
                    x=x + 5,
                    y=y - 2,
                ),
                "Group ID": t.attribute(".chain_anchor", "INT", x + 4, y - 4),
            },
            data_type="FLOAT_VECTOR",
        ).outputs["Total"]
        way = t.vmath(
            "NORMALIZE", t.vmath("ADD", way, (0.0, 0.0, 1e-4), x=x + 6, y=y), x=x + 7, y=y
        )
        ray = t.node(
            "GeometryNodeRaycast",
            x + 6,
            y - 2,
            {"Target Geometry": rest_colliders, "Ray Direction": way, "Ray Length": 1000.0},
            data_type="FLOAT",
        ).outputs
        outside = t.node(
            "GeometryNodeSetPosition",
            x + 7,
            -9,
            {
                "Geometry": outside,
                "Selection": t.node(
                    "FunctionNodeBooleanMath",
                    x + 7,
                    y - 2,
                    {0: inside, 1: ray["Is Hit"]},
                    operation="AND",
                ).outputs[0],
                "Position": t.vmath(
                    "ADD",
                    ray["Hit Position"],
                    t.vmath("SCALE", way, radius, x=x + 7, y=y - 4),
                    x=x + 8,
                    y=y - 2,
                ),
            },
        ).outputs[0]

    relax_in = t.node(
        "GeometryNodeRepeatInput",
        55,
        0,
        {"Iterations": switch(needed, 0, RELAX_STEPS, 55, -3, "INT")},
    )
    relax_out = t.node("GeometryNodeRepeatOutput", 57, 0)
    relax_in.pair_with_output(relax_out)
    t.connect(outside, relax_in.inputs["Geometry"])
    t.connect(
        solve(
            relax_in.outputs["Geometry"],
            anchors,
            rest_colliders,
            1.0 / 24.0,
            RELAX_SUBSTEPS,
            RELAX_DAMPING,
            56,
            0,
        ),
        relax_out.inputs["Geometry"],
    )
    relaxed = solve(
        relax_out.outputs["Geometry"],
        anchors,
        rest_colliders,
        FINISH_TIME,
        FINISH_SUBSTEPS,
        RELAX_DAMPING,
        58,
        0,
    )
    relaxed = t.store(relaxed, ".chain_velocity", "FLOAT_VECTOR", (0.0, 0.0, 0.0), 59, 0)
    at_rest = switch(needed, start, relaxed, 60, 0, "GEOMETRY")

    t.section("Simulation")
    # Links going into the zone are evaluated at each frame, the rest shape only when needed
    waiting_shape = t.node(
        "GeometryNodeSwitch", 50, -6, {"Switch": waiting, "True": at_rest}, input_type="GEOMETRY"
    ).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 51, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 56, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(at_rest, sim_in.inputs["Geometry"])
    moved = solve(
        sim_in.outputs["Geometry"],
        anchors,
        crop(t, colliders, sim_in.outputs["Geometry"], 44, -8),
        t.math("MULTIPLY", sim_in.outputs["Delta Time"], inputs["Time Scale"], x=52, y=-5),
        inputs["Substeps"],
        inputs["Damping"],
        53,
        0,
    )
    moved = switch(
        t.math("GREATER_THAN", sim_in.outputs["Delta Time"], 0.0, x=53, y=-5),
        sim_in.outputs["Geometry"],
        moved,
        54,
        0,
        "GEOMETRY",
    )
    t.connect(switch(waiting, moved, waiting_shape, 55, 0, "GEOMETRY"), sim_out.inputs["Geometry"])
    state = switch(inputs["Dynamics"], at_rest, sim_out.outputs["Geometry"], 55, 0, "GEOMETRY")

    t.section("Links", row=True)
    # The links as many as they fit along the chain, each one going through the next
    wire = inputs["Thickness"]
    spacing = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT", inputs["Link Length"], t.math("MULTIPLY", wire, 2.0, x=0, y=-2), x=1, y=-2
        ),
        t.math("MULTIPLY", inputs["Link Length"], 0.25, x=1, y=-3),
        x=2,
        y=-2,
    )
    attached = t.math("GREATER_THAN", last, 0.5, x=1, y=-5)
    chain_length = t.math(
        "ADD",
        t.math("MULTIPLY", inputs["Length"], attached, x=2, y=-5),
        inputs["Free Length"],
        x=3,
        y=-5,
    )
    links = t.math(
        "MINIMUM",
        t.math(
            "MAXIMUM",
            t.math("ROUND", t.math("DIVIDE", chain_length, spacing, x=4, y=-5), x=5, y=-5),
            1.0,
            x=6,
            y=-5,
        ),
        MAX_LINKS,
        x=7,
        y=-5,
    )
    # Taken from here, not to be interpolated on the links
    kept = t.store(
        state,
        ".link_normal",
        "FLOAT_VECTOR",
        t.attribute(".chain_normal", "FLOAT_VECTOR", 0, -7),
        1,
        0,
    )
    kept = t.node(
        "GeometryNodeRemoveAttribute",
        2,
        0,
        {"Geometry": kept, "Pattern Mode": "Wildcard", "Name": ".chain_*"},
    ).outputs[0]
    curve = t.node("GeometryNodePointsToCurves", 3, 0, {"Points": kept, "Weight": index}).outputs[0]
    curve = t.node(
        "GeometryNodeCurveSplineType", 4, 0, {"Curve": curve}, spline_type="CATMULL_ROM"
    ).outputs[0]
    curve_length = t.node("GeometryNodeCurveLength", 5, -3, {"Curve": curve}).outputs[0]
    centers = t.node(
        "GeometryNodeCurveToPoints",
        8,
        0,
        {"Curve": curve, "Count": t.math("ADD", links, 1.0, x=8, y=-5)},
        mode="COUNT",
    )
    link = t.node("GeometryNodeInputIndex", 9, -2).outputs[0]
    odd = t.math("GREATER_THAN", t.math("FLOORED_MODULO", link, 2.0, x=9, y=-3), 0.5, x=10, y=-3)
    tangent = centers.outputs["Tangent"]
    across = t.attribute(".link_normal", "FLOAT_VECTOR", 9, -5)
    secondary = switch(
        odd, across, t.vmath("CROSS_PRODUCT", tangent, across, x=10, y=-5), 11, -5, "VECTOR"
    )
    rotation = t.node(
        "FunctionNodeAxesToRotation",
        12,
        -3,
        {"Primary Axis": tangent, "Secondary Axis": secondary},
        primary_axis="X",
        secondary_axis="Y",
    ).outputs[0]

    # The ring of a link: half of a circle moved at each end
    circle = t.node(
        "GeometryNodeCurvePrimitiveCircle",
        6,
        -8,
        {"Resolution": inputs["Resolution"], "Radius": 1.0},
        mode="RADIUS",
    ).outputs["Curve"]
    middle_x = t.math("SUBTRACT", inputs["Link Length"], wire, x=6, y=-11)
    middle_y = t.math("SUBTRACT", inputs["Link Width"], wire, x=6, y=-12)
    radius_y = t.math("MULTIPLY", t.math("MAXIMUM", middle_y, 0.0, x=7, y=-12), 0.5, x=8, y=-12)
    long_part = t.math(
        "MAXIMUM",
        t.math("MULTIPLY", t.math("SUBTRACT", middle_x, middle_y, x=7, y=-11), 0.5, x=8, y=-11),
        0.0,
        x=9,
        y=-11,
    )
    position_xyz = t.node("ShaderNodeSeparateXYZ", 7, -13, {0: position}).outputs
    ring = t.node(
        "GeometryNodeSetPosition",
        10,
        -8,
        {
            "Geometry": circle,
            "Position": t.node(
                "ShaderNodeCombineXYZ",
                10,
                -12,
                {
                    "X": t.math(
                        "ADD",
                        t.math("MULTIPLY", position_xyz[0], radius_y, x=9, y=-13),
                        t.math(
                            "MULTIPLY",
                            t.math("SIGN", position_xyz[0], x=9, y=-14),
                            long_part,
                            x=10,
                            y=-14,
                        ),
                        x=11,
                        y=-13,
                    ),
                    "Y": t.math("MULTIPLY", position_xyz[1], radius_y, x=9, y=-15),
                },
            ).outputs[0],
        },
    ).outputs[0]
    profile = t.node(
        "GeometryNodeCurvePrimitiveCircle",
        10,
        -16,
        {
            "Resolution": t.math(
                "MAXIMUM",
                t.math("MULTIPLY", inputs["Resolution"], 0.5, x=9, y=-17),
                3.0,
                x=10,
                y=-17,
            ),
            "Radius": t.math("MULTIPLY", wire, 0.5, x=9, y=-18),
        },
        mode="RADIUS",
    ).outputs["Curve"]
    mesh = t.node(
        "GeometryNodeCurveToMesh", 11, -8, {"Curve": ring, "Profile Curve": profile}
    ).outputs[0]
    mesh = t.node("GeometryNodeSetShadeSmooth", 12, -8, {"Mesh": mesh}).outputs[0]

    # Stretched along when the chain is, not to come apart
    stretch = t.math(
        "DIVIDE",
        t.math("DIVIDE", curve_length, links, x=9, y=-20),
        spacing,
        x=10,
        y=-20,
    )
    instances = t.node(
        "GeometryNodeInstanceOnPoints",
        13,
        0,
        {
            "Points": centers.outputs["Points"],
            "Instance": mesh,
            "Rotation": rotation,
            "Scale": t.node(
                "ShaderNodeCombineXYZ", 11, -20, {"X": stretch, "Y": 1.0, "Z": 1.0}
            ).outputs[0],
        },
    ).outputs[0]
    # For the material to tell the links apart
    instances = t.store(
        instances,
        "chain_link",
        "FLOAT",
        t.node("FunctionNodeRandomValue", 13, -3, data_type="FLOAT").outputs[0],
        14,
        0,
        domain="INSTANCE",
    )
    instances = t.node(
        "GeometryNodeRemoveAttribute",
        15,
        0,
        {"Geometry": instances, "Pattern Mode": "Wildcard", "Name": ".link_*"},
    ).outputs[0]
    realized = t.node("GeometryNodeRealizeInstances", 16, 0, {"Geometry": instances}).outputs[0]
    output = t.node(
        "GeometryNodeSetMaterial", 17, 0, {"Geometry": realized, "Material": inputs["Material"]}
    ).outputs[0]
    t.node("NodeGroupOutput", 18, 0, {"Geometry": output})
    t.arrange()
    return ng


def build_material():
    material = bpy.data.materials.new(NODE_GROUP)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree)
    link = t.node("ShaderNodeAttribute", -3, 0, attribute_name="chain_link").outputs["Fac"]
    bsdf = t.node(
        "ShaderNodeBsdfPrincipled",
        -1,
        0,
        {
            "Base Color": (0.62, 0.62, 0.64, 1.0),
            "Metallic": 1.0,
            "Roughness": t.node(
                "ShaderNodeMapRange", -2, 0, {"Value": link, "To Min": 0.22, "To Max": 0.38}
            ).outputs[0],
        },
    )
    t.node("ShaderNodeOutputMaterial", 1, 0, {"Surface": bsdf.outputs[0]})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(build_solver()), build_material()))
