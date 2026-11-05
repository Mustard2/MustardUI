# Build shrinkwrap.blend: the Shrinkwrap node group
# Usage: Blender --background --factory-startup --python shrinkwrap_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "shrinkwrap.blend"
NODE_GROUP = "MustardUI Shrinkwrap"
# Raised at every change, the add-on replacing older copies in the files
VERSION = 22
# Rounds spreading the push, then pushing the mesh around out of the Colliders
ROUNDS = 3
# Smoothing iterations of the roll of the pressed volume
ROLL_ITERATIONS = 6
# Smoothing iterations of the drag among the contact, to move together
DRAG_ITERATIONS = 4
# Smoothing iterations over the contact moved together by the Firmness, its reach on the mesh
FIRM_ITERATIONS = 10
# Exponent of the soft maximum of the push nearby
FIRM_POWER = 6.0
# Distance the mesh is kept out of the Colliders by, not to flicker on them
SKIN = 0.0001
# How much farther than the nearest way out the way back can be
BACK_RATIO = 2.5
# Directions around the Zone axis and heights along it the Colliders reach is cast at
OPENING_DIRECTIONS = 96
OPENING_HEIGHTS = 12
# Height of the roll in the Zone, of the reach of the Colliders all squeezed with a Roll of 1
OPENING_ROLL = 0.25
# How much farther the mesh at other heights of the Zone counts where the mesh starts
OPENING_LEVEL = 2.0
# Steps along the mesh to the nearest contact, doubling each time
PATH_JUMPS = 12
# How much of the distance along the mesh to the contact counts, through the volume
PATH_RATIO = 0.5


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng["MustardUI Version"] = VERSION
    ng.description = (
        "Push the mesh softly out of the Colliders, e.g. lips around a cylinder, the mesh around "
        "following, the pressed volume rolling up at the edges and the contact dragged along as "
        "they slide"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects pushing the mesh out",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.003,
        min_value=0.0,
        max_value=1.0,
        description="Soft layer around the Colliders pushing the mesh before it touches them, "
        "higher for a softer push",
    )
    add_input(
        ng,
        "Spread",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.015,
        min_value=0.0001,
        max_value=10.0,
        description="Distance from the pushed parts the mesh around follows them to, fading out "
        "like an elastic body, up to twice as far for the deeper pushes",
    )
    add_input(
        ng,
        "Roll",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Bulge next to the contact of the volume pushed in by the Colliders",
    )
    add_input(
        ng,
        "Firmness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="How much the volume under the contact is pushed as a whole by its deepest "
        "part, keeping its shape, from the surface flattening on the Colliders",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group of the parts pushed by the Colliders, e.g. the lips, the mesh "
        "around following them",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        default_value=12,
        min_value=1,
        max_value=1000,
        description="Iterations smoothing the push over the mesh around, rounding off the "
        "contact and the roll",
    )
    add_input(
        ng,
        "Friction",
        "NodeSocketBool",
        default_value=True,
        description="Contact dragged along by the Colliders sliding on the mesh, simulated from "
        "the Start Frame",
    )
    add_input(
        ng,
        "Stretch",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.004,
        min_value=0.0,
        max_value=1.0,
        description="How far the contact is dragged along before slipping",
    )
    add_input(
        ng,
        "Frequency",
        "NodeSocketFloat",
        default_value=4.0,
        min_value=0.1,
        max_value=30.0,
        description="Wobbles per second of the mesh springing back when released, higher for a "
        "stiffer mesh",
    )
    add_input(
        ng,
        "Damping",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="How fast the mesh settles springing back, from wobbling long to not "
        "overshooting",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    add_input(
        ng,
        "Opening",
        "NodeSocketBool",
        default_value=False,
        description="Move the mesh in the Zone out from its axis, e.g. the lips around the "
        "mouth, smoothly as the Colliders go through it, keeping each part on its side",
    )
    add_input(
        ng,
        "Zone",
        "NodeSocketObject",
        description="Empty around the opening, its Z axis through it, the mesh moved within "
        "its box",
    )
    add_input(
        ng,
        "Smooth Normals",
        "NodeSocketInt",
        default_value=5,
        min_value=0,
        max_value=200,
        description="Iterations smoothing the directions the pressed volume rolls up in",
    )
    arrange_interface(
        ng,
        [
            (
                None,
                "Friction",
                False,
                "Friction",
                ["Stretch", "Frequency", "Damping", "Start Frame"],
            ),
            (None, "Opening", False, "Opening", ["Zone"]),
            (None, "Advanced", True, None, ["Smooth Normals"]),
        ],
    )

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -8, 0).outputs

    t.section("Colliders", row=True)
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        0,
        -2,
        {"Collection": inputs["Colliders"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", 1, -2, {0: colliders}).outputs[0]
    colliders = outward(t, colliders)
    nearest = t.node(
        "GeometryNodeProximity",
        2,
        -2,
        {
            "Geometry": colliders,
            "Sample Position": t.node("GeometryNodeInputPosition", 1, -3).outputs[0],
        },
        target_element="FACES",
    ).outputs
    # Only the part of the mesh near them, the rest staying as it is
    reach = t.math(
        "ADD", t.math("MULTIPLY", inputs["Spread"], 2.0, x=1, y=-5), inputs["Thickness"], x=2, y=-4
    )
    near = t.math("LESS_THAN", nearest["Distance"], reach, x=3, y=-2)
    near = t.math("MULTIPLY", near, nearest["Is Valid"], x=4, y=-2)
    captured = t.node("GeometryNodeCaptureAttribute", 6, 0, {"Geometry": inputs["Geometry"]})
    captured.capture_items.new("FLOAT", "Mask")
    captured.capture_items.new("BOOLEAN", "Near")
    captured.capture_items.new("INT", "Index")
    t.connect(inputs["Mask"], captured.inputs["Mask"])
    t.connect(near, captured.inputs["Near"])
    t.connect(t.node("GeometryNodeInputIndex", 5, -4).outputs[0], captured.inputs["Index"])
    geometry = captured.outputs["Geometry"]
    near = captured.outputs["Near"]
    crop = t.node(
        "GeometryNodeSeparateGeometry",
        7,
        0,
        {"Geometry": geometry, "Selection": near},
        domain="POINT",
    ).outputs["Selection"]
    # Of the vertex in the mesh
    crop = t.store(crop, ".shrinkwrap_index", "INT", captured.outputs["Index"], 8, 0)
    crop = t.store(crop, ".shrinkwrap_mask", "FLOAT", captured.outputs["Mask"], 9, 0)

    crop = build_contact(t, inputs, crop, colliders)
    crop = build_rounds(t, inputs, crop, colliders)
    offset, moved = build_friction(t, inputs, geometry, near, crop, colliders)

    t.section("Wrap", row=True)
    wrapped = t.node(
        "GeometryNodeSetPosition",
        0,
        0,
        {"Geometry": geometry, "Selection": moved, "Offset": offset},
    )
    opened = build_opening(t, inputs, inputs["Geometry"], colliders)
    t.section("Output", row=True)
    result = t.node(
        "GeometryNodeSwitch",
        0,
        0,
        {"Switch": inputs["Opening"], "False": wrapped.outputs["Geometry"], "True": opened},
        input_type="GEOMETRY",
    ).outputs[0]
    t.node("NodeGroupOutput", 1, 0, {0: result})
    t.arrange()
    return ng


def build_opening(t, inputs, geometry, colliders):
    """Geometry with the mesh in the Zone, a radius of 1 and a height of 2, moved out from its
    axis as far as the Colliders reach out from it, to the Spread past them: monotone, the parts
    on each side never crossing, smooth as the Colliders move, and dragged along the axis by the
    Friction"""
    t.section("Opening", row=True)
    zone = t.node(
        "GeometryNodeObjectInfo",
        0,
        -2,
        {"Object": inputs["Zone"]},
        transform_space="RELATIVE",
    ).outputs["Transform"]
    local = t.node("FunctionNodeInvertMatrix", 1, -2, {"Matrix": zone}).outputs["Matrix"]

    def to_mesh(vector, x, y, point=False, matrix=zone):
        return t.node(
            "FunctionNodeTransformPoint" if point else "FunctionNodeTransformDirection",
            x,
            y,
            {"Transform": matrix, "Vector" if point else "Direction": vector},
        ).outputs[0]

    def to_zone(vector, x, y, matrix=local):
        return t.node(
            "FunctionNodeTransformPoint", x, y, {"Transform": matrix, "Vector": vector}
        ).outputs[0]

    def length(vector, x, y):
        return t.math(
            "MAXIMUM", t.vmath("LENGTH", to_mesh(vector, x, y), x=x + 1, y=y), 1e-9, x=x + 2, y=y
        )

    def axis(vector, name, x, y):
        return t.node("ShaderNodeSeparateXYZ", x, y, {0: vector}).outputs[name]

    # Sizes of the Zone in the mesh
    size = length((1.0, 0.0, 0.0), 0, -11)
    tall = length((0.0, 0.0, 1.0), 0, -12)

    # How far the Colliders reach out from the axis, cast in from the side of the Zone, on a
    # cylinder of directions and heights, smoothed not to cut at their outlines
    grid = t.node(
        "GeometryNodeMeshCylinder",
        0,
        -5,
        {
            "Vertices": OPENING_DIRECTIONS,
            "Side Segments": OPENING_HEIGHTS,
            "Radius": 1.0,
            "Depth": 2.0,
        },
        fill_type="NONE",
    ).outputs["Mesh"]
    point = t.node("GeometryNodeInputPosition", 0, -7).outputs[0]
    outward = to_mesh(t.vmath("MULTIPLY", point, (1.0, 1.0, 0.0), x=1, y=-8), 2, -8)
    across = t.vmath("LENGTH", outward, x=3, y=-9)
    direction = t.vmath("NORMALIZE", outward, x=3, y=-8)

    def fraction(ray, x, y):
        """Hit distance as a fraction of the radius of the Zone"""
        return t.math(
            "DIVIDE",
            ray["Hit Distance"],
            t.math("MAXIMUM", across, 1e-9, x=x, y=y - 1),
            x=x + 1,
            y=y,
        )

    reach = t.node(
        "GeometryNodeRaycast",
        4,
        -7,
        {
            "Target Geometry": colliders,
            "Source Position": to_mesh(point, 2, -7, point=True),
            "Ray Direction": t.vmath("SCALE", direction, -1.0, x=3, y=-7),
            "Ray Length": across,
        },
    ).outputs
    reach = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", 1.0, fraction(reach, 5, -9), x=7, y=-9),
        reach["Is Hit"],
        x=8,
        y=-8,
    )
    grid = t.store(grid, ".shrinkwrap_reach", "FLOAT", reach, 12, -5)
    smooth = t.node(
        "GeometryNodeBlurAttribute",
        13,
        -6,
        {
            "Value": t.attribute(".shrinkwrap_reach", "FLOAT", 12, -7),
            "Iterations": inputs["Smooth"],
        },
        data_type="FLOAT",
    ).outputs["Value"]
    grid = t.store(grid, ".shrinkwrap_reach", "FLOAT", smooth, 14, -5)
    # Where the mesh starts out from the axis at each height: its nearest point, those at
    # other heights farther by OPENING_LEVEL times, 0 where it closes on the axis, smoothed
    near = t.vmath(
        "MULTIPLY",
        t.node("GeometryNodeInputPosition", 13, -24).outputs[0],
        (1.0, 1.0, 0.0),
        x=14,
        y=-24,
    )
    inside = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", t.vmath("LENGTH", near, x=15, y=-24), 1.0, x=16, y=-24),
        t.math(
            "LESS_THAN",
            t.math(
                "ABSOLUTE",
                axis(t.node("GeometryNodeInputPosition", 13, -26).outputs[0], "Z", 14, -26),
                x=15,
                y=-26,
            ),
            1.0,
            x=16,
            y=-26,
        ),
        x=17,
        y=-24,
    )
    scaled = t.node(
        "ShaderNodeCombineXYZ",
        13,
        -28,
        {"X": size, "Y": size, "Z": t.math("MULTIPLY", tall, OPENING_LEVEL, x=12, y=-28)},
    ).outputs[0]
    mesh = t.node(
        "GeometryNodeSetPosition",
        14,
        -22,
        {
            "Geometry": geometry,
            "Position": to_zone(t.node("GeometryNodeInputPosition", 12, -23).outputs[0], 13, -23),
        },
    ).outputs["Geometry"]
    mesh = t.node(
        "GeometryNodeSeparateGeometry",
        18,
        -22,
        {
            "Geometry": mesh,
            "Selection": t.math(
                "MULTIPLY",
                inside,
                t.math("GREATER_THAN", inputs["Mask"], 0.0, x=17, y=-27),
                x=18,
                y=-25,
            ),
        },
    ).outputs["Selection"]
    mesh = t.node(
        "GeometryNodeSetPosition",
        19,
        -22,
        {
            "Geometry": mesh,
            "Position": t.vmath(
                "MULTIPLY",
                t.node("GeometryNodeInputPosition", 18, -28).outputs[0],
                scaled,
                x=19,
                y=-28,
            ),
        },
    ).outputs["Geometry"]
    on_axis = t.vmath(
        "MULTIPLY", t.vmath("MULTIPLY", point, (0.0, 0.0, 1.0), x=19, y=-30), scaled, x=20, y=-30
    )
    start = t.node(
        "GeometryNodeProximity",
        20,
        -24,
        {"Geometry": mesh, "Sample Position": on_axis},
        target_element="POINTS",
    ).outputs["Distance"]
    grid = t.store(
        grid, ".shrinkwrap_start", "FLOAT", t.math("DIVIDE", start, size, x=21, y=-26), 22, -5
    )
    smooth = t.node(
        "GeometryNodeBlurAttribute",
        23,
        -6,
        {
            "Value": t.attribute(".shrinkwrap_start", "FLOAT", 22, -7),
            "Iterations": inputs["Smooth"],
        },
        data_type="FLOAT",
    ).outputs["Value"]
    grid = t.store(grid, ".shrinkwrap_start", "FLOAT", smooth, 24, -5)
    grid = t.store(grid, ".shrinkwrap_drag", "FLOAT", 0.0, 17, -5)
    grid = build_opening_friction(t, inputs, grid, colliders, zone, local, tall, size)

    t.section("Open")
    # Each vertex in the Zone, from the grid in its direction at its height
    position = to_zone(t.node("GeometryNodeInputPosition", 0, -3).outputs[0], 0, -2)
    flat = t.vmath("MULTIPLY", position, (1.0, 1.0, 0.0), x=1, y=-2)
    radius = t.vmath("LENGTH", flat, x=2, y=-3)
    out = t.vmath("NORMALIZE", flat, x=2, y=-2)
    height = axis(position, "Z", 1, -4)
    on_grid = t.node(
        "ShaderNodeCombineXYZ",
        3,
        -4,
        {
            "X": axis(out, "X", 2, -5),
            "Y": axis(out, "Y", 2, -6),
            "Z": t.math("MINIMUM", t.math("MAXIMUM", height, -1.0, x=2, y=-4), 1.0, x=2.5, y=-4),
        },
    ).outputs[0]

    def sample(name, y):
        return t.node(
            "GeometryNodeSampleNearestSurface",
            4,
            y,
            {
                "Mesh": grid,
                "Value": t.attribute(name, "FLOAT", 3, y - 1),
                "Sample Position": on_grid,
            },
            data_type="FLOAT",
        ).outputs["Value"]

    reach, drag = sample(".shrinkwrap_reach", -3), sample(".shrinkwrap_drag", -5)
    start = sample(".shrinkwrap_start", -14)
    # Fading out to the top and bottom of the Zone, past its side not moving
    fade = t.node(
        "ShaderNodeMapRange",
        5,
        -9,
        {"Value": t.math("ABSOLUTE", height, x=4, y=-10), "From Min": 1.0, "From Max": 0.6},
        interpolation_type="SMOOTHSTEP",
        label="Fade",
    ).outputs[0]
    fade = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", fade, t.math("LESS_THAN", radius, 1.0, x=5, y=-11), x=6, y=-10),
        inputs["Mask"],
        x=7,
        y=-10,
    )
    # The Colliders with the Thickness kept from them, as far as the cushion keeps them, T / e
    skin = t.math(
        "DIVIDE",
        t.math("MULTIPLY", inputs["Thickness"], 0.3679, x=4, y=-12),
        size,
        x=5,
        y=-12,
    )
    reach = t.math(
        "MINIMUM",
        t.math(
            "ADD",
            reach,
            t.math("MULTIPLY", skin, t.math("GREATER_THAN", reach, 0.0, x=5, y=-13), x=6, y=-13),
            x=7,
            y=-3,
        ),
        0.95,
        x=8,
        y=-3,
    )
    # Squeezed out to the Spread past the Colliders: from [S, E] to [R, E], S where the mesh
    # starts if inside them, r' = R + (E - R) h((r - S) / (E - S)), h a cubic from 0 to 1 with
    # its slopes a at the Colliders and b at E: b = (E - S) / (E - R) easing into the mesh not
    # moved past E, not to crease there, a from 1 to b by the Firmness, moving it as a whole
    # near them, both up to 3 to stay monotone
    end = t.math(
        "MINIMUM",
        t.math("ADD", reach, t.math("DIVIDE", inputs["Spread"], size, x=9, y=-6), x=10, y=-6),
        1.0,
        x=11,
        y=-6,
    )
    start = t.math("MINIMUM", start, reach, x=9, y=-14)
    span = t.math("MAXIMUM", t.math("SUBTRACT", end, start, x=11, y=-7), 1e-6, x=12, y=-7)
    gap = t.math("MAXIMUM", t.math("SUBTRACT", end, reach, x=11, y=-8), 1e-6, x=12, y=-8)
    part = t.math(
        "DIVIDE", t.math("SUBTRACT", radius, start, x=12, y=-9), span, x=13, y=-9, clamp=True
    )
    rest = t.math("SUBTRACT", 1.0, part, x=14, y=-9)
    outer = t.math("MINIMUM", t.math("DIVIDE", span, gap, x=13, y=-8), 3.0, x=14, y=-8)
    inner = t.node(
        "ShaderNodeMix",
        15,
        -8,
        {"Factor": inputs["Firmness"], "A": 1.0, "B": outer},
        data_type="FLOAT",
    ).outputs[0]

    def poly(c3, c2, c1, c0, x, y):
        """c3 x^3 + c2 x^2 + c1 x + c0 of the part"""
        value = t.math("MULTIPLY_ADD", c3, part, c2, x=x, y=y)
        value = t.math("MULTIPLY_ADD", value, part, c1, x=x + 1, y=y)
        return t.math("MULTIPLY_ADD", value, part, c0, x=x + 2, y=y)

    # h = a (x^3 - 2x^2 + x) + (3x^2 - 2x^3) + b (x^3 - x^2)
    profile = t.math(
        "ADD",
        t.math(
            "ADD",
            t.math("MULTIPLY", inner, poly(1.0, -2.0, 1.0, 0.0, 15, -11), x=18, y=-11),
            poly(-2.0, 3.0, 0.0, 0.0, 15, -12),
            x=19,
            y=-11,
        ),
        t.math("MULTIPLY", outer, poly(1.0, -1.0, 0.0, 0.0, 15, -13), x=18, y=-13),
        x=20,
        y=-11,
    )
    squeezed = t.math("LESS_THAN", radius, end, x=16, y=-10)
    moved = t.math(
        "SUBTRACT",
        t.math("ADD", reach, t.math("MULTIPLY", gap, profile, x=18, y=-8), x=19, y=-8),
        radius,
        x=20,
        y=-8,
    )
    weight = t.math("MULTIPLY", squeezed, fade, x=19, y=-10)
    shift = t.math("MULTIPLY", t.math("MAXIMUM", moved, 0.0, x=21, y=-8), weight, x=22, y=-8)
    offset = to_mesh(t.vmath("SCALE", out, shift, x=23, y=-2), 24, -2)
    # Dragged along the axis, the most next to the Colliders
    along = t.math("MULTIPLY", t.math("MULTIPLY", drag, rest, x=21, y=-12), weight, x=22, y=-12)
    offset = t.vmath(
        "ADD",
        offset,
        to_mesh(t.node("ShaderNodeCombineXYZ", 23, -12, {"Z": along}).outputs[0], 24, -12),
        x=25,
        y=-2,
    )
    # The squeezed volume rolling up along the normals by the Roll, as much as squeezed,
    # fading to nothing at both ends, 4 x (1 - x), not to jump there
    # h' = a (3x^2 - 4x + 1) + (6x - 6x^2) + b (3x^2 - 2x)
    slope = t.math(
        "ADD",
        t.math(
            "ADD",
            t.math("MULTIPLY", inner, poly(0.0, 3.0, -4.0, 1.0, 15, -16), x=18, y=-16),
            poly(0.0, -6.0, 6.0, 0.0, 15, -17),
            x=19,
            y=-16,
        ),
        t.math("MULTIPLY", outer, poly(0.0, 3.0, -2.0, 0.0, 15, -18), x=18, y=-18),
        x=20,
        y=-16,
    )
    squeeze = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT",
            1.0,
            t.math("MULTIPLY", t.math("DIVIDE", gap, span, x=19, y=-17), slope, x=20, y=-16),
            x=21,
            y=-16,
        ),
        0.0,
        x=22,
        y=-16,
    )
    bump = t.math("MULTIPLY", t.math("MULTIPLY", part, rest, x=21, y=-18), 4.0, x=22, y=-18)
    roll = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", squeeze, bump, x=23, y=-16),
            t.math(
                "MULTIPLY",
                t.math("SUBTRACT", reach, start, x=22, y=-21),
                t.math("MULTIPLY", size, OPENING_ROLL, x=22, y=-20),
                x=23,
                y=-19,
            ),
            x=24,
            y=-16,
        ),
        t.math("MULTIPLY", inputs["Roll"], weight, x=24, y=-18),
        x=25,
        y=-16,
    )
    offset = t.vmath(
        "ADD",
        offset,
        t.vmath("SCALE", t.node("GeometryNodeInputNormal", 25, -20).outputs[0], roll, x=26, y=-20),
        x=27,
        y=-2,
    )
    return t.node(
        "GeometryNodeSetPosition", 28, 0, {"Geometry": geometry, "Offset": offset}
    ).outputs["Geometry"]


def build_opening_friction(t, inputs, grid, colliders, zone, local, tall, size):
    """Grid with the drag along the axis of the Zone in each direction and height, by the
    Colliders sliding along it where they reach up to the Stretch, springing back elsewhere,
    since the Start Frame"""
    t.section("Opening Friction", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2),
        inputs["Friction"],
        x=2,
        y=-2,
    )
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 20, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("GEOMETRY", "Colliders")

    def previous(item, y):
        return t.node(
            "GeometryNodeSwitch",
            3,
            y,
            {"Switch": started, "True": sim_in.outputs[item]},
            input_type="GEOMETRY",
        ).outputs[0]

    state, last_colliders = previous("Geometry", 0), previous("Colliders", -1)

    def count(source, x, y, component="MESH"):
        return t.node(
            "GeometryNodeAttributeDomainSize", x, y, {"Geometry": source}, component=component
        ).outputs["Point Count"]

    def same(a, b, x, y):
        return t.node(
            "FunctionNodeCompare", x, y, {"A": a, "B": b}, data_type="INT", operation="EQUAL"
        ).outputs[0]

    index = t.node("GeometryNodeInputIndex", 3, -3).outputs[0]
    kept = same(count(state, 3, -4), count(grid, 3, -5), 4, -4)

    def last(name, data_type, fallback, x, y):
        value = t.node(
            "GeometryNodeSampleIndex",
            x,
            y,
            {
                "Geometry": state,
                "Value": t.attribute(name, data_type, x - 1, y - 1),
                "Index": index,
            },
            data_type=data_type,
        ).outputs[0]
        return t.node(
            "GeometryNodeSwitch",
            x + 1,
            y,
            {"Switch": kept, "False": fallback, "True": value},
            input_type="MATRIX" if data_type == "FLOAT4X4" else "FLOAT",
        ).outputs[0]

    drag = last(".shrinkwrap_drag", "FLOAT", 0.0, 5, -6)
    speed = last(".shrinkwrap_speed", "FLOAT", 0.0, 5, -8)
    last_local = last(".shrinkwrap_zone", "FLOAT4X4", local, 5, -10)
    # How far the Colliders slid along the axis where they reach out to, in the Zone then and
    # now, not to drag the mesh moving with them
    point = t.node("GeometryNodeInputPosition", 4, -12).outputs[0]
    reach = t.attribute(".shrinkwrap_reach", "FLOAT", 4, -13)
    contact = t.node(
        "ShaderNodeCombineXYZ",
        6,
        -12,
        {
            "X": t.math(
                "MULTIPLY",
                t.node("ShaderNodeSeparateXYZ", 5, -12, {0: point}).outputs["X"],
                reach,
                x=6,
                y=-13,
            ),
            "Y": t.math(
                "MULTIPLY",
                t.node("ShaderNodeSeparateXYZ", 5, -15, {0: point}).outputs["Y"],
                reach,
                x=6,
                y=-15,
            ),
            "Z": t.node("ShaderNodeSeparateXYZ", 5, -17, {0: point}).outputs["Z"],
        },
    ).outputs[0]
    nearest = t.node(
        "GeometryNodeSampleNearest",
        8,
        -12,
        {
            "Geometry": colliders,
            "Sample Position": t.node(
                "FunctionNodeTransformPoint", 7, -12, {"Transform": zone, "Vector": contact}
            ).outputs[0],
        },
    ).outputs[0]

    def collider(source, x, y):
        return t.node(
            "GeometryNodeSampleIndex",
            x,
            y,
            {
                "Geometry": source,
                "Value": t.node("GeometryNodeInputPosition", x - 1, y - 1).outputs[0],
                "Index": nearest,
            },
            data_type="FLOAT_VECTOR",
        ).outputs[0]

    def height(matrix, vector, x, y):
        return t.node(
            "ShaderNodeSeparateXYZ",
            x + 1,
            y,
            {
                0: t.node(
                    "FunctionNodeTransformPoint", x, y, {"Transform": matrix, "Vector": vector}
                ).outputs[0]
            },
        ).outputs["Z"]

    moved = same(count(colliders, 8, -18), count(last_colliders, 8, -19), 9, -18)
    slide = t.math(
        "MULTIPLY",
        t.math(
            "SUBTRACT",
            height(local, collider(colliders, 10, -14), 11, -14),
            height(last_local, collider(last_colliders, 10, -16), 11, -16),
            x=13,
            y=-14,
        ),
        t.math("MULTIPLY", moved, kept, x=10, y=-18),
        x=14,
        y=-14,
    )
    # In contact where the Colliders reach, fading in not to switch at once
    touch = t.node(
        "ShaderNodeMapRange",
        12,
        -19,
        {"Value": reach, "From Min": 0.0, "From Max": 0.05},
        interpolation_type="SMOOTHSTEP",
        label="Touch",
    ).outputs[0]
    stretch = t.math("DIVIDE", inputs["Stretch"], tall, x=13, y=-21)
    held = t.math(
        "MINIMUM",
        t.math(
            "MAXIMUM",
            t.math("ADD", drag, slide, x=15, y=-14),
            t.math("MULTIPLY", stretch, -1.0, x=14, y=-21),
            x=16,
            y=-14,
        ),
        stretch,
        x=17,
        y=-14,
    )
    # Released, springing back: v' = (v - dt k d) / (1 + dt c + dt^2 k), d' = d + dt v'
    dt = sim_in.outputs["Delta Time"]
    omega = t.math("MULTIPLY", inputs["Frequency"], 6.283185307, x=12, y=-24)
    stiffness = t.math("MULTIPLY", omega, omega, x=13, y=-24)
    damping = t.math(
        "MULTIPLY", t.math("MULTIPLY", inputs["Damping"], 2.0, x=12, y=-25), omega, x=13, y=-25
    )
    resist = t.math(
        "ADD",
        t.math("ADD", 1.0, t.math("MULTIPLY", dt, damping, x=14, y=-25), x=15, y=-25),
        t.math("MULTIPLY", t.math("MULTIPLY", dt, dt, x=14, y=-26), stiffness, x=15, y=-26),
        x=16,
        y=-25,
    )
    spring = t.math(
        "DIVIDE",
        t.math(
            "SUBTRACT",
            speed,
            t.math("MULTIPLY", t.math("MULTIPLY", dt, stiffness, x=14, y=-23), drag, x=15, y=-23),
            x=16,
            y=-23,
        ),
        resist,
        x=17,
        y=-23,
    )
    sprung = t.math("ADD", drag, t.math("MULTIPLY", spring, dt, x=18, y=-24), x=19, y=-23)
    drag = t.node(
        "ShaderNodeMix",
        18,
        -14,
        {"Factor": touch, "A": sprung, "B": held},
        data_type="FLOAT",
    ).outputs[0]
    speed = t.math("MULTIPLY", spring, t.math("SUBTRACT", 1.0, touch, x=18, y=-26), x=19, y=-26)
    stepped = t.store(grid, ".shrinkwrap_drag", "FLOAT", drag, 18, 0)
    stepped = t.store(stepped, ".shrinkwrap_speed", "FLOAT", speed, 19, 0)
    stepped = t.store(stepped, ".shrinkwrap_zone", "FLOAT4X4", local, 19.5, 0)
    t.connect(stepped, sim_out.inputs["Geometry"])
    t.connect(colliders, sim_out.inputs["Colliders"])
    # The grid simulated while it is, else without drag
    result = sim_out.outputs["Geometry"]
    simulating = t.math(
        "MULTIPLY",
        same(count(result, 21, -3), count(grid, 21, -4), 22, -3),
        started,
        x=23,
        y=-3,
    )
    return t.node(
        "GeometryNodeSwitch",
        24,
        0,
        {"Switch": simulating, "False": grid, "True": result},
        input_type="GEOMETRY",
    ).outputs[0]


def outward(t, colliders):
    """Colliders with the faces of each part flipped if facing in, by its signed volume, e.g.
    mirrored by a negative scale"""
    t.section("Outward")
    island = t.node("GeometryNodeInputMeshIsland", 0, -6).outputs["Island Index"]
    area = t.node("GeometryNodeInputMeshFaceArea", 0, -7).outputs[0]
    center = t.node("GeometryNodeInputPosition", 0, -8).outputs[0]

    def total(value, data_type, y):
        return t.node(
            "GeometryNodeAccumulateField",
            2,
            y,
            {"Value": value, "Group ID": island},
            data_type=data_type,
            domain="FACE",
        ).outputs["Total"]

    middle = t.vmath(
        "DIVIDE",
        total(t.vmath("SCALE", center, area, x=1, y=-8), "FLOAT_VECTOR", -8),
        t.math("MAXIMUM", total(area, "FLOAT", -7), 1e-12, x=3, y=-7),
        x=4,
        y=-8,
    )
    volume = total(
        t.math(
            "MULTIPLY",
            t.vmath(
                "DOT_PRODUCT",
                t.vmath("SUBTRACT", center, middle, x=5, y=-8),
                t.node("GeometryNodeInputNormal", 4, -9).outputs[0],
                x=6,
                y=-8,
            ),
            area,
            x=7,
            y=-8,
        ),
        "FLOAT",
        -10,
    )
    return t.node(
        "GeometryNodeFlipFaces",
        8,
        0,
        {"Mesh": colliders, "Selection": t.math("LESS_THAN", volume, -1e-15, x=8, y=-10)},
    ).outputs[0]


def surface(t, colliders, position, x, y, facing=None, reach=None):
    """Nearest point of the Colliders, the way out of them from there and how far it is along
    it, negative inside: the side told by their vertex normals, between the faces at the edges
    whatever the shading, not to take a point by an edge for inside. With the direction the
    mesh faces, the way out of the vertices inside is back against it, within the reach, rather
    than through the Colliders out of the side they went in, e.g. lips past the middle of a rod,
    as the Colliders only push the mesh into what is behind it"""
    nearest = t.node(
        "GeometryNodeProximity",
        x,
        y,
        {"Geometry": colliders, "Sample Position": position},
        target_element="FACES",
    ).outputs
    normal = t.node(
        "GeometryNodeSampleNearestSurface",
        x,
        y - 2,
        {
            "Mesh": colliders,
            "Value": t.node(
                "GeometryNodeFieldOnDomain",
                x - 1,
                y - 2,
                {"Value": t.node("GeometryNodeInputNormal", x - 2, y - 2).outputs[0]},
                data_type="FLOAT_VECTOR",
                domain="POINT",
            ).outputs[0],
            "Sample Position": position,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    toward = t.vmath("SUBTRACT", position, nearest["Position"], x=x + 1, y=y - 1)
    sign = t.math(
        "SIGN", t.vmath("DOT_PRODUCT", toward, normal, x=x + 2, y=y - 2), x=x + 3, y=y - 2
    )
    # Along the normal on the surface
    away = t.node(
        "GeometryNodeSwitch",
        x + 4,
        y - 1,
        {
            "Switch": t.math("GREATER_THAN", nearest["Distance"], 1e-7, x=x + 3, y=y - 3),
            "False": t.vmath("NORMALIZE", normal, x=x + 3, y=y - 4),
            "True": t.vmath(
                "SCALE", t.vmath("NORMALIZE", toward, x=x + 2, y=y - 1), sign, x=x + 3, y=y - 1
            ),
        },
        input_type="VECTOR",
    ).outputs[0]
    side = t.math("MULTIPLY", nearest["Distance"], sign, x=x + 4, y=y - 3)
    if facing is None:
        return nearest, away, side
    back = t.vmath("SCALE", facing, -1.0, x=x + 4, y=y - 5)
    ray = t.node(
        "GeometryNodeRaycast",
        x + 5,
        y - 5,
        {
            "Target Geometry": colliders,
            "Source Position": position,
            "Ray Direction": back,
            "Ray Length": reach,
        },
    ).outputs
    # Smoothly back to the nearest way when the way back is much longer, e.g. along a rod, so
    # not to switch at once as the Colliders move
    ratio = t.math(
        "DIVIDE",
        ray["Hit Distance"],
        t.math("MAXIMUM", nearest["Distance"], 1e-7, x=x + 5, y=y - 7),
        x=x + 6,
        y=y - 6,
    )
    back_weight = t.node(
        "ShaderNodeMapRange",
        x + 7,
        y - 6,
        {"Value": ratio, "From Min": BACK_RATIO * 1.6, "From Max": BACK_RATIO * 0.6},
        interpolation_type="SMOOTHSTEP",
        label="Back",
    ).outputs[0]
    back_weight = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", back_weight, ray["Is Hit"], x=x + 8, y=y - 6),
        t.math("LESS_THAN", side, 0.0, x=x + 7, y=y - 4),
        x=x + 9,
        y=y - 5,
    )
    away = t.node(
        "ShaderNodeMix",
        x + 10,
        y - 1,
        {"Factor": back_weight, "A": away, "B": back},
        data_type="VECTOR",
    ).outputs[1]
    away = t.vmath("NORMALIZE", away, x=x + 11, y=y - 1)
    side = t.node(
        "ShaderNodeMix",
        x + 10,
        y - 3,
        {
            "Factor": back_weight,
            "A": side,
            "B": t.math("MULTIPLY", ray["Hit Distance"], -1.0, x=x + 9, y=y - 7),
        },
        data_type="FLOAT",
    ).outputs[0]
    return nearest, away, side


def build_contact(t, inputs, crop, colliders):
    """Crop with how far the vertices are pushed out of the Colliders, and how much they are
    held in place at the Spread"""
    t.section("Contact", row=True)
    position = t.node("GeometryNodeInputPosition", 0, -2).outputs[0]
    smooth = t.node(
        "GeometryNodeBlurAttribute",
        0,
        -13,
        {
            "Value": t.node("GeometryNodeInputNormal", 0, -14).outputs[0],
            "Iterations": inputs["Smooth Normals"],
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    smooth = t.vmath("NORMALIZE", smooth, x=1, y=-13)
    nearest, normal, side = surface(
        t, colliders, position, 1, -2, smooth, exit_reach(t, inputs, 0, -16)
    )
    thickness = t.math("MAXIMUM", inputs["Thickness"], 1e-6, x=3, y=-5)
    # Out to T e^((s - T) / T) from the side s under the Thickness T, never into the Colliders
    # and smooth where the Thickness starts
    under = t.math("MINIMUM", side, thickness, x=4, y=-4)
    cushion = t.math(
        "MULTIPLY",
        thickness,
        t.math(
            "EXPONENT",
            t.math("DIVIDE", t.math("SUBTRACT", under, thickness, x=5, y=-4), thickness, x=6, y=-4),
            x=7,
            y=-4,
        ),
        x=8,
        y=-4,
    )
    push = t.math("MAXIMUM", t.math("SUBTRACT", cushion, side, x=9, y=-3), 0.0, x=10, y=-3)
    push = t.math("MULTIPLY", push, t.attribute(".shrinkwrap_mask", "FLOAT", 9, -5), x=11, y=-3)
    # In contact from the push of a vertex on the surface, T / e
    contact = t.math(
        "DIVIDE", push, t.math("MULTIPLY", thickness, 0.3679, x=10, y=-6), x=12, y=-5, clamp=True
    )
    # Held at the reach of the push, fading in from 3/4 of it
    reach = t.math(
        "ADD",
        t.math("MULTIPLY", inputs["Spread"], 2.0, x=2, y=-12),
        inputs["Thickness"],
        x=3,
        y=-11,
    )
    far = t.node(
        "ShaderNodeMapRange",
        5,
        -10,
        {
            "Value": nearest["Distance"],
            "From Min": t.math("MULTIPLY", reach, 0.75, x=4, y=-11),
            "From Max": reach,
        },
        interpolation_type="SMOOTHSTEP",
        label="Far",
    ).outputs[0]
    crop = t.store(crop, ".shrinkwrap_side", "FLOAT", side, 12, 1)
    crop = t.store(crop, ".shrinkwrap_away", "FLOAT_VECTOR", normal, 13, 0)
    crop = t.store(crop, ".shrinkwrap_push", "FLOAT", push, 14, 0)
    crop = t.store(crop, ".shrinkwrap_grip", "FLOAT", contact, 15, 0)
    crop = t.store(crop, ".shrinkwrap_pin", "FLOAT", far, 16, 0)
    crop = t.store(crop, ".shrinkwrap_normal", "FLOAT_VECTOR", smooth, 17, 0)
    offset = t.vmath("SCALE", normal, push, x=12, y=-2)
    return t.store(crop, ".shrinkwrap_offset", "FLOAT_VECTOR", offset, 18, 0)


def spread(t, crop, iterations, name, constrain, x, y):
    """Vectors in the named attribute spread over the mesh around, held by the pins, then
    constrained, e.g. to the push"""
    start = t.node("GeometryNodeRepeatInput", x, y, {"Iterations": iterations})
    end = t.node("GeometryNodeRepeatOutput", x + 6, y)
    start.pair_with_output(end)
    t.connect(crop, start.inputs["Geometry"])
    blur = t.node(
        "GeometryNodeBlurAttribute",
        x + 1,
        y - 1,
        {"Value": t.attribute(name, "FLOAT_VECTOR", x, y - 1)},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    held = t.math(
        "SUBTRACT", 1.0, t.attribute(".shrinkwrap_pin", "FLOAT", x + 1, y - 3), x=x + 2, y=y - 3
    )
    value = constrain(t.vmath("SCALE", blur, held, x=x + 2, y=y - 1), x + 3, y - 1)
    stored = t.store(start.outputs["Geometry"], name, "FLOAT_VECTOR", value, x + 5, y)
    t.connect(stored, end.inputs["Geometry"])
    return end.outputs["Geometry"]


def pushed(t, inputs, value, x, y):
    """The offset pushed out at least by the push, never pulled in, and by just the push in
    contact without Firmness, flattening on the Colliders"""
    away = t.attribute(".shrinkwrap_away", "FLOAT_VECTOR", x, y - 1)
    push = t.attribute(".shrinkwrap_push", "FLOAT", x, y - 2)
    along = t.vmath("DOT_PRODUCT", value, away, x=x + 1, y=y - 1)
    least = t.math("MAXIMUM", along, push, x=x + 2, y=y - 2)
    target = t.node(
        "ShaderNodeMix",
        x + 3,
        y - 2,
        {
            "Factor": t.math(
                "MULTIPLY",
                t.attribute(".shrinkwrap_grip", "FLOAT", x + 1, y - 3),
                t.math("SUBTRACT", 1.0, inputs["Firmness"], x=x + 1, y=y - 4),
                x=x + 2,
                y=y - 3,
            ),
            "A": least,
            "B": push,
        },
        data_type="FLOAT",
    ).outputs[0]
    short = t.math("SUBTRACT", target, along, x=x + 4, y=y - 2)
    return t.vmath("ADD", value, t.vmath("SCALE", away, short, x=x + 4, y=y - 1), x=x + 5, y=y)


def exit_reach(t, inputs, x, y):
    """How far the mesh is pushed out of the Colliders at most, twice the Spread"""
    return t.math("MULTIPLY", inputs["Spread"], 2.0, x=x, y=y)


def push_out(t, inputs, crop, colliders, x, y):
    """Vertices of the Mask moved into the Colliders back out, pushed from then on"""
    position = t.vmath(
        "ADD",
        t.node("GeometryNodeInputPosition", x, y - 1).outputs[0],
        t.attribute(".shrinkwrap_offset", "FLOAT_VECTOR", x, y - 2),
        x=x + 1,
        y=y - 1,
    )
    _, normal, side = surface(
        t,
        colliders,
        position,
        x + 2,
        y - 1,
        t.attribute(".shrinkwrap_normal", "FLOAT_VECTOR", x + 1, y - 7),
        exit_reach(t, inputs, x + 1, y - 8),
    )
    short = t.math("SUBTRACT", SKIN, side, x=x + 5, y=y - 2)
    inside = t.math("GREATER_THAN", short, 0.0, x=x + 6, y=y - 2)
    masked = t.math(
        "GREATER_THAN",
        t.attribute(".shrinkwrap_mask", "FLOAT", x + 5, y - 4),
        0.0,
        x=x + 6,
        y=y - 4,
    )
    held = t.math(
        "LESS_THAN", t.attribute(".shrinkwrap_pin", "FLOAT", x + 5, y - 5), 1.0, x=x + 6, y=y - 5
    )
    inside = t.math(
        "MULTIPLY", t.math("MULTIPLY", inside, masked, x=x + 7, y=y - 4), held, x=x + 7, y=y - 2
    )
    offset = t.vmath(
        "ADD",
        t.attribute(".shrinkwrap_offset", "FLOAT_VECTOR", x + 6, y - 6),
        t.vmath("SCALE", normal, short, x=x + 6, y=y - 3),
        x=x + 7,
        y=y - 3,
    )
    # Captured not to move the vertices before reading where the others are
    captured = t.node("GeometryNodeCaptureAttribute", x + 8, y, {"Geometry": crop})
    for name, item_type, value in (
        ("Inside", "BOOLEAN", inside),
        ("Offset", "VECTOR", offset),
        ("Away", "VECTOR", normal),
    ):
        captured.capture_items.new(item_type, name)
        t.connect(value, captured.inputs[name])
    selected = captured.outputs["Inside"]
    away = captured.outputs["Away"]
    offset = captured.outputs["Offset"]
    crop = captured.outputs["Geometry"]
    crop = t.store(crop, ".shrinkwrap_away", "FLOAT_VECTOR", away, x + 9, y, selection=selected)
    push = t.vmath("DOT_PRODUCT", offset, away, x=x + 9, y=y - 2)
    crop = t.store(crop, ".shrinkwrap_push", "FLOAT", push, x + 10, y, selection=selected)
    crop = t.store(crop, ".shrinkwrap_grip", "FLOAT", 1.0, x + 11, y, selection=selected)
    return t.store(
        crop, ".shrinkwrap_offset", "FLOAT_VECTOR", offset, x + 12, y, selection=selected
    )


def build_follow(t, inputs, crop, colliders):
    """Crop with the offsets of the push of the nearest vertex in contact along the mesh,
    fading out with the distance like an elastic body pushed, a regularized Kelvinlet, to the
    Spread"""
    t.section("Follow", row=True)
    grip = t.attribute(".shrinkwrap_grip", "FLOAT", 0, -3)
    push = t.vmath(
        "SCALE",
        t.attribute(".shrinkwrap_away", "FLOAT_VECTOR", 0, -4),
        t.attribute(".shrinkwrap_push", "FLOAT", 0, -5),
        x=1,
        y=-4,
    )

    def blur(value, data_type, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            2,
            y,
            {"Value": value, "Iterations": DRAG_ITERATIONS},
            data_type=data_type,
        ).outputs["Value"]

    # Averaged over the contact nearby, not to change at once between them
    push = t.vmath(
        "DIVIDE",
        blur(t.vmath("SCALE", push, grip, x=1, y=-2), "FLOAT_VECTOR", -2),
        t.math("MAXIMUM", blur(grip, "FLOAT", -3), 1e-6, x=3, y=-3),
        x=3,
        y=-2,
    )
    crop = t.store(crop, ".shrinkwrap_follow", "FLOAT_VECTOR", push, 4, 0)
    touching = t.math(
        "GREATER_THAN", t.attribute(".shrinkwrap_push", "FLOAT", 4, -2), 0.0, x=5, y=-2
    )
    contact = t.node(
        "GeometryNodeSeparateGeometry",
        5,
        0,
        {"Geometry": crop, "Selection": touching},
        domain="POINT",
    ).outputs["Selection"]
    # The contact nearby moved together by the Firmness along its mean push, out of the
    # Colliders by about its deepest point along it, not torn apart where they go through it
    push = t.attribute(".shrinkwrap_follow", "FLOAT_VECTOR", 5, -5)

    def nearby(value, data_type, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            6,
            y,
            {"Value": value, "Iterations": FIRM_ITERATIONS},
            data_type=data_type,
        ).outputs["Value"]

    total = nearby(push, "FLOAT_VECTOR", -6)
    mean = t.vmath("NORMALIZE", total, x=7, y=-6)
    # How much the pushes nearby agree, none around a rod inside the mesh, as their mean
    # direction is no way out then
    agree = t.math(
        "DIVIDE",
        t.vmath("LENGTH", total, x=7, y=-14),
        t.math(
            "MAXIMUM",
            nearby(t.vmath("LENGTH", push, x=6, y=-15), "FLOAT", -15),
            1e-9,
            x=7,
            y=-15,
        ),
        x=8,
        y=-14,
    )
    agree = t.node(
        "ShaderNodeMapRange",
        9,
        -14,
        {"Value": agree, "From Min": 0.5, "From Max": 0.9},
        interpolation_type="SMOOTHSTEP",
        label="Agree",
    ).outputs[0]
    exit = t.node(
        "GeometryNodeRaycast",
        7,
        -8,
        {
            "Target Geometry": colliders,
            "Ray Direction": mean,
            "Ray Length": t.math("MULTIPLY", inputs["Spread"], 4.0, x=6, y=-9),
        },
    ).outputs
    side = t.attribute(".shrinkwrap_side", "FLOAT", 6, -10)
    inside = t.math(
        "MULTIPLY", t.math("LESS_THAN", side, 0.0, x=7, y=-10), exit["Is Hit"], x=8, y=-10
    )
    # Out along it with the cushion of the surface, else as pushed along it
    thickness = t.math("MAXIMUM", inputs["Thickness"], 1e-6, x=7, y=-12)
    cushion = t.math(
        "MULTIPLY",
        thickness,
        t.math(
            "EXPONENT",
            t.math(
                "DIVIDE",
                t.math(
                    "SUBTRACT",
                    t.math("MULTIPLY", exit["Hit Distance"], -1.0, x=8, y=-11),
                    thickness,
                    x=9,
                    y=-11,
                ),
                thickness,
                x=10,
                y=-11,
            ),
            x=11,
            y=-11,
        ),
        x=12,
        y=-11,
    )
    need = t.node(
        "GeometryNodeSwitch",
        13,
        -8,
        {
            "Switch": inside,
            "False": t.math(
                "MAXIMUM", t.vmath("DOT_PRODUCT", push, mean, x=11, y=-7), 0.0, x=12, y=-7
            ),
            # Not much more than its own push, not to slide far along the Colliders
            "True": t.math(
                "MINIMUM",
                t.math("ADD", exit["Hit Distance"], cushion, x=12, y=-10),
                t.math("MULTIPLY", t.vmath("LENGTH", push, x=11, y=-13), 1.5, x=12, y=-13),
                x=13,
                y=-10,
            ),
        },
        input_type="FLOAT",
    ).outputs[0]
    # Soft maximum, (mean of need^p)^(1 / p), not below its own
    deepest = t.math(
        "POWER",
        nearby(t.math("POWER", need, FIRM_POWER, x=13, y=-6), "FLOAT", -7),
        1.0 / FIRM_POWER,
        x=14,
        y=-6,
    )
    deepest = t.math("MAXIMUM", deepest, need, x=14, y=-7)
    firmness = t.math("MULTIPLY", inputs["Firmness"], agree, x=14, y=-14)
    follow = t.node(
        "ShaderNodeMix",
        15,
        -5,
        {"Factor": firmness, "A": push, "B": t.vmath("SCALE", mean, deepest, x=15, y=-6)},
        data_type="VECTOR",
    ).outputs[1]
    # Pushed at least that far that way from then on
    away = t.node(
        "ShaderNodeMix",
        15,
        -8,
        {
            "Factor": firmness,
            "A": t.attribute(".shrinkwrap_away", "FLOAT_VECTOR", 14, -9),
            "B": mean,
        },
        data_type="VECTOR",
    ).outputs[1]
    least = t.node(
        "ShaderNodeMix",
        15,
        -10,
        {
            "Factor": firmness,
            "A": t.attribute(".shrinkwrap_push", "FLOAT", 14, -11),
            "B": deepest,
        },
        data_type="FLOAT",
    ).outputs[0]
    contact = t.store(contact, ".shrinkwrap_follow", "FLOAT_VECTOR", follow, 16, 0)
    contact = t.store(
        contact, ".shrinkwrap_away", "FLOAT_VECTOR", t.vmath("NORMALIZE", away, x=16, y=-8), 17, 0
    )
    contact = t.store(contact, ".shrinkwrap_push", "FLOAT", least, 18, 0)
    # Back on the crop, whose order the contact keeps
    order = t.node(
        "GeometryNodeAccumulateField", 18, -5, {"Value": touching}, data_type="INT"
    ).outputs["Trailing"]
    for i, (name, data_type) in enumerate(
        (
            (".shrinkwrap_follow", "FLOAT_VECTOR"),
            (".shrinkwrap_away", "FLOAT_VECTOR"),
            (".shrinkwrap_push", "FLOAT"),
        )
    ):
        value = t.node(
            "GeometryNodeSampleIndex",
            19,
            -2 - 2 * i,
            {
                "Geometry": contact,
                "Value": t.attribute(name, data_type, 18, -3 - 2 * i),
                "Index": order,
            },
            data_type=data_type,
        ).outputs[0]
        crop = t.store(crop, name, data_type, value, 20 + i, 0, selection=touching)

    t.section("Nearest Contact", row=True)
    # Along the mesh, not across a gap, e.g. the lower lip under the upper one
    ends = t.node("GeometryNodeInputMeshEdgeVertices", 0, -4).outputs
    paths = t.node(
        "GeometryNodeInputShortestEdgePaths",
        1,
        -3,
        {
            "End Vertex": t.math(
                "GREATER_THAN", t.attribute(".shrinkwrap_push", "FLOAT", 0, -2), 0.0, x=1, y=-2
            ),
            "Edge Cost": t.vmath("DISTANCE", ends["Position 1"], ends["Position 2"], x=1, y=-4),
        },
    ).outputs
    crop = t.store(crop, ".shrinkwrap_root", "INT", paths["Next Vertex Index"], 2, 0)
    crop = t.store(crop, ".shrinkwrap_path", "FLOAT", paths["Total Cost"], 3, 0)
    # Following the paths to their ends, doubling the steps each time
    start = t.node("GeometryNodeRepeatInput", 4, 0, {"Iterations": PATH_JUMPS})
    end = t.node("GeometryNodeRepeatOutput", 6, 0)
    start.pair_with_output(end)
    t.connect(crop, start.inputs["Geometry"])
    root = t.attribute(".shrinkwrap_root", "INT", 4, -2)
    jumped = t.node(
        "GeometryNodeSampleIndex",
        5,
        -2,
        {"Geometry": start.outputs["Geometry"], "Value": root, "Index": root},
        data_type="INT",
    ).outputs[0]
    t.connect(
        t.store(start.outputs["Geometry"], ".shrinkwrap_root", "INT", jumped, 5, 0),
        end.inputs["Geometry"],
    )
    crop = end.outputs["Geometry"]
    root = t.attribute(".shrinkwrap_root", "INT", 6, -3)

    def sample(value, y, data_type="FLOAT_VECTOR"):
        return t.node(
            "GeometryNodeSampleIndex",
            7,
            y,
            {"Geometry": crop, "Value": value, "Index": root},
            data_type=data_type,
        ).outputs[0]

    position = t.node("GeometryNodeInputPosition", 6, -6).outputs[0]
    # None for the vertices not reaching any
    reached = t.math(
        "GREATER_THAN",
        sample(t.attribute(".shrinkwrap_push", "FLOAT", 6, -5), -5, "FLOAT"),
        0.0,
        x=8,
        y=-5,
    )
    follow = t.vmath(
        "SCALE",
        sample(t.attribute(".shrinkwrap_follow", "FLOAT_VECTOR", 6, -4), -4),
        reached,
        x=8,
        y=-4,
    )
    # Through the volume, as long as the mesh between is not much longer
    distance = t.math(
        "MAXIMUM",
        t.vmath("DISTANCE", sample(position, -6), position, x=8, y=-6),
        t.math("MULTIPLY", t.attribute(".shrinkwrap_path", "FLOAT", 7, -8), PATH_RATIO, x=8, y=-8),
        x=9,
        y=-6,
    )

    t.section("Fade", row=True)
    # (e / r)(1 + e^2 / 2r^2) / 1.5, r = sqrt(d^2 + e^2), 1 at the contact, e and the reach
    # wider for the deeper pushes, up to twice the Spread, not to fold the mesh over
    depth = t.vmath("LENGTH", follow, x=7, y=-8)
    size = t.math(
        "MINIMUM",
        t.math(
            "MAXIMUM",
            t.math("DIVIDE", inputs["Spread"], 3.0, x=8, y=-8),
            t.math("MULTIPLY", depth, 1.5, x=8, y=-7),
            x=9,
            y=-8,
        ),
        t.math("MULTIPLY", inputs["Spread"], 0.6667, x=8, y=-9),
        x=9,
        y=-7,
    )
    reach = t.math(
        "MINIMUM",
        t.math("MAXIMUM", inputs["Spread"], t.math("MULTIPLY", depth, 3.0, x=8, y=-11), x=9, y=-11),
        t.math("MULTIPLY", inputs["Spread"], 2.0, x=8, y=-12),
        x=10,
        y=-11,
    )
    radius = t.math(
        "SQRT",
        t.math(
            "ADD",
            t.math("MULTIPLY", distance, distance, x=10, y=-6),
            t.math("MULTIPLY", size, size, x=10, y=-7),
            x=11,
            y=-6,
        ),
        x=12,
        y=-6,
    )
    ratio = t.math("DIVIDE", size, radius, x=13, y=-6)
    fade = t.math(
        "MULTIPLY",
        ratio,
        t.math(
            "ADD",
            1.0,
            t.math("MULTIPLY", t.math("MULTIPLY", ratio, ratio, x=14, y=-7), 0.5, x=15, y=-7),
            x=16,
            y=-7,
        ),
        x=17,
        y=-6,
    )
    fade = t.math("DIVIDE", fade, 1.5, x=18, y=-6)
    cut = t.node(
        "ShaderNodeMapRange",
        17,
        -8,
        {
            "Value": distance,
            "From Min": reach,
            "From Max": t.math("MULTIPLY", reach, 0.5, x=16, y=-9),
        },
        interpolation_type="SMOOTHSTEP",
        label="Cut",
    ).outputs[0]
    fade = t.math("MULTIPLY", fade, cut, x=19, y=-6)
    offset = t.vmath("SCALE", follow, fade, x=20, y=-2)
    return t.store(crop, ".shrinkwrap_offset", "FLOAT_VECTOR", offset, 21, 0)


def build_rounds(t, inputs, crop, colliders):
    """Crop with the offsets followed and smoothed, kept out of the Colliders, with the roll"""
    crop = build_follow(t, inputs, crop, colliders)
    t.section("Smooth", row=True)
    start = t.node("GeometryNodeRepeatInput", 0, 0, {"Iterations": ROUNDS})
    end = t.node("GeometryNodeRepeatOutput", 24, 0)
    start.pair_with_output(end)
    t.connect(crop, start.inputs["Geometry"])
    iterations = t.math("CEIL", t.math("DIVIDE", inputs["Smooth"], ROUNDS, x=0, y=-2), x=1, y=-2)
    spreaded = spread(
        t,
        start.outputs["Geometry"],
        iterations,
        ".shrinkwrap_offset",
        lambda value, x, y: pushed(t, inputs, value, x, y),
        1,
        0,
    )
    t.connect(push_out(t, inputs, spreaded, colliders, 8, 0), end.inputs["Geometry"])
    crop = end.outputs["Geometry"]

    t.section("Roll", row=True)
    # How deep the vertices in contact are pushed in, rolling up next to them
    normal = t.attribute(".shrinkwrap_normal", "FLOAT_VECTOR", 0, -2)
    offset = t.attribute(".shrinkwrap_offset", "FLOAT_VECTOR", 0, -3)
    grip = t.attribute(".shrinkwrap_grip", "FLOAT", 0, -4)
    pressed = t.math("MULTIPLY", t.attribute(".shrinkwrap_push", "FLOAT", 0, -5), grip, x=4, y=-3)

    def blur(value, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            5,
            y,
            {"Value": value, "Iterations": ROLL_ITERATIONS},
            data_type="FLOAT",
        ).outputs["Value"]

    # Depth of the vertices in contact nearby, highest right next to them
    near = blur(grip, -6)
    pressed = t.math(
        "DIVIDE", blur(pressed, -3), t.math("MAXIMUM", near, 1e-6, x=6, y=-6), x=6, y=-3
    )
    pressed = t.math("MULTIPLY", pressed, near, x=6.5, y=-3)
    free = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", 1.0, grip, x=5, y=-4),
        t.math("SUBTRACT", 1.0, t.attribute(".shrinkwrap_pin", "FLOAT", 4, -5), x=5, y=-5),
        x=6,
        y=-4,
    )
    height = t.math(
        "MULTIPLY", t.math("MULTIPLY", pressed, inputs["Roll"], x=7, y=-3), free, x=8, y=-3
    )
    offset = t.vmath("ADD", offset, t.vmath("SCALE", normal, height, x=8, y=-2), x=9, y=-2)
    crop = t.store(crop, ".shrinkwrap_offset", "FLOAT_VECTOR", offset, 10, 0)
    # Smoothed with the roll
    crop = spread(
        t,
        crop,
        iterations,
        ".shrinkwrap_offset",
        lambda value, x, y: pushed(t, inputs, value, x, y),
        11,
        0,
    )
    return push_out(t, inputs, crop, colliders, 18, 0)


def build_friction(t, inputs, geometry, near, crop, colliders):
    """Offsets of the vertices, with the contact dragged along by the Colliders since the Start
    Frame and springing back when released, the pushed ones without Friction, and the vertices
    they move"""
    t.section("Friction", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 40, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("GEOMETRY", "Colliders")

    def previous(item, y):
        return t.node(
            "GeometryNodeSwitch",
            3,
            y,
            {"Switch": started, "True": sim_in.outputs[item]},
            input_type="GEOMETRY",
        ).outputs[0]

    state, last_colliders = previous("Geometry", 0), previous("Colliders", -1)

    def count(source, x, y, component="MESH"):
        return t.node(
            "GeometryNodeAttributeDomainSize", x, y, {"Geometry": source}, component=component
        ).outputs["Point Count"]

    def same(a, b, x, y):
        return t.node(
            "FunctionNodeCompare", x, y, {"A": a, "B": b}, data_type="INT", operation="EQUAL"
        ).outputs[0]

    vertices = count(geometry, 3, -3)
    kept = same(vertices, count(state, 3, -4, "POINTCLOUD"), 4, -4)

    def sample(source, name, index, x, y, data_type="FLOAT_VECTOR"):
        return t.node(
            "GeometryNodeSampleIndex",
            x,
            y,
            {
                "Geometry": source,
                "Value": t.attribute(name, data_type, x - 1, y - 1),
                "Index": index,
            },
            data_type=data_type,
        ).outputs[0]

    def switch(condition, false, true, x, y):
        return t.node(
            "GeometryNodeSwitch",
            x,
            y,
            {"Switch": condition, "False": false, "True": true},
            input_type="VECTOR",
        ).outputs[0]

    # How far the Colliders moved since the last frame
    t.section("Colliders Motion")
    position = t.node("GeometryNodeInputPosition", 0, -2).outputs[0]
    moved = t.node(
        "GeometryNodeSampleIndex",
        1,
        -2,
        {
            "Geometry": last_colliders,
            "Value": position,
            "Index": t.node("GeometryNodeInputIndex", 0, -3).outputs[0],
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    moved = switch(
        same(count(colliders, 1, -4), count(last_colliders, 1, -5), 2, -4),
        (0.0, 0.0, 0.0),
        t.vmath("SUBTRACT", position, moved, x=2, y=-2),
        3,
        -2,
    )
    moving = t.store(colliders, ".shrinkwrap_motion", "FLOAT_VECTOR", moved, 4, 0)

    t.section("Drag", row=True)
    # The contact dragged along by the Colliders sliding past the wrapped mesh, up to the Stretch
    index = t.attribute(".shrinkwrap_index", "INT", 0, -4)
    wrapped = t.vmath(
        "ADD",
        t.node("GeometryNodeInputPosition", 0, -2).outputs[0],
        t.attribute(".shrinkwrap_offset", "FLOAT_VECTOR", 0, -3),
        x=1,
        y=-2,
    )
    last_drag = switch(
        kept, (0.0, 0.0, 0.0), sample(state, ".shrinkwrap_drag", index, 2, -5), 3, -5
    )
    last_wrapped = switch(kept, wrapped, sample(state, ".shrinkwrap_wrapped", index, 2, -7), 3, -7)
    last_speed = switch(
        kept, (0.0, 0.0, 0.0), sample(state, ".shrinkwrap_speed", index, 2, -9), 3, -9
    )
    contact = t.vmath("ADD", wrapped, last_drag, x=4, y=-4)
    motion = t.node(
        "GeometryNodeSampleNearestSurface",
        5,
        -4,
        {
            "Mesh": moving,
            "Value": t.attribute(".shrinkwrap_motion", "FLOAT_VECTOR", 4, -5),
            "Sample Position": contact,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    _, normal, _ = surface(t, colliders, contact, 5, -7)
    slide = t.vmath(
        "SUBTRACT", motion, t.vmath("SUBTRACT", wrapped, last_wrapped, x=5, y=-10), x=6, y=-4
    )
    drag = t.vmath("ADD", last_drag, slide, x=7, y=-4)
    drag = t.vmath(
        "SUBTRACT",
        drag,
        t.vmath("SCALE", normal, t.vmath("DOT_PRODUCT", drag, normal, x=8, y=-6), x=9, y=-6),
        x=10,
        y=-4,
    )
    length = t.vmath("LENGTH", drag, x=11, y=-6)
    limit = t.math(
        "MINIMUM",
        t.math(
            "DIVIDE", inputs["Stretch"], t.math("MAXIMUM", length, 1e-9, x=12, y=-6), x=13, y=-6
        ),
        1.0,
        x=14,
        y=-6,
    )
    drag = t.vmath("SCALE", drag, limit, x=15, y=-4)
    # Averaged over the contact nearby, the vertices just touching sticking with the others
    grip = t.attribute(".shrinkwrap_grip", "FLOAT", 15, -8)

    def blur(value, data_type, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            16,
            y,
            {"Value": value, "Iterations": DRAG_ITERATIONS},
            data_type=data_type,
        ).outputs["Value"]

    drag = t.vmath(
        "DIVIDE",
        blur(t.vmath("SCALE", drag, grip, x=15, y=-5), "FLOAT_VECTOR", -4),
        t.math("MAXIMUM", blur(grip, "FLOAT", -8), 1e-6, x=17, y=-8),
        x=17,
        y=-4,
    )
    # Captured as the Colliders normals are sampled where the vertices were
    held = t.node("GeometryNodeCaptureAttribute", 18, 0, {"Geometry": crop})
    for name, item_type in (
        ("Source", "VECTOR"),
        ("Drag", "VECTOR"),
        ("Wrapped", "VECTOR"),
        ("Speed", "VECTOR"),
    ):
        held.capture_items.new(item_type, name)
    for name, value in (
        ("Source", drag),
        ("Drag", last_drag),
        ("Wrapped", wrapped),
        ("Speed", last_speed),
    ):
        t.connect(value, held.inputs[name])
    dragged = t.store(
        held.outputs["Geometry"], ".shrinkwrap_drag", "FLOAT_VECTOR", held.outputs["Drag"], 17, 0
    )
    # Set to the drag in the contact
    dragged = spread(
        t,
        dragged,
        inputs["Smooth"],
        ".shrinkwrap_drag",
        lambda value, x, y: t.node(
            "ShaderNodeMix",
            x,
            y,
            {
                "Factor": t.attribute(".shrinkwrap_grip", "FLOAT", x, y - 1),
                "A": value,
                "B": held.outputs["Source"],
            },
            data_type="VECTOR",
        ).outputs[1],
        19,
        0,
    )

    t.section("Spring Back", row=True)
    dt = sim_in.outputs["Delta Time"]
    omega = t.math("MULTIPLY", inputs["Frequency"], 6.283185307, x=0, y=-6)
    stiffness = t.math("MULTIPLY", omega, omega, x=1, y=-6)
    damping = t.math(
        "MULTIPLY", t.math("MULTIPLY", inputs["Damping"], 2.0, x=0, y=-7), omega, x=1, y=-7
    )
    resist = t.math(
        "ADD",
        t.math("ADD", 1.0, t.math("MULTIPLY", dt, damping, x=2, y=-7), x=3, y=-7),
        t.math("MULTIPLY", t.math("MULTIPLY", dt, dt, x=2, y=-8), stiffness, x=3, y=-8),
        x=4,
        y=-7,
    )

    def spring(last, speed, goal, x, y):
        """Drag and speed springing after the goal, stepped implicitly not to blow up at any
        frame rate: v' = (v + dt k (goal - d)) / (1 + dt c + dt^2 k), d' = d + dt v'"""
        pull = t.vmath(
            "SCALE",
            t.vmath("SUBTRACT", goal, last, x=x, y=y),
            t.math("MULTIPLY", dt, stiffness, x=x, y=y - 1),
            x=x + 1,
            y=y,
        )
        speed = t.vmath(
            "SCALE",
            t.vmath("ADD", speed, pull, x=x + 2, y=y),
            t.math("DIVIDE", 1.0, resist, x=x + 2, y=y - 1),
            x=x + 3,
            y=y,
        )
        return t.vmath(
            "ADD", last, t.vmath("SCALE", speed, dt, x=x + 4, y=y - 1), x=x + 5, y=y
        ), speed

    # The mesh out of the contact springing after it
    goal = t.attribute(".shrinkwrap_drag", "FLOAT_VECTOR", 0, -2)
    grip = t.attribute(".shrinkwrap_grip", "FLOAT", 0, -3)
    sprung, speed = spring(held.outputs["Drag"], held.outputs["Speed"], goal, 1, -2)
    free = t.math("SUBTRACT", 1.0, grip, x=5, y=-4)
    sprung = t.node(
        "ShaderNodeMix",
        7,
        -2,
        {"Factor": grip, "A": sprung, "B": goal},
        data_type="VECTOR",
    ).outputs[1]
    speed = t.vmath("SCALE", speed, free, x=7, y=-4)
    stepped = t.store(dragged, ".shrinkwrap_speed", "FLOAT_VECTOR", speed, 8, 0)
    stepped = t.store(stepped, ".shrinkwrap_drag", "FLOAT_VECTOR", sprung, 9, 0)
    stepped = t.store(
        stepped, ".shrinkwrap_wrapped", "FLOAT_VECTOR", held.outputs["Wrapped"], 10, 0
    )

    t.section("State", row=True)
    # A point for each vertex, none without Friction not to simulate them
    points = t.node(
        "GeometryNodePoints",
        0,
        0,
        {"Count": t.math("MULTIPLY", vertices, inputs["Friction"], x=0, y=-1)},
    ).outputs[0]
    point = t.node("GeometryNodeInputIndex", 0, -3).outputs[0]
    is_near = t.node(
        "GeometryNodeSampleIndex",
        1,
        -3,
        {"Geometry": geometry, "Value": near, "Index": point},
        data_type="BOOLEAN",
    ).outputs[0]
    cropped = t.node(
        "GeometryNodeSampleIndex",
        1,
        -4,
        {
            "Geometry": geometry,
            "Value": t.node(
                "GeometryNodeAccumulateField", 0, -5, {"Value": near}, data_type="INT"
            ).outputs["Trailing"],
            "Index": point,
        },
        data_type="INT",
    ).outputs[0]
    unmoved = t.node(
        "GeometryNodeSampleIndex",
        1,
        -6,
        {
            "Geometry": geometry,
            "Value": t.node("GeometryNodeInputPosition", 0, -6).outputs[0],
            "Index": point,
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    # The vertices away from the Colliders springing back to rest
    zero = (0.0, 0.0, 0.0)
    released, speed = spring(
        switch(kept, zero, sample(state, ".shrinkwrap_drag", point, 2, -12), 3, -12),
        switch(kept, zero, sample(state, ".shrinkwrap_speed", point, 2, -14), 3, -14),
        zero,
        4,
        -12,
    )
    for i, (name, fallback) in enumerate(
        (
            (".shrinkwrap_drag", released),
            (".shrinkwrap_speed", speed),
            (".shrinkwrap_wrapped", unmoved),
        )
    ):
        value = switch(
            is_near, fallback, sample(stepped, name, cropped, 3, -3 - 2 * i), 4, -3 - 2 * i
        )
        points = t.store(points, name, "FLOAT_VECTOR", value, 5 + i, 0)
    t.connect(points, sim_out.inputs["Geometry"])
    t.connect(colliders, sim_out.inputs["Colliders"])

    t.section("Offset", row=True)
    # The drag simulated so far added to the push, always of the Colliders where they are now,
    # e.g. moved without playing the frames
    result = sim_out.outputs["Geometry"]
    simulating = t.math(
        "MULTIPLY",
        same(vertices, count(result, 0, -3, "POINTCLOUD"), 1, -3),
        t.math("MULTIPLY", inputs["Friction"], started, x=1, y=-4),
        x=2,
        y=-3,
    )

    def drag(index, x, y):
        return t.vmath(
            "SCALE", sample(result, ".shrinkwrap_drag", index, x, y), simulating, x=x + 1, y=y
        )

    offset = t.vmath(
        "ADD",
        t.attribute(".shrinkwrap_offset", "FLOAT_VECTOR", 3, -6),
        drag(t.attribute(".shrinkwrap_index", "INT", 2, -8), 3, -7),
        x=5,
        y=-6,
    )
    crop = t.store(crop, ".shrinkwrap_offset", "FLOAT_VECTOR", offset, 6, 0)
    crop = push_out(t, inputs, crop, colliders, 7, 0)
    pushed = t.node(
        "GeometryNodeSampleIndex",
        20,
        -2,
        {
            "Geometry": crop,
            "Value": t.attribute(".shrinkwrap_offset", "FLOAT_VECTOR", 19, -3),
            "Index": t.node(
                "GeometryNodeAccumulateField", 19, -4, {"Value": near}, data_type="INT"
            ).outputs["Trailing"],
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    # Away from the Colliders, only springing back
    offset = switch(
        near, drag(t.node("GeometryNodeInputIndex", 19, -6).outputs[0], 20, -6), pushed, 22, -4
    )
    # All the vertices while simulating, also the ones springing back
    return offset, t.math("MAXIMUM", near, simulating, x=22, y=-6)


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(),), fake_user=True)
