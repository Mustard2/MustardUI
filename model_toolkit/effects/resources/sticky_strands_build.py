# Build sticky_strands.blend: the Sticky Strands node group and the strands material
# Usage: Blender --background --factory-startup --python sticky_strands_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, socket, write

RESOURCE = "sticky_strands.blend"
NODE_GROUP = "MustardUI Sticky Strands"
MATERIAL = "MustardUI Sticky Strands"
# Shown in the node trees, to document the strand attributes
ATTRIBUTES = """\
Attributes of the strands for the shader, read with Attribute nodes of Geometry type:
- sticky_length: length of the strands, broken ones split in two
- sticky_factor: 0 to 1 along the strands, from the mesh to the Target, also when broken
- sticky_length_normalized: length relative to the Break Length, 1 when breaking, \
0 without Break Length and once broken
"""
# Spacing of the points at the strand ends, relative to the average, to shape the flares
END_SPACING = 0.2


def note(t, text, x, y):
    """Frame showing the text, to document the node tree"""
    t.node(
        "NodeFrame", x, y, label="Shader Attributes", text=text, shrink=False, width=900, height=200
    )


def build_node_group(text):
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Simulated strands of saliva or goo between the mesh and the Target, with the "
        "sticky_length, sticky_factor and sticky_length_normalized attributes for the shader"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Control",
        "NodeSocketObject",
        description="Empty whose sphere defines where the strands start on the mesh",
    )
    add_input(
        ng,
        "Target",
        "NodeSocketObject",
        description="Mesh where the strands end, empty for the mesh itself",
    )
    add_input(
        ng,
        "Start Vertex Group",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group of the mesh where the strands start",
    )
    add_input(
        ng,
        "End Vertex Group",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group of the Target where the strands end, "
        "or of the mesh itself without Target",
    )
    add_input(
        ng,
        "Material",
        "NodeSocketMaterial",
        description="Material of the strands, whose shader can read the sticky_length, "
        "sticky_factor and sticky_length_normalized attributes",
    )
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the random placement")
    add_input(
        ng,
        "Start Frame",
        "NodeSocketInt",
        default_value=1,
        description="Frame where the strands appear, placed on the meshes and simulated from it",
    )
    add_input(
        ng,
        "End Frame",
        "NodeSocketInt",
        default_value=0,
        min_value=0,
        description="Last frame showing the strands, 0 to never end",
    )

    panel = ng.interface.new_panel("Strands")
    add_input(
        ng,
        "Count",
        "NodeSocketInt",
        panel,
        default_value=12,
        min_value=1,
        max_value=10000,
        description="Number of strands",
    )
    add_input(
        ng,
        "Spread",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Randomness of the strand placement relative to the Control radius, "
        "0 to connect the closest points",
    )
    add_input(
        ng,
        "Variation",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Variation of thickness, sag and break length between the strands",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        panel,
        default_value=24,
        min_value=3,
        max_value=256,
        description="Simulated points along each strand",
    )

    panel = ng.interface.new_panel("Shape")
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0006,
        min_value=0.0,
        max_value=1.0,
        description="Radius of the strands",
    )
    add_input(
        ng,
        "Mid Pinch",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="Thickness in the middle of the strands, relative to the ends",
    )
    add_input(
        ng,
        "Irregularity",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Lumps of varying thickness along the strands",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        panel,
        default_value=0,
        min_value=0,
        max_value=100,
        description="Iterations smoothing the shape of the strands",
    )
    add_input(
        ng,
        "Flare Width",
        "NodeSocketFloat",
        panel,
        default_value=2.5,
        min_value=1.0,
        max_value=20.0,
        description="Thickness of the tips flaring onto the surface, relative to the strand",
    )
    add_input(
        ng,
        "Flare Length",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.003,
        min_value=0.0001,
        max_value=1.0,
        description="Length of the flared tips",
    )
    add_input(
        ng,
        "End Insert",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.001,
        min_value=0.0,
        max_value=1.0,
        description="Depth of the strand ends under the surface, for them to stick to it",
    )
    add_input(
        ng,
        "Sticky Ends",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.9,
        min_value=0.0,
        max_value=1.0,
        description="Spread of the flared tips over the surface",
    )
    add_input(
        ng,
        "Profile Resolution",
        "NodeSocketInt",
        panel,
        default_value=12,
        min_value=3,
        max_value=64,
        description="Sides of the strands",
    )

    panel = ng.interface.new_panel("Physics")
    add_input(
        ng,
        "Physics",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Simulate the swinging and colliding strands. "
        "Off for faster static strands, removed when they break",
    )
    add_input(
        ng,
        "New Strands on Contact",
        "NodeSocketBool",
        panel,
        default_value=False,
        description="Replace the broken strands with new ones where the meshes touch again",
    )
    add_input(
        ng,
        "Contact Distance",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.005,
        min_value=0.0,
        max_value=1.0,
        description="Distance between the meshes creating new strands",
    )
    add_input(
        ng,
        "Sag",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=10.0,
        description="Extra length of the strands, making them sag",
    )
    add_input(
        ng,
        "Break Length",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.08,
        min_value=0.0,
        max_value=100.0,
        description="Distance between the ends breaking the strands, 0 to never break",
    )
    add_input(
        ng,
        "Elasticity",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.0,
        max_value=100.0,
        description="Speed at which the stretched strands shrink back, per second",
    )
    add_input(
        ng,
        "Gravity",
        "NodeSocketVector",
        panel,
        subtype="ACCELERATION",
        default_value=(0.0, 0.0, -9.81),
        description="Acceleration of the strands, in world space",
    )
    add_input(
        ng,
        "Drag",
        "NodeSocketFloat",
        panel,
        default_value=2.0,
        min_value=0.0,
        max_value=100.0,
        description="Slowdown of the strands per second",
    )
    add_input(
        ng,
        "Substeps",
        "NodeSocketInt",
        panel,
        default_value=4,
        min_value=1,
        max_value=100,
        description="Simulation steps per frame",
    )
    add_input(
        ng,
        "Iterations",
        "NodeSocketInt",
        panel,
        default_value=10,
        min_value=1,
        max_value=200,
        description="Length constraint iterations per step, higher for less stretchy strands",
    )
    add_input(
        ng,
        "Collision",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Collide with the mesh, the Target and the Colliders",
    )
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        panel,
        description="Other meshes the strands collide with",
    )
    # The common inputs first, the advanced ones in closed sub panels
    arrange_interface(
        ng,
        (
            (None, "Strands", False, None, ("Sag", "Break Length", "Seed")),
            ("Strands", "Vertex Groups", False, None, ("Start Vertex Group", "End Vertex Group")),
            ("Strands", "Frame Range", True, None, ("Start Frame", "End Frame")),
            (None, "Shape", False, None, ("Profile Resolution",)),
            (
                "Shape",
                "Flared Ends",
                True,
                None,
                ("Flare Width", "Flare Length", "End Insert", "Sticky Ends"),
            ),
            (None, "Physics", False, "Physics", ()),
            ("Physics", "Motion", False, None, ("Gravity", "Drag", "Elasticity")),
            ("Physics", "Collision", False, "Collision", ("Colliders",)),
            (
                "Physics",
                "New Strands on Contact",
                True,
                "New Strands on Contact",
                ("Contact Distance",),
            ),
            ("Physics", "Solver", True, None, ("Substeps", "Iterations")),
        ),
    )

    t = Tree(ng, spacing=(200, 160))
    t.section("Spaces and Target")
    inputs = t.node("NodeGroupInput", -30, 0).outputs
    position = t.node("GeometryNodeInputPosition", -30, -8).outputs[0]
    normal = t.node("GeometryNodeInputNormal", -30, -9).outputs[0]
    rest = t.node(
        "GeometryNodeInputNamedAttribute",
        -30,
        -10,
        {"Name": "rest_position"},
        data_type="FLOAT_VECTOR",
    ).outputs
    rest = t.node(
        "GeometryNodeSwitch",
        -29,
        -10,
        {"Switch": rest["Exists"], "False": position, "True": socket(rest, "Attribute")},
        input_type="VECTOR",
    ).outputs[0]

    # Simulated in world space, for the strands to swing when the objects move
    self_object = t.node("GeometryNodeSelfObject", -30, -3).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -29, -3, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", -28, -3, {"Matrix": to_world}).outputs[0]
    control = t.node(
        "GeometryNodeObjectInfo", -29, -5, {"Object": inputs["Control"]}, transform_space="ORIGINAL"
    ).outputs
    to_control = t.node("FunctionNodeInvertMatrix", -28, -5, {"Matrix": control["Transform"]})
    radius = t.vmath("DOT_PRODUCT", control["Scale"], (1 / 3, 1 / 3, 1 / 3), x=-28, y=-6)

    # Without a Target, the strands end on the mesh itself
    target_info = t.node(
        "GeometryNodeObjectInfo", -29, 4, {"Object": inputs["Target"]}, transform_space="ORIGINAL"
    ).outputs
    target_size = t.node(
        "GeometryNodeAttributeDomainSize", -28, 5, {"Geometry": target_info["Geometry"]}
    ).outputs["Point Count"]
    has_target = t.math("GREATER_THAN", target_size, 0.0, x=-27, y=5)
    target_geometry = t.node(
        "GeometryNodeSwitch",
        -26,
        4,
        {"Switch": has_target, "False": inputs["Geometry"], "True": target_info["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    target_transform = t.node(
        "GeometryNodeSwitch",
        -26,
        3,
        {"Switch": has_target, "False": to_world, "True": target_info["Transform"]},
        input_type="MATRIX",
    ).outputs[0]

    def surface(geometry, transform, mask, threshold, x, y):
        """World mesh with its world position and normal, its masked part, and that at rest"""
        local = t.node("GeometryNodeCaptureAttribute", x, y, {"Geometry": geometry})
        for data_type, name, value in (("VECTOR", "Rest", rest), ("FLOAT", "Mask", mask)):
            local.capture_items.new(data_type, name)
            t.connect(value, local.inputs[name])
        world = t.node(
            "GeometryNodeTransform",
            x + 1,
            y,
            {"Geometry": local.outputs["Geometry"], "Mode": "Matrix", "Transform": transform},
        ).outputs[0]
        world = t.node("GeometryNodeCaptureAttribute", x + 2, y, {"Geometry": world})
        for name, value in (("Position", position), ("Normal", normal)):
            world.capture_items.new("VECTOR", name)
            t.connect(value, world.inputs[name])
        masked = t.node(
            "GeometryNodeDeleteGeometry",
            x + 3,
            y,
            {
                "Geometry": world.outputs["Geometry"],
                "Selection": t.math(
                    "LESS_THAN", local.outputs["Mask"], threshold, x=x + 3, y=y - 1
                ),
            },
            domain="FACE",
        ).outputs[0]
        # Sampled at the rest position, for the strand ends to stay on the deforming mesh
        at_rest = t.node(
            "GeometryNodeSetPosition",
            x + 4,
            y,
            {"Geometry": masked, "Position": local.outputs["Rest"]},
        ).outputs[0]
        captured = dict(world.outputs.items())
        captured["Rest"] = local.outputs["Rest"]
        captured["Mask"] = local.outputs["Mask"]
        return world.outputs["Geometry"], masked, at_rest, captured

    source, source_masked, source_rest, source_fields = surface(
        inputs["Geometry"], to_world, inputs["Start Vertex Group"], 0.001, -24, 0
    )
    target, target_masked, target_rest, target_fields = surface(
        target_geometry, target_transform, inputs["End Vertex Group"], 0.5, -24, 4
    )
    t.section("Surfaces")
    # Placed once on the deformed meshes for the simulation, or every frame without physics,
    # on the meshes at rest for the strands not to move around while they deform
    source_placed, target_placed = (
        t.node(
            "GeometryNodeSwitch",
            -19,
            4 * i,
            {
                "Switch": inputs["Physics"],
                "False": t.node(
                    "GeometryNodeTransform",
                    -20,
                    4 * i + 1,
                    {"Geometry": at_rest, "Mode": "Matrix", "Transform": transform},
                ).outputs[0],
                "True": masked,
            },
            input_type="GEOMETRY",
        ).outputs[0]
        for i, (masked, at_rest, transform) in enumerate(
            (
                (source_masked, source_rest, to_world),
                (target_masked, target_rest, target_transform),
            )
        )
    )

    def anchor(at_rest, fields, coordinate, x, y):
        """Surface point at the rest coordinate sunk under it by End Insert, and its normal"""
        sampled = [
            t.node(
                "GeometryNodeSampleNearestSurface",
                x,
                y - i,
                {"Mesh": at_rest, "Value": fields[name], "Sample Position": coordinate},
                data_type="FLOAT_VECTOR",
            ).outputs["Value"]
            for i, name in enumerate(("Position", "Normal"))
        ]
        normal = t.vmath("NORMALIZE", sampled[1], x=x + 1, y=y - 1)
        sink = t.vmath("SCALE", normal, inputs["End Insert"], x=x + 2, y=y - 1)
        return t.vmath("SUBTRACT", sampled[0], sink, x=x + 3, y=y), normal

    def attribute(name, data_type, x, y):
        return t.attribute("strand_" + name, data_type, x, y)

    def near(geometry, around, margin, x, y):
        """Faces of the geometry in the bounding box of the other one grown by the margin"""
        box = t.node("GeometryNodeBoundBox", x, y - 1, {"Geometry": around}).outputs
        # The face centers, in the box grown by the face sizes too, to keep the faces larger than
        # it: twice the average distance of the corners, at least the farthest one in quads
        center = t.node(
            "GeometryNodeFieldOnDomain",
            x - 2,
            y - 4,
            {"Value": position},
            data_type="FLOAT_VECTOR",
            domain="FACE",
        ).outputs[0]
        size = t.node(
            "GeometryNodeFieldOnDomain",
            x - 1,
            y - 4,
            {"Value": t.vmath("DISTANCE", position, center, x=x - 1, y=y - 5)},
            domain="CORNER",
        ).outputs[0]
        margin = t.math("MULTIPLY_ADD", size, 2.0, margin, x=x, y=y - 4)
        inside = [
            t.node(
                "FunctionNodeCompare",
                x + 1,
                y - 2 - i,
                {"A": position, "B": t.vmath(operation, box[corner], margin, x=x, y=y - 2 - i)},
                data_type="VECTOR",
                mode="ELEMENT",
                operation=compare,
            ).outputs[0]
            for i, (corner, operation, compare) in enumerate(
                (("Min", "SUBTRACT", "GREATER_EQUAL"), ("Max", "ADD", "LESS_EQUAL"))
            )
        ]
        outside = t.node(
            "FunctionNodeBooleanMath", x + 2, y - 2, {0: inside[0], 1: inside[1]}, operation="NAND"
        ).outputs[0]
        return t.node(
            "GeometryNodeDeleteGeometry",
            x + 3,
            y,
            {"Geometry": geometry, "Selection": outside},
            domain="FACE",
        ).outputs[0]

    def spacing(index, last, x, y):
        """Length factor of the point at the index, the points denser at the ends"""
        u = t.math("DIVIDE", index, last, x=x, y=y)
        wave = t.math("MULTIPLY", u, 2 * math.pi, x=x + 1, y=y - 1)
        wave = t.math("SINE", wave, x=x + 2, y=y - 1)
        return t.math("MULTIPLY_ADD", wave, (END_SPACING - 1) / (2 * math.pi), u, x=x + 3, y=y)

    down = t.vmath("NORMALIZE", inputs["Gravity"], x=8, y=-6)

    def hanging(a, b, length, factor, x, y):
        """Point at the length factor of a strand hanging as a parabola between its ends"""
        distance = t.vmath("DISTANCE", a, b, x=x, y=y - 1)
        line = t.vmath("SUBTRACT", b, a, x=x, y=y)
        line = t.vmath("ADD", a, t.vmath("SCALE", line, factor, x=x + 1, y=y), x=x + 2, y=y)
        # length ~ distance + 8 depth² / (3 distance)
        depth = t.math("SUBTRACT", length, distance, x=x + 1, y=y - 1)
        depth = t.math("MULTIPLY", depth, distance, x=x + 2, y=y - 1)
        depth = t.math("SQRT", t.math("MULTIPLY", depth, 0.375, x=x + 3, y=y - 1), x=x + 4, y=y - 1)
        bow = t.math(
            "MULTIPLY", factor, t.math("SUBTRACT", 1.0, factor, x=x + 1, y=y - 2), x=x + 2, y=y - 2
        )
        bow = t.math(
            "MULTIPLY", bow, t.math("MULTIPLY", depth, 4.0, x=x + 5, y=y - 1), x=x + 3, y=y - 2
        )
        return t.vmath("ADD", line, t.vmath("SCALE", down, bow, x=x + 4, y=y - 2), x=x + 5, y=y)

    t.section("Strand Starts")
    # Strand starts: inside the Control sphere, the Count points closest to the Target with a
    # random jitter, where the surfaces were touching
    in_control = t.node(
        "FunctionNodeTransformPoint",
        -19,
        -3,
        {"Vector": source_fields["Position"], "Transform": to_control.outputs[0]},
    ).outputs[0]
    in_control = t.vmath("DOT_PRODUCT", in_control, in_control, x=-18, y=-3)
    density = t.math("LESS_THAN", in_control, 1.0, x=-17, y=-3)
    density = t.math("MULTIPLY", density, source_fields["Mask"], x=-16, y=-3)
    # On the points, for the face area sum to average it like the distribution does: at face
    # centers, the area is 0 when the sphere holds only vertices, making billions of candidates
    captured = t.node("GeometryNodeCaptureAttribute", -15, -2, {"Geometry": source_placed})
    captured.capture_items.new("FLOAT", "Density")
    t.connect(density, captured.inputs["Density"])
    source_placed, density = captured.outputs["Geometry"], captured.outputs["Density"]
    area = t.node("GeometryNodeInputMeshFaceArea", -17, -5).outputs[0]
    area = t.node(
        "GeometryNodeAttributeStatistic",
        -15,
        -4,
        {
            "Geometry": source_placed,
            "Attribute": t.math("MULTIPLY", area, density, x=-16, y=-5),
        },
        data_type="FLOAT",
        domain="FACE",
    ).outputs["Sum"]
    # Many more candidates than needed, to pick from
    candidates = t.math("MULTIPLY", inputs["Count"], 20.0, x=-14, y=-5)
    candidates = t.math(
        "DIVIDE", candidates, t.math("MAXIMUM", area, 1e-9, x=-14, y=-6), x=-13, y=-5
    )
    distribute = t.node(
        "GeometryNodeDistributePointsOnFaces",
        -12,
        0,
        {
            "Mesh": source_placed,
            "Density": t.math("MULTIPLY", candidates, density, x=-12, y=-4),
            "Seed": inputs["Seed"],
        },
        distribute_method="RANDOM",
    )
    spread = t.math("MULTIPLY", inputs["Spread"], radius, x=-13, y=-11)
    jitter = t.node("FunctionNodeRandomValue", -13, -2, {"Seed": inputs["Seed"]})
    closest = t.node(
        "GeometryNodeProximity", -13, -1, {0: target_placed}, target_element="FACES"
    ).outputs["Distance"]
    shuffled = t.node(
        "GeometryNodeSortElements",
        -11,
        0,
        {
            "Geometry": distribute.outputs["Points"],
            "Sort Weight": t.math(
                "MULTIPLY_ADD", socket(jitter.outputs, "Value"), spread, closest, x=-12, y=-2
            ),
        },
        domain="POINT",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", -11, -2).outputs[0]
    starts = t.node(
        "GeometryNodeDeleteGeometry",
        -10,
        0,
        {
            "Geometry": shuffled,
            "Selection": t.math(
                "GREATER_THAN",
                index,
                t.math("SUBTRACT", inputs["Count"], 0.5, x=-11, y=-3),
                x=-10,
                y=-2,
            ),
        },
        domain="POINT",
    ).outputs[0]

    t.section("Strand Ends")
    # Strand ends: on the masked Target, near the start offset at random
    offset = t.node(
        "FunctionNodeRandomValue",
        -12,
        -10,
        {"Min": (-1.0, -1.0, -1.0), "Seed": t.math("ADD", inputs["Seed"], 1.0, x=-13, y=-10)},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    end = t.node(
        "GeometryNodeSampleNearestSurface",
        -8,
        -8,
        {
            "Mesh": target_placed,
            "Value": target_fields["Rest"],
            "Sample Position": t.vmath(
                "ADD", position, t.vmath("SCALE", offset, spread, x=-10, y=-10), x=-9, y=-9
            ),
        },
        data_type="FLOAT_VECTOR",
    ).outputs
    strands = t.node(
        "GeometryNodeDeleteGeometry",
        -9,
        0,
        {"Geometry": starts, "Selection": t.math("SUBTRACT", 1.0, end["Is Valid"], x=-8, y=-6)},
        domain="POINT",
    ).outputs[0]
    for i, (name, value) in enumerate(
        (("rest_a", source_fields["Rest"]), ("rest_b", end["Value"]))
    ):
        strands = t.store(strands, "strand_" + name, "FLOAT_VECTOR", value, -8 + i, 0)

    def anchors(x, y):
        """Strand ends of the stored rest coordinates with their normals, and their distance"""
        a = anchor(source_rest, source_fields, attribute("rest_a", "FLOAT_VECTOR", x, y), x + 1, y)
        b = anchor(
            target_rest, target_fields, attribute("rest_b", "FLOAT_VECTOR", x, y - 3), x + 1, y - 3
        )
        return a, b, t.vmath("DISTANCE", a[0], b[0], x=x + 5, y=y - 2)

    t.section("Strand Values")
    # Per strand: the distance and random values, from which the slack length, break length and
    # thickness follow the inputs, also while simulating
    _, _, distance = anchors(-7, -14)
    random = t.node(
        "FunctionNodeRandomValue",
        -7,
        -5,
        {"Seed": t.math("ADD", inputs["Seed"], 2.0, x=-8, y=-5)},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    segments = t.math("SUBTRACT", inputs["Resolution"], 1.0, x=-5, y=-8)
    cut = t.math(
        "MULTIPLY_ADD",
        t.node("ShaderNodeSeparateXYZ", -6, -7, {0: random}).outputs["Z"],
        0.4,
        0.3,
        x=-5,
        y=-7,
    )
    cut = t.math("FLOOR", t.math("MULTIPLY", cut, segments, x=-4, y=-7), x=-3, y=-7)
    for i, (name, data_type, value) in enumerate(
        (("distance", "FLOAT", distance), ("random", "FLOAT_VECTOR", random), ("cut", "INT", cut))
    ):
        strands = t.store(strands, "strand_" + name, data_type, value, -2 + i, 0)
    placed = strands

    random = t.node(
        "ShaderNodeSeparateXYZ", -2, -10, {0: attribute("random", "FLOAT_VECTOR", -3, -10)}
    ).outputs
    sag = t.math("MULTIPLY_ADD", random["X"], 2.0, -1.0, x=-1, y=-10)
    sag = t.math("MULTIPLY_ADD", sag, inputs["Variation"], 1.0, x=0, y=-10)
    sag = t.math("MULTIPLY", sag, inputs["Sag"], x=1, y=-10)
    distance = attribute("distance", "FLOAT", 1, -11)
    strand_slack = t.math("MULTIPLY_ADD", distance, sag, distance, x=2, y=-10)
    # Thicker strands break later
    strength = t.math("MULTIPLY", random["Y"], inputs["Variation"], x=-1, y=-12)
    strength = t.math("MULTIPLY_ADD", strength, -0.5, 1.0, x=0, y=-12)
    strand_break = t.math("MULTIPLY", strength, inputs["Break Length"], x=2, y=-12)
    strand_thickness = t.math("MULTIPLY", strength, inputs["Thickness"], x=2, y=-13)
    strands = t.store(strands, "strand_length", "FLOAT", strand_slack, 1, 0)

    t.section("Chains")
    # Chains of points between the ends, sagging as a parabola of the strand length
    strand = t.node("GeometryNodeCaptureAttribute", 3, 0, {"Geometry": strands})
    strand.capture_items.new("INT", "Strand")
    t.connect(index, strand.inputs["Strand"])
    duplicate = t.node(
        "GeometryNodeDuplicateElements",
        4,
        0,
        {"Geometry": strand.outputs["Geometry"], "Amount": inputs["Resolution"]},
        domain="POINT",
    ).outputs
    factor = spacing(duplicate["Duplicate Index"], segments, 4, -2)
    (a, _), (b, _), _ = anchors(0, -18)
    chain = t.node(
        "GeometryNodeSetPosition",
        10,
        0,
        {
            "Geometry": duplicate["Geometry"],
            "Position": hanging(a, b, strand_slack, factor, 5, -4),
        },
    ).outputs[0]
    curves = t.node(
        "GeometryNodePointsToCurves",
        12,
        0,
        {
            "Points": chain,
            "Curve Group ID": strand.outputs["Strand"],
            "Weight": duplicate["Duplicate Index"],
        },
    ).outputs[0]

    t.section("Frame Range")
    # Hidden before the Start Frame and after the End Frame
    frame = t.node("GeometryNodeInputSceneTime", 12, -3).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=13, y=-3)
    ended = t.math("GREATER_THAN", frame, inputs["End Frame"], x=13, y=-4)
    ended = t.math(
        "MULTIPLY",
        ended,
        t.math("GREATER_THAN", inputs["End Frame"], 0.0, x=13, y=-5),
        x=14,
        y=-4,
    )
    hidden = t.math(
        "MAXIMUM", t.math("LESS_THAN", frame, inputs["Start Frame"], x=13, y=-2), ended, x=15, y=-3
    )

    t.section("New Strands on Contact", row=True)
    # Simulation: follow the ends, stretch, break, swing and collide
    sim_in = t.node("GeometryNodeSimulationInput", 14, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 44, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(curves, sim_in.inputs["Geometry"])
    # Placed again until the Start Frame, without moving on it as on the first simulated frame
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=15, y=-1)
    spline = t.node("GeometryNodeSplineParameter", 26, -10).outputs
    in_curve = spline["Index"]
    spline_length = t.node("GeometryNodeSplineLength", 26, -11).outputs
    last = t.math("SUBTRACT", spline_length["Point Count"], 1.0, x=27, y=-11)
    state = t.node(
        "GeometryNodeSwitch",
        15,
        0,
        {"Switch": started, "False": curves, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]

    # New strands on contact: the broken strands placed again where the meshes touch
    contacts = t.node(
        "GeometryNodeDeleteGeometry",
        14,
        8,
        {
            "Geometry": placed,
            "Selection": t.math("GREATER_THAN", closest, inputs["Contact Distance"], x=14, y=7),
        },
        domain="POINT",
    ).outputs[0]
    contacts_count = t.node(
        "GeometryNodeAttributeDomainSize", 15, 9, {"Geometry": contacts}, component="POINTCLOUD"
    ).outputs["Point Count"]
    was_broken = attribute("broken", "FLOAT", 14, 5)
    rank = t.node(
        "GeometryNodeAccumulateField", 15, 5, {"Value": was_broken}, domain="CURVE"
    ).outputs["Trailing"]
    reset = t.node("GeometryNodeCaptureAttribute", 16, 4, {"Geometry": state})
    reset.capture_items.new("FLOAT", "Reset")
    t.connect(
        t.math(
            "MULTIPLY", was_broken, t.math("LESS_THAN", rank, contacts_count, x=16, y=6), x=17, y=6
        ),
        reset.inputs["Reset"],
    )
    renewed = reset.outputs["Geometry"]
    for i, (name, data_type) in enumerate(
        (
            ("rest_a", "FLOAT_VECTOR"),
            ("rest_b", "FLOAT_VECTOR"),
            ("distance", "FLOAT"),
            ("random", "FLOAT_VECTOR"),
            ("cut", "INT"),
        )
    ):
        value = t.node(
            "GeometryNodeSampleIndex",
            17 + i * 0.5,
            7 + i,
            {
                "Geometry": contacts,
                "Value": attribute(name, data_type, 16 + i * 0.5, 7 + i),
                "Index": rank,
            },
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
        renewed = t.node(
            "GeometryNodeStoreNamedAttribute",
            17 + i * 0.5,
            4,
            {
                "Geometry": renewed,
                "Selection": reset.outputs["Reset"],
                "Name": "strand_" + name,
                "Value": value,
            },
            data_type=data_type,
        ).outputs[0]
    (a, _), (b, _), _ = anchors(18, 14)
    renewed = t.node(
        "GeometryNodeSetPosition",
        20,
        4,
        {
            "Geometry": renewed,
            "Selection": reset.outputs["Reset"],
            "Position": hanging(a, b, strand_slack, spacing(in_curve, last, 19, 12), 20, 12),
        },
    ).outputs[0]
    for i, (name, data_type, value) in enumerate(
        (
            ("velocity", "FLOAT_VECTOR", (0.0, 0.0, 0.0)),
            ("pin", "FLOAT_VECTOR", position),
            ("length", "FLOAT", strand_slack),
            ("broken", "BOOLEAN", False),
        )
    ):
        renewed = t.node(
            "GeometryNodeStoreNamedAttribute",
            21 + i * 0.5,
            4,
            {
                "Geometry": renewed,
                "Selection": reset.outputs["Reset"],
                "Name": "strand_" + name,
                "Value": value,
            },
            data_type=data_type,
        ).outputs[0]
    t.section("Breaking")
    # Only while some strands are broken, not to place them every frame
    any_broken = t.node(
        "GeometryNodeAttributeStatistic", 15, 2, {"Geometry": state, "Attribute": was_broken}
    ).outputs["Max"]
    state = t.node(
        "GeometryNodeSwitch",
        22,
        2,
        {
            "Switch": t.node(
                "FunctionNodeBooleanMath",
                21,
                1,
                {0: inputs["New Strands on Contact"], 1: any_broken},
                operation="AND",
            ).outputs[0],
            "False": state,
            "True": renewed,
        },
        input_type="GEOMETRY",
    ).outputs[0]

    (a, a_normal), (b, b_normal), _ = anchors(14, -18)
    for i, (name, value) in enumerate(
        (("anchor_a", a), ("normal_a", a_normal), ("anchor_b", b), ("normal_b", b_normal))
    ):
        state = t.store(state, "strand_" + name, "FLOAT_VECTOR", value, 19 + i * 0.25, 0)
    anchor_a = attribute("anchor_a", "FLOAT_VECTOR", 20, -3)
    anchor_b = attribute("anchor_b", "FLOAT_VECTOR", 20, -4)
    normal_a = attribute("normal_a", "FLOAT_VECTOR", 32, -16)
    normal_b = attribute("normal_b", "FLOAT_VECTOR", 32, -17)
    distance = t.vmath("DISTANCE", anchor_a, anchor_b, x=21, y=-3)

    breaking = t.math("GREATER_THAN", distance, strand_break, x=22, y=-4)
    breaking = t.math(
        "MULTIPLY", breaking, t.math("GREATER_THAN", strand_break, 0.0, x=22, y=-5), x=23, y=-4
    )
    broken = t.math("MAXIMUM", attribute("broken", "FLOAT", 23, -5), breaking, x=24, y=-4)
    state = t.store(state, "strand_broken", "BOOLEAN", broken, 24, 0)
    broken = attribute("broken", "FLOAT", 24, -6)

    t.section("Relaxing")
    # Stretched strands shrink back to their slack length, broken ones dangle
    length = attribute("length", "FLOAT", 22, -7)
    relax = t.math("MULTIPLY", inputs["Elasticity"], dt, x=22, y=-8, clamp=True)
    relaxed = t.math("SUBTRACT", strand_slack, length, x=23, y=-8)
    relaxed = t.math("MULTIPLY_ADD", relaxed, relax, length, x=24, y=-8)
    taut = t.math("MAXIMUM", relaxed, distance, x=25, y=-8)
    length = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", relaxed, taut, x=25, y=-7), broken, taut, x=26, y=-7
    )
    state = t.store(state, "strand_length", "FLOAT", length, 26, 0)

    t.section("Colliders")
    # Colliders: the meshes and the Colliders collection
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        36,
        -14,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", 37, -14, {"Geometry": colliders}).outputs[0]
    colliders = t.node(
        "GeometryNodeTransform",
        38,
        -14,
        {"Geometry": colliders, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    other_target = t.node(
        "GeometryNodeSwitch",
        38,
        -15,
        {"Switch": has_target, "True": target},
        input_type="GEOMETRY",
    ).outputs[0]
    collider = t.node("GeometryNodeJoinGeometry", 39, -14)
    for geometry in (colliders, other_target, source):
        t.connect(geometry, collider.inputs[0])
    # Only the faces around the strands, for a fast lookup
    collider = near(collider.outputs[0], state, radius, 22, -20)

    first = t.math("COMPARE", in_curve, 0.0, 0.5, x=28, y=-10)
    pinned = t.math(
        "MAXIMUM", first, t.math("COMPARE", in_curve, last, 0.5, x=28, y=-11), x=29, y=-10
    )
    free = t.math("SUBTRACT", 1.0, pinned, x=30, y=-10)
    cut = attribute("cut", "FLOAT", 26, -12)

    t.section("Constraints")
    # Ends pinned on the meshes, the points next to them along the surface normals, and the
    # segment lengths, denser at the ends, but at the break
    length = attribute("length", "FLOAT", 27, -12)
    here = spacing(in_curve, last, 27, -13)
    after = spacing(t.math("ADD", in_curve, 1.0, x=27, y=-15), last, 28, -15)
    segment = t.math("MULTIPLY", t.math("SUBTRACT", after, here, x=31, y=-14), length, x=32, y=-14)
    reach = t.math("MULTIPLY", spacing(1.0, last, 28, -17), length, x=32, y=-17)
    near_a = t.math("COMPARE", in_curve, 1.0, 0.5, x=29, y=-18)
    near_b = t.math(
        "COMPARE", in_curve, t.math("SUBTRACT", last, 1.0, x=28, y=-19), 0.5, x=29, y=-19
    )
    pin = anchor_b
    for i, (select, value) in enumerate(
        (
            (
                near_b,
                t.vmath(
                    "ADD", anchor_b, t.vmath("SCALE", normal_b, reach, x=30, y=-21), x=31, y=-21
                ),
            ),
            (
                near_a,
                t.vmath(
                    "ADD", anchor_a, t.vmath("SCALE", normal_a, reach, x=30, y=-22), x=31, y=-22
                ),
            ),
            (first, anchor_a),
        )
    ):
        pin = t.node(
            "GeometryNodeSwitch",
            32 + i * 0.5,
            -20,
            {"Switch": select, "False": pin, "True": value},
            input_type="VECTOR",
        ).outputs[0]
    hold = t.math("ADD", near_a, near_b, x=30, y=-18)
    hold = t.math("MULTIPLY_ADD", pinned, 2.0, hold, x=31, y=-18)
    cut_here = t.math(
        "MULTIPLY", t.math("COMPARE", in_curve, cut, 0.5, x=30, y=-16), broken, x=31, y=-16
    )
    captured = t.node("GeometryNodeCaptureAttribute", 33, 0, {"Geometry": state})
    for data_type, name, value in (
        ("VECTOR", "Pin", pin),
        ("FLOAT", "Hold", hold),
        ("FLOAT", "Segment", segment),
        ("FLOAT", "Cut", cut_here),
        ("FLOAT", "Here", here),
        ("FLOAT", "Index", in_curve),
    ):
        captured.capture_items.new(data_type, name)
        t.connect(value, captured.inputs[name])
    state = captured.outputs["Geometry"]
    pin, hold = captured.outputs["Pin"], captured.outputs["Hold"]

    t.section("Solver")
    # XPBD solver on the strands as edges: the ends heavy for their pins to hold, broken
    # strands without the edge at the break
    mesh = t.node("GeometryNodeCurveToMesh", 34, 0, {"Curve": state}).outputs[0]
    first_vertex = t.node("GeometryNodeInputMeshEdgeVertices", 34, -2).outputs["Vertex Index 1"]

    def on_edges(value, x, y):
        return t.node(
            "GeometryNodeSampleIndex",
            x,
            y,
            {"Geometry": mesh, "Value": value, "Index": first_vertex},
            data_type="FLOAT",
            domain="POINT",
        ).outputs[0]

    mesh = t.node(
        "GeometryNodeDeleteGeometry",
        35,
        0,
        {"Geometry": mesh, "Selection": on_edges(captured.outputs["Cut"], 35, -2)},
        domain="EDGE",
        mode="EDGE_FACE",
    ).outputs[0]
    mass = t.math(
        "MULTIPLY_ADD", t.math("GREATER_THAN", hold, 1.5, x=35, y=-4), 1e6, 1.0, x=36, y=-4
    )
    gravity = t.vmath("SCALE", inputs["Gravity"], mass, x=37, y=-4)
    previous = t.node(
        "GeometryNodeInputNamedAttribute", 35, -6, {"Name": "strand_pin"}, data_type="FLOAT_VECTOR"
    ).outputs
    previous = t.node(
        "GeometryNodeSwitch",
        36,
        -6,
        {"Switch": previous["Exists"], "False": pin, "True": socket(previous, "Attribute")},
        input_type="VECTOR",
    ).outputs[0]
    held = t.math("GREATER_THAN", hold, 0.5, x=36, y=-7)
    for i, (name, data_type, value, domain) in enumerate(
        (
            ("strand_hold", "FLOAT", hold, "POINT"),
            ("strand_here", "FLOAT", captured.outputs["Here"], "POINT"),
            ("strand_index", "FLOAT", captured.outputs["Index"], "POINT"),
            ("mass", "FLOAT", mass, "POINT"),
            ("external_force", "FLOAT_VECTOR", gravity, "POINT"),
            ("velocity", "FLOAT_VECTOR", attribute("velocity", "FLOAT_VECTOR", 36, -8), "POINT"),
            ("sim:prop:Strands/Pin:selection", "BOOLEAN", held, "POINT"),
            ("sim:prop:Strands/Pin:position", "FLOAT_VECTOR", pin, "POINT"),
            ("sim:prop:Strands/Pin:compliance", "FLOAT", 0.0, "POINT"),
            ("sim:prop_prev:Strands/Pin:selection", "BOOLEAN", held, "POINT"),
            ("sim:prop_prev:Strands/Pin:position", "FLOAT_VECTOR", previous, "POINT"),
            ("sim:prop:Strands/Damping:linear", "FLOAT", inputs["Drag"], "POINT"),
            ("sim:prop:Strands/Damping:angular", "FLOAT", 0.0, "POINT"),
            (
                "sim:prop:Strands/Length:rest_length",
                "FLOAT",
                on_edges(captured.outputs["Segment"], 36, -10),
                "EDGE",
            ),
            ("sim:prop:Strands/Length:compliance", "FLOAT", 0.0, "EDGE"),
        )
    ):
        mesh = t.store(mesh, name, data_type, value, 36 + i * 0.25, 0, domain=domain)

    def bundle(x, y, items):
        node = t.node("NodeCombineBundle", x, y)
        for name, socket_type, value in items:
            node.bundle_items.new(socket_type, name)
            t.connect(value, node.inputs[name])
        return node.outputs[0]

    def effector(kind, x, y, *items):
        return bundle(x, y, (("Type", "STRING", kind), ("filter", "STRING", ""), *items))

    threshold = ("error_threshold", "FLOAT", 0.001)
    strands = bundle(
        39,
        -6,
        (
            ("Strands", "GEOMETRY", mesh),
            (
                "Pin",
                "BUNDLE",
                effector(
                    "Blender.Constraint.PinPosition",
                    38,
                    -6,
                    threshold,
                    ("lambda_attribute", "STRING", ""),
                ),
            ),
            ("Length", "BUNDLE", effector("Blender.Constraint.EdgeLength", 38, -8, threshold)),
            ("Damping", "BUNDLE", effector("Blender.Damping", 38, -9)),
        ),
    )
    world = bundle(40, 0, (("Strands", "BUNDLE", strands),))

    t.section("Substeps")
    # Substeps of the solver, the pins moving along them
    steps_in = t.node("GeometryNodeRepeatInput", 41, 0, {"Iterations": inputs["Substeps"]})
    steps_out = t.node("GeometryNodeRepeatOutput", 48, 0)
    steps_in.pair_with_output(steps_out)
    steps_out.repeat_items.new("BUNDLE", "World")
    steps_out.repeat_items.remove(steps_out.repeat_items[0])
    t.connect(world, steps_in.inputs["World"])
    # Until the Start Frame, a negligible step only satisfying the constraints
    step = t.math("DIVIDE", t.math("MAXIMUM", dt, 1e-5, x=40, y=-3), inputs["Substeps"], x=41, y=-3)
    begin = t.math("DIVIDE", steps_in.outputs["Iteration"], inputs["Substeps"], x=41, y=-4)
    end = t.math(
        "DIVIDE",
        t.math("ADD", steps_in.outputs["Iteration"], 1.0, x=41, y=-5),
        inputs["Substeps"],
        x=42,
        y=-5,
    )
    world = t.node(
        "GeometryNodeXPBDSolver",
        42,
        0,
        {
            "World": steps_in.outputs["World"],
            "Delta Time": step,
            "Substeps": 1,
            "Constraint Iterations": inputs["Iterations"],
            "Begin": begin,
            "End": end,
        },
    ).outputs[0]
    solved = t.node(
        "NodeGetBundleItem",
        43,
        0,
        {"Bundle": world, "Path": "Strands/Strands"},
        socket_type="GEOMETRY",
    ).outputs["Item"]

    # Long range attachments: no point farther from the attached ends than along the strand,
    # for the strands not to stretch under gravity, the velocities following
    before = t.node("GeometryNodeCaptureAttribute", 44, 0, {"Geometry": solved})
    before.capture_items.new("VECTOR", "Position")
    t.connect(position, before.inputs["Position"])
    chain = before.outputs["Geometry"]
    here = attribute("here", "FLOAT", 43, -8)
    in_strand = attribute("index", "FLOAT", 43, -9)
    after_cut = t.math("GREATER_THAN", in_strand, t.math("ADD", cut, 0.5, x=43, y=-10), x=44, y=-10)
    loose = t.math("LESS_THAN", attribute("hold", "FLOAT", 43, -11), 1.5, x=44, y=-11)
    for i, (end, along, attached) in enumerate(
        (
            (anchor_a, here, t.math("MULTIPLY", broken, after_cut, x=45, y=-10)),
            (
                anchor_b,
                t.math("SUBTRACT", 1.0, here, x=45, y=-12),
                t.math(
                    "MULTIPLY", broken, t.math("SUBTRACT", 1.0, after_cut, x=45, y=-13), x=46, y=-13
                ),
            ),
        )
    ):
        y = -14 - 4 * i
        reach = t.math("MULTIPLY", along, length, x=46, y=y - 1)
        offset = t.vmath("SUBTRACT", position, end, x=46, y=y)
        scale = t.math(
            "DIVIDE",
            t.math("MINIMUM", t.vmath("LENGTH", offset, x=47, y=y - 1), reach, x=48, y=y - 1),
            t.vmath("LENGTH", offset, x=47, y=y - 2),
            x=49,
            y=y - 1,
        )
        chain = t.node(
            "GeometryNodeSetPosition",
            45 + 0.5 * i,
            0,
            {
                "Geometry": chain,
                "Selection": t.math(
                    "MULTIPLY",
                    loose,
                    t.math("SUBTRACT", 1.0, attached, x=47, y=y - 3),
                    x=48,
                    y=y - 3,
                ),
                "Position": t.vmath(
                    "ADD", end, t.vmath("SCALE", offset, scale, x=49, y=y), x=50, y=y
                ),
            },
        ).outputs[0]

    # Collision: points under the surfaces, not deeper than the Control radius, pushed out, not
    # through open meshes as the solver colliders do
    nearest = [
        t.node(
            "GeometryNodeSampleNearestSurface",
            46,
            -26 - i,
            {"Mesh": collider, "Value": value, "Sample Position": position},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, value in enumerate((position, normal))
    ]
    outward = t.vmath("NORMALIZE", nearest[1], x=47, y=-27)
    side = t.vmath(
        "DOT_PRODUCT", t.vmath("SUBTRACT", position, nearest[0], x=47, y=-25), outward, x=48, y=-25
    )
    hit = t.math("LESS_THAN", side, strand_thickness, x=48, y=-24)
    hit = t.math(
        "MULTIPLY",
        hit,
        t.math("GREATER_THAN", side, t.math("MULTIPLY", radius, -1.0, x=47, y=-29), x=48, y=-29),
        x=49,
        y=-24,
    )
    hit = t.math("MULTIPLY", hit, loose, x=49, y=-23)
    collided = t.node(
        "GeometryNodeSetPosition",
        46.25,
        0,
        {
            "Geometry": chain,
            "Selection": hit,
            "Position": t.vmath(
                "ADD",
                nearest[0],
                t.vmath("SCALE", outward, strand_thickness, x=48, y=-28),
                x=49,
                y=-28,
            ),
        },
    ).outputs[0]
    chain = t.node(
        "GeometryNodeSwitch",
        46.5,
        0,
        {"Switch": inputs["Collision"], "False": chain, "True": collided},
        input_type="GEOMETRY",
    ).outputs[0]
    moved = t.vmath("SUBTRACT", position, before.outputs["Position"], x=46, y=-22)
    velocity = t.vmath(
        "ADD",
        t.attribute("velocity", "FLOAT_VECTOR", 46, -23),
        t.vmath("SCALE", moved, t.math("DIVIDE", 1.0, step, x=46, y=-24), x=47, y=-23),
        x=48,
        y=-23,
    )
    chain = t.store(chain, "velocity", "FLOAT_VECTOR", velocity, 46.75, 0)
    world = t.node(
        "NodeStoreBundleItem",
        47,
        0,
        {"Bundle": world, "Path": "Strands/Strands", "Item": chain},
        socket_type="GEOMETRY",
    ).outputs[0]
    t.connect(world, steps_out.inputs["World"])
    solved = t.node(
        "NodeGetBundleItem",
        49,
        0,
        {"Bundle": steps_out.outputs["World"], "Path": "Strands/Strands"},
        socket_type="GEOMETRY",
    ).outputs["Item"]

    t.section("Back on the Strands")
    # Positions and velocities back on the curves, the pins kept to move them smoothly next
    chain = state
    for name, target in (("position", "position"), ("velocity", "strand_velocity")):
        value = t.node(
            "GeometryNodeSampleIndex",
            43,
            -3,
            {
                "Geometry": solved,
                "Value": t.attribute(name, "FLOAT_VECTOR", 42, -3),
                "Index": index,
            },
            data_type="FLOAT_VECTOR",
            domain="POINT",
        ).outputs[0]
        if name == "velocity":
            # At rest until the Start Frame
            value = t.vmath("SCALE", value, started, x=44, y=-3)
        chain = t.store(chain, target, "FLOAT_VECTOR", value, 44, 0)
    chain = t.store(chain, "strand_pin", "FLOAT_VECTOR", pin, 45, 0)
    # Not simulated while hidden
    simulated = t.node(
        "GeometryNodeSwitch",
        46,
        0,
        {"Switch": hidden, "False": chain, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    t.connect(simulated, sim_out.inputs["Geometry"])
    # The zone output after its last nodes
    sim_out.parent = t.frame

    t.section("Without Physics", row=True)
    # Without physics: the hanging chains, without the simulation zone not to need its cache,
    # removed when broken
    _, _, distance = anchors(40, 8)
    breaking = t.math("GREATER_THAN", distance, strand_break, x=46, y=6)
    breaking = t.math(
        "MULTIPLY", breaking, t.math("GREATER_THAN", strand_break, 0.0, x=46, y=5), x=47, y=6
    )
    static = t.node(
        "GeometryNodeDeleteGeometry",
        48,
        4,
        {"Geometry": curves, "Selection": breaking},
        domain="POINT",
    ).outputs[0]

    t.section("Radius")
    # Radius: pinched in the middle, flared on the surface, tapered at the break
    strands = t.node(
        "GeometryNodeSwitch",
        49,
        2,
        {"Switch": inputs["Physics"], "False": static, "True": sim_out.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    strands = t.node(
        "GeometryNodeSwitch", 49.5, 2, {"Switch": hidden, "False": strands}, input_type="GEOMETRY"
    ).outputs[0]
    factor = spacing(in_curve, last, 43, -4)
    pinch = t.math("SINE", t.math("MULTIPLY", factor, math.pi, x=46, y=-4), x=47, y=-4)
    pinch = t.math(
        "MULTIPLY_ADD",
        pinch,
        t.math("SUBTRACT", inputs["Mid Pinch"], 1.0, x=47, y=-5),
        1.0,
        x=48,
        y=-4,
    )
    # Closeness to breaking, 0 without Break Length as the division by 0 is 0
    tension = t.math(
        "DIVIDE",
        attribute("length", "FLOAT", 45, -7),
        strand_break,
        x=46,
        y=-7,
        clamp=True,
    )
    # Thinner closer to breaking, down to a third
    thin = t.math("MULTIPLY", tension, tension, x=47, y=-7)
    thin = t.math("MULTIPLY_ADD", thin, -0.65, 1.0, x=48, y=-7)
    along = t.math("SUBTRACT", spline_length["Length"], spline["Length"], x=45, y=-10)
    along = t.math("MINIMUM", along, spline["Length"], x=46, y=-10)
    along = t.math("SUBTRACT", along, inputs["End Insert"], x=47, y=-10)
    flare = t.math("DIVIDE", along, inputs["Flare Length"], x=48, y=-10)
    flare = t.math("SUBTRACT", 1.0, flare, x=49, y=-10, clamp=True)
    # Pulled onto the surface further than the flare, for it to blend in
    stick = t.math("POWER", flare, 1.5, x=50, y=-9)
    strands = t.store(strands, "strand_flare", "FLOAT", stick, 52, 0)
    flare = t.math("POWER", flare, 3.0, x=50, y=-10)
    flare = t.math(
        "MULTIPLY_ADD",
        flare,
        t.math("SUBTRACT", inputs["Flare Width"], 1.0, x=50, y=-11),
        1.0,
        x=51,
        y=-10,
    )
    from_cut = t.math("SUBTRACT", in_curve, cut, x=45, y=-13)
    tip = t.math("ABSOLUTE", t.math("SUBTRACT", from_cut, 0.5, x=46, y=-13), x=47, y=-13)
    tip = t.math("SUBTRACT", 1.0, t.math("DIVIDE", tip, 3.0, x=48, y=-13, clamp=True), x=49, y=-13)
    tip = t.math(
        "MULTIPLY_ADD", tip, t.math("MULTIPLY", broken, -1.0, x=49, y=-14), 1.0, x=50, y=-13
    )
    curve = t.node("GeometryNodeCurveOfPoint", 43, -16).outputs["Curve Index"]
    lumps = t.node(
        "ShaderNodeTexNoise",
        46,
        -16,
        {
            "W": t.math(
                "MULTIPLY_ADD",
                factor,
                6.0,
                t.math("MULTIPLY", curve, 7.31, x=44, y=-16),
                x=45,
                y=-16,
            )
        },
        noise_dimensions="1D",
    ).outputs["Factor"]
    lumps = t.math("MULTIPLY_ADD", lumps, 2.0, -1.0, x=47, y=-16)
    lumps = t.math("MULTIPLY_ADD", lumps, inputs["Irregularity"], 1.0, x=48, y=-16)
    radius = strand_thickness
    for i, value in enumerate((pinch, thin, flare, tip, lumps)):
        radius = t.math("MULTIPLY", radius, value, x=50 + i, y=-3)
    strands = t.store(strands, "strand_radius", "FLOAT", radius, 53, 0)
    # For the shader: the length relative to the break one, 0 once broken
    unbroken = t.math("SUBTRACT", 1.0, broken, x=52, y=-18)
    tension = t.math("MULTIPLY", tension, unbroken, x=53, y=-18)
    strands = t.store(strands, "sticky_length_normalized", "FLOAT", tension, 53.5, 0)
    gap = t.math("COMPARE", from_cut, 0.5, 0.6, x=50, y=-15)
    strands = t.store(
        strands, "strand_gap", "FLOAT", t.math("MULTIPLY", gap, broken, x=51, y=-15), 54, 0
    )

    # For the shader: the factor along the whole strands, 0 and 1 on the meshes when broken too
    strands = t.store(strands, "sticky_factor", "FLOAT", spline["Factor"], 54.5, 0)

    t.section("Strand Mesh")
    # Broken strands split in two at the break, by deleting that edge
    edges = t.node("GeometryNodeCurveToMesh", 55, 0, {"Curve": strands}).outputs[0]
    edges = t.node(
        "GeometryNodeDeleteGeometry",
        56,
        0,
        {
            "Geometry": edges,
            "Selection": t.math(
                "GREATER_THAN", attribute("gap", "FLOAT", 55, -2), 0.75, x=56, y=-2
            ),
        },
        domain="EDGE",
    ).outputs[0]
    strands = t.node("GeometryNodeMeshToCurve", 57, 0, {"Mesh": edges}).outputs[0]

    # Smoothed, keeping the ends on the surfaces and at the break
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        57,
        -2,
        {"Value": position, "Iterations": inputs["Smooth"]},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    strands = t.node(
        "GeometryNodeSetPosition",
        57.5,
        0,
        {"Geometry": strands, "Selection": free, "Position": blurred},
    ).outputs[0]
    strands = t.node(
        "GeometryNodeCurveSplineType", 58, 0, {"Curve": strands}, spline_type="CATMULL_ROM"
    ).outputs[0]
    strands = t.node(
        "GeometryNodeSetSplineResolution", 59, 0, {"Curve": strands, "Resolution": 4}
    ).outputs[0]
    # For the shader: the length of the strands, broken ones split
    strands = t.store(strands, "sticky_length", "FLOAT", spline_length["Length"], 59.5, 0)
    profile = t.node(
        "GeometryNodeCurvePrimitiveCircle",
        59,
        -2,
        {"Resolution": inputs["Profile Resolution"], "Radius": 1.0},
    ).outputs["Curve"]
    strands = t.node(
        "GeometryNodeCurveToMesh",
        60,
        0,
        {
            "Curve": strands,
            "Profile Curve": profile,
            "Scale": attribute("radius", "FLOAT", 59, -4),
            "Fill Caps": True,
        },
    ).outputs[0]
    t.section("Sticky Ends")
    # Sticky ends: the flared tips pulled onto the surfaces
    surfaces = t.node("GeometryNodeJoinGeometry", 60, -6)
    for geometry in (other_target, source):
        t.connect(geometry, surfaces.inputs[0])
    surfaces = near(surfaces.outputs[0], strands, inputs["Flare Length"], 56, -6)
    nearest = t.node(
        "GeometryNodeProximity", 61, -6, {0: surfaces}, target_element="FACES"
    ).outputs["Position"]
    stick = t.math(
        "MULTIPLY", attribute("flare", "FLOAT", 60, -8), inputs["Sticky Ends"], x=61, y=-8
    )
    sticky = t.node(
        "GeometryNodeSetPosition",
        60.5,
        0,
        {
            "Geometry": strands,
            "Offset": t.vmath(
                "SCALE", t.vmath("SUBTRACT", nearest, position, x=62, y=-6), stick, x=62, y=-8
            ),
        },
    ).outputs[0]
    strands = t.node(
        "GeometryNodeSwitch",
        61,
        1,
        {
            "Switch": t.math("GREATER_THAN", inputs["Sticky Ends"], 0.0, x=60, y=2),
            "False": strands,
            "True": sticky,
        },
        input_type="GEOMETRY",
    ).outputs[0]
    strands = t.node(
        "GeometryNodeRemoveAttribute",
        61,
        0,
        {"Geometry": strands, "Pattern Mode": "Wildcard", "Name": "strand_*"},
    ).outputs[0]
    strands = t.node("GeometryNodeSetShadeSmooth", 63, 0, {"Mesh": strands}).outputs[0]
    strands = t.node(
        "GeometryNodeSetMaterial", 64, 0, {"Geometry": strands, "Material": inputs["Material"]}
    ).outputs[0]
    strands = t.node(
        "GeometryNodeTransform",
        65,
        0,
        {"Geometry": strands, "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]

    t.section("Output")
    # An instance, for the mesh not to be copied into a new one with the strands
    strands = t.node("GeometryNodeGeometryToInstance", 65.5, 0, {0: strands}).outputs[0]
    join = t.node("GeometryNodeJoinGeometry", 66, 0)
    t.connect(strands, join.inputs[0])
    t.connect(inputs["Geometry"], join.inputs[0])
    t.node("NodeGroupOutput", 67, 0, {0: join.outputs[0]})
    t.arrange()
    note(t, text, 0, 3)
    return ng


def build_material(text):
    """Saliva: clear, wet and glossy, with a faint cloudy tint and milky ends"""
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    # Refraction through the thin strands in EEVEE, and their light shadows
    material.use_raytrace_refraction = True
    material.thickness_mode = "SPHERE"
    material.use_transparent_shadow = True
    t = Tree(material.node_tree)
    note(t, text, -6, 3.5)
    # Example of the strand attributes: milky ends, clearing up as the strands stretch
    factor, tension = (
        t.node("ShaderNodeAttribute", -6, y, attribute_type="GEOMETRY", attribute_name=name)
        for y, name in ((1, "sticky_factor"), (-1, "sticky_length_normalized"))
    )
    ends = t.math("MULTIPLY_ADD", factor.outputs["Fac"], 2.0, -1.0, x=-5, y=1)
    ends = t.math("POWER", t.math("ABSOLUTE", ends, x=-4, y=1), 8.0, x=-3, y=1)
    clear = t.math("SUBTRACT", 1.0, tension.outputs["Fac"], x=-4, y=-1)
    milky = t.math("MULTIPLY", ends, clear, x=-2, y=0)
    saliva = t.node(
        "ShaderNodeBsdfPrincipled",
        0,
        0,
        {
            "Base Color": (0.92, 0.95, 0.97, 1.0),
            "Roughness": 0.03,
            "IOR": 1.335,
            "Transmission Weight": t.math("MULTIPLY_ADD", milky, -0.4, 1.0, x=-1, y=0),
        },
    )
    t.node("ShaderNodeOutputMaterial", 2, 0, {"Surface": saliva.outputs[0]})
    return material


if __name__ == "__main__":
    text = bpy.data.texts.new(NODE_GROUP)
    text.write(ATTRIBUTES)
    write(RESOURCE, (build_node_group(text), build_material(text)))
