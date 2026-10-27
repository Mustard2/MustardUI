# Build crush.blend: the Crush node group
# Usage: Blender --background --factory-startup --python crush_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, socket, write
from imprints_build import blur_iterations, shallowest_neighbor

RESOURCE = "crush.blend"
NODE_GROUP = "MustardUI Crush"
# Cells of the grid the Colliders are found on along the longest side of the mesh, and of the
# coarser one the crush spreads on along the Stiffness, at least
GRID = 128
STIFFNESS_CELLS = 8
# Cells of the grid around the mesh, to find the Colliders at its sides
MARGIN = 2
# Rounds spreading the crush, at most, and its fading away from the pressed points, by round
SPREAD_ROUNDS = 256
FADE = 2.0
# Steepest rise of the mesh around the crush, not to leave thin parts standing, found by jump
# flooding with offsets halving from this many cells
SLOPE = 1.0
FLOOR_SLOPE = 2.0
JUMP = 128
NEIGHBORS = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]
# Share of the depth under the top of the mesh the crush fades out by, the parts under it
# squeezed together keeping their order
COLLAPSE = 0.85
# Depth of the folds at full Crumple, relative to their size
FOLD_DEPTH = 0.3
# Share of its height a floor keeps crushed, as its slab and rubble
RUBBLE = 0.15
# Debris chips: speed up as a share of their speed out, bounce, speed kept sliding on the plane
DEBRIS_RISE = 0.15
DEBRIS_BOUNCE = 0.2
DEBRIS_SLIDE = 0.6
# Chips squeezed out at this times the speed their side is crushed, fanning out by up to this
# angle in radians from it
DEBRIS_EJECT = 1.5
DEBRIS_FAN = 0.6
# Parts chips are thrown from, at least this share of the size of the mesh
DEBRIS_PART = 0.2
# Thickness of the chips over their size, and their tilt in radians, so they lie on the plane
CHIP_FLAT = 0.4
CHIP_TILT = 0.15
# Buckles: depth between the creases relative to the Crumple Size, share of it the creases take,
# and how unevenly they run
BUCKLE_STEP = 3.0
BUCKLE_CREASE = 0.25
BUCKLE_WOBBLE = 0.5
# Loose parts: share of the height over them crushed before they are thrown, upward share of
# their speed, speed and spin kept at each bounce, gravity and seed of the Chance
TRIGGER = 0.15
LIFT = 0.5
FRICTION = 0.7
# Spin kept at each bounce, tipping or lying stably, sideways spin share wobbling the parts
# thrown, points of a part touching the plane within this share of its size, and its inertia
# relative to its size squared
SPIN_KEEP = 0.9
SETTLE = 0.5
WOBBLE = 0.3
CONTACT = 0.1
INERTIA = 0.4
# Turn of the parts on the plane in a frame at most, not to overshoot as they tip
MAX_TURN = 0.2
# Points of each part kept, about, to find where it touches the plane, besides the furthest out
# along these directions and their opposites
SUPPORT = 256
DIRECTIONS = (
    (1, 0, 0),
    (0, 1, 0),
    (0, 0, 1),
    (1, 1, 1),
    (1, 1, -1),
    (1, -1, 1),
    (-1, 1, 1),
    (1, 1, 0),
    (1, -1, 0),
    (1, 0, 1),
    (1, 0, -1),
    (0, 1, 1),
    (0, 1, -1),
)
# Resting: middle over the touching points within this share of the size, and slowest turn in a
# frame kept
STABLE = 0.15
REST_TURN = 0.005
# Seconds on the plane the parts may tip over for, held by the friction after it
TIP_TIME = 1.0
GRAVITY = 9.81
SEED = 7


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Crush the mesh where the Colliders press it down, flattening it on the plane under it, "
        "as a car stepped on"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects crushing the mesh from above, e.g. the body and the shoes",
    )
    add_input(
        ng,
        "Subdivisions",
        "NodeSocketInt",
        default_value=0,
        min_value=0,
        max_value=8,
        description="Subdivisions of the mesh before the crush, for detailed dents and folds",
    )
    add_input(
        ng,
        "Stiffness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.3,
        min_value=0.0,
        description="Distance the crush spreads over around the Colliders, bending the mesh "
        "down with it",
    )
    add_input(
        ng,
        "Flat Height",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.05,
        min_value=0.0,
        description="Height of the mesh crushed flat on the plane under it",
    )
    add_input(
        ng,
        "Bulge",
        "NodeSocketFloat",
        default_value=0.3,
        min_value=0.0,
        max_value=2.0,
        description="Sideways bulge of the crushed sides, relative to how far they are crushed",
    )
    add_input(
        ng,
        "Crumple",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Depth of the folds of the crushed parts",
    )
    add_input(
        ng,
        "Crumple Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.05,
        min_value=0.001,
        description="Size of the folds",
    )
    add_input(
        ng,
        "Lasting",
        "NodeSocketBool",
        default_value=True,
        description="Keep the mesh crushed after the Colliders leave, simulated from the Start "
        "Frame",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    add_input(
        ng,
        "Loose Parts",
        "NodeSocketBool",
        default_value=False,
        description="Throw small parts off to the sides once crushed, as rigid bodies, e.g. "
        "the wheels",
    )
    add_input(
        ng,
        "Parts",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group of the parts always thrown off, the parts touching each other "
        "thrown together",
    )
    add_input(
        ng,
        "Chance",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Chance of the other parts smaller than the Part Size to be thrown off",
    )
    add_input(
        ng,
        "Part Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.5,
        min_value=0.0,
        description="Size of the largest parts thrown off by Chance",
    )
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        default_value=3.0,
        min_value=0.0,
        description="Speed of the parts thrown off, in meters per second",
    )
    add_input(
        ng,
        "Bounce",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Share of the speed kept by the parts bouncing on the plane under the mesh",
    )
    buckle = add_input(
        ng,
        "Buckle",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.8,
        min_value=0.0,
        max_value=1.0,
        description="Bend the mesh around the crush at a few creases, flat between them as sheet "
        "metal, instead of smoothly",
    )
    ng.interface.move(
        buckle, list(ng.interface.items_tree).index(ng.interface.items_tree["Crumple Size"]) + 1
    )
    floors = add_input(
        ng,
        "Floor Height",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0,
        min_value=0.0,
        description="Height of the floors of a building, crushed one after the other from the top "
        "down to slabs of rubble, the ones under them standing, 0 for none",
    )
    ng.interface.move(
        floors, list(ng.interface.items_tree).index(ng.interface.items_tree["Flat Height"]) + 1
    )
    add_input(
        ng,
        "Debris",
        "NodeSocketBool",
        default_value=False,
        description="Throw chips of the sides out as they are crushed, resting on the plane under "
        "the mesh",
    )
    add_input(
        ng,
        "Debris Amount",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        description="Chips thrown per square meter of the sides crushed all the way",
    )
    add_input(
        ng,
        "Debris Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.05,
        min_value=0.0,
        description="Size of the largest chips",
    )
    add_input(
        ng,
        "Debris Speed",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        description="Speed of the chips thrown out, in meters per second",
    )
    arrange_interface(
        ng,
        [
            (None, "Lasting", False, "Lasting", ["Start Frame"]),
            (
                None,
                "Physics",
                True,
                None,
                ["Loose Parts", "Parts", "Chance", "Part Size", "Speed", "Bounce"],
            ),
            (None, "Debris", True, "Debris", ["Debris Amount", "Debris Size", "Debris Speed"]),
        ],
    )

    t = Tree(ng)
    t.section("Mesh")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    geometry = t.node(
        "GeometryNodeSubdivideMesh",
        -1,
        0,
        {"Mesh": inputs["Geometry"], "Level": inputs["Subdivisions"]},
    ).outputs[0]
    # Everything in the space of the mesh, the distances scaled as its object
    transform = t.node(
        "GeometryNodeObjectInfo",
        -1,
        -2,
        {"Object": t.node("GeometryNodeSelfObject", -2, -2).outputs[0]},
        transform_space="ORIGINAL",
    ).outputs["Transform"]
    scale = t.vmath(
        "DOT_PRODUCT",
        t.node("FunctionNodeSeparateTransform", 0, -2, {0: transform}).outputs["Scale"],
        (1 / 3,) * 3,
        x=1,
        y=-2,
    )
    stiffness, flat, size, part_size, speed, storey, chip, chip_speed = (
        t.math("DIVIDE", inputs[name], scale, x=2, y=-3 - i)
        for i, name in enumerate(
            (
                "Stiffness",
                "Flat Height",
                "Crumple Size",
                "Part Size",
                "Speed",
                "Floor Height",
                "Debris Size",
                "Debris Speed",
            )
        )
    )
    box = t.node("GeometryNodeBoundBox", 0, -7, {"Geometry": inputs["Geometry"]}).outputs
    low = t.node("ShaderNodeSeparateXYZ", 1, -7, {0: box["Min"]}).outputs
    extent = t.node(
        "ShaderNodeSeparateXYZ",
        1,
        -11,
        {0: t.vmath("SUBTRACT", box["Max"], box["Min"], x=0.5, y=-11)},
    ).outputs
    floor, height = low["Z"], extent["Z"]
    spacing = t.math(
        "MAXIMUM",
        t.math(
            "DIVIDE", t.math("MAXIMUM", extent["X"], extent["Y"], x=2, y=-11), GRID, x=2.5, y=-11
        ),
        1e-4,
        x=3,
        y=-11,
    )
    coarse = t.math(
        "MAXIMUM", t.math("DIVIDE", stiffness, STIFFNESS_CELLS, x=3, y=-12), spacing, x=3.5, y=-12
    )
    middle = t.node(
        "ShaderNodeSeparateXYZ",
        1.5,
        -13,
        {
            0: t.vmath(
                "SCALE", t.vmath("ADD", box["Min"], box["Max"], x=0.5, y=-13), 0.5, x=1, y=-13
            )
        },
    ).outputs

    t.section("Grid")
    grid, cells = new_grid(t, extent, middle, floor, spacing, 0, 0)
    # Height of the top of the mesh over each point, and next to the sides of the mesh as there
    position = t.node("GeometryNodeInputPosition", 4, -2).outputs[0]
    top = t.node(
        "GeometryNodeRaycast",
        5,
        -2,
        {
            "Target Geometry": inputs["Geometry"],
            "Source Position": t.vmath(
                "ADD",
                position,
                t.node(
                    "ShaderNodeCombineXYZ",
                    4,
                    -3,
                    {"Z": t.math("ADD", height, spacing, x=3.5, y=-3)},
                ).outputs[0],
                x=4.5,
                y=-2,
            ),
            "Ray Direction": (0.0, 0.0, -1.0),
            "Ray Length": t.math("MULTIPLY_ADD", spacing, 2.0, height, x=4.5, y=-4),
        },
    ).outputs
    top = t.math(
        "MULTIPLY",
        t.math(
            "MAXIMUM",
            t.math(
                "SUBTRACT",
                t.math("ADD", height, spacing, x=5, y=-4),
                top["Hit Distance"],
                x=6,
                y=-3,
            ),
            0.0,
            x=6.5,
            y=-3,
        ),
        top["Is Hit"],
        x=7,
        y=-2,
    )
    grid = t.store(grid, ".crush_top", "FLOAT", top, 7.5, 0)
    for i in range(MARGIN):
        top = t.attribute(".crush_top", "FLOAT", 8 + 4 * i, -2)
        neighbor = t.math(
            "MULTIPLY",
            shallowest_neighbor(t, t.math("MULTIPLY", top, -1.0, x=8 + 4 * i, y=-4), 8 + 4 * i, -5),
            -1.0,
            x=12 + 4 * i,
            y=-4,
        )
        empty = t.math("LESS_THAN", top, 1e-6, x=11 + 4 * i, y=-3)
        grid = t.store(
            grid,
            ".crush_top",
            "FLOAT",
            t.math("MULTIPLY_ADD", empty, neighbor, top, x=12.5 + 4 * i, y=-2),
            12.5 + 4 * i,
            0,
        )

    t.section("Colliders", row=True)
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        0,
        0,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", 1, 0, {"Geometry": colliders}).outputs[0]
    # Only the faces reaching the space over the grid, from under the plane by the height
    margin = t.math("MULTIPLY", spacing, MARGIN + 1, x=0, y=-2)
    co = t.node(
        "ShaderNodeSeparateXYZ", 0, -4, {0: t.node("GeometryNodeInputPosition", -1, -4).outputs[0]}
    ).outputs
    below = t.node(
        "ShaderNodeSeparateXYZ",
        1.5,
        -5,
        {
            0: t.vmath(
                "SUBTRACT",
                box["Min"],
                t.node(
                    "ShaderNodeCombineXYZ",
                    0.5,
                    -6,
                    {"X": margin, "Y": margin, "Z": t.math("ADD", margin, height, x=0, y=-6)},
                ).outputs[0],
                x=1,
                y=-5,
            )
        },
    ).outputs
    above = t.node(
        "ShaderNodeSeparateXYZ", 1.5, -7, {0: t.vmath("ADD", box["Max"], margin, x=1, y=-7)}
    ).outputs
    outside = None
    for i, axis in enumerate("XYZ"):
        for j, (operation, limit) in enumerate(
            (("LESS_THAN", below[axis]), ("GREATER_THAN", above[axis]))
        ):
            beyond = t.node(
                "FunctionNodeCompare",
                2,
                -5 - 2 * i - j,
                {"A": co[axis], "B": limit},
                data_type="FLOAT",
                operation=operation,
            ).outputs[0]
            # All the points of the face past the plane
            beyond = t.node(
                "GeometryNodeFieldOnDomain",
                3,
                -5 - 2 * i - j,
                {"Value": beyond},
                data_type="BOOLEAN",
                domain="POINT",
            ).outputs[0]
            outside = (
                beyond
                if outside is None
                else t.node(
                    "FunctionNodeBooleanMath",
                    4,
                    -5 - 2 * i - j,
                    {0: outside, 1: beyond},
                    operation="OR",
                ).outputs[0]
            )
    colliders = t.node(
        "GeometryNodeDeleteGeometry",
        5,
        0,
        {"Geometry": colliders, "Selection": outside},
        domain="FACE",
    ).outputs[0]

    t.section("Lasting")
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 9, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(grid, sim_in.inputs["Geometry"])
    state = t.node(
        "GeometryNodeSwitch",
        3,
        0,
        {"Switch": started, "False": grid, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    # Depth the lowest Collider surface over each point presses the top of the mesh down, up
    # from under the plane not to start inside the Colliders sinking a little in it
    top = t.attribute(".crush_top", "FLOAT", 3, -3)
    sole = t.node(
        "GeometryNodeRaycast",
        5,
        -3,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath(
                "SUBTRACT",
                t.node("GeometryNodeInputPosition", 3, -4).outputs[0],
                t.node("ShaderNodeCombineXYZ", 3, -5, {"Z": height}).outputs[0],
                x=4,
                y=-4,
            ),
            "Ray Direction": (0.0, 0.0, 1.0),
            "Ray Length": t.math("ADD", height, top, x=4, y=-6),
        },
    ).outputs
    pressed = t.math(
        "SUBTRACT",
        top,
        t.math("SUBTRACT", sole["Hit Distance"], height, x=6, y=-4),
        x=6.5,
        y=-3,
    )
    pressed = t.math(
        "MULTIPLY",
        t.math("MINIMUM", t.math("MAXIMUM", pressed, 0.0, x=7, y=-3), top, x=7.5, y=-3),
        sole["Is Hit"],
        x=8,
        y=-3,
    )
    state = t.store(state, ".crush_live", "FLOAT", pressed, 8, 0)
    kept = t.math(
        "MAXIMUM",
        t.attribute(".crush_kept", "FLOAT", 8, -5),
        t.attribute(".crush_live", "FLOAT", 8, -6),
        x=8.5,
        y=-5,
    )
    state = t.store(state, ".crush_kept", "FLOAT", kept, 8.5, 0)
    t.connect(state, sim_out.inputs["Geometry"])

    t.section("Spread", row=True)
    grid = sim_out.outputs["Geometry"]
    pressed = t.node(
        "GeometryNodeSwitch",
        0,
        -2,
        {
            "Switch": inputs["Lasting"],
            "False": t.attribute(".crush_live", "FLOAT", -1, -2),
            "True": t.attribute(".crush_kept", "FLOAT", -1, -3),
        },
        input_type="FLOAT",
    ).outputs[0]
    grid = t.store(grid, ".crush_pressed", "FLOAT", pressed, 1, 0)
    # The deepest crush in each cell of the coarser grid, not to miss thin Colliders
    spread, columns = new_grid(t, extent, middle, floor, coarse, 0, -12)
    co = t.node(
        "ShaderNodeSeparateXYZ",
        0,
        -16,
        {0: t.node("GeometryNodeInputPosition", -1, -16).outputs[0]},
    ).outputs
    cell = [
        t.math(
            "ROUND",
            t.math(
                "ADD",
                t.math(
                    "DIVIDE",
                    t.math("SUBTRACT", co[axis], middle[axis], x=0.5, y=-16 - i),
                    coarse,
                    x=1,
                    y=-16 - i,
                ),
                t.math(
                    "MULTIPLY", t.math("SUBTRACT", columns[i], 1, x=0.5, y=-18 - i), 0.5, x=1, y=-18
                ),
                x=1.5,
                y=-16 - i,
            ),
            x=2,
            y=-16 - i,
        )
        for i, axis in enumerate("XY")
    ]
    pooled = t.node(
        "GeometryNodeFieldMinAndMax",
        3,
        -15,
        {
            "Value": t.attribute(".crush_pressed", "FLOAT", 2, -15),
            "Group ID": t.math("MULTIPLY_ADD", cell[1], columns[0], cell[0], x=2.5, y=-16),
        },
        data_type="FLOAT",
    ).outputs["Max"]
    grid = t.store(grid, ".crush_pool", "FLOAT", pooled, 3.5, 0)
    pooled = t.node(
        "GeometryNodeSampleIndex",
        3,
        -13,
        {
            "Geometry": grid,
            "Value": t.attribute(".crush_pool", "FLOAT", 2, -14),
            "Index": t.node(
                "GeometryNodeSampleNearest",
                2.5,
                -13,
                {
                    "Geometry": grid,
                    "Sample Position": t.node("GeometryNodeInputPosition", 2, -13).outputs[0],
                },
            ).outputs[0],
        },
        data_type="FLOAT",
    ).outputs[0]
    spread = t.store(spread, ".crush_pressed", "FLOAT", pooled, 4, -12)
    spread = t.store(
        spread, ".crush_depth", "FLOAT", t.attribute(".crush_pressed", "FLOAT", 4, -14), 4.5, -12
    )
    # Spread over the Stiffness keeping the pressed points as deep, sinking less and less away
    # from them as on an elastic foundation
    rounds_in = t.node(
        "GeometryNodeRepeatInput",
        3,
        -12,
        {"Iterations": blur_iterations(t, stiffness, coarse, SPREAD_ROUNDS, 1, -20)},
    )
    rounds_out = t.node("GeometryNodeRepeatOutput", 7, -12)
    rounds_in.pair_with_output(rounds_out)
    t.connect(spread, rounds_in.inputs["Geometry"])
    ratio = t.math("DIVIDE", coarse, stiffness, x=3, y=-21)
    keep = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", t.math("MULTIPLY", ratio, ratio, x=3.5, y=-21), FADE, x=4, y=-21),
        x=4.5,
        y=-21,
        clamp=True,
    )
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        4,
        -14,
        {"Value": t.attribute(".crush_depth", "FLOAT", 3, -14), "Iterations": 1},
        data_type="FLOAT",
    ).outputs[0]
    depth = t.math(
        "MAXIMUM",
        t.attribute(".crush_pressed", "FLOAT", 5, -15),
        t.math("MULTIPLY", blurred, keep, x=5, y=-14),
        x=5.5,
        y=-14,
    )
    t.connect(
        t.store(rounds_in.outputs["Geometry"], ".crush_depth", "FLOAT", depth, 6, -12),
        rounds_out.inputs["Geometry"],
    )
    spread = rounds_out.outputs["Geometry"]

    # On the grid, around the pressed points at most as steeply as the Slope, not to leave thin
    # parts standing: the deepest of the points at each offset, less the rise to there
    grid = t.store(
        grid, ".crush_slope", "FLOAT", t.attribute(".crush_pressed", "FLOAT", 4, -2), 4.5, 0
    )
    # Rise per cell, steeper for floors: buildings fail straight down, not in a ramp
    rise = t.math(
        "MULTIPLY",
        spacing,
        t.node(
            "GeometryNodeSwitch",
            3,
            -6,
            {
                "Switch": t.math("GREATER_THAN", inputs["Floor Height"], 0.0, x=2.5, y=-6),
                "False": SLOPE,
                "True": FLOOR_SLOPE,
            },
            input_type="FLOAT",
        ).outputs[0],
        x=3.5,
        y=-6,
    )
    jumps_in = t.node("GeometryNodeRepeatInput", 5, 0, {"Iterations": JUMP.bit_length() + 1})
    jumps_out = t.node("GeometryNodeRepeatOutput", 12, 0)
    jumps_in.pair_with_output(jumps_out)
    t.connect(grid, jumps_in.inputs["Geometry"])
    # Offsets of JUMP to 1 cell, then 1 again
    jump = t.math(
        "MAXIMUM",
        t.math(
            "POWER",
            2.0,
            t.math("SUBTRACT", JUMP.bit_length() - 1, jumps_in.outputs["Iteration"], x=5, y=-3),
            x=5.5,
            y=-3,
        ),
        1.0,
        x=6,
        y=-3,
    )
    index = t.node("GeometryNodeInputIndex", 5, -5).outputs[0]
    column = t.math("FLOOR", t.math("DIVIDE", index, cells[1], x=5.5, y=-5), x=6, y=-5)
    row = t.math("SUBTRACT", index, t.math("MULTIPLY", column, cells[1], x=6, y=-6), x=6.5, y=-6)
    slope = t.attribute(".crush_slope", "FLOAT", 6, -2)
    for i, (dx, dy) in enumerate(NEIGHBORS):
        y = -8 - 3 * i
        at = [
            t.math("MULTIPLY_ADD", jump, d, value, x=7, y=y - j) if d else value
            for j, (d, value) in enumerate(((dx, column), (dy, row)))
        ]
        inside = t.node(
            "FunctionNodeBooleanMath",
            8.5,
            y,
            {
                0: t.node(
                    "FunctionNodeBooleanMath",
                    8,
                    y,
                    {
                        0: t.node(
                            "FunctionNodeCompare",
                            7.5,
                            y,
                            {"A": at[0], "B": t.math("SUBTRACT", cells[0], 1, x=7, y=y - 2)},
                            data_type="FLOAT",
                            operation="LESS_EQUAL",
                        ).outputs[0],
                        1: t.node(
                            "FunctionNodeCompare",
                            7.5,
                            y - 1,
                            {"A": at[1], "B": t.math("SUBTRACT", cells[1], 1, x=7, y=y - 3)},
                            data_type="FLOAT",
                            operation="LESS_EQUAL",
                        ).outputs[0],
                    },
                    operation="AND",
                ).outputs[0],
                1: t.node(
                    "FunctionNodeCompare",
                    8,
                    y - 1,
                    {"A": t.math("MINIMUM", at[0], at[1], x=7.5, y=y - 2), "B": 0.0},
                    data_type="FLOAT",
                    operation="GREATER_EQUAL",
                ).outputs[0],
            },
            operation="AND",
        ).outputs[0]
        reached = t.node(
            "GeometryNodeSampleIndex",
            9,
            y,
            {
                "Geometry": jumps_in.outputs["Geometry"],
                "Value": slope,
                "Index": t.math("MULTIPLY_ADD", at[0], cells[1], at[1], x=8.5, y=y - 2),
            },
            data_type="FLOAT",
        ).outputs[0]
        reached = t.math(
            "SUBTRACT",
            reached,
            t.math(
                "MULTIPLY",
                jump,
                t.math("MULTIPLY", rise, (dx * dx + dy * dy) ** 0.5, x=8.5, y=y - 1),
                x=9,
                y=y - 1,
            ),
            x=9.5,
            y=y,
        )
        reached = t.node(
            "GeometryNodeSwitch",
            10,
            y,
            {"Switch": inside, "False": 0.0, "True": reached},
            input_type="FLOAT",
        ).outputs[0]
        slope = t.math("MAXIMUM", slope, reached, x=10.5, y=-2 - i)
    t.connect(
        t.store(jumps_in.outputs["Geometry"], ".crush_slope", "FLOAT", slope, 11, 0),
        jumps_out.inputs["Geometry"],
    )
    grid = jumps_out.outputs["Geometry"]
    # Middle of the crush, weighted by its depth, the parts thrown away from it
    pressed = t.attribute(".crush_pressed", "FLOAT", 12, -4)
    sums = [
        t.node(
            "GeometryNodeAttributeStatistic",
            13,
            -4 - 2 * i,
            {"Geometry": grid, "Attribute": value},
            data_type=data_type,
        ).outputs["Sum"]
        for i, (value, data_type) in enumerate(
            (
                (
                    t.vmath(
                        "SCALE",
                        t.node("GeometryNodeInputPosition", 12, -5).outputs[0],
                        pressed,
                        x=12.5,
                        y=-4,
                    ),
                    "FLOAT_VECTOR",
                ),
                (pressed, "FLOAT"),
            )
        )
    ]
    focus = t.vmath(
        "SCALE",
        sums[0],
        t.math("DIVIDE", 1.0, t.math("MAXIMUM", sums[1], 1e-9, x=13.5, y=-6), x=14, y=-6),
        x=14.5,
        y=-4,
    )

    # As deep as on the grid, or spread on the coarser one, buckled, on the grid
    plane = t.node(
        "ShaderNodeSeparateXYZ",
        0,
        -30,
        {0: t.node("GeometryNodeInputPosition", -1, -30).outputs[0]},
    ).outputs
    grid = t.store(
        grid,
        ".crush_final",
        "FLOAT",
        buckled(
            t,
            t.math(
                "MAXIMUM",
                t.attribute(".crush_slope", "FLOAT", 0, -31),
                t.node(
                    "GeometryNodeSampleNearestSurface",
                    0,
                    -32,
                    {
                        "Mesh": spread,
                        "Value": t.attribute(".crush_depth", "FLOAT", -1, -32),
                        "Sample Position": t.node("GeometryNodeInputPosition", -1, -33).outputs[0],
                    },
                    data_type="FLOAT",
                ).outputs["Value"],
                x=0.5,
                y=-31,
            ),
            t.attribute(".crush_pressed", "FLOAT", 0, -34),
            plane,
            size,
            inputs["Buckle"],
            1,
            -30,
        ),
        10,
        -28,
    )

    t.section("Crush", row=True)
    position = t.node("GeometryNodeInputPosition", 0, -2).outputs[0]
    co = t.node("ShaderNodeSeparateXYZ", 1, -2, {0: position}).outputs
    sample = t.node(
        "ShaderNodeSeparateXYZ",
        3,
        -2,
        {
            0: bilinear(
                t,
                grid,
                t.node(
                    "ShaderNodeCombineXYZ",
                    1,
                    -4,
                    {
                        "X": t.attribute(".crush_top", "FLOAT", 0, -4),
                        "Y": t.attribute(".crush_final", "FLOAT", 0, -5),
                        "Z": t.attribute(".crush_pressed", "FLOAT", 0, -6),
                    },
                ).outputs[0],
                cells,
                middle,
                spacing,
                co,
                2,
                -2,
            )
        },
    ).outputs
    top, depth = sample["X"], sample["Y"]
    # The top pressed down by the depth, the parts under it less and less, squeezed together down
    # to the Flat Height on the plane in the order they were
    h = t.math("SUBTRACT", co["Z"], floor, x=3, y=-4)
    sink = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT",
            depth,
            # The points over the top found on the grid, as on curved sides, as at the top
            t.math(
                "MULTIPLY",
                t.math("MAXIMUM", t.math("SUBTRACT", top, h, x=3.5, y=-3), 0.0, x=4, y=-3),
                COLLAPSE,
                x=4.5,
                y=-3,
            ),
            x=5,
            y=-2,
        ),
        0.0,
        x=5.5,
        y=-2,
    )
    flattened = t.math(
        "DIVIDE",
        t.math("MULTIPLY", h, t.math("MINIMUM", flat, top, x=4, y=-5), x=5, y=-5),
        t.math("MAXIMUM", top, 1e-6, x=4, y=-6),
        x=5.5,
        y=-5,
    )
    crushed = t.math("MAXIMUM", t.math("SUBTRACT", h, sink, x=6, y=-2), flattened, x=6.5, y=-2)
    # With floors, crushed one after the other from the top
    storeys = t.math("GREATER_THAN", inputs["Floor Height"], 0.0, x=5, y=-20)
    # Each of the four columns around the point crushed by its floors, mixed after, only the
    # columns reaching up to it: next to a column lower or empty, as out of the walls, mixing
    # their top and depth would leave it hanging
    blended = [pancaked(t, h, top, depth, storey, -20, -20)]
    weights, values = [], []
    for i, (value, weight) in enumerate(
        bilinear(
            t,
            grid,
            t.node(
                "ShaderNodeCombineXYZ",
                -30,
                -40,
                {
                    "X": t.attribute(".crush_top", "FLOAT", -31, -40),
                    "Y": t.attribute(".crush_final", "FLOAT", -31, -41),
                },
            ).outputs[0],
            cells,
            middle,
            spacing,
            co,
            -28,
            -40,
            corners=True,
        )
    ):
        column = t.node("ShaderNodeSeparateXYZ", -24, -40 - 30 * i, {0: value}).outputs
        reach = t.math(
            "GREATER_THAN",
            column["X"],
            t.math("SUBTRACT", h, spacing, x=-24, y=-42 - 30 * i),
            x=-23.5,
            y=-41 - 30 * i,
        )
        weights.append(t.math("MULTIPLY", weight, reach, x=-23, y=-41 - 30 * i))
        values.append(pancaked(t, h, column["X"], column["Y"], storey, -22, -40 - 30 * i))
    total = t.math(
        "ADD",
        t.math("ADD", weights[0], weights[1], x=0, y=-160),
        t.math("ADD", weights[2], weights[3], x=0, y=-161),
        x=0.5,
        y=-160,
    )
    reached = t.math("GREATER_THAN", total, 1e-6, x=1, y=-161)
    mixed = []
    for k in range(4):
        part = [
            t.math("MULTIPLY", w, v[k], x=1, y=-162 - 4 * k - j)
            for j, (w, v) in enumerate(zip(weights, values, strict=True))
        ]
        part = t.math(
            "DIVIDE",
            t.math(
                "ADD",
                t.math("ADD", part[0], part[1], x=1.5, y=-162 - 4 * k),
                t.math("ADD", part[2], part[3], x=1.5, y=-163 - 4 * k),
                x=2,
                y=-162 - 4 * k,
            ),
            t.math("MAXIMUM", total, 1e-6, x=1.5, y=-164 - 4 * k),
            x=2.5,
            y=-162 - 4 * k,
        )
        mixed.append(
            t.node(
                "GeometryNodeSwitch",
                3,
                -162 - 4 * k,
                {"Switch": reached, "False": blended[0][k], "True": part},
                input_type="FLOAT",
            ).outputs[0]
        )
    pancake, floor_share, floor_lost, along = mixed
    crushed = t.node(
        "GeometryNodeSwitch",
        6.8,
        -2,
        {"Switch": storeys, "False": crushed, "True": pancake},
        input_type="FLOAT",
    ).outputs[0]
    move = t.math("SUBTRACT", h, crushed, x=7, y=-2)
    # How far the point is crushed, for the debris: its floor, or its column
    spilled = t.node(
        "GeometryNodeSwitch",
        7,
        -20,
        {
            "Switch": storeys,
            "False": t.math(
                "DIVIDE", depth, t.math("MAXIMUM", top, 1e-6, x=6, y=-21), x=6.5, y=-20, clamp=True
            ),
            "True": floor_share,
        },
        input_type="FLOAT",
    ).outputs[0]

    # Sides bulging out as a barrel, most halfway up, away from the middle of the mesh, and
    # crumpled where crushed, the same for the layers on top of each other, as both sides of a
    # panel, not to tear them apart
    up = t.math("DIVIDE", h, t.math("MAXIMUM", top, 1e-6, x=6, y=-8), x=6.5, y=-8, clamp=True)
    barrel = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", up, t.math("SUBTRACT", 1.0, up, x=7, y=-9), x=7.5, y=-8),
        4.0,
        x=8,
        y=-8,
    )
    away = t.node(
        "ShaderNodeCombineXYZ",
        7.5,
        -6,
        {
            axis: t.math(
                "DIVIDE",
                t.math("SUBTRACT", co[axis], middle[axis], x=6.5, y=-6 - i),
                t.math("MAXIMUM", extent[axis], 1e-6, x=6.5, y=-7 - i),
                x=7,
                y=-6 - i,
            )
            for i, axis in enumerate("XY")
        },
    ).outputs[0]
    # With floors each crushed floor bulging out as its walls fold, its rubble spilling
    swell = t.node(
        "GeometryNodeSwitch",
        8,
        -7.5,
        {
            "Switch": storeys,
            "False": t.math("MULTIPLY", move, barrel, x=7.5, y=-7.5),
            "True": t.math(
                "MULTIPLY",
                floor_lost,
                t.math(
                    "MULTIPLY",
                    t.math(
                        "MULTIPLY", along, t.math("SUBTRACT", 1.0, along, x=6.5, y=-23), x=7, y=-23
                    ),
                    4.0,
                    x=7.5,
                    y=-23,
                ),
                x=7.8,
                y=-23,
            ),
        },
        input_type="FLOAT",
    ).outputs[0]
    bulge = t.vmath(
        "SCALE",
        t.vmath("NORMALIZE", away, x=8, y=-6),
        t.math("MULTIPLY", swell, inputs["Bulge"], x=8.5, y=-7),
        x=9,
        y=-6,
    )
    folds = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Crumple"], FOLD_DEPTH, x=7.5, y=-11),
        t.math("MINIMUM", move, size, x=8, y=-10),
        x=8.5,
        y=-10,
    )
    frequency = t.math("DIVIDE", 1.0, size, x=6, y=-9)
    # Flat parts creased, sides rippled, by the slant of the normals, the same on both sides of
    # a panel
    normal = t.node("GeometryNodeInputNormal", 6, -14).outputs["Normal"]
    flat = t.math(
        "POWER",
        t.node("ShaderNodeSeparateXYZ", 6.5, -14, {0: normal}).outputs["Z"],
        2.0,
        x=7,
        y=-14,
    )
    # Creases sunk along the cell edges of the plane, the cells raised
    edge = t.node(
        "ShaderNodeTexVoronoi",
        7,
        -9,
        {"Vector": position, "Scale": frequency},
        voronoi_dimensions="2D",
        feature="DISTANCE_TO_EDGE",
    ).outputs["Distance"]
    crease = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY_ADD",
            t.math("MULTIPLY", edge, 4.0, x=8, y=-9, clamp=True),
            2.0,
            -1.0,
            x=8.5,
            y=-9,
        ),
        t.math("MULTIPLY", folds, flat, x=8.5, y=-10),
        x=9,
        y=-9,
    )
    # Only sunk where the Colliders press, not to rise into them
    contact = t.math(
        "DIVIDE", sample["Z"], t.math("MAXIMUM", depth, 1e-6, x=8.5, y=-11), x=9, y=-11, clamp=True
    )
    crease = t.math(
        "SUBTRACT",
        crease,
        t.math("MULTIPLY", t.math("MAXIMUM", crease, 0.0, x=9.5, y=-10), contact, x=10, y=-10),
        x=10.5,
        y=-9,
    )
    # The sides rippled as they fold
    ripple = t.node(
        "ShaderNodeSeparateXYZ",
        8.5,
        -12,
        {
            0: t.vmath(
                "SUBTRACT",
                t.node(
                    "ShaderNodeTexNoise",
                    7,
                    -12,
                    {"Vector": position, "Scale": frequency, "Detail": 1.0},
                ).outputs["Color"],
                (0.5, 0.5, 0.5),
                x=8,
                y=-12,
            )
        },
    ).outputs
    side = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", folds, 2.0, x=9, y=-13),
        t.math("SUBTRACT", 1.0, flat, x=9, y=-14),
        x=9.5,
        y=-14,
    )
    offset = t.vmath(
        "ADD",
        bulge,
        t.node(
            "ShaderNodeCombineXYZ",
            9.5,
            -4,
            {
                "X": t.math(
                    "MULTIPLY",
                    ripple["X"],
                    side,
                    x=9.5,
                    y=-12,
                ),
                "Y": t.math(
                    "MULTIPLY",
                    ripple["Y"],
                    side,
                    x=9.5,
                    y=-13,
                ),
                "Z": t.math("SUBTRACT", crease, move, x=9, y=-4),
            },
        ).outputs[0],
        x=10.5,
        y=-4,
    )
    moved = t.node(
        "ShaderNodeSeparateXYZ", 11, -4, {0: t.vmath("ADD", position, offset, x=11, y=-3)}
    ).outputs
    # Never under the plane
    moved = t.node(
        "ShaderNodeCombineXYZ",
        12,
        -3,
        {
            "X": moved["X"],
            "Y": moved["Y"],
            "Z": t.math("MAXIMUM", moved["Z"], floor, x=11.5, y=-5),
        },
    ).outputs[0]
    # What the Loose Parts need, only with them
    kept = t.store(geometry, ".crush_rest", "FLOAT_VECTOR", position, 11, -2)
    kept = t.store(kept, ".crush_contact", "FLOAT", sample["Z"], 11.5, -2)
    kept = t.store(
        kept,
        ".crush_ratio",
        "FLOAT",
        t.math("DIVIDE", depth, t.math("MAXIMUM", top, 1e-6, x=11.5, y=-8), x=12, y=-8),
        12,
        -2,
    )
    geometry = t.node(
        "GeometryNodeSwitch",
        12.5,
        0,
        {"Switch": inputs["Loose Parts"], "False": geometry, "True": kept},
        input_type="GEOMETRY",
    ).outputs[0]
    geometry = t.store(geometry, ".crush_spill", "FLOAT", spilled, 12.7, 0)
    geometry = t.store(
        geometry,
        ".crush_lost",
        "FLOAT",
        t.node(
            "GeometryNodeSwitch",
            12.5,
            -22,
            {"Switch": storeys, "False": move, "True": floor_lost},
            input_type="FLOAT",
        ).outputs[0],
        12.8,
        0,
    )
    geometry = t.node(
        "GeometryNodeSetPosition",
        13,
        0,
        {
            "Geometry": geometry,
            "Selection": t.math("GREATER_THAN", move, 0.0, x=12, y=-6),
            "Position": moved,
        },
    ).outputs[0]
    crushed_geometry = geometry

    t.section("Loose Parts", row=True)
    thrown = build_parts(
        t, inputs, geometry, focus, started, floor, spacing, scale, part_size, speed
    )
    geometry = t.node(
        "GeometryNodeSwitch",
        30,
        0,
        {"Switch": inputs["Loose Parts"], "False": geometry, "True": thrown},
        input_type="GEOMETRY",
    ).outputs[0]
    t.section("Debris", row=True)
    chips = build_debris(t, inputs, crushed_geometry, started, floor, scale, chip, chip_speed)
    # The mesh linked last, for its materials to come first, as the last linked comes first
    with_chips = t.node("GeometryNodeJoinGeometry", 30.5, 1)
    t.connect(chips, with_chips.inputs[0])
    t.connect(geometry, with_chips.inputs[0])
    geometry = t.node(
        "GeometryNodeSwitch",
        30.8,
        0,
        {"Switch": inputs["Debris"], "False": geometry, "True": with_chips.outputs[0]},
        input_type="GEOMETRY",
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeRemoveAttribute",
        31,
        0,
        {"Geometry": geometry, "Pattern Mode": "Wildcard", "Name": ".crush_*"},
    ).outputs[0]
    t.node("NodeGroupOutput", 32, 0, {"Geometry": geometry})
    t.arrange()
    return ng


def build_parts(t, inputs, geometry, focus, started, floor, spacing, scale, part_size, speed):
    """Geometry with its parts thrown off once crushed, as rigid bodies simulated from the Start
    Frame: the islands in the Parts group or smaller than the Part Size, joined with the ones
    touching them, each part in the group or by Chance"""
    rest = t.attribute(".crush_rest", "FLOAT_VECTOR", 0, -2)
    island = t.node("GeometryNodeInputMeshIsland", 0, -3).outputs["Island Index"]
    geometry = t.store(geometry, ".crush_island", "INT", island, 0.5, 0)
    table, parts, support = found_parts(t, inputs, geometry, rest, spacing, part_size)

    t.section("Thrown Parts", row=True)
    sim_in = t.node("GeometryNodeSimulationInput", 0, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 20, 0)
    sim_in.pair_with_output(sim_out)
    for name in ("Table", "Support"):
        sim_out.state_items.new("GEOMETRY", name)
    found = {"Geometry": parts, "Table": table, "Support": support}
    for name, value in found.items():
        t.connect(value, sim_in.inputs[name])
    state, table, support = (
        t.node(
            "GeometryNodeSwitch",
            1,
            -i,
            {"Switch": started, "False": value, "True": sim_in.outputs[name]},
            input_type="GEOMETRY",
        ).outputs[0]
        for i, (name, value) in enumerate(found.items())
    )
    # Kept as found
    t.connect(table, sim_out.inputs["Table"])
    t.connect(support, sim_out.inputs["Support"])
    dt = sim_in.outputs["Delta Time"]
    point = t.node("GeometryNodeInputIndex", 0, -2).outputs[0]
    mesh = with_parts(t, geometry, table, 1, -20)
    vertex = t.attribute(".crush_vertex", "INT", 1.5, -21)

    def of_part(source, value, data_type, index, y):
        """Value of each part, found on the source at its index"""
        return t.node(
            "GeometryNodeSampleIndex",
            2,
            y,
            {"Geometry": source, "Value": value, "Index": index},
            data_type=data_type,
        ).outputs[0]

    # Crushed enough to be thrown, pressed by the Colliders, and how far it was crushed
    part = t.attribute(".crush_part", "INT", 1, -22)
    crushed = t.node(
        "ShaderNodeSeparateXYZ",
        2.5,
        -22,
        {
            0: of_part(
                mesh,
                extreme(
                    t,
                    t.node(
                        "ShaderNodeCombineXYZ",
                        1,
                        -23,
                        {
                            "X": t.attribute(".crush_ratio", "FLOAT", 0.5, -23),
                            "Y": t.attribute(".crush_contact", "FLOAT", 0.5, -24),
                        },
                    ).outputs[0],
                    part,
                    "Max",
                    1.5,
                    -23,
                    data_type="FLOAT_VECTOR",
                ),
                "FLOAT_VECTOR",
                vertex,
                -23,
            )
        },
    ).outputs
    shift = of_part(
        mesh,
        average(
            t,
            t.vmath(
                "SUBTRACT",
                t.node("GeometryNodeInputPosition", 0.5, -26).outputs[0],
                rest,
                x=1,
                y=-26,
            ),
            part,
            1.5,
            -26,
        ),
        "FLOAT_VECTOR",
        vertex,
        -26,
    )
    # In the group always, else by Chance where the Colliders do not press it, as under the foot
    chance = t.node(
        "FunctionNodeBooleanMath",
        3,
        -5,
        {
            0: random_value(
                t, {"Probability": inputs["Chance"], "ID": point, "Seed": SEED}, "BOOLEAN", 2, -5
            ),
            1: t.math("GREATER_THAN", crushed["Y"], 0.0, x=2.5, y=-6),
        },
        operation="NIMPLY",
    ).outputs[0]
    thrown = t.node(
        "FunctionNodeBooleanMath",
        3.5,
        -4,
        {0: t.attribute(".crush_painted", "BOOLEAN", 3, -4), 1: chance},
        operation="OR",
    ).outputs[0]
    loose = t.attribute(".crush_loose", "BOOLEAN", 2, -3)
    newly = t.node(
        "FunctionNodeBooleanMath",
        4.5,
        -3,
        {
            0: t.node(
                "FunctionNodeBooleanMath",
                4,
                -4,
                {0: thrown, 1: t.math("GREATER_THAN", crushed["X"], TRIGGER, x=3.5, y=-7)},
                operation="AND",
            ).outputs[0],
            1: loose,
        },
        operation="NIMPLY",
    ).outputs[0]
    # Thrown away from the middle of the crush, a little at random, and up, rolling that way
    middle = t.attribute(".crush_middle", "FLOAT_VECTOR", 1, -8)
    size = t.math("MAXIMUM", t.attribute(".crush_radius", "FLOAT", 1, -9), 1e-4, x=2, y=-9)
    away = t.node(
        "ShaderNodeSeparateXYZ",
        3,
        -8,
        {
            0: t.vmath(
                "ADD",
                t.vmath("SUBTRACT", middle, focus, x=2, y=-8),
                t.vmath(
                    "SCALE",
                    random_value(
                        t,
                        {
                            "Min": (-1.0, -1.0, 0.0),
                            "Max": (1.0, 1.0, 0.0),
                            "ID": point,
                            "Seed": SEED,
                        },
                        "FLOAT_VECTOR",
                        1.5,
                        -10,
                    ),
                    size,
                    x=2,
                    y=-10,
                ),
                x=2.5,
                y=-8,
            )
        },
    ).outputs
    away = t.vmath(
        "NORMALIZE",
        t.node("ShaderNodeCombineXYZ", 3.5, -8, {"X": away["X"], "Y": away["Y"]}).outputs[0],
        x=4,
        y=-8,
    )
    throw = t.math(
        "MULTIPLY",
        speed,
        random_value(t, {"Min": 0.6, "Max": 1.0, "ID": point, "Seed": SEED + 1}, "FLOAT", 3.5, -11),
        x=4,
        y=-11,
    )
    velocity = t.vmath(
        "SCALE", t.vmath("ADD", away, (0.0, 0.0, LIFT), x=4.5, y=-8), throw, x=5, y=-8
    )
    # Rolling, wobbling sideways not to stay on edge
    spin = t.vmath(
        "SCALE",
        t.vmath(
            "ADD",
            t.vmath("CROSS_PRODUCT", (0.0, 0.0, 1.0), away, x=4, y=-12),
            t.vmath(
                "SCALE",
                away,
                random_value(
                    t,
                    {"Min": -WOBBLE, "Max": WOBBLE, "ID": point, "Seed": SEED + 2},
                    "FLOAT",
                    3.5,
                    -14,
                ),
                x=4,
                y=-13,
            ),
            x=4.5,
            y=-12,
        ),
        t.math("DIVIDE", throw, size, x=4.5, y=-13),
        x=5,
        y=-12,
    )

    def pick(name, data_type, started_value, input_type, y):
        return t.node(
            "GeometryNodeSwitch",
            6,
            y,
            {"Switch": newly, "False": t.attribute(name, data_type, 5.5, y), "True": started_value},
            input_type=input_type,
        ).outputs[0]

    gravity = t.node(
        "ShaderNodeCombineXYZ",
        6,
        -16,
        {"Z": t.math("DIVIDE", -GRAVITY, scale, x=5.5, y=-16)},
    ).outputs[0]
    velocity = t.vmath(
        "ADD",
        pick(".crush_velocity", "FLOAT_VECTOR", velocity, "VECTOR", -8),
        t.vmath("SCALE", gravity, dt, x=6.5, y=-16),
        x=7,
        y=-8,
    )
    offset = t.vmath(
        "ADD",
        pick(".crush_offset", "FLOAT_VECTOR", shift, "VECTOR", -10),
        t.vmath("SCALE", velocity, dt, x=7, y=-11),
        x=7.5,
        y=-10,
    )
    spin = pick(".crush_spin", "FLOAT_VECTOR", spin, "VECTOR", -12)
    rotation = t.node(
        "FunctionNodeRotateRotation",
        8,
        -14,
        {
            "Rotation": pick(".crush_rotation", "QUATERNION", None, "ROTATION", -14),
            "Rotate By": t.node(
                "FunctionNodeAxisAngleToRotation",
                7.5,
                -15,
                {
                    "Axis": t.vmath("NORMALIZE", spin, x=7, y=-15),
                    "Angle": t.math(
                        "MULTIPLY", t.vmath("LENGTH", spin, x=7, y=-16), dt, x=7.5, y=-16
                    ),
                },
            ).outputs[0],
        },
        rotation_space="GLOBAL",
    ).outputs[0]
    moving = t.node("FunctionNodeBooleanMath", 8, -3, {0: loose, 1: newly}, operation="OR").outputs[
        0
    ]
    for i, (name, data_type, value) in enumerate(
        # Each one before the values it is found from
        (
            (".crush_rotation", "QUATERNION", rotation),
            (".crush_spin", "FLOAT_VECTOR", spin),
            (".crush_offset", "FLOAT_VECTOR", offset),
            (".crush_velocity", "FLOAT_VECTOR", velocity),
        )
    ):
        state = t.node(
            "GeometryNodeStoreNamedAttribute",
            9 + 0.5 * i,
            0,
            {"Geometry": state, "Name": name, "Value": value, "Selection": moving},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
    state = t.store(state, ".crush_loose", "BOOLEAN", moving, 11, 0)

    # Bouncing on the plane, from the lowest of the few points of each part as turned, and tipping
    # over the middle of the points touching it
    turned = thrown_position(t, state, 11, -6)
    height = t.node("ShaderNodeSeparateXYZ", 12, -6, {0: turned}).outputs["Z"]
    part = t.attribute(".crush_part", "INT", 12, -8)
    first = t.attribute(".crush_first", "INT", 12.5, -5)
    lowest = extreme(t, height, part, "Min", 12.5, -7)
    touching = t.math(
        "LESS_THAN",
        height,
        t.math(
            "MULTIPLY_ADD",
            of_part(state, t.attribute(".crush_radius", "FLOAT", 11.5, -16), "FLOAT", part, -16),
            CONTACT,
            lowest,
            x=12.5,
            y=-16,
        ),
        x=13,
        y=-16,
    )
    contact = t.vmath(
        "SCALE",
        average(t, t.vmath("SCALE", turned, touching, x=13, y=-17), part, 13.5, -17),
        t.math(
            "DIVIDE",
            1.0,
            t.math(
                "MAXIMUM",
                average(t, touching, part, 13.5, -18, data_type="FLOAT"),
                1e-6,
                x=14,
                y=-18,
            ),
            x=14.5,
            y=-18,
        ),
        x=15,
        y=-17,
    )
    lowest = of_part(support, lowest, "FLOAT", first, -5)
    lever = t.vmath(
        "SUBTRACT",
        t.vmath("ADD", middle, t.attribute(".crush_offset", "FLOAT_VECTOR", 13, -20), x=14, y=-19),
        of_part(support, contact, "FLOAT_VECTOR", first, -17),
        x=15.5,
        y=-19,
    )
    # Not when the middle is over the touching points, resting
    leaning = t.math(
        "GREATER_THAN",
        t.vmath("LENGTH", t.vmath("MULTIPLY", lever, (1.0, 1.0, 0.0), x=15.5, y=-22), x=16, y=-22),
        t.math("MULTIPLY", size, STABLE, x=16, y=-23),
        x=16.5,
        y=-22,
    )
    leaning = t.math(
        "MULTIPLY",
        leaning,
        t.math(
            "LESS_THAN", t.attribute(".crush_ground", "FLOAT", 16, -25), TIP_TIME, x=16.5, y=-25
        ),
        x=17,
        y=-22,
    )
    tipping = t.vmath(
        "SCALE",
        t.vmath(
            "SCALE",
            t.vmath("CROSS_PRODUCT", lever, gravity, x=16, y=-19),
            leaning,
            x=16.5,
            y=-20,
        ),
        t.math(
            "DIVIDE",
            dt,
            t.math(
                "ADD",
                t.math(
                    "MULTIPLY", t.math("MULTIPLY", size, size, x=14.5, y=-21), INERTIA, x=15, y=-21
                ),
                t.vmath("DOT_PRODUCT", lever, lever, x=15, y=-20),
                x=15.5,
                y=-21,
            ),
            x=16,
            y=-21,
        ),
        x=16.5,
        y=-19,
    )
    under = t.math("SUBTRACT", floor, lowest, x=13.5, y=-5)
    landed = t.node(
        "FunctionNodeBooleanMath",
        14,
        -3,
        {
            0: t.math("GREATER_THAN", under, 0.0, x=14, y=-5),
            1: t.attribute(".crush_loose", "BOOLEAN", 13.5, -3),
        },
        operation="AND",
    ).outputs[0]
    velocity = t.node(
        "ShaderNodeSeparateXYZ",
        14,
        -8,
        {0: t.attribute(".crush_velocity", "FLOAT_VECTOR", 13.5, -8)},
    ).outputs
    # Bouncing back up, resting when landing slower than gravity gives in a couple of frames
    falling = t.math("MULTIPLY", velocity["Z"], -1.0, x=14, y=-10)
    bounce = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", falling, inputs["Bounce"], x=14.5, y=-10),
        t.math(
            "GREATER_THAN",
            falling,
            t.math(
                "MULTIPLY", t.math("DIVIDE", 2.0 * GRAVITY, scale, x=13.5, y=-12), dt, x=14, y=-12
            ),
            x=14.5,
            y=-11,
        ),
        x=15,
        y=-11,
    )
    bounced = t.node(
        "ShaderNodeCombineXYZ",
        15,
        -8,
        {
            "X": t.math("MULTIPLY", velocity["X"], FRICTION, x=14.5, y=-8),
            "Y": t.math("MULTIPLY", velocity["Y"], FRICTION, x=14.5, y=-9),
            "Z": t.math("MAXIMUM", velocity["Z"], bounce, x=15, y=-10),
        },
    ).outputs[0]
    for i, (name, value) in enumerate(
        (
            (".crush_velocity", bounced),
            (
                ".crush_offset",
                t.vmath(
                    "ADD",
                    t.attribute(".crush_offset", "FLOAT_VECTOR", 15, -12),
                    t.node("ShaderNodeCombineXYZ", 15, -13, {"Z": under}).outputs[0],
                    x=15.5,
                    y=-12,
                ),
            ),
            (
                ".crush_spin",
                limited(
                    t,
                    t.vmath(
                        "ADD",
                        t.vmath(
                            "SCALE",
                            t.attribute(".crush_spin", "FLOAT_VECTOR", 15, -14),
                            t.node(
                                "GeometryNodeSwitch",
                                15,
                                -15,
                                {"Switch": leaning, "False": SETTLE, "True": SPIN_KEEP},
                                input_type="FLOAT",
                            ).outputs[0],
                            x=15.5,
                            y=-14,
                        ),
                        tipping,
                        x=16,
                        y=-14,
                    ),
                    t.math(
                        "DIVIDE", MAX_TURN, t.math("MAXIMUM", dt, 1e-6, x=16, y=-16), x=16.5, y=-16
                    ),
                    17,
                    -14,
                    rest=t.math(
                        "DIVIDE", REST_TURN, t.math("MAXIMUM", dt, 1e-6, x=16, y=-17), x=16.5, y=-17
                    ),
                ),
            ),
        )
    ):
        state = t.node(
            "GeometryNodeStoreNamedAttribute",
            16 + 0.5 * i,
            0,
            {"Geometry": state, "Name": name, "Value": value, "Selection": landed},
            data_type="FLOAT_VECTOR",
            domain="POINT",
        ).outputs[0]
    state = t.node(
        "GeometryNodeStoreNamedAttribute",
        17.5,
        0,
        {
            "Geometry": state,
            "Name": ".crush_ground",
            "Value": t.math("ADD", t.attribute(".crush_ground", "FLOAT", 17, -2), dt, x=17.5, y=-2),
            "Selection": landed,
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    t.connect(state, sim_out.inputs["Geometry"])

    # The thrown parts moved as rigid bodies, the others as crushed
    state = sim_out.outputs["Geometry"]
    geometry = with_parts(t, geometry, sim_out.outputs["Table"], 20.5, -2)
    loose = t.node(
        "GeometryNodeSampleIndex",
        21,
        -3,
        {
            "Geometry": state,
            "Value": t.attribute(".crush_loose", "BOOLEAN", 20.5, -3),
            "Index": t.attribute(".crush_part", "INT", 20.5, -4),
        },
        data_type="BOOLEAN",
    ).outputs[0]
    return t.node(
        "GeometryNodeSetPosition",
        22,
        0,
        {"Geometry": geometry, "Selection": loose, "Position": thrown_position(t, state, 21, -6)},
    ).outputs[0]


def build_debris(t, inputs, geometry, started, floor, scale, size, speed):
    """Chips thrown out of the sides as they are crushed, as many as the share they got crushed
    in the frame, falling and coming to rest on the plane under the mesh, from the Start Frame"""
    index = t.node("GeometryNodeInputIndex", 0, -3).outputs[0]
    frame = t.node("GeometryNodeInputSceneTime", 0, -4).outputs["Frame"]
    position = t.node("GeometryNodeInputPosition", 0, -5).outputs[0]
    now = t.node("GeometryNodeMeshToPoints", 1, 2, {"Mesh": geometry}).outputs[0]
    none = t.node("GeometryNodePoints", 1, 0, {"Count": 0}).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 22, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("GEOMETRY", "Spill")
    t.connect(none, sim_in.inputs["Geometry"])
    t.connect(now, sim_in.inputs["Spill"])
    dt = sim_in.outputs["Delta Time"]
    # Crushed more since the frame before, on the sides
    spill = t.attribute(".crush_spill", "FLOAT", 2, -3)
    more = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT",
            spill,
            t.node(
                "GeometryNodeSampleIndex",
                3,
                -3,
                {"Geometry": sim_in.outputs["Spill"], "Value": spill, "Index": index},
                data_type="FLOAT",
                domain="POINT",
            ).outputs[0],
            x=4,
            y=-3,
        ),
        0.0,
        x=4.5,
        y=-3,
    )
    mesh = t.store(geometry, ".crush_more", "FLOAT", more, 5, 2)
    # How fast it is crushed, the chips squeezed out the faster
    lost = t.attribute(".crush_lost", "FLOAT", 2, -6)
    rate = t.math(
        "DIVIDE",
        t.math(
            "MAXIMUM",
            t.math(
                "SUBTRACT",
                lost,
                t.node(
                    "GeometryNodeSampleIndex",
                    3,
                    -6,
                    {"Geometry": sim_in.outputs["Spill"], "Value": lost, "Index": index},
                    data_type="FLOAT",
                    domain="POINT",
                ).outputs[0],
                x=4,
                y=-6,
            ),
            0.0,
            x=4.5,
            y=-6,
        ),
        t.math("MAXIMUM", dt, 1e-4, x=4, y=-7),
        x=5,
        y=-6,
    )
    mesh = t.store(mesh, ".crush_rate", "FLOAT", rate, 5.2, 2)
    mesh = t.store(
        mesh,
        ".crush_chip_mat",
        "INT",
        t.node("GeometryNodeInputMaterialIndex", 4.5, 4).outputs[0],
        5.5,
        2,
        domain="FACE",
    )
    normal_z = t.node(
        "ShaderNodeSeparateXYZ", 5, 5, {0: t.node("GeometryNodeInputNormal", 4.5, 5).outputs[0]}
    ).outputs["Z"]
    sides = t.math("SUBTRACT", 1.0, t.math("MULTIPLY", normal_z, normal_z, x=5.5, y=5), x=6, y=5)
    # Only from the large parts, as walls: the small ones are the Loose Parts
    island = t.node("GeometryNodeInputMeshIsland", 3, 7).outputs["Island Index"]
    span = t.vmath(
        "DISTANCE",
        extreme(t, position, island, "Max", 4, 7, "FLOAT_VECTOR"),
        extreme(t, position, island, "Min", 4, 8, "FLOAT_VECTOR"),
        x=4.5,
        y=7,
    )
    box = t.node("GeometryNodeBoundBox", 3, 9, {"Geometry": geometry}).outputs
    large = t.math(
        "GREATER_THAN",
        span,
        t.math(
            "MULTIPLY",
            t.vmath("DISTANCE", box["Max"], box["Min"], x=4, y=9),
            DEBRIS_PART,
            x=4.5,
            y=9,
        ),
        x=5,
        y=7,
    )
    mesh = t.store(mesh, ".crush_large", "FLOAT", large, 5.8, 2)
    sides = t.math("MULTIPLY", sides, t.attribute(".crush_large", "FLOAT", 5.5, 6), x=6.3, y=5)
    thrown = t.node(
        "GeometryNodeDistributePointsOnFaces",
        7,
        2,
        {
            "Mesh": mesh,
            "Density": t.math(
                "MULTIPLY",
                t.math(
                    "MULTIPLY",
                    inputs["Debris Amount"],
                    t.math("MULTIPLY", scale, scale, x=6, y=4),
                    x=6.5,
                    y=4,
                ),
                t.math(
                    "MULTIPLY",
                    t.attribute(".crush_more", "FLOAT", 6, 3),
                    sides,
                    x=6.5,
                    y=3,
                    clamp=True,
                ),
                x=6.8,
                y=3.5,
            ),
            "Seed": frame,
        },
        distribute_method="RANDOM",
    )
    # Out from the side, fanning out, at Debris Speed and faster the faster it is crushed, a
    # little up, each at its own speed and size
    normal = t.node("ShaderNodeSeparateXYZ", 8, 0, {0: thrown.outputs["Normal"]}).outputs
    rand = t.node(
        "FunctionNodeRandomValue",
        8.5,
        -2,
        {"Min": (0.3, 0.0, 0.3), "Max": (1.0, 1.0, 1.0), "Seed": frame},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    rand = t.node("ShaderNodeSeparateXYZ", 9, -2, {0: rand}).outputs
    turn = t.node(
        "FunctionNodeRandomValue",
        8.5,
        -4,
        {"Min": -DEBRIS_FAN, "Max": DEBRIS_FAN, "Seed": t.math("ADD", frame, 7, x=8, y=-5)},
        data_type="FLOAT",
    ).outputs["Value"]
    cos, sin = (t.math(op, turn, x=9, y=-4 - k) for k, op in enumerate(("COSINE", "SINE")))
    out = t.vmath(
        "NORMALIZE",
        t.node(
            "ShaderNodeCombineXYZ",
            9.5,
            0,
            {
                "X": t.math(
                    "SUBTRACT",
                    t.math("MULTIPLY", normal["X"], cos, x=9, y=0),
                    t.math("MULTIPLY", normal["Y"], sin, x=9, y=-1),
                    x=9.3,
                    y=0,
                ),
                "Y": t.math(
                    "ADD",
                    t.math("MULTIPLY", normal["X"], sin, x=9, y=-2),
                    t.math("MULTIPLY", normal["Y"], cos, x=9, y=-3),
                    x=9.3,
                    y=-2,
                ),
            },
        ).outputs[0],
        x=10,
        y=0,
    )
    squeezed = t.node(
        "GeometryNodeSampleNearestSurface",
        9,
        -6,
        {
            "Mesh": mesh,
            "Value": t.attribute(".crush_rate", "FLOAT", 8.5, -6),
            "Sample Position": position,
        },
        data_type="FLOAT",
    ).outputs["Value"]
    fast = t.math(
        "MULTIPLY",
        t.math("MULTIPLY_ADD", squeezed, DEBRIS_EJECT, speed, x=9.5, y=-6),
        rand["X"],
        x=10,
        y=-6,
    )
    velocity = t.vmath(
        "ADD",
        t.vmath("SCALE", out, fast, x=10.5, y=-1),
        t.node(
            "ShaderNodeCombineXYZ",
            10.5,
            -3,
            {
                "Z": t.math(
                    "MULTIPLY",
                    fast,
                    t.math("MULTIPLY", rand["Y"], DEBRIS_RISE, x=10, y=-4),
                    x=10.3,
                    y=-3,
                )
            },
        ).outputs[0],
        x=11,
        y=-1,
    )
    new = t.store(thrown.outputs["Points"], ".crush_velocity", "FLOAT_VECTOR", velocity, 11, 0)
    new = t.store(
        new, ".crush_size", "FLOAT", t.math("MULTIPLY", rand["Z"], size, x=10.5, y=-4), 11.5, 0
    )
    # The material of the face each chip came from
    face = t.node(
        "GeometryNodeSampleNearest",
        11.5,
        -6,
        {"Geometry": geometry, "Sample Position": position},
        domain="FACE",
    ).outputs[0]
    new = t.store(
        new,
        ".crush_chip_mat",
        "INT",
        t.node(
            "GeometryNodeSampleIndex",
            12,
            -6,
            {
                "Geometry": geometry,
                "Value": t.node("GeometryNodeInputMaterialIndex", 11.5, -7).outputs[0],
                "Index": face,
            },
            data_type="INT",
            domain="FACE",
        ).outputs[0],
        12.5,
        0,
    )
    # The ones thrown before falling, bouncing a little on the plane and sliding to a stop
    chips = sim_in.outputs["Geometry"]
    moving = t.vmath(
        "SUBTRACT",
        t.attribute(".crush_velocity", "FLOAT_VECTOR", 12, -3),
        t.node(
            "ShaderNodeCombineXYZ",
            12,
            -4,
            {
                "Z": t.math(
                    "MULTIPLY", t.math("DIVIDE", GRAVITY, scale, x=11, y=-5), dt, x=11.5, y=-5
                )
            },
        ).outputs[0],
        x=13,
        y=-3,
    )
    moved = t.node(
        "ShaderNodeSeparateXYZ",
        14,
        -2,
        {0: t.vmath("ADD", position, t.vmath("SCALE", moving, dt, x=13, y=-5), x=13.5, y=-5)},
    ).outputs
    rest = t.math(
        "ADD",
        floor,
        t.math("MULTIPLY", t.attribute(".crush_size", "FLOAT", 13, -7), CHIP_FLAT, x=13.5, y=-7),
        x=14,
        y=-7,
    )
    landed = t.math("LESS_THAN", moved["Z"], rest, x=14.5, y=-6)
    v = t.node("ShaderNodeSeparateXYZ", 14, -9, {0: moving}).outputs
    kept = t.math(
        "SUBTRACT", 1.0, t.math("MULTIPLY", landed, 1.0 - DEBRIS_SLIDE, x=14.5, y=-10), x=15, y=-10
    )
    bounced = t.node(
        "ShaderNodeCombineXYZ",
        15.5,
        -9,
        {
            "X": t.math("MULTIPLY", v["X"], kept, x=15, y=-9),
            "Y": t.math("MULTIPLY", v["Y"], kept, x=15, y=-11),
            "Z": t.node(
                "GeometryNodeSwitch",
                15,
                -12,
                {
                    "Switch": landed,
                    "False": v["Z"],
                    "True": t.math(
                        "MULTIPLY",
                        t.math("ABSOLUTE", v["Z"], x=14.5, y=-12),
                        DEBRIS_BOUNCE,
                        x=14.8,
                        y=-12,
                    ),
                },
                input_type="FLOAT",
            ).outputs[0],
        },
    ).outputs[0]
    chips = t.node(
        "GeometryNodeSetPosition",
        16,
        0,
        {
            "Geometry": chips,
            "Position": t.node(
                "ShaderNodeCombineXYZ",
                15.5,
                -6,
                {
                    "X": moved["X"],
                    "Y": moved["Y"],
                    "Z": t.math("MAXIMUM", moved["Z"], rest, x=15, y=-6),
                },
            ).outputs[0],
        },
    ).outputs[0]
    chips = t.store(chips, ".crush_velocity", "FLOAT_VECTOR", bounced, 16.5, 0)
    joined = t.node("GeometryNodeJoinGeometry", 17, 0)
    t.connect(chips, joined.inputs[0])
    t.connect(new, joined.inputs[0])
    chips = t.node(
        "GeometryNodeSwitch",
        18,
        0,
        {"Switch": started, "False": none, "True": joined.outputs[0]},
        input_type="GEOMETRY",
    ).outputs[0]
    t.connect(chips, sim_out.inputs["Geometry"])
    t.connect(now, sim_out.inputs["Spill"])
    # Each chip a flattened ico sphere turned its own way, with the material of its side
    shape = t.node(
        "GeometryNodeTransform",
        23,
        -3,
        {
            "Geometry": t.node(
                "GeometryNodeMeshIcoSphere", 22.5, -3, {"Radius": 1.0, "Subdivisions": 1}
            ).outputs["Mesh"],
            "Scale": (1.0, 0.75, CHIP_FLAT),
        },
    ).outputs[0]
    # With the materials of the mesh, for the chips to keep their indices: one of its faces shrunk
    # to a point, an empty mesh losing them, linked last, as the last linked comes first
    one = t.node(
        "GeometryNodeDeleteGeometry",
        22,
        -5,
        {"Geometry": geometry, "Selection": t.math("GREATER_THAN", index, 0, x=21.5, y=-6)},
        domain="FACE",
    ).outputs[0]
    slots = t.node("GeometryNodeJoinGeometry", 23.5, -4)
    t.connect(shape, slots.inputs[0])
    t.connect(
        t.node(
            "GeometryNodeTransform", 22.8, -5, {"Geometry": one, "Scale": (0.0, 0.0, 0.0)}
        ).outputs[0],
        slots.inputs[0],
    )
    shape = slots.outputs[0]
    # Turned about the vertical, a little tilted, lying flat once landed
    turn = t.node(
        "FunctionNodeRandomValue",
        23,
        -5,
        {"Min": (-CHIP_TILT, -CHIP_TILT, 0.0), "Max": (CHIP_TILT, CHIP_TILT, 6.3), "ID": index},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    placed = t.node(
        "GeometryNodeInstanceOnPoints",
        24,
        0,
        {
            "Points": sim_out.outputs["Geometry"],
            "Instance": shape,
            "Rotation": turn,
            "Scale": t.attribute(".crush_size", "FLOAT", 23.5, -2),
        },
    ).outputs[0]
    placed = t.node("GeometryNodeRealizeInstances", 25, 0, {"Geometry": placed}).outputs[0]
    return t.node(
        "GeometryNodeSetMaterialIndex",
        26,
        0,
        {"Geometry": placed, "Material Index": t.attribute(".crush_chip_mat", "INT", 25.5, -2)},
    ).outputs[0]


def found_parts(t, inputs, geometry, rest, spacing, part_size):
    """Found once at the Start Frame: a point by island with its part, -1 for the islands
    staying, the islands in the Parts group or smaller than the Part Size joined where touching; a
    point by part with its middle, size, whether in the group, and first vertex; and a few points
    of each part, where it touches the plane"""
    index = t.node("GeometryNodeInputIndex", 0, -30).outputs[0]
    island = t.attribute(".crush_island", "INT", 0, -31)
    painted = t.math("GREATER_THAN", inputs["Parts"], 0.5, x=0.5, y=-32)
    box = [
        extreme(t, rest, island, output, 1, -33 - i, data_type="FLOAT_VECTOR")
        for i, output in enumerate(("Min", "Max"))
    ]
    candidate = t.node(
        "FunctionNodeBooleanMath",
        3,
        -32,
        {
            0: extreme(t, painted, island, "Max", 1.5, -32),
            1: t.math("LESS_THAN", t.vmath("DISTANCE", *box, x=2, y=-33), part_size, x=2.5, y=-33),
        },
        operation="OR",
    ).outputs[0]
    geometry = t.store(geometry, ".crush_candidate", "BOOLEAN", candidate, 3.5, -30)
    candidate = t.attribute(".crush_candidate", "BOOLEAN", 4, -32)
    # Joined where touching, a grid cell apart at most
    copy = t.node(
        "GeometryNodeSetPosition", 4, -35, {"Geometry": geometry, "Position": rest}
    ).outputs[0]
    copy = t.node(
        "GeometryNodeDeleteGeometry",
        4.5,
        -35,
        {
            "Geometry": copy,
            "Selection": t.node(
                "FunctionNodeBooleanMath", 4, -36, {0: candidate}, operation="NOT"
            ).outputs[0],
        },
        domain="POINT",
    ).outputs[0]
    copy = t.node(
        "GeometryNodeMergeByDistance",
        5,
        -35,
        {"Geometry": copy, "Mode": "All", "Distance": spacing},
    ).outputs[0]
    copy = t.store(
        copy,
        ".crush_part",
        "INT",
        t.node("GeometryNodeInputMeshIsland", 5, -37).outputs["Island Index"],
        5.5,
        -35,
    )
    table = first_points(t, geometry, island, index, 6, -30)
    joined = t.node(
        "GeometryNodeSampleIndex",
        7,
        -33,
        {
            "Geometry": copy,
            "Value": t.attribute(".crush_part", "INT", 6.5, -34),
            "Index": t.node(
                "GeometryNodeSampleNearest", 6.5, -33, {"Geometry": copy, "Sample Position": rest}
            ).outputs[0],
        },
        data_type="INT",
    ).outputs[0]
    table = t.store(
        table,
        ".crush_part",
        "INT",
        t.node(
            "GeometryNodeSwitch",
            7.5,
            -32,
            {"Switch": candidate, "False": -1, "True": joined},
            input_type="INT",
        ).outputs[0],
        8,
        -30,
    )

    # Each part: middle, size, in the group or not, and first vertex
    geometry = with_parts(t, geometry, table, 8.5, -30)
    part = t.attribute(".crush_part", "INT", 9, -32)
    middle = average(t, rest, part, 9.5, -33)
    values = (
        (".crush_middle", "FLOAT_VECTOR", middle),
        (
            ".crush_radius",
            "FLOAT",
            extreme(t, t.vmath("DISTANCE", rest, middle, x=10, y=-34), part, "Max", 10.5, -34),
        ),
        (
            ".crush_painted",
            "BOOLEAN",
            t.math("GREATER_THAN", extreme(t, painted, part, "Max", 10, -35), 0.5, x=10.5, y=-35),
        ),
        (".crush_vertex", "INT", index),
    )
    for i, (name, data_type, value) in enumerate(values):
        geometry = t.store(geometry, name, data_type, value, 11 + 0.5 * i, -30)
    parts = first_points(t, geometry, part, index, 13, -30)

    # A few points of each part: its first one, the furthest out along the directions, and
    # others at random
    furthest = None
    # Nudged at random, not to keep all the points of a flat side
    nudge = t.math(
        "MULTIPLY",
        random_value(t, {"ID": index, "Seed": SEED + 4}, "FLOAT", 9.5, -40),
        t.math("MULTIPLY", spacing, 1e-4, x=9.5, y=-41),
        x=10,
        y=-40,
    )
    for i in range(0, len(DIRECTIONS), 3):
        y = -40 - i
        reach = t.node(
            "ShaderNodeCombineXYZ",
            11,
            y,
            {
                axis: t.math(
                    "ADD",
                    t.vmath("DOT_PRODUCT", rest, direction, x=10, y=y - j),
                    nudge,
                    x=10.5,
                    y=y - j,
                )
                # The last ones repeated, not to leave a component at zero
                for j, (axis, direction) in enumerate(
                    zip("XYZ", (DIRECTIONS[i : i + 3] * 3)[:3], strict=True)
                )
            },
        ).outputs[0]
        for output in ("Min", "Max"):
            gap = t.node(
                "ShaderNodeSeparateXYZ",
                12.5,
                y,
                {
                    0: t.vmath(
                        "ABSOLUTE",
                        t.vmath(
                            "SUBTRACT",
                            reach,
                            extreme(t, reach, part, output, 11.5, y, data_type="FLOAT_VECTOR"),
                            x=12,
                            y=y,
                        ),
                        x=12,
                        y=y - 1,
                    )
                },
            ).outputs
            at = t.math(
                "LESS_THAN",
                t.math(
                    "MINIMUM",
                    t.math("MINIMUM", gap["X"], gap["Y"], x=13, y=y),
                    gap["Z"],
                    x=13,
                    y=y - 1,
                ),
                t.math("MULTIPLY", spacing, 1e-6, x=13, y=y - 2),
                x=13.5,
                y=y,
            )
            furthest = at if furthest is None else t.math("MAXIMUM", furthest, at, x=14, y=y)
    count = t.node(
        "GeometryNodeAccumulateField",
        13,
        -38,
        {"Value": 1, "Group ID": part},
        data_type="INT",
        domain="POINT",
    ).outputs["Total"]
    keep = t.node(
        "FunctionNodeBooleanMath",
        15,
        -37,
        {
            0: t.node(
                "FunctionNodeCompare",
                14,
                -37,
                {"A": extreme(t, index, part, "Min", 13.5, -37, data_type="INT"), "B": index},
                data_type="INT",
                operation="EQUAL",
            ).outputs[0],
            1: t.math(
                "MAXIMUM",
                t.math(
                    "LESS_THAN",
                    random_value(t, {"ID": index, "Seed": SEED + 3}, "FLOAT", 13.5, -39),
                    t.math("DIVIDE", SUPPORT, count, x=14, y=-38),
                    x=14.5,
                    y=-38,
                ),
                furthest,
                x=14.5,
                y=-39,
            ),
        },
        operation="OR",
    ).outputs[0]
    keep = t.node(
        "FunctionNodeBooleanMath",
        15.5,
        -37,
        {
            0: keep,
            1: t.node(
                "FunctionNodeCompare",
                15,
                -38,
                {"A": part, "B": 0},
                data_type="INT",
                operation="GREATER_EQUAL",
            ).outputs[0],
        },
        operation="AND",
    ).outputs[0]
    support = t.node(
        "GeometryNodeSeparateGeometry",
        16,
        -36,
        {"Geometry": geometry, "Selection": keep},
        domain="POINT",
    ).outputs["Selection"]
    support = t.node(
        "GeometryNodeMeshToPoints", 16.5, -36, {"Mesh": support}, mode="VERTICES"
    ).outputs[0]
    support = t.node(
        "GeometryNodeSortElements",
        17,
        -36,
        {"Geometry": support, "Sort Weight": t.attribute(".crush_part", "INT", 16.5, -38)},
        domain="POINT",
    ).outputs[0]
    # The first of them of each part kept by the part
    support = t.store(support, ".crush_first", "INT", index, 17.5, -36)
    firsts = first_points(
        t, support, t.attribute(".crush_part", "INT", 17.5, -39), index, 18, -36, mesh=False
    )
    parts = t.store(
        parts,
        ".crush_first",
        "INT",
        t.node(
            "GeometryNodeSampleIndex",
            19,
            -32,
            {
                "Geometry": firsts,
                "Value": t.attribute(".crush_first", "INT", 18.5, -33),
                "Index": index,
            },
            data_type="INT",
        ).outputs[0],
        19.5,
        -30,
    )
    return table, parts, support


def first_points(t, geometry, group, index, x, y, mesh=True):
    """A point by group of the geometry, its first one, in the order of the groups, the ones with
    a negative group left out"""
    first = t.node(
        "FunctionNodeCompare",
        x,
        y - 2,
        {"A": extreme(t, index, group, "Min", x - 0.5, y - 2, data_type="INT"), "B": index},
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    keep = t.node(
        "FunctionNodeBooleanMath",
        x + 0.5,
        y - 2,
        {
            0: first,
            1: t.node(
                "FunctionNodeCompare",
                x,
                y - 3,
                {"A": group, "B": 0},
                data_type="INT",
                operation="GREATER_EQUAL",
            ).outputs[0],
        },
        operation="AND",
    ).outputs[0]
    points = t.node(
        "GeometryNodeSeparateGeometry",
        x + 1,
        y,
        {"Geometry": geometry, "Selection": keep},
        domain="POINT",
    ).outputs["Selection"]
    if mesh:
        points = t.node(
            "GeometryNodeMeshToPoints", x + 1.5, y, {"Mesh": points}, mode="VERTICES"
        ).outputs[0]
    points = t.store(points, ".crush_group", "INT", group, x + 2, y)
    return t.node(
        "GeometryNodeSortElements",
        x + 2.5,
        y,
        {"Geometry": points, "Sort Weight": t.attribute(".crush_group", "INT", x + 2, y - 2)},
        domain="POINT",
    ).outputs[0]


def with_parts(t, geometry, table, x, y):
    """Geometry with the part of each point, from the point of its island in the table"""
    return t.store(
        geometry,
        ".crush_part",
        "INT",
        t.node(
            "GeometryNodeSampleIndex",
            x,
            y - 1,
            {
                "Geometry": table,
                "Value": t.attribute(".crush_part", "INT", x - 0.5, y - 1),
                "Index": t.attribute(".crush_island", "INT", x - 0.5, y - 2),
            },
            data_type="INT",
        ).outputs[0],
        x + 0.5,
        y,
    )


def average(t, value, group, x, y, data_type="FLOAT_VECTOR"):
    return t.node(
        "GeometryNodeFieldAverage",
        x,
        y,
        {"Value": value, "Group ID": group},
        data_type=data_type,
        domain="POINT",
    ).outputs["Mean"]


def extreme(t, value, group, output, x, y, data_type="FLOAT"):
    return t.node(
        "GeometryNodeFieldMinAndMax",
        x,
        y,
        {"Value": value, "Group ID": group},
        data_type=data_type,
        domain="POINT",
    ).outputs[output]


def buckled(t, depth, pressed, co, size, amount, x, y):
    """Depth bent at creases along the rings of equal depth, a few Crumple Sizes deep apart and
    wobbling, nearly flat between them, blended by the amount, as deep as pressed at least"""
    step = t.math("MULTIPLY", size, BUCKLE_STEP, x=x, y=y - 1)
    # Wobbling more away from the untouched mesh, which stays as it is
    wobble = t.math(
        "MULTIPLY",
        t.math(
            "SUBTRACT",
            t.node(
                "ShaderNodeTexNoise",
                x,
                y - 2,
                {
                    "Vector": t.node(
                        "ShaderNodeCombineXYZ", x - 0.5, y - 2, {"X": co["X"], "Y": co["Y"]}
                    ).outputs[0],
                    "Scale": t.math("DIVIDE", 1.0, step, x=x - 0.5, y=y - 3),
                    "Detail": 0.0,
                },
                noise_dimensions="2D",
            ).outputs["Fac"],
            0.5,
            x=x + 0.5,
            y=y - 2,
        ),
        t.math(
            "MULTIPLY",
            t.math("DIVIDE", depth, step, x=x + 0.5, y=y - 3, clamp=True),
            t.math("MULTIPLY", step, BUCKLE_WOBBLE * 2.0, x=x + 0.5, y=y - 4),
            x=x + 1,
            y=y - 3,
        ),
        x=x + 1.5,
        y=y - 2,
    )
    level = t.math("DIVIDE", t.math("ADD", depth, wobble, x=x + 2, y=y), step, x=x + 2.5, y=y)
    floor = t.math("FLOOR", level, x=x + 3, y=y - 1)
    crease = t.math(
        "DIVIDE",
        t.math(
            "SUBTRACT",
            t.math("SUBTRACT", level, floor, x=x + 3.5, y=y),
            1.0 - BUCKLE_CREASE,
            x=x + 4,
            y=y,
        ),
        BUCKLE_CREASE,
        x=x + 4.5,
        y=y,
        clamp=True,
    )
    terraced = t.math(
        "SUBTRACT",
        t.math("MULTIPLY", t.math("ADD", floor, crease, x=x + 5, y=y), step, x=x + 5.5, y=y),
        wobble,
        x=x + 6,
        y=y,
    )
    blended = t.node(
        "ShaderNodeMix",
        x + 6.5,
        y,
        {"Factor": amount, "A": depth, "B": t.math("MAXIMUM", terraced, 0.0, x=x + 6, y=y - 1)},
        data_type="FLOAT",
    ).outputs[0]
    return t.math("MAXIMUM", blended, pressed, x=x + 7, y=y)


def pancaked(t, h, top, depth, height, x, y):
    """Height of each point with the depth taken floor by floor from the top of its column, each
    floor squashed to its rubble before the one under it gives, the share of its floor crushed,
    how much it lost and where the point is up its floor"""

    def m(operation, *values, dx=0.0, dy=0.0, clamp=False):
        return t.math(operation, *values, x=x + dx, y=y + dy, clamp=clamp)

    def pick(condition, true, false, dx, dy):
        return t.node(
            "GeometryNodeSwitch",
            x + dx,
            y + dy,
            {"Switch": condition, "False": false, "True": true},
            input_type="FLOAT",
        ).outputs[0]

    height = m("MAXIMUM", height, 1e-4)
    give = m("MULTIPLY", height, 1.0 - RUBBLE, dy=-1)
    rubble = m("MULTIPLY", height, RUBBLE, dy=-2)
    floors = m("MAXIMUM", m("CEIL", m("DIVIDE", top, height, dx=1), dx=2), 1.0, dx=3)
    under_top = m("MULTIPLY", m("SUBTRACT", floors, 1.0, dx=3, dy=-1), height, dx=4, dy=-1)
    # The top floor, maybe lower than the others, gives first
    top_floor = m("MAXIMUM", m("SUBTRACT", top, under_top, dx=5, dy=-1), 1e-6, dx=6, dy=-1)
    top_give = m("MULTIPLY", top_floor, 1.0 - RUBBLE, dx=6, dy=-2)
    top_lost = m("MINIMUM", depth, top_give, dx=7, dy=-1)
    # Then the floors under it, from the top: the ones past gone, the next one giving
    rest = m(
        "MINIMUM",
        m("MAXIMUM", m("SUBTRACT", depth, top_lost, dx=7, dy=-3), 0.0, dx=8, dy=-3),
        m("MULTIPLY", m("SUBTRACT", floors, 1.0, dx=7, dy=-4), give, dx=8, dy=-4),
        dx=9,
        dy=-3,
    )
    gone = m("FLOOR", m("DIVIDE", rest, give, dx=10, dy=-3), dx=11, dy=-3)
    lost = m("SUBTRACT", rest, m("MULTIPLY", gone, give, dx=11, dy=-4), dx=12, dy=-3)
    giving = m("SUBTRACT", m("SUBTRACT", floors, 2.0, dx=12, dy=-5), gone, dx=13, dy=-5)
    level = m(
        "MINIMUM",
        m("FLOOR", m("DIVIDE", h, height, dx=1, dy=-6), dx=2, dy=-6),
        m("SUBTRACT", floors, 1.0, dx=2, dy=-7),
        dx=3,
        dy=-6,
    )
    up = m(
        "DIVIDE",
        m("SUBTRACT", h, m("MULTIPLY", level, height, dx=3, dy=-8), dx=4, dy=-8),
        height,
        dx=5,
        dy=-8,
        clamp=True,
    )
    below = m("LESS_THAN", level, giving, dx=14, dy=-6)
    at = m("COMPARE", level, giving, 0.1, dx=14, dy=-7)
    base = m("MULTIPLY", giving, height, dx=14, dy=-8)
    at_height = m("MULTIPLY_ADD", up, m("SUBTRACT", height, lost, dx=15, dy=-9), base, dx=16, dy=-8)
    over_height = m(
        "ADD",
        m("ADD", base, m("SUBTRACT", height, lost, dx=15, dy=-10), dx=16, dy=-10),
        m(
            "MULTIPLY",
            m(
                "ADD",
                m("SUBTRACT", m("SUBTRACT", level, giving, dx=14, dy=-11), 1.0, dx=15, dy=-11),
                up,
                dx=16,
                dy=-11,
            ),
            rubble,
            dx=17,
            dy=-11,
        ),
        dx=18,
        dy=-10,
    )
    lower = pick(below, h, pick(at, at_height, over_height, 18, -9), 19, -8)
    lower_lost = pick(below, 0.0, pick(at, lost, give, 18, -12), 19, -12)
    # The top floor on what is left under it
    on_top = m("GREATER_THAN", m("SUBTRACT", h, under_top, dx=8, dy=-14), -1e-6, dx=9, dy=-14)
    up_top = m(
        "DIVIDE", m("SUBTRACT", h, under_top, dx=9, dy=-15), top_floor, dx=10, dy=-15, clamp=True
    )
    top_height = m(
        "MULTIPLY_ADD",
        up_top,
        m("SUBTRACT", top_floor, top_lost, dx=11, dy=-16),
        m("SUBTRACT", under_top, rest, dx=11, dy=-17),
        dx=12,
        dy=-16,
    )
    # Points over the top found on the grid, as on curved sides, as far over the new top
    top_height = m(
        "ADD",
        top_height,
        m("MAXIMUM", m("SUBTRACT", h, top, dx=12, dy=-18), 0.0, dx=13, dy=-18),
        dx=13,
        dy=-16,
    )
    crushed = pick(on_top, top_height, lower, 20, -14)
    floor_lost = pick(on_top, top_lost, lower_lost, 20, -15)
    share = m(
        "DIVIDE", floor_lost, pick(on_top, top_give, give, 20, -17), dx=21, dy=-16, clamp=True
    )
    return crushed, share, floor_lost, pick(on_top, up_top, up, 20, -18)


def limited(t, vector, length, x, y, rest=0.0):
    """Vector shortened to the length at most, zero if shorter than the rest length"""
    size = t.vmath("LENGTH", vector, x=x, y=y - 1)
    shorter = t.math(
        "MINIMUM",
        1.0,
        t.math(
            "DIVIDE", length, t.math("MAXIMUM", size, 1e-9, x=x + 0.5, y=y - 1), x=x + 1, y=y - 1
        ),
        x=x + 1.5,
        y=y - 1,
    )
    moving = t.math("GREATER_THAN", size, rest, x=x + 1, y=y - 2)
    return t.vmath(
        "SCALE", vector, t.math("MULTIPLY", shorter, moving, x=x + 1.5, y=y - 2), x=x + 2, y=y
    )


def bilinear(t, grid, value, cells, middle, spacing, co, x, y, corners=False):
    """Vector of the grid at the position of the point on the plane, mixed between the four grid
    points around it, the grid rows along Y, or the four of them with their weights"""
    cell, share = [], []
    for i, axis in enumerate("XY"):
        corner = t.math(
            "SUBTRACT",
            middle[axis],
            t.math(
                "MULTIPLY",
                t.math("SUBTRACT", cells[i], 1, x=x - 2, y=y - 10 - i),
                t.math("MULTIPLY", spacing, 0.5, x=x - 2, y=y - 12),
                x=x - 1.5,
                y=y - 10 - i,
            ),
            x=x - 1,
            y=y - 10 - i,
        )
        along = t.math(
            "DIVIDE",
            t.math("SUBTRACT", co[axis], corner, x=x - 0.5, y=y - 8 - i),
            spacing,
            x=x,
            y=y - 8 - i,
        )
        first = t.math(
            "MINIMUM",
            t.math(
                "MAXIMUM", t.math("FLOOR", along, x=x + 0.5, y=y - 8 - i), 0.0, x=x + 1, y=y - 8 - i
            ),
            t.math("SUBTRACT", cells[i], 2, x=x + 1, y=y - 10 - i),
            x=x + 1.5,
            y=y - 8 - i,
        )
        cell.append(first)
        share.append(t.math("SUBTRACT", along, first, x=x + 2, y=y - 8 - i, clamp=True))

    def at(dx, dy, ry):
        return t.node(
            "GeometryNodeSampleIndex",
            x + 3,
            ry,
            {
                "Geometry": grid,
                "Value": value,
                "Index": t.math(
                    "MULTIPLY_ADD",
                    t.math("ADD", cell[0], dx, x=x + 2.5, y=ry),
                    cells[1],
                    t.math("ADD", cell[1], dy, x=x + 2.5, y=ry - 1),
                    x=x + 3,
                    y=ry - 1,
                ),
            },
            data_type="FLOAT_VECTOR",
        ).outputs[0]

    def mix(a, b, factor, ry):
        node = t.node(
            "ShaderNodeMix", x + 4, ry, {"Factor": factor, "A": a, "B": b}, data_type="VECTOR"
        )
        return socket(node.outputs, "Result")

    if corners:
        rest = [t.math("SUBTRACT", 1.0, x_, x=x + 2.5, y=y - 12 - i) for i, x_ in enumerate(share)]
        return [
            (
                at(dx, dy, y - 2 * (2 * dy + dx)),
                t.math(
                    "MULTIPLY",
                    share[0] if dx else rest[0],
                    share[1] if dy else rest[1],
                    x=x + 3.5,
                    y=y - 14 - 2 * dy - dx,
                ),
            )
            for dy in (0, 1)
            for dx in (0, 1)
        ]
    return mix(
        mix(at(0, 0, y), at(1, 0, y - 2), share[0], y),
        mix(at(0, 1, y - 4), at(1, 1, y - 6), share[0], y - 4),
        share[1],
        y,
    )


def random_value(t, inputs, data_type, x, y):
    return socket(
        t.node("FunctionNodeRandomValue", x, y, inputs, data_type=data_type).outputs, "Value"
    )


def thrown_position(t, state, x, y):
    """Position of the points of the parts thrown as simulated in the state, turned around their
    middle and moved"""
    part = t.attribute(".crush_part", "INT", x - 1, y - 1)

    def of_part(name, data_type, dy):
        return t.node(
            "GeometryNodeSampleIndex",
            x - 0.5,
            y + dy,
            {
                "Geometry": state,
                "Value": t.attribute(name, data_type, x - 1, y + dy),
                "Index": part,
            },
            data_type=data_type,
        ).outputs[0]

    middle = of_part(".crush_middle", "FLOAT_VECTOR", -2)
    turned = t.node(
        "FunctionNodeRotateVector",
        x,
        y,
        {
            "Vector": t.vmath(
                "SUBTRACT",
                t.attribute(".crush_rest", "FLOAT_VECTOR", x - 1, y - 5),
                middle,
                x=x - 0.5,
                y=y - 2,
            ),
            "Rotation": of_part(".crush_rotation", "QUATERNION", -3),
        },
    ).outputs[0]
    return t.vmath(
        "ADD",
        t.vmath("ADD", turned, middle, x=x + 0.5, y=y),
        of_part(".crush_offset", "FLOAT_VECTOR", -4),
        x=x + 1,
        y=y,
    )


def new_grid(t, extent, middle, floor, spacing, x, y):
    """Grid over the mesh and its margin on the plane under it, the points the spacing apart,
    with the counts of its columns and rows"""
    counts = [
        t.math(
            "ADD",
            t.math("CEIL", t.math("DIVIDE", extent[axis], spacing, x=x, y=y - i), x=x + 1, y=y - i),
            1 + 2 * MARGIN,
            x=x + 2,
            y=y - i,
        )
        for i, axis in enumerate("XY")
    ]
    grid = t.node(
        "GeometryNodeMeshGrid",
        x + 3,
        y,
        {
            "Size X": t.math(
                "MULTIPLY",
                t.math("SUBTRACT", counts[0], 1, x=x + 2, y=y - 2),
                spacing,
                x=x + 3,
                y=y - 2,
            ),
            "Size Y": t.math(
                "MULTIPLY",
                t.math("SUBTRACT", counts[1], 1, x=x + 2, y=y - 3),
                spacing,
                x=x + 3,
                y=y - 3,
            ),
            "Vertices X": counts[0],
            "Vertices Y": counts[1],
        },
    ).outputs["Mesh"]
    center = t.node(
        "ShaderNodeCombineXYZ", x + 3, y - 4, {"X": middle["X"], "Y": middle["Y"], "Z": floor}
    ).outputs[0]
    grid = t.node(
        "GeometryNodeTransform", x + 4, y, {"Geometry": grid, "Translation": center}
    ).outputs[0]
    return grid, counts


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(),), fake_user=True)
