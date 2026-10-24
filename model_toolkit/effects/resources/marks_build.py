# Build marks.blend: the Marks node group and the Marks Tint shader group
# Usage: Blender --background --factory-startup --python marks_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "marks.blend"
NODE_GROUP = "MustardUI Marks"
TINT = "MustardUI Marks Tint"
# Borders beyond the edge of a mark keeping its amount, not to fade it between the points
REACH = 4.0
# Border of the hand prints, outside and inside of their outline, relative to the Control radius
HAND_EDGE = (0.03, 0.1)
# Distance to the edge the hand prints drawn by pixel keep from the one interpolated between the
# points, not to show where the coordinates of two marks blend
HAND_TOLERANCE = 0.12
# Hand print, in units of the Control radius, palm down along +Y seen from +Z (a right hand):
# palm (center, half size, corner radius) and fingers (base, tip, radius) from thumb to little
PALM = ((0.0, -0.42), (0.37, 0.43), 0.2)
FINGERS = (
    ((-0.34, -0.5), (-0.7, -0.06), 0.095),
    ((-0.26, -0.02), (-0.36, 0.7), 0.08),
    ((-0.09, 0.0), (-0.11, 0.8), 0.085),
    ((0.1, -0.02), (0.15, 0.74), 0.078),
    ((0.27, -0.1), (0.4, 0.55), 0.065),
)


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Mark the mesh inside the sphere of the Control, storing the mark and mark_color "
        "attributes read by the Marks Tint shader"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Control", "NodeSocketObject", description="Empty whose sphere defines the mark")
    add_input(
        ng,
        "Hand",
        "NodeSocketBool",
        description="A hand print in the XY plane of the Control, fingers along its Y axis, "
        "a negative X scale for a left hand",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(1.0, 0.4, 0.4, 1.0),
        description="Color multiplying the base color of the marked materials",
    )
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Amount of the mark, animate it to show or fade it",
    )
    add_input(
        ng,
        "Falloff",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.8,
        min_value=0.0,
        max_value=1.0,
        description="Width of the soft border of the round marks, relative to the Control radius",
    )
    add_input(
        ng,
        "Blotches",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Lighter blotches in the mark",
    )
    add_input(
        ng,
        "Blotch Scale",
        "NodeSocketFloat",
        default_value=30.0,
        min_value=0.0,
        description="Number of blotches per meter",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the mark",
    )
    add_input(
        ng,
        "Lasting",
        "NodeSocketBool",
        description="Keep the marks where the Control was, painting them as it moves, "
        "simulated from the Start Frame",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    add_input(
        ng,
        "Fade",
        "NodeSocketFloat",
        default_value=0.0,
        min_value=0.0,
        description="Seconds for the lasting marks to fade, 0 to keep them",
    )
    arrange_interface(ng, [(None, "Lasting", True, "Lasting", ["Start Frame", "Fade"])])

    t = Tree(ng)
    t.section("Mark")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    geometry = inputs["Geometry"]
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

    # Position in the space of the Control, its sphere of radius 1
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

    # Distance to the edge of the mark, negative inside, and relative to its border
    edge = t.node(
        "GeometryNodeSwitch",
        6,
        -2,
        {
            "Switch": inputs["Hand"],
            "False": t.math("SUBTRACT", t.vmath("LENGTH", local, x=4, y=-2), 1.0, x=5, y=-2),
            "True": t.math("SUBTRACT", hand_distance(t, local, 2, -10), HAND_EDGE[0], x=5, y=-3),
        },
        input_type="FLOAT",
    ).outputs[0]
    border = t.node(
        "GeometryNodeSwitch",
        6,
        -4,
        {
            "Switch": inputs["Hand"],
            "False": t.math("MAXIMUM", inputs["Falloff"], 0.01, x=5, y=-4),
            "True": HAND_EDGE[1],
        },
        input_type="FLOAT",
    ).outputs[0]
    inside = t.math("DIVIDE", edge, border, x=7, y=-3)

    blotch = t.node(
        "ShaderNodeTexNoise",
        1,
        -6,
        {"Vector": rest, "Scale": inputs["Blotch Scale"], "Detail": 2.0},
    ).outputs["Fac"]
    blotch = t.node(
        "ShaderNodeMapRange",
        2,
        -6,
        {"Value": blotch, "From Min": 0.35, "From Max": 0.65},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    blotch = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", blotch, 1.0, x=3, y=-6),
        inputs["Blotches"],
        1.0,
        x=4,
        y=-6,
    )
    # The hand prints fading where the surface curves away from the hand
    depth = t.node(
        "ShaderNodeMapRange",
        3,
        -8,
        {
            "Value": t.math(
                "ABSOLUTE",
                t.node("ShaderNodeSeparateXYZ", 1, -8, {0: local}).outputs["Z"],
                x=2,
                y=-8,
            ),
            "From Min": 0.6,
            "From Max": 0.3,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    depth = t.node(
        "GeometryNodeSwitch",
        4,
        -8,
        {"Switch": inputs["Hand"], "False": 1.0, "True": depth},
        input_type="FLOAT",
    ).outputs[0]
    amount = t.math("MULTIPLY", inputs["Strength"], blotch, x=5, y=-6)
    amount = t.math("MULTIPLY", amount, inputs["Mask"], x=6, y=-6)
    amount = t.math("MULTIPLY", amount, depth, x=7, y=-6)

    t.section("Lasting", row=True)
    local, edge, inside, amount = build_lasting(
        t,
        inputs,
        geometry,
        (
            (".mark_local", "FLOAT_VECTOR", "VECTOR", local),
            (".mark_edge", "FLOAT", "FLOAT", edge),
            (".mark_inside", "FLOAT", "FLOAT", inside),
            (".mark_amount", "FLOAT", "FLOAT", amount),
        ),
    )

    t.section("Attributes", row=True)
    # Over the marks of the previous Marks modifiers where weighing more
    weight = mark_weight(t, amount, inside, 0, -2)
    previous = t.node(
        "GeometryNodeInputNamedAttribute", 0, -4, {"Name": ".mark_weight"}, data_type="FLOAT"
    ).outputs
    over = t.math(
        "MAXIMUM",
        t.math("SUBTRACT", 1.0, previous["Exists"], x=2, y=-5),
        t.math(
            "GREATER_THAN",
            t.math("SUBTRACT", weight, previous["Attribute"], x=2, y=-3),
            -1e-6,
            x=3,
            y=-3,
        ),
        x=4,
        y=-4,
    )
    xyz = t.node("ShaderNodeSeparateXYZ", 1, -7, {0: local}).outputs
    # The amount left unmarked in the alpha, 1 as read by the shaders without the attribute
    mark = t.node(
        "FunctionNodeCombineColor",
        2,
        -7,
        {
            "Red": xyz["X"],
            "Green": xyz["Y"],
            "Blue": edge,
            "Alpha": t.math("SUBTRACT", 1.0, amount, x=1, y=-8),
        },
    ).outputs[0]
    rgb = t.node("FunctionNodeSeparateColor", 1, -10, {0: inputs["Color"]}).outputs
    # The border, negative for the hand prints
    shape = t.node(
        "GeometryNodeSwitch",
        1,
        -12,
        {"Switch": inputs["Hand"], "False": border, "True": -HAND_EDGE[1]},
        input_type="FLOAT",
    ).outputs[0]
    color = t.node(
        "FunctionNodeCombineColor",
        2,
        -10,
        {"Red": rgb["Red"], "Green": rgb["Green"], "Blue": rgb["Blue"], "Alpha": shape},
    ).outputs[0]
    for i, (name, value) in enumerate((("mark", mark), ("mark_color", color))):
        chosen = t.node(
            "GeometryNodeSwitch",
            5,
            -7 - 3 * i,
            {
                "Switch": over,
                "False": t.attribute(name, "FLOAT_COLOR", 4, -8 - 3 * i),
                "True": value,
            },
            input_type="RGBA",
        ).outputs[0]
        geometry = t.store(geometry, name, "FLOAT_COLOR", chosen, 6 + i, 0)
    weight = t.node(
        "GeometryNodeSwitch",
        5,
        -2,
        {"Switch": over, "False": previous["Attribute"], "True": weight},
        input_type="FLOAT",
    ).outputs[0]
    geometry = t.store(geometry, ".mark_weight", "FLOAT", weight, 8, 0)
    t.node("NodeGroupOutput", 9, 0, {"Geometry": geometry})
    t.arrange()
    return ng


def mark_weight(t, amount, inside, x, y):
    """Amount of the mark, more inside its border and up to REACH borders out, then the closer
    to it the higher"""
    near = t.math(
        "MAXIMUM",
        t.math("MULTIPLY_ADD", inside, -1.0 / REACH, 1.0, x=x, y=y - 1),
        0.0,
        x=x + 1,
        y=y - 1,
    )
    return t.math(
        "MULTIPLY_ADD",
        t.math("MINIMUM", inside, 100.0, x=x, y=y - 2),
        -1e-4,
        t.math("MULTIPLY", amount, near, x=x + 1, y=y),
        x=x + 2,
        y=y,
    )


def build_lasting(t, inputs, geometry, values):
    """The values (name, data type, socket type, field) of each point kept from when the mark
    weighed the most there, the amount fading, simulated on points by index"""
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    mesh = t.node("GeometryNodeSeparateComponents", 0, 0, {0: geometry}).outputs["Mesh"]
    count = t.node("GeometryNodeAttributeDomainSize", 1, 0, {0: mesh}).outputs["Point Count"]
    points = t.node("GeometryNodePoints", 2, 0, {"Count": count}).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 3, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 12, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(points, sim_in.inputs["Geometry"])
    state = t.node(
        "GeometryNodeSwitch",
        4,
        0,
        {"Switch": started, "False": points, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 4, -2).outputs[0]
    live = [
        t.node(
            "GeometryNodeSampleIndex",
            5,
            -3 - i,
            {"Geometry": mesh, "Value": value, "Index": index},
            data_type=data_type,
        ).outputs[0]
        for i, (_, data_type, _, value) in enumerate(values)
    ]
    kept = [
        t.attribute(name, data_type, 5, -8 - i) for i, (name, data_type, _, _) in enumerate(values)
    ]
    # Fading, then replaced where the live mark weighs as much
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=5, y=-13)
    kept[-1] = t.math(
        "SUBTRACT",
        kept[-1],
        t.math("DIVIDE", dt, inputs["Fade"], x=6, y=-13),
        x=7,
        y=-12,
        clamp=True,
    )
    take = t.math(
        "GREATER_THAN",
        t.math(
            "SUBTRACT",
            mark_weight(t, live[-1], live[-2], 6, -3),
            mark_weight(t, kept[-1], kept[-2], 6, -8),
            x=9,
            y=-5,
        ),
        -1e-6,
        x=10,
        y=-5,
    )
    # All live on the first frame
    take = t.math("MAXIMUM", take, t.math("SUBTRACT", 1.0, started, x=9, y=-6), x=10, y=-4)
    # Once, not to read the values already stored
    captured = t.node("GeometryNodeCaptureAttribute", 10, -2, {"Geometry": state})
    captured.capture_items.new("FLOAT", "Take")
    t.connect(take, captured.inputs["Take"])
    state, take = captured.outputs["Geometry"], captured.outputs["Take"]
    for i, (name, data_type, socket_type, _) in enumerate(values):
        chosen = t.node(
            "GeometryNodeSwitch",
            10,
            -7 - i,
            {"Switch": take, "False": kept[i], "True": live[i]},
            input_type=socket_type,
        ).outputs[0]
        state = t.store(state, name, data_type, chosen, 11, -i)
    t.connect(state, sim_out.inputs["Geometry"])

    # Back on the mesh by index, without Lasting the live values
    results = []
    for i, (name, data_type, socket_type, value) in enumerate(values):
        result = t.node(
            "GeometryNodeSampleIndex",
            14,
            -2 * i,
            {
                "Geometry": sim_out.outputs["Geometry"],
                "Value": t.attribute(name, data_type, 13, -2 * i - 1),
                "Index": t.node("GeometryNodeInputIndex", 13, -2 * i - 1.5).outputs[0],
            },
            data_type=data_type,
        ).outputs[0]
        results.append(
            t.node(
                "GeometryNodeSwitch",
                15,
                -2 * i,
                {"Switch": inputs["Lasting"], "False": value, "True": result},
                input_type=socket_type,
            ).outputs[0]
        )
    return results


def hand_distance(t, p, x, y):
    """Signed distance of the point to the hand print, in its XY plane"""
    flat = t.vmath("MULTIPLY", p, (1.0, 1.0, 0.0), x=x, y=y)
    (cx, cy), (bx, by), r = PALM
    q = t.vmath("ABSOLUTE", t.vmath("SUBTRACT", flat, (cx, cy, 0.0), x=x + 1, y=y), x=x + 2, y=y)
    q = t.vmath("SUBTRACT", q, (bx - r, by - r, 0.0), x=x + 3, y=y)
    outside = t.vmath("LENGTH", t.vmath("MAXIMUM", q, (0.0, 0.0, 0.0), x=x + 4, y=y), x=x + 5, y=y)
    xyz = t.node("ShaderNodeSeparateXYZ", x + 4, y - 1, {0: q}).outputs
    inside = t.math(
        "MINIMUM", t.math("MAXIMUM", xyz["X"], xyz["Y"], x=x + 5, y=y - 1), 0.0, x=x + 6, y=y - 1
    )
    distance = t.math("SUBTRACT", t.math("ADD", outside, inside, x=x + 7, y=y), r, x=x + 8, y=y)
    for i, ((ax, ay), (tx, ty), r) in enumerate(FINGERS):
        row = y - 2 - i
        ba = (tx - ax, ty - ay, 0.0)
        pa = t.vmath("SUBTRACT", flat, (ax, ay, 0.0), x=x + 1, y=row)
        h = t.math(
            "MULTIPLY",
            t.vmath("DOT_PRODUCT", pa, ba, x=x + 2, y=row),
            1.0 / (ba[0] ** 2 + ba[1] ** 2),
            x=x + 3,
            y=row,
            clamp=True,
        )
        along = t.vmath("SCALE", ba, h, x=x + 4, y=row)
        finger = t.vmath("LENGTH", t.vmath("SUBTRACT", pa, along, x=x + 5, y=row), x=x + 6, y=row)
        finger = t.math("SUBTRACT", finger, r, x=x + 7, y=row)
        distance = t.math("MINIMUM", distance, finger, x=x + 9, y=row)
    return distance


def build_tint():
    """The color multiplied by the color of the marks, from the attributes of the Marks modifiers"""
    ng = bpy.data.node_groups.new(TINT, "ShaderNodeTree")
    add_input(ng, "Color", "NodeSocketColor", default_value=(0.8, 0.8, 0.8, 1.0))
    add_output(ng, "Color", "NodeSocketColor")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    mark = t.node(
        "ShaderNodeAttribute", 0, -2, attribute_type="GEOMETRY", attribute_name="mark"
    ).outputs
    color = t.node(
        "ShaderNodeAttribute", 0, -4, attribute_type="GEOMETRY", attribute_name="mark_color"
    ).outputs
    values = t.node("ShaderNodeSeparateXYZ", 1, -2, {0: mark["Vector"]}).outputs
    p = t.node("ShaderNodeCombineXYZ", 2, -2, {"X": values["X"], "Y": values["Y"]}).outputs[0]
    edge = values["Z"]
    amount = t.math("SUBTRACT", 1.0, mark["Alpha"], x=1, y=-3)
    is_hand = t.math("LESS_THAN", color["Alpha"], 0.0, x=1, y=-5)
    border = t.math("MAXIMUM", t.math("ABSOLUTE", color["Alpha"], x=1, y=-6), 0.01, x=2, y=-6)

    # The hand prints by pixel, close to the edge interpolated between the points
    hand = t.math("SUBTRACT", hand_distance(t, p, 3, -14), HAND_EDGE[0], x=12, y=-14)
    hand = t.math(
        "MAXIMUM",
        t.math("MINIMUM", hand, t.math("ADD", edge, HAND_TOLERANCE, x=12, y=-12), x=13, y=-13),
        t.math("SUBTRACT", edge, HAND_TOLERANCE, x=12, y=-11),
        x=14,
        y=-13,
    )
    edge = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", hand, edge, x=15, y=-12),
        is_hand,
        edge,
        x=16,
        y=-10,
    )

    # Ragged border and mottled inside, on the coordinates in the Control space
    ragged = t.node(
        "ShaderNodeTexNoise", 3, -6, {"Vector": p, "Scale": 4.0, "Detail": 4.0}
    ).outputs["Fac"]
    ragged = t.math("SUBTRACT", ragged, 0.5, x=4, y=-6)
    spread = t.math("MULTIPLY", border, 0.6, x=3, y=-7)
    spread = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", 0.08, spread, x=4, y=-7),
        is_hand,
        spread,
        x=5,
        y=-7,
    )
    edge = t.math("MULTIPLY_ADD", ragged, spread, edge, x=17, y=-8)
    mottle = t.node(
        "ShaderNodeTexNoise", 3, -9, {"Vector": p, "Scale": 14.0, "Detail": 2.0}
    ).outputs["Fac"]
    mottle = t.node(
        "ShaderNodeMapRange",
        4,
        -9,
        {"Value": mottle, "From Min": 0.3, "From Max": 0.7, "To Min": 0.65},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]

    mask = t.node(
        "ShaderNodeMapRange",
        18,
        -6,
        {"Value": edge, "From Min": 0.0, "From Max": t.math("MULTIPLY", border, -1.0, x=17, y=-6)},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    mask = t.math("MULTIPLY", mask, mottle, x=19, y=-6)
    mask = t.math("MULTIPLY", mask, amount, x=20, y=-5, clamp=True)
    tinted = t.node(
        "ShaderNodeMix",
        21,
        0,
        {"Factor": mask, "A": inputs["Color"], "B": color["Color"]},
        data_type="RGBA",
        blend_type="MULTIPLY",
    ).outputs
    t.node("NodeGroupOutput", 22, 0, {"Color": next(s for s in tinted if s.type == "RGBA")})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_tint()), fake_user=True)
