# Build cloth_tear.blend: the Cloth Tear node group
# Usage: Blender --background --factory-startup --python cloth_tear_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "cloth_tear.blend"
NODE_GROUP = "MustardUI Cloth Tear"
# Distance of the pieces from the collider and the floor
COLLISION = 0.002
# Distance from the top of the cloth of the parts still holding it, when cut off
SUPPORT = 0.02
# Pleats of the cloth gathered by a Pull: height, in Pull radii, and frequency around it
CRUMPLE = 0.15
CRUMPLE_SCALE = 8.0
# XPBD compliance of the bending pairs at half Bending, in m/N with points of 1 kg
BEND_COMPLIANCE = 3e-5


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = "Tear the mesh inside the Control sphere, with frayed threads on the edge"

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Controls",
        "NodeSocketCollection",
        description="Collection of the Empties whose spheres tear the mesh",
    )
    add_input(
        ng,
        "Pulls",
        "NodeSocketCollection",
        description="Collection of the Empties grabbing the cloth in their spheres on the Start "
        "Frame, pulling it until it rips. Needs Physics",
    )

    panel = ng.interface.new_panel("Tear")
    add_input(
        ng,
        "Jaggedness",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Length of the rips out of the Control sphere, relative to its radius",
    )
    add_input(
        ng,
        "Noise Scale",
        "NodeSocketFloat",
        panel,
        default_value=4.0,
        min_value=0.0,
        max_value=100.0,
        description="Scale of the tear irregularity",
    )
    add_input(
        ng,
        "Edge Width",
        "NodeSocketFloat",
        panel,
        default_value=0.01,
        min_value=0.0001,
        max_value=1.0,
        subtype="DISTANCE",
        description="Width of the edge, stored in the cloth_tear_edge attribute",
    )

    panel = ng.interface.new_panel("Threads")
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        panel,
        default_value=600.0,
        min_value=0.0,
        max_value=1e5,
        description="Yarn ends per meter of edge",
    )
    add_input(
        ng,
        "Length",
        "NodeSocketFloat",
        panel,
        default_value=0.005,
        min_value=0.0,
        max_value=1.0,
        subtype="DISTANCE",
        description="Length of the threads out of the edge",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        panel,
        default_value=0.00015,
        min_value=0.0,
        max_value=0.1,
        subtype="DISTANCE",
        description="Radius of the threads at the root",
    )
    add_input(
        ng,
        "Droop",
        "NodeSocketFloat",
        panel,
        default_value=0.003,
        min_value=0.0,
        max_value=1.0,
        subtype="DISTANCE",
        description="Fall of the thread tips under gravity",
    )
    add_input(
        ng,
        "Randomness",
        "NodeSocketFloat",
        panel,
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Variation of length and bending between threads",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        panel,
        default_value=5,
        min_value=2,
        max_value=64,
        description="Points along each thread",
    )
    add_input(
        ng,
        "Fibers",
        "NodeSocketInt",
        panel,
        default_value=3,
        min_value=1,
        max_value=32,
        description="Fibers of each yarn end, in a tuft",
    )
    add_input(
        ng,
        "Spread",
        "NodeSocketFloat",
        panel,
        default_value=0.35,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Spread of the fibers of a tuft",
    )
    add_input(
        ng,
        "Grain",
        "NodeSocketVector",
        panel,
        default_value=(0.0, 0.0, 1.0),
        subtype="DIRECTION",
        description="Direction of the threads of the fabric, in the space of the mesh: the "
        "threads out of the edge follow it or go across it",
    )
    add_input(
        ng,
        "Share",
        "NodeSocketFloat",
        panel,
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Share of the threads still across the tear, where it is narrower than the "
        "Bridge Length along the grain",
    )
    add_input(
        ng,
        "Bridge Length",
        "NodeSocketFloat",
        panel,
        default_value=0.02,
        min_value=0.0,
        max_value=1.0,
        subtype="DISTANCE",
        description="Longest threads across the tear",
    )

    panel = ng.interface.new_panel("Physics")
    add_input(
        ng,
        "Physics",
        "NodeSocketBool",
        panel,
        default_value=False,
        description="Tear whole pieces once touched, hanging from the cloth or falling. "
        "Simulated from the Start Frame",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", panel, description="First simulated frame")
    add_input(
        ng,
        "Piece Size",
        "NodeSocketFloat",
        panel,
        default_value=0.05,
        min_value=0.001,
        max_value=10.0,
        subtype="DISTANCE",
        description="Size of the torn pieces",
    )
    add_input(
        ng,
        "Rip Out",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Chance of the pieces to rip out, instead of hanging where still attached",
    )
    add_input(
        ng,
        "Release",
        "NodeSocketFloat",
        panel,
        default_value=0.1,
        min_value=0.0,
        max_value=10.0,
        subtype="DISTANCE",
        description="Distance from the tear where the cloth gets physics, less and less, held "
        "by the body farther away",
    )
    add_input(
        ng,
        "Push",
        "NodeSocketFloat",
        panel,
        default_value=0.2,
        min_value=0.0,
        max_value=100.0,
        description="Speed of the torn pieces away from the Control in m/s, varying to tumble them",
    )
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        panel,
        description="Collection of the meshes the pieces and the released cloth collide with, as "
        "the body",
    )
    add_input(
        ng,
        "Floor",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        description="Height of the floor the pieces land on, in world space",
    )
    add_input(
        ng,
        "Anchor",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group holding the cloth: the parts cut off from it fall. "
        "Without it, the parts cut off from the top of the cloth fall",
    )
    add_input(
        ng,
        "Shape",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Hold of the released cloth on the shape of the outfit, not to sag, less and "
        "less towards the tear and the Pulls",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        panel,
        min_value=0.0,
        max_value=1e4,
        subtype="TIME_ABSOLUTE",
        description="Seconds before the torn pieces disappear, 0 to keep them",
    )
    add_input(
        ng,
        "Gravity",
        "NodeSocketVector",
        panel,
        subtype="ACCELERATION",
        default_value=(0.0, 0.0, -9.81),
        description="Acceleration of the pieces, in world space",
    )
    add_input(
        ng,
        "Drag",
        "NodeSocketFloat",
        panel,
        default_value=3.0,
        min_value=0.0,
        max_value=100.0,
        description="Slowdown of the pieces per second, from the air",
    )
    add_input(
        ng,
        "Damping",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Slowdown of the motion between neighbor points, as flutter and jitter, "
        "without slowing the pieces as a whole",
    )
    add_input(
        ng,
        "Bending",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Resistance of the pieces and of the released cloth to folding and crumpling",
    )
    add_input(
        ng,
        "Time Scale",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.01,
        max_value=10.0,
        description="Speed of the simulation, lower for slow motion",
    )
    add_input(
        ng,
        "Substeps",
        "NodeSocketInt",
        panel,
        default_value=10,
        min_value=1,
        max_value=100,
        description="Simulation steps per frame",
    )
    add_input(
        ng,
        "Iterations",
        "NodeSocketInt",
        panel,
        default_value=6,
        min_value=1,
        max_value=100,
        description="Length constraint iterations per step, higher for less stretchy pieces",
    )
    add_input(
        ng,
        "Self Collision",
        "NodeSocketFloat",
        panel,
        default_value=0.003,
        min_value=0.0,
        max_value=1.0,
        subtype="DISTANCE",
        description="Distance kept between the points of the pieces and of the released cloth, "
        "below the length of their edges. 0 for none",
    )
    add_input(
        ng,
        "Friction",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
        min_value=0.0,
        max_value=2.0,
        description="Friction coefficient of the pieces and of the released cloth sliding on the "
        "Colliders and on the cloth",
    )
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.01,
        max_value=100.0,
        description="Stretch of the cloth before it rips, relative to its length",
    )
    add_input(
        ng,
        "Reach",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.0,
        max_value=100.0,
        subtype="DISTANCE",
        description="Distance from the Pulls where the cloth gets physics and is dragged along, "
        "less and less, held by the body farther away. Large for the whole outfit",
    )
    add_input(
        ng,
        "In Hand",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Ripped off parts held by the Pulls, falling otherwise",
    )

    arrange_interface(ng)

    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -12, 0).outputs
    self_object = t.node("GeometryNodeSelfObject", -12, -2).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -11, -2, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", -10, -2, {0: to_world}).outputs[0]
    index = t.node("GeometryNodeInputIndex", -4, -4).outputs[0]
    position = t.node("GeometryNodeInputPosition", -4, -3).outputs[0]

    t.section("Tear", row=True)
    # Distance from the closest jagged sphere of the Controls, out of it by the noise along each
    # direction, with the index of the Control
    controls = t.node(
        "GeometryNodeCollectionInfo",
        -12,
        2,
        {"Collection": inputs["Controls"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]

    def jagged(point, control, y):
        """Point in the space of the Control, its direction and the radius of its jagged sphere"""
        inverse = t.node(
            "FunctionNodeInvertMatrix", -9, y, {0: control_transform(t, controls, control, -10, y)}
        ).outputs[0]
        local = t.node(
            "FunctionNodeTransformPoint", -8, y, {"Vector": point, "Transform": inverse}
        ).outputs[0]
        direction = t.vmath("NORMALIZE", local, x=-7, y=y + 1)
        noise = t.node(
            "ShaderNodeTexNoise",
            -6,
            y + 2,
            {
                "Vector": direction,
                "W": control,
                "Scale": inputs["Noise Scale"],
                "Detail": 3.0,
                "Roughness": 0.65,
            },
            noise_dimensions="4D",
            noise_type="HETERO_TERRAIN",
        )
        # The noise being about -1 to 1
        radius = t.math("ADD", noise.outputs["Fac"], 1.0, x=-5, y=y + 2)
        radius = t.math("MULTIPLY_ADD", radius, inputs["Jaggedness"], 1.0, x=-4, y=y + 2)
        return local, direction, t.math("MAXIMUM", radius, 1.0, x=-3, y=y + 2)

    geometry = t.store(inputs["Geometry"], ".cloth_tear_distance", "FLOAT", 1e9, -11, 0)
    repeat_in = t.node(
        "GeometryNodeRepeatInput",
        -10,
        0,
        {
            "Iterations": t.node(
                "GeometryNodeAttributeDomainSize",
                -11,
                1,
                {"Geometry": controls},
                component="INSTANCES",
            ).outputs["Instance Count"]
        },
    )
    repeat_out = t.node("GeometryNodeRepeatOutput", -1, 0)
    repeat_in.pair_with_output(repeat_out)
    t.connect(geometry, repeat_in.inputs["Geometry"])
    control = repeat_in.outputs["Iteration"]
    local, _, radius = jagged(position, control, 1)
    length = t.vmath("LENGTH", local, x=-6, y=1)
    # In the units of the mesh, by the average scale of the Control
    scale = t.node(
        "FunctionNodeSeparateTransform", -3, 2, {0: control_transform(t, controls, control, -4, 2)}
    ).outputs["Scale"]
    scale = t.vmath("DOT_PRODUCT", scale, (1 / 3, 1 / 3, 1 / 3), x=-2, y=2)
    # The noise only where it matters, farther than its largest radius elsewhere, faster
    largest = t.math("MULTIPLY_ADD", inputs["Jaggedness"], 2.5, 1.0, x=-5, y=4)
    lower = t.math("MULTIPLY", t.math("SUBTRACT", length, largest, x=-4, y=4), scale, x=-3, y=4)
    cutoff = t.math(
        "ADD",
        t.math(
            "ADD",
            inputs["Release"],
            t.math("MULTIPLY_ADD", inputs["Piece Size"], 2.0, inputs["Edge Width"], x=-5, y=6),
            x=-4,
            y=6,
        ),
        0.1,
        x=-3,
        y=6,
    )
    near = t.math("LESS_THAN", lower, cutoff, x=-2, y=5)
    geometry = t.node(
        "GeometryNodeStoreNamedAttribute",
        -4,
        0,
        {
            "Geometry": repeat_in.outputs["Geometry"],
            "Selection": near,
            "Name": ".cloth_tear_exact",
            "Value": t.math(
                "MULTIPLY", t.math("SUBTRACT", length, radius, x=-2, y=1), scale, x=-1, y=1
            ),
        },
        data_type="FLOAT",
    ).outputs[0]
    distance = t.node(
        "GeometryNodeSwitch",
        -1,
        2,
        {
            "Switch": near,
            "False": lower,
            "True": t.attribute(".cloth_tear_exact", "FLOAT", -2, 3),
        },
        input_type="FLOAT",
    ).outputs[0]
    closer = t.math(
        "LESS_THAN", distance, t.attribute(".cloth_tear_distance", "FLOAT", -2, -1), x=-1, y=-1
    )
    for i, (name, data_type, value) in enumerate(
        ((".cloth_tear_control", "INT", control), (".cloth_tear_distance", "FLOAT", distance))
    ):
        geometry = t.node(
            "GeometryNodeStoreNamedAttribute",
            -3 + i,
            0,
            {"Geometry": geometry, "Selection": closer, "Name": name, "Value": value},
            data_type=data_type,
        ).outputs[0]
    t.connect(geometry, repeat_out.inputs["Geometry"])
    repeat_out.parent = t.frame
    geometry = repeat_out.outputs["Geometry"]
    distance = t.attribute(".cloth_tear_distance", "FLOAT", 0, -2)
    control = t.attribute(".cloth_tear_control", "INT", 0, -3)

    t.section("Cut", row=True)
    # The points next to the inside moved to the crossings towards the other points of their
    # faces, along the edges and the diagonals, deleting the faces inside
    corner = t.node("GeometryNodeInputIndex", -5, -1).outputs[0]
    total = count = None
    for i in range(3):
        y = -1 - 3 * i
        other = t.node(
            "GeometryNodeVertexOfCorner",
            -4,
            y,
            {
                0: t.node(
                    "GeometryNodeOffsetCornerInFace",
                    -5,
                    y,
                    {"Corner Index": corner, "Offset": i + 1},
                ).outputs[0]
            },
        ).outputs[0]
        other_distance, other_position = (
            t.node(
                "GeometryNodeFieldAtIndex",
                -3,
                y - j,
                {"Value": value, "Index": other},
                data_type=data_type,
                domain="POINT",
            ).outputs[0]
            for j, (value, data_type) in enumerate(
                ((distance, "FLOAT"), (position, "FLOAT_VECTOR"))
            )
        )
        crossing = t.math(
            "LESS_THAN", t.math("MULTIPLY", distance, other_distance, x=-2, y=y), 0.0, x=-1, y=y
        )
        factor = t.math(
            "DIVIDE",
            distance,
            t.math("SUBTRACT", distance, other_distance, x=-2, y=y - 1),
            x=-1,
            y=y - 1,
        )
        point = t.vmath(
            "ADD",
            position,
            t.vmath(
                "SCALE",
                t.vmath("SUBTRACT", other_position, position, x=-2, y=y - 2),
                factor,
                x=-1,
                y=y - 2,
            ),
            x=0,
            y=y - 2,
        )
        point = t.vmath("SCALE", point, crossing, x=0, y=y)
        total = point if total is None else t.vmath("ADD", total, point, x=0.5, y=y)
        count = crossing if count is None else t.math("ADD", count, crossing, x=0.5, y=y - 1)
    crossings = [
        t.node(
            "GeometryNodeFieldOnDomain",
            1,
            -2 - i,
            {"Value": value},
            data_type=data_type,
            domain="CORNER",
        ).outputs[0]
        for i, (value, data_type) in enumerate(((total, "FLOAT_VECTOR"), (count, "FLOAT")))
    ]
    crossed = t.math("GREATER_THAN", crossings[1], 0.0, x=2, y=-1)
    snapped = t.node(
        "GeometryNodeSwitch",
        3,
        -2,
        {
            "Switch": crossed,
            "False": position,
            "True": t.vmath(
                "SCALE",
                crossings[0],
                t.math("DIVIDE", 1.0, crossings[1], x=2, y=-3),
                x=3,
                y=-3,
            ),
        },
        input_type="VECTOR",
    ).outputs[0]
    # On the jagged sphere, the average of the crossings being inside it where it is convex
    _, direction, radius = jagged(snapped, control, -6)
    snapped = t.node(
        "FunctionNodeTransformPoint",
        3,
        -4,
        {
            "Vector": t.vmath("SCALE", direction, radius, x=2, y=-4),
            "Transform": control_transform(t, controls, control, 2, -5),
        },
    ).outputs[0]
    inside = t.math("LESS_THAN", distance, 0.0, x=0, y=0)
    moved = t.node(
        "FunctionNodeBooleanMath", 3, -1, {0: crossed, 1: inside}, operation="NIMPLY"
    ).outputs[0]
    # As floats, for the faces with any point inside and the edges with both points on the tear
    cut = t.store(geometry, ".cloth_tear_inside", "FLOAT", inside, 1, 0)
    cut = t.store(cut, ".cloth_tear_moved", "FLOAT", moved, 2, 0)
    cut = t.node(
        "GeometryNodeSetPosition", 4, 0, {"Geometry": cut, "Selection": moved, "Position": snapped}
    ).outputs[0]
    cut = t.node(
        "GeometryNodeDeleteGeometry",
        5,
        0,
        {
            "Geometry": cut,
            "Selection": t.math(
                "GREATER_THAN", t.attribute(".cloth_tear_inside", "FLOAT", 4, -1), 0.0, x=5, y=-1
            ),
        },
        domain="FACE",
    ).outputs[0]
    tear = border(t, cut, 5, -3)

    physics_cloth, physics_tear = build_physics(
        t, inputs, geometry, controls, inside, to_world, to_local, index
    )

    t.section("Edge", row=True)
    cut, tear = (
        t.node(
            "GeometryNodeSwitch",
            0,
            -i,
            {"Switch": inputs["Physics"], "False": static, "True": dynamic},
            input_type="GEOMETRY",
        ).outputs[0]
        for i, (static, dynamic) in enumerate(((cut, physics_cloth), (tear, physics_tear)))
    )
    tear = t.node("GeometryNodeProximity", 1, -1, {0: tear}, target_element="EDGES").outputs
    edge = t.node(
        "ShaderNodeMapRange",
        2,
        -1,
        {0: tear["Distance"], 2: inputs["Edge Width"], 3: 1.0, 4: 0.0},
    ).outputs[0]
    # Nowhere without a tear
    edge = t.math("MULTIPLY", edge, tear["Is Valid"], x=3, y=-1)
    # Only around the points on the tear, two rings of faces away, faster
    on_tear = t.math(
        "GREATER_THAN", t.attribute(".cloth_tear_moved", "FLOAT", 0, -3), 0.0, x=1, y=-3
    )
    around = rings(t, on_tear, 2, 2, -3)
    cut = t.node(
        "GeometryNodeStoreNamedAttribute",
        4,
        0,
        {
            "Geometry": cut,
            "Selection": t.math("GREATER_THAN", around, 0.0, x=4, y=-3),
            "Name": "cloth_tear_edge",
            "Value": edge,
        },
        data_type="FLOAT",
    ).outputs[0]

    t.section("Roots", row=True)
    # On the faces with points at the edge, with their material and normal
    in_edge = t.math(
        "GREATER_THAN", t.attribute("cloth_tear_edge", "FLOAT", -2, -6), 0.0, x=-1, y=-6
    )
    faces = t.node(
        "GeometryNodeFieldOnDomain", 0, -6, {"Value": in_edge}, data_type="FLOAT", domain="POINT"
    ).outputs[0]
    material = t.node("GeometryNodeInputMaterialIndex", 1, -5).outputs[0]
    roots = t.store(cut, ".cloth_tear_material", "INT", material, 2, -4, domain="FACE")
    distribute = t.node(
        "GeometryNodeDistributePointsOnFaces",
        3,
        -4,
        {
            "Mesh": roots,
            "Selection": t.math("GREATER_THAN", faces, 0.0, x=1, y=-6),
            "Density": t.math("DIVIDE", inputs["Density"], inputs["Edge Width"], x=2, y=-7),
        },
        distribute_method="RANDOM",
    ).outputs
    roots = t.store(
        distribute["Points"], ".cloth_tear_normal", "FLOAT_VECTOR", distribute["Normal"], 4, -4
    )
    roots = t.node(
        "GeometryNodeDeleteGeometry",
        9,
        -4,
        {
            "Geometry": roots,
            "Selection": t.math(
                "LESS_THAN",
                t.math(
                    "MULTIPLY",
                    t.math("LESS_THAN", tear["Distance"], inputs["Edge Width"], x=6, y=-6),
                    tear["Is Valid"],
                    x=7,
                    y=-6,
                ),
                0.5,
                x=8,
                y=-6,
            ),
        },
        domain="POINT",
    ).outputs[0]
    # Tufts of fibers at each yarn end
    roots = t.node(
        "GeometryNodeDuplicateElements",
        10,
        -4,
        {"Geometry": roots, "Amount": inputs["Fibers"]},
        domain="POINT",
    ).outputs["Geometry"]

    t.section("Threads", row=True)
    # Each thread from the tear closest to its root, along the grain or across it, bending
    # sideways and drooping as a parabola
    root_normal = t.vmath(
        "NORMALIZE", t.attribute(".cloth_tear_normal", "FLOAT_VECTOR", -4, -12), x=-3, y=-12
    )
    across = t.vmath("SUBTRACT", tear["Position"], position, x=-3, y=-10)
    tangent = t.vmath(
        "SUBTRACT",
        across,
        t.vmath(
            "SCALE",
            root_normal,
            t.vmath("DOT_PRODUCT", across, root_normal, x=-2, y=-11),
            x=-1,
            y=-11,
        ),
        x=0,
        y=-10,
    )
    tangent = t.vmath("NORMALIZE", tangent, x=1, y=-10)
    # The grain on the surface, or another direction where it is along the normal
    weave = [
        t.vmath(
            "SUBTRACT",
            axis,
            t.vmath(
                "SCALE",
                root_normal,
                t.vmath("DOT_PRODUCT", axis, root_normal, x=-2, y=-20 - i),
                x=-1,
                y=-20 - i,
            ),
            x=0,
            y=-20 - i,
        )
        for i, axis in enumerate((inputs["Grain"], (1.0, 0.0, 0.0)))
    ]
    warp = t.node(
        "GeometryNodeSwitch",
        1,
        -20,
        {
            "Switch": t.math(
                "GREATER_THAN", t.vmath("LENGTH", weave[0], x=0, y=-22), 0.3, x=1, y=-22
            ),
            "False": weave[1],
            "True": weave[0],
        },
        input_type="VECTOR",
    ).outputs[0]
    warp = t.vmath("NORMALIZE", warp, x=2, y=-20)
    weft = t.vmath("CROSS_PRODUCT", root_normal, warp, x=2, y=-21)
    # The one closest to the way out of the edge
    along = [
        t.vmath("DOT_PRODUCT", tangent, axis, x=3, y=-20 - i) for i, axis in enumerate((warp, weft))
    ]
    grain = t.node(
        "GeometryNodeSwitch",
        4,
        -20,
        {
            "Switch": t.math(
                "GREATER_THAN",
                t.math("ABSOLUTE", along[0], x=3, y=-22),
                t.math("ABSOLUTE", along[1], x=3, y=-23),
                x=4,
                y=-22,
            ),
            "False": t.vmath("SCALE", weft, t.math("SIGN", along[1], x=4, y=-24), x=4, y=-23),
            "True": t.vmath("SCALE", warp, t.math("SIGN", along[0], x=4, y=-25), x=4, y=-21),
        },
        input_type="VECTOR",
    ).outputs[0]
    random = t.node("FunctionNodeRandomValue", -3, -14, data_type="FLOAT_VECTOR").outputs[0]
    random = t.node("ShaderNodeSeparateXYZ", -2, -14, {0: random}).outputs
    # Spread in the tuft
    across = t.vmath("CROSS_PRODUCT", root_normal, grain, x=5, y=-21)
    spread = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", random["Z"], 0.5, x=4, y=-26),
        t.math("MULTIPLY", inputs["Spread"], 2.0, x=4, y=-27),
        x=5,
        y=-26,
    )
    tangent = t.vmath(
        "NORMALIZE",
        t.vmath("ADD", grain, t.vmath("SCALE", across, spread, x=6, y=-21), x=6, y=-20),
        x=7,
        y=-20,
    )
    side = t.vmath(
        "NORMALIZE", t.vmath("CROSS_PRODUCT", root_normal, tangent, x=1, y=-12), x=2, y=-12
    )
    # Mostly short threads, with a few long ones
    short = t.math("SUBTRACT", t.math("POWER", random["X"], 3.0, x=-2, y=-15), 1.0, x=-1, y=-15)
    short = t.math("MULTIPLY_ADD", short, inputs["Randomness"], 1.0, x=0, y=-15)
    out = t.math("MULTIPLY", inputs["Length"], short, x=1, y=-15)
    bend = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", random["Y"], 0.5, x=-1, y=-16),
        inputs["Randomness"],
        x=0,
        y=-16,
    )
    bend = t.math("MULTIPLY", bend, out, x=1, y=-16)

    # Gravity from world to object space
    gravity = t.node(
        "FunctionNodeTransformDirection",
        0,
        -18,
        {"Transform": to_local, "Direction": (0.0, 0.0, -1.0)},
    ).outputs[0]
    gravity = t.vmath(
        "SCALE", t.vmath("NORMALIZE", gravity, x=1, y=-18), inputs["Droop"], x=2, y=-18
    )

    # Bridges: some threads still across the tear along the grain, to the first cloth found on
    # the other side, sagging
    bridging = t.math(
        "LESS_THAN",
        t.node("FunctionNodeRandomValue", -3, -30, {"Seed": 7}, data_type="FLOAT").outputs[0],
        inputs["Share"],
        x=-2,
        y=-30,
    )
    # Landing on the faces around the tear only, faster
    landings = t.node(
        "GeometryNodeDeleteGeometry",
        -1,
        -36,
        {
            "Geometry": cut,
            "Selection": t.math("LESS_THAN", rings(t, on_tear, 6, -3, -36), 1e-6, x=-1, y=-37),
        },
        domain="FACE",
    ).outputs[0]
    roots = t.store(roots, ".cloth_tear_start", "FLOAT_VECTOR", tear["Position"], 0, -8)
    roots = t.store(roots, ".cloth_tear_grain", "FLOAT_VECTOR", grain, 1, -8)
    roots = t.store(roots, ".cloth_tear_bridging", "BOOLEAN", bridging, 1.5, -8)
    steps = 8
    bridge_in = t.node("GeometryNodeRepeatInput", 2, -8, {"Iterations": steps})
    bridge_out = t.node("GeometryNodeRepeatOutput", 2.9, -8)
    bridge_in.pair_with_output(bridge_out)
    t.connect(roots, bridge_in.inputs["Geometry"])
    # From the farthest, for the closest to be kept
    step = t.math("DIVIDE", inputs["Bridge Length"], float(steps), x=0, y=-32)
    reach = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", float(steps), bridge_in.outputs["Iteration"], x=0, y=-31),
        step,
        x=1,
        y=-31,
    )
    sample = t.vmath(
        "ADD",
        t.attribute(".cloth_tear_start", "FLOAT_VECTOR", 0, -33),
        t.vmath(
            "SCALE",
            t.attribute(".cloth_tear_grain", "FLOAT_VECTOR", 0, -34),
            reach,
            x=1,
            y=-34,
        ),
        x=2,
        y=-33,
    )
    landing = t.node(
        "GeometryNodeProximity",
        2,
        -35,
        {"Target": landings, "Sample Position": sample},
        target_element="FACES",
    ).outputs
    bridge = bridge_in.outputs["Geometry"]
    bridging = t.attribute(".cloth_tear_bridging", "BOOLEAN", 2, -36)
    bridge = t.node(
        "GeometryNodeStoreNamedAttribute",
        2.2,
        -8,
        {
            "Geometry": bridge,
            "Selection": bridging,
            "Name": ".cloth_tear_landing",
            "Value": landing["Position"],
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    landing = t.attribute(".cloth_tear_landing", "FLOAT_VECTOR", 2.4, -36)
    # On the cloth again, not just past the edge
    landed = t.math(
        "MULTIPLY",
        t.math(
            "LESS_THAN",
            t.vmath("DISTANCE", landing, sample, x=2.5, y=-37),
            t.math("MULTIPLY", step, 0.25, x=2.5, y=-38),
            x=3,
            y=-37,
        ),
        t.math("GREATER_THAN", reach, step, x=3, y=-38),
        x=3.5,
        y=-37,
    )
    landed = t.math("MULTIPLY", landed, bridging, x=4, y=-37)
    for i, (name, data_type, value) in enumerate(
        (
            (
                ".cloth_tear_far",
                "FLOAT_VECTOR",
                landing,
            ),
            (".cloth_tear_bridged", "BOOLEAN", True),
        )
    ):
        bridge = t.node(
            "GeometryNodeStoreNamedAttribute",
            2.6 + 0.1 * i,
            -8,
            {"Geometry": bridge, "Selection": landed, "Name": name, "Value": value},
            data_type=data_type,
        ).outputs[0]
    t.connect(bridge, bridge_out.inputs["Geometry"])
    bridge_out.parent = t.frame
    roots = bridge_out.outputs["Geometry"]
    bridged = t.attribute(".cloth_tear_bridged", "BOOLEAN", 3, -40)
    span = t.vmath(
        "SUBTRACT",
        t.attribute(".cloth_tear_far", "FLOAT_VECTOR", 3, -41),
        t.attribute(".cloth_tear_start", "FLOAT_VECTOR", 3, -42),
        x=4,
        y=-41,
    )
    # Sagging as a parabola through both ends
    sag = t.vmath(
        "SCALE",
        t.vmath("NORMALIZE", gravity, x=4, y=-43),
        t.math("MULTIPLY", t.vmath("LENGTH", span, x=4, y=-44), 0.3, x=5, y=-44),
        x=5,
        y=-43,
    )
    line = t.node(
        "GeometryNodeSwitch",
        6,
        -40,
        {
            "Switch": bridged,
            "False": t.vmath("SCALE", tangent, out, x=2, y=-10),
            "True": t.vmath("ADD", span, sag, x=6, y=-41),
        },
        input_type="VECTOR",
    ).outputs[0]
    curve = t.node(
        "GeometryNodeSwitch",
        6,
        -42,
        {
            "Switch": bridged,
            "False": t.vmath("ADD", t.vmath("SCALE", side, bend, x=3, y=-12), gravity, x=3, y=-16),
            "True": t.vmath("SCALE", sag, -1.0, x=6, y=-43),
        },
        input_type="VECTOR",
    ).outputs[0]
    threads = t.store(roots, ".cloth_tear_line", "FLOAT_VECTOR", line, 3, -8)
    threads = t.store(threads, ".cloth_tear_curve", "FLOAT_VECTOR", curve, 4, -8)
    threads = t.node(
        "GeometryNodeSetPosition", 5, -8, {"Geometry": threads, "Position": tear["Position"]}
    ).outputs[0]
    threads = t.store(threads, ".cloth_tear_root", "FLOAT_VECTOR", tear["Position"], 5.2, -8)
    thread = t.node("GeometryNodeCaptureAttribute", 5, -8, {"Geometry": threads})
    thread.capture_items.new("INT", "Thread")
    t.connect(t.node("GeometryNodeInputIndex", 4, -10).outputs[0], thread.inputs["Thread"])
    duplicate = t.node(
        "GeometryNodeDuplicateElements",
        6,
        -8,
        {"Geometry": thread.outputs["Geometry"], "Amount": inputs["Resolution"]},
        domain="POINT",
    ).outputs
    factor = t.math(
        "DIVIDE",
        duplicate["Duplicate Index"],
        t.math("SUBTRACT", inputs["Resolution"], 1.0, x=6, y=-11),
        x=7,
        y=-10,
    )
    offset = t.vmath(
        "ADD",
        t.vmath(
            "SCALE", t.attribute(".cloth_tear_line", "FLOAT_VECTOR", 7, -12), factor, x=8, y=-12
        ),
        t.vmath(
            "SCALE",
            t.attribute(".cloth_tear_curve", "FLOAT_VECTOR", 7, -14),
            t.math("MULTIPLY", factor, factor, x=8, y=-11),
            x=8,
            y=-14,
        ),
        x=9,
        y=-12,
    )
    threads = t.node(
        "GeometryNodeSetPosition", 9, -8, {"Geometry": duplicate["Geometry"], "Offset": offset}
    ).outputs[0]
    # Not through the cloth, staying on the side of their root, nor in the Colliders
    root = t.attribute(".cloth_tear_root", "FLOAT_VECTOR", 9, -16)
    normal = t.node("GeometryNodeInputNormal", 9, -17).outputs[0]
    for i, (surface, two_sided) in enumerate(
        (
            (cut, True),
            (
                t.node(
                    "GeometryNodeRealizeInstances",
                    9,
                    -19,
                    {
                        "Geometry": t.node(
                            "GeometryNodeCollectionInfo",
                            8,
                            -19,
                            {"Collection": inputs["Colliders"]},
                            transform_space="RELATIVE",
                        ).outputs[0]
                    },
                ).outputs[0],
                False,
            ),
        )
    ):
        y = -16 - 5 * i
        nearest, outward = (
            t.node(
                "GeometryNodeSampleNearestSurface",
                10,
                y - j,
                {"Mesh": surface, "Value": value, "Sample Position": position},
                data_type="FLOAT_VECTOR",
            ).outputs["Value"]
            for j, value in enumerate((position, normal))
        )
        outward = t.vmath("NORMALIZE", outward, x=11, y=y - 1)
        away = t.vmath("SUBTRACT", position, nearest, x=11, y=y)
        side = t.vmath("DOT_PRODUCT", away, outward, x=12, y=y)
        along = t.vmath(
            "LENGTH",
            t.vmath(
                "SUBTRACT", away, t.vmath("SCALE", outward, side, x=12, y=y - 2), x=13, y=y - 2
            ),
            x=14,
            y=y - 2,
        )
        if two_sided:
            # The root clearly off that surface, not on the cloth next to it
            root_side = t.vmath(
                "DOT_PRODUCT",
                t.vmath("SUBTRACT", root, nearest, x=11, y=y - 3),
                outward,
                x=12,
                y=y - 3,
            )
            keep = t.math("SIGN", root_side, x=13, y=y - 3)
            hit = t.math(
                "MULTIPLY",
                t.math(
                    "LESS_THAN", t.math("MULTIPLY", side, keep, x=13, y=y), COLLISION, x=14, y=y
                ),
                t.math(
                    "GREATER_THAN",
                    t.math("ABSOLUTE", root_side, x=13, y=y - 4),
                    COLLISION,
                    x=14,
                    y=y - 4,
                ),
                x=15,
                y=y,
            )
        else:
            keep = 1.0
            # Without Colliders, nothing to sample
            hit = t.math(
                "MULTIPLY",
                t.math("LESS_THAN", side, COLLISION, x=14, y=y),
                t.math(
                    "GREATER_THAN",
                    t.node(
                        "GeometryNodeAttributeDomainSize", 13, y - 4, {"Geometry": surface}
                    ).outputs["Face Count"],
                    0.0,
                    x=14,
                    y=y - 4,
                ),
                x=15,
                y=y,
            )
        hit = t.math(
            "MULTIPLY", hit, t.math("LESS_THAN", along, COLLISION, x=15, y=y - 2), x=16, y=y
        )
        threads = t.node(
            "GeometryNodeSetPosition",
            9.3 + 0.2 * i,
            -8,
            {
                "Geometry": threads,
                "Selection": hit,
                "Position": t.vmath(
                    "ADD",
                    nearest,
                    t.vmath(
                        "SCALE",
                        outward,
                        t.math("MULTIPLY", keep, COLLISION, x=15, y=y - 3),
                        x=16,
                        y=y - 3,
                    ),
                    x=17,
                    y=y - 3,
                ),
            },
        ).outputs[0]
    threads = t.node(
        "GeometryNodePointsToCurves",
        10,
        -8,
        {
            "Points": threads,
            "Curve Group ID": thread.outputs["Thread"],
            "Weight": duplicate["Duplicate Index"],
        },
    ).outputs[0]
    # Tapering to the tip
    tip = t.node("GeometryNodeSplineParameter", 11, -10).outputs["Factor"]
    radius = t.math(
        "MULTIPLY",
        inputs["Thickness"],
        t.math("MULTIPLY_ADD", tip, -0.7, 1.0, x=11, y=-11),
        x=12,
        y=-10,
    )
    profile = t.node("GeometryNodeCurvePrimitiveCircle", 12, -12, {"Resolution": 3})
    threads = t.node(
        "GeometryNodeCurveToMesh",
        13,
        -8,
        {"Curve": threads, "Profile Curve": profile.outputs[0], "Scale": radius},
    ).outputs[0]
    # As a pattern, not warning without threads
    threads = t.node(
        "GeometryNodeRemoveAttribute",
        14,
        -8,
        {"Geometry": threads, "Pattern Mode": "Wildcard", "Name": "id*"},
    )
    threads = t.store(threads.outputs[0], ".cloth_tear_thread", "BOOLEAN", True, 15, -8)

    # The threads with the material of their roots, after joining the materials of the mesh, as an
    # instance not to be subdivided by the next modifiers
    output = t.node("GeometryNodeJoinGeometry", 16, 0)
    t.connect(threads, output.inputs[0])
    t.connect(cut, output.inputs[0])
    output = t.node(
        "GeometryNodeSetMaterialIndex",
        17,
        0,
        {
            "Geometry": output.outputs[0],
            "Selection": t.attribute(".cloth_tear_thread", "BOOLEAN", 16, -2),
            "Material Index": t.attribute(".cloth_tear_material", "INT", 16, -3),
        },
    )
    separate = t.node(
        "GeometryNodeSeparateGeometry",
        18,
        0,
        {
            "Geometry": output.outputs[0],
            "Selection": t.attribute(".cloth_tear_thread", "BOOLEAN", 17, -2),
        },
        domain="FACE",
    ).outputs
    instance = t.node("GeometryNodeGeometryToInstance", 19, -1, {0: separate["Selection"]})
    output = t.node("GeometryNodeJoinGeometry", 20, 0)
    t.connect(instance.outputs[0], output.inputs[0])
    t.connect(separate["Inverted"], output.inputs[0])
    clean = remove(t, output.outputs[0], (".cloth_tear_*", ".cloth_piece_*"), 21, 0)
    t.node("NodeGroupOutput", 22, 0, {0: clean})
    t.arrange()
    return ng


def arrange_interface(ng):
    """Inputs grouped in sub panels, the advanced ones closed, Physics in its panel header"""

    def item(name, item_type):
        return next(
            x for x in ng.interface.items_tree if x.name == name and x.item_type == item_type
        )

    item("Physics", "SOCKET").is_panel_toggle = True
    for parent_name, name, closed, sockets in (
        ("Threads", "Tufts", True, ("Fibers", "Spread", "Randomness", "Droop", "Grain")),
        ("Threads", "Bridges", True, ("Share", "Bridge Length")),
        ("Physics", "Pieces", False, ("Piece Size", "Rip Out", "Push", "Lifetime")),
        ("Physics", "Released Cloth", False, ("Release", "Anchor", "Shape")),
        ("Physics", "Ripping", False, ("Reach", "Strength", "In Hand")),
        ("Physics", "Collisions", False, ("Colliders", "Floor", "Friction", "Self Collision")),
        ("Physics", "Motion", False, ("Gravity", "Drag", "Damping", "Bending", "Time Scale")),
        ("Physics", "Solver", True, ("Substeps", "Iterations")),
    ):
        parent = item(parent_name, "PANEL")
        panel = ng.interface.new_panel(name, default_closed=closed)
        ng.interface.move_to_parent(panel, parent, len(parent.interface_items))
        for socket in sockets:
            ng.interface.move_to_parent(item(socket, "SOCKET"), panel, len(panel.interface_items))


def control_transform(t, controls, control, x, y):
    """Transform of the Control at the index, relative to the mesh"""
    return t.node(
        "GeometryNodeSampleIndex",
        x,
        y,
        {
            "Geometry": controls,
            "Value": t.node("GeometryNodeInstanceTransform", x - 1, y).outputs[0],
            "Index": control,
        },
        data_type="FLOAT4X4",
        domain="INSTANCE",
    ).outputs[0]


def settle(t, geometry, selection, normal, target, inputs, x, y):
    """Geometry with the selected points moved to target without bouncing, keeping only their
    velocity along the surface, slowed by the Friction"""
    # Sampled once, for the previous position and the position
    captured = t.node("GeometryNodeCaptureAttribute", x, y, {"Geometry": geometry})
    for data_type, name, value in (
        ("FLOAT", "Hit", selection),
        ("VECTOR", "Normal", normal),
        ("VECTOR", "Target", target),
    ):
        captured.capture_items.new(data_type, name)
        t.connect(value, captured.inputs[name])
    geometry, selection, normal, target = (
        captured.outputs[x] for x in ("Geometry", "Hit", "Normal", "Target")
    )
    # Previous position first, from the velocity before moving
    velocity = t.vmath(
        "SUBTRACT",
        t.node("GeometryNodeInputPosition", x, y - 1).outputs[0],
        t.attribute(".cloth_piece_prev", "FLOAT_VECTOR", x, y - 2),
        x=x + 1,
        y=y - 1,
    )
    across = t.vmath("DOT_PRODUCT", velocity, normal, x=x + 1, y=y - 3)
    along = t.vmath(
        "SUBTRACT",
        velocity,
        t.vmath("SCALE", normal, across, x=x + 2, y=y - 3),
        x=x + 3,
        y=y - 1,
    )
    # Coulomb friction, slowing the sliding by the Friction times the speed against the surface
    slowdown = t.math(
        "DIVIDE",
        t.math(
            "MULTIPLY",
            inputs["Friction"],
            t.math("ABSOLUTE", across, x=x + 2, y=y - 4),
            x=x + 3,
            y=y - 4,
        ),
        t.math("MAXIMUM", t.vmath("LENGTH", along, x=x + 3, y=y - 5), 1e-9, x=x + 4, y=y - 5),
        x=x + 4,
        y=y - 4,
    )
    along = t.vmath(
        "SCALE",
        along,
        t.math("SUBTRACT", 1.0, slowdown, x=x + 5, y=y - 4, clamp=True),
        x=x + 4,
        y=y - 1,
    )
    geometry = t.node(
        "GeometryNodeStoreNamedAttribute",
        x + 5,
        y,
        {
            "Geometry": geometry,
            "Selection": selection,
            "Name": ".cloth_piece_prev",
            "Value": t.vmath("SUBTRACT", target, along, x=x + 5, y=y - 1),
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    return t.node(
        "GeometryNodeSetPosition",
        x + 6,
        y,
        {"Geometry": geometry, "Selection": selection, "Position": target},
    ).outputs[0]


def bend_partners(t, x, y):
    """Vertices across the edges after and before the corner, from the vertex before and the one
    after it, as bending pairs, or the vertex of the corner on the boundary"""
    corner = t.node("GeometryNodeInputIndex", x, y).outputs[0]
    own = t.node("GeometryNodeVertexOfCorner", x + 4, y, {0: corner}).outputs[0]
    partners = []
    for i, (before, after) in enumerate(((1, 2), (-2, -1))):
        y_i = y - 3 * i
        start = t.node(
            "GeometryNodeOffsetCornerInFace",
            x + 1,
            y_i,
            {"Corner Index": corner, "Offset": before},
        ).outputs[0]
        edge = t.node("GeometryNodeEdgesOfCorner", x + 2, y_i, {"Corner Index": start}).outputs[
            "Next Edge Index"
        ]
        sides = [
            t.node(
                "GeometryNodeCornersOfEdge",
                x + 3,
                y_i - j,
                {"Edge Index": edge, "Sort Index": j},
            ).outputs
            for j in range(2)
        ]
        first, second = (side["Corner Index"] for side in sides)
        # The corner of the face on the other side of the edge
        other = t.math(
            "MULTIPLY_ADD",
            t.math("SUBTRACT", second, first, x=x + 4, y=y_i - 1),
            t.math("COMPARE", first, start, 0.5, x=x + 4, y=y_i - 2),
            first,
            x=x + 5,
            y=y_i - 1,
        )
        partner = t.node(
            "GeometryNodeVertexOfCorner",
            x + 7,
            y_i,
            {
                0: t.node(
                    "GeometryNodeOffsetCornerInFace",
                    x + 6,
                    y_i,
                    {"Corner Index": other, "Offset": after},
                ).outputs[0]
            },
        ).outputs[0]
        partners.append(
            t.node(
                "GeometryNodeSwitch",
                x + 8,
                y_i,
                {
                    "Switch": t.math("COMPARE", sides[0]["Total"], 2.0, 0.5, x=x + 7, y=y_i - 1),
                    "False": own,
                    "True": partner,
                },
                input_type="INT",
            ).outputs[0]
        )
    return partners


def correction(t, geometry, constraints, free, position, x, y):
    """Geometry with the free points moved by one Jacobi XPBD step towards the rest lengths of the
    (vertex, other position, rest length, share, compliance over the step squared or None)
    constraints of each corner: all the way towards a pinned point, half towards a free one, less
    the more compliant"""
    total = None
    for i, (vertex, other, rest_length, share, compliance) in enumerate(constraints):
        y_i = y - 3 * i
        weight = t.math(
            "ADD",
            t.node(
                "GeometryNodeFieldAtIndex",
                x,
                y_i - 3,
                {"Value": free, "Index": vertex},
                data_type="FLOAT",
                domain="POINT",
            ).outputs[0],
            1.0,
            x=x + 1,
            y=y_i - 3,
        )
        if compliance is not None:
            weight = t.math("ADD", weight, compliance, x=x + 2, y=y_i - 3)
        towards = t.vmath("SUBTRACT", other, position, x=x, y=y_i)
        current = t.math(
            "MAXIMUM", t.vmath("LENGTH", towards, x=x, y=y_i - 1), 1e-9, x=x + 1, y=y_i - 1
        )
        stretch = t.math(
            "MULTIPLY",
            t.math(
                "SUBTRACT",
                1.0,
                t.math("DIVIDE", rest_length, current, x=x + 1, y=y_i - 2),
                x=x + 2,
                y=y_i - 2,
            ),
            t.math("DIVIDE", share, weight, x=x + 3, y=y_i - 3),
            x=x + 3,
            y=y_i - 2,
        )
        term = t.vmath("SCALE", towards, stretch, x=x + 4, y=y_i)
        total = term if total is None else t.vmath("ADD", total, term, x=x + 5, y=y_i)
    return t.node(
        "GeometryNodeSetPosition",
        x + 7,
        y,
        {
            "Geometry": geometry,
            "Selection": free,
            "Offset": t.node(
                "GeometryNodeFieldOnDomain",
                x + 6,
                y,
                {"Value": total},
                data_type="FLOAT_VECTOR",
                domain="CORNER",
            ).outputs[0],
        },
    ).outputs[0]


def couple_groups(t, geometry, free, x, y):
    """Geometry with the groups of attached points and released cloth points, fixed in a frame"""
    index = t.node("GeometryNodeInputIndex", x, y - 1).outputs[0]
    link = t.attribute(".cloth_tear_link", "INT", x, y - 2)
    group = t.node(
        "GeometryNodeSwitch",
        x + 1,
        y - 1,
        {
            "Switch": t.math("GREATER_THAN", link, -0.5, x=x + 1, y=y - 2),
            "False": index,
            "True": link,
        },
        input_type="INT",
    ).outputs[0]
    geometry = t.store(geometry, ".cloth_tear_group", "INT", group, x + 2, y)
    group = t.attribute(".cloth_tear_group", "INT", x + 2, y - 1)
    fixed = t.math("SUBTRACT", 1.0, free, x=x + 2, y=y - 4)
    count, fixed_count, fixed_total = (
        t.node(
            "GeometryNodeAccumulateField",
            x + 3,
            y - 1 - i,
            {"Value": value, "Group ID": group},
            data_type=data_type,
            domain="POINT",
        ).outputs["Total"]
        for i, (value, data_type) in enumerate(
            (
                (1.0, "FLOAT"),
                (fixed, "FLOAT"),
                (
                    t.vmath(
                        "SCALE",
                        t.attribute(".cloth_tear_target", "FLOAT_VECTOR", x + 2, y - 5),
                        fixed,
                        x=x + 3,
                        y=y - 5,
                    ),
                    "FLOAT_VECTOR",
                ),
            )
        )
    )
    held = t.vmath(
        "SCALE",
        fixed_total,
        t.math(
            "DIVIDE", 1.0, t.math("MAXIMUM", fixed_count, 1.0, x=x + 4, y=y - 3), x=x + 4, y=y - 4
        ),
        x=x + 5,
        y=y - 3,
    )
    geometry = t.store(geometry, ".cloth_tear_count", "FLOAT", count, x + 4, y)
    geometry = t.store(
        geometry,
        ".cloth_tear_fixed",
        "FLOAT",
        t.math("GREATER_THAN", fixed_count, 0.0, x=x + 4, y=y - 2),
        x + 5,
        y,
    )
    return t.store(geometry, ".cloth_tear_held", "FLOAT_VECTOR", held, x + 6, y)


def couple(t, geometry, free, x, y):
    """Geometry with the attached points and their released cloth point together"""
    count = t.attribute(".cloth_tear_count", "FLOAT", x, y - 1)
    total = t.node(
        "GeometryNodeAccumulateField",
        x + 1,
        y - 1,
        {
            "Value": t.node("GeometryNodeInputPosition", x, y - 2).outputs[0],
            "Group ID": t.attribute(".cloth_tear_group", "INT", x, y - 3),
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs["Total"]
    target = t.node(
        "GeometryNodeSwitch",
        x + 2,
        y,
        {
            "Switch": t.math(
                "GREATER_THAN",
                t.attribute(".cloth_tear_fixed", "FLOAT", x + 1, y - 4),
                0.5,
                x=x + 2,
                y=y - 4,
            ),
            "False": t.vmath(
                "SCALE", total, t.math("DIVIDE", 1.0, count, x=x + 1, y=y - 2), x=x + 2, y=y - 2
            ),
            "True": t.attribute(".cloth_tear_held", "FLOAT_VECTOR", x + 1, y - 5),
        },
        input_type="VECTOR",
    ).outputs[0]
    return t.node(
        "GeometryNodeSetPosition",
        x + 3,
        y,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "MULTIPLY",
                free,
                t.math("GREATER_THAN", count, 1.5, x=x + 2, y=y - 6),
                x=x + 3,
                y=y - 6,
            ),
            "Position": target,
        },
    ).outputs[0]


def rings(t, value, count, x, y):
    """The value spread to the points around, as many rings of faces away"""
    for i in range(count):
        value = t.node(
            "GeometryNodeFieldOnDomain",
            x + i,
            y,
            {
                "Value": t.node(
                    "GeometryNodeFieldOnDomain",
                    x + i,
                    y - 1,
                    {"Value": value},
                    data_type="FLOAT",
                    domain="POINT",
                ).outputs[0]
            },
            data_type="FLOAT",
            domain="FACE",
        ).outputs[0]
    return value


def remove(t, geometry, names, x, y):
    """Geometry without the named attributes, the patterns with a * not warning when missing"""
    for i, name in enumerate(names):
        geometry = t.node(
            "GeometryNodeRemoveAttribute",
            x + i * 0.1,
            y,
            {
                "Geometry": geometry,
                "Pattern Mode": "Wildcard" if "*" in name else "Exact",
                "Name": name,
            },
        ).outputs[0]
    return geometry


def border(t, mesh, x, y):
    """Border edges of the mesh between points on the tear, in the .cloth_tear_moved attribute"""
    faces = t.node("GeometryNodeInputMeshEdgeNeighbors", x, y).outputs["Face Count"]
    selection = t.math(
        "MULTIPLY",
        t.math("COMPARE", faces, 1.0, 0.5, x=x + 1, y=y),
        t.math(
            "GREATER_THAN",
            t.attribute(".cloth_tear_moved", "FLOAT", x, y - 1),
            0.75,
            x=x + 1,
            y=y - 1,
        ),
        x=x + 2,
        y=y,
    )
    return t.node(
        "GeometryNodeDeleteGeometry",
        x + 3,
        y,
        {"Geometry": mesh, "Selection": t.math("LESS_THAN", selection, 0.5, x=x + 2, y=y - 1)},
        domain="EDGE",
    ).outputs[0]


def build_physics(t, inputs, geometry, controls, inside, to_world, to_local, index):
    """Cloth without the torn pieces and its tear, with the pieces simulated in world space"""
    position = t.node("GeometryNodeInputPosition", -4, -3).outputs[0]
    edge_ends = t.node("GeometryNodeInputMeshEdgeVertices", -4, -5).outputs
    edge_length = t.vmath("DISTANCE", edge_ends["Position 1"], edge_ends["Position 2"], x=-3, y=-5)

    t.section("Pulls", row=True)
    # Distance from the closest sphere of the Pulls, with the index of the Pull
    pulls = t.node(
        "GeometryNodeCollectionInfo",
        -6,
        2,
        {"Collection": inputs["Pulls"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    pull_count = t.node(
        "GeometryNodeAttributeDomainSize", -6, 1, {"Geometry": pulls}, component="INSTANCES"
    ).outputs["Instance Count"]
    pull_in = t.node("GeometryNodeRepeatInput", -5, 0, {"Iterations": pull_count})
    pull_out = t.node("GeometryNodeRepeatOutput", 0, 0)
    pull_in.pair_with_output(pull_out)
    t.connect(
        t.store(geometry, ".cloth_tear_pull", "FLOAT", 1e9, -6, 0), pull_in.inputs["Geometry"]
    )
    pull = pull_in.outputs["Iteration"]
    transform = control_transform(t, pulls, pull, -4, -2)
    local = t.node(
        "FunctionNodeTransformPoint",
        -2,
        -2,
        {
            "Vector": position,
            "Transform": t.node("FunctionNodeInvertMatrix", -3, -2, {0: transform}).outputs[0],
        },
    ).outputs[0]
    # In the units of the mesh, by the average scale of the Pull
    scale = t.node("FunctionNodeSeparateTransform", -3, -3, {0: transform}).outputs["Scale"]
    distance = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", t.vmath("LENGTH", local, x=-1, y=-2), 1.0, x=0, y=-2),
        t.vmath("DOT_PRODUCT", scale, (1 / 3, 1 / 3, 1 / 3), x=-2, y=-3),
        x=1,
        y=-2,
    )
    closer = t.math(
        "LESS_THAN", distance, t.attribute(".cloth_tear_pull", "FLOAT", 0, -4), x=1, y=-4
    )
    mesh = pull_in.outputs["Geometry"]
    for i, (name, data_type, value) in enumerate(
        ((".cloth_tear_puller", "INT", pull), (".cloth_tear_pull", "FLOAT", distance))
    ):
        mesh = t.node(
            "GeometryNodeStoreNamedAttribute",
            -2 + i,
            0,
            {"Geometry": mesh, "Selection": closer, "Name": name, "Value": value},
            data_type=data_type,
        ).outputs[0]
    t.connect(mesh, pull_out.inputs["Geometry"])
    pull_out.parent = t.frame
    mesh = pull_out.outputs["Geometry"]

    t.section("Pieces", row=True)
    # Pieces from the cells around the rest position, torn once most of their faces are inside
    rest = t.node(
        "GeometryNodeInputNamedAttribute",
        -3,
        -2,
        {"Name": "rest_position"},
        data_type="FLOAT_VECTOR",
    ).outputs
    rest = t.node(
        "GeometryNodeSwitch",
        -2,
        -2,
        {"Switch": rest["Exists"], "False": position, "True": rest["Attribute"]},
        input_type="VECTOR",
    ).outputs[0]
    cells = t.math("DIVIDE", 1.0, inputs["Piece Size"], x=-2, y=-3)
    cell = t.node(
        "ShaderNodeTexVoronoi", -1, -2, {"Vector": rest, "Scale": cells}, voronoi_dimensions="3D"
    ).outputs["Color"]
    cell = t.node("FunctionNodeHashValue", 0, -2, {"Value": cell}, data_type="RGBA").outputs[0]
    # Once, and only on the faces that may tear, closer than two pieces to the Controls
    near = t.math(
        "LESS_THAN",
        t.attribute(".cloth_tear_distance", "FLOAT", -1, -7),
        t.math("MULTIPLY", inputs["Piece Size"], 2.0, x=-1, y=-8),
        x=0,
        y=-7,
    )
    mesh = t.node(
        "GeometryNodeStoreNamedAttribute",
        1,
        0,
        {"Geometry": mesh, "Selection": near, "Name": ".cloth_tear_cell", "Value": cell},
        data_type="INT",
        domain="FACE",
    ).outputs[0]
    cell = t.attribute(".cloth_tear_cell", "INT", 1, -2)
    touched = t.node(
        "GeometryNodeFieldOnDomain", -1, -4, {"Value": inside}, data_type="FLOAT", domain="POINT"
    ).outputs[0]
    touched, faces = (
        t.node(
            "GeometryNodeAccumulateField",
            1,
            -3 - i,
            {"Value": value, "Group ID": cell},
            data_type="FLOAT",
            domain="FACE",
        ).outputs["Total"]
        for i, value in enumerate((t.math("GREATER_THAN", touched, 0.0, x=0, y=-4), 1.0))
    )
    touched = t.math("GREATER_THAN", t.math("DIVIDE", touched, faces, x=2, y=-4), 0.5, x=3, y=-3)
    random = t.node("FunctionNodeRandomValue", 1, -5, {"ID": cell}, data_type="FLOAT").outputs[0]
    # Hanging from about half of their border
    hinge = t.node(
        "ShaderNodeTexNoise",
        1,
        -6,
        {"Vector": rest, "Scale": t.math("MULTIPLY", cells, 2.0, x=0, y=-6)},
        noise_dimensions="3D",
    ).outputs["Fac"]

    t.section("Simulation", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    sim_in = t.node("GeometryNodeSimulationInput", 1, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 30, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("GEOMETRY", "Pieces")
    sim_out.state_items.new("GEOMETRY", "Cloth")
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=2, y=-2)
    dt = t.math("MULTIPLY", dt, inputs["Time Scale"], x=2.5, y=-2)
    # Nothing torn until the Start Frame
    state, pieces, cloth_state = (
        t.node(
            "GeometryNodeSwitch",
            2,
            -i,
            {"Switch": started, "True": sim_in.outputs[name]},
            input_type="GEOMETRY",
        ).outputs[0]
        for i, name in enumerate(("Geometry", "Pieces", "Cloth"))
    )
    was, ripped = (
        t.node(
            "GeometryNodeSampleIndex",
            3,
            -3 - i,
            {"Geometry": state, "Value": t.attribute(name, "FLOAT", 2, -4 - i), "Index": index},
            data_type="FLOAT",
            domain="POINT",
        ).outputs[0]
        for i, name in enumerate(("torn", "ripped"))
    )
    # Touched by the Controls, or ripped by the Pulls on the previous frame
    torn = t.math(
        "MAXIMUM",
        t.math("MAXIMUM", was, t.math("MULTIPLY", touched, started, x=3, y=-5), x=4, y=-4),
        ripped,
        x=4,
        y=-3,
    )
    island = t.node("GeometryNodeInputMeshIsland", 3, -6).outputs["Island Index"]
    mesh = t.store(mesh, ".cloth_tear_island", "INT", island, 3, 0, domain="FACE")
    anchor = t.math("GREATER_THAN", inputs["Anchor"], 0.5, x=2, y=-6)
    mesh = t.store(mesh, ".cloth_tear_anchor", "FLOAT", anchor, 3.5, 0)
    # The cloth around the tear simulated, from where it was on the previous frame
    was_released, simulated, simulated_prev, was_grab, was_grabber, was_offset, was_grip = (
        t.node(
            "GeometryNodeSampleIndex",
            6,
            -14 - i,
            {"Geometry": cloth_state, "Value": value, "Index": index},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
        for i, (value, data_type) in enumerate(
            (
                (t.attribute("influence", "FLOAT", 5, -14), "FLOAT"),
                (position, "FLOAT_VECTOR"),
                (t.attribute("prev", "FLOAT_VECTOR", 5, -16), "FLOAT_VECTOR"),
                (t.attribute("grab", "FLOAT", 5, -17), "FLOAT"),
                (t.attribute("grabber", "INT", 5, -18), "INT"),
                (t.attribute("offset", "FLOAT_VECTOR", 5, -19), "FLOAT_VECTOR"),
                (t.attribute("grip", "FLOAT", 5, -20), "FLOAT"),
            )
        )
    )
    # Grabbed by the Pulls on the first simulated frame, in their space, or as before
    grabbing = t.math(
        "COMPARE",
        frame,
        t.math("ADD", inputs["Start Frame"], 1.0, x=1, y=-21),
        0.5,
        x=2,
        y=-21,
    )
    puller = t.attribute(".cloth_tear_puller", "INT", 1, -22)
    offset = t.node(
        "FunctionNodeTransformPoint",
        3,
        -23,
        {
            "Vector": position,
            "Transform": t.node(
                "FunctionNodeInvertMatrix",
                2,
                -23,
                {0: control_transform(t, pulls, puller, 1, -23)},
            ).outputs[0],
        },
    ).outputs[0]
    for i, (name, data_type, before, now) in enumerate(
        (
            (
                ".cloth_tear_grab",
                "FLOAT",
                was_grab,
                t.math(
                    "LESS_THAN", t.attribute(".cloth_tear_pull", "FLOAT", 2, -24), 0.0, x=3, y=-24
                ),
            ),
            (".cloth_tear_grabber", "INT", was_grabber, puller),
            (".cloth_tear_offset", "FLOAT_VECTOR", was_offset, offset),
            (
                ".cloth_tear_grip",
                "FLOAT",
                was_grip,
                t.attribute(".cloth_tear_pull", "FLOAT", 3, -25),
            ),
        )
    ):
        mesh = t.store(
            mesh,
            name,
            data_type,
            t.node(
                "GeometryNodeSwitch",
                4,
                -21 - i,
                {"Switch": grabbing, "False": before, "True": now},
                input_type={"FLOAT_VECTOR": "VECTOR"}.get(data_type, data_type),
            ).outputs[0],
            3.6 + 0.1 * i,
            0,
        )
    # Held by the body, never simulated
    mesh = t.store(
        mesh,
        ".cloth_tear_held",
        "FLOAT",
        t.math("LESS_THAN", was_released, 1e-6, x=3, y=-25),
        3.9,
        0,
    )
    mesh = t.store(mesh, ".cloth_tear_torn", "FLOAT", torn, 4, 0, domain="FACE")
    mesh = t.store(mesh, ".cloth_tear_ripped", "FLOAT", ripped, 4.1, 0, domain="FACE")
    # The parts cut off from the top of their island fall too
    torn = t.attribute(".cloth_tear_torn", "FLOAT", 4, -5)
    height = t.node(
        "FunctionNodeTransformPoint", 3, -7, {"Vector": position, "Transform": to_world}
    ).outputs[0]
    height = t.node("ShaderNodeSeparateXYZ", 4, -7, {0: height}).outputs["Z"]
    parts = t.store(mesh, ".cloth_tear_height", "FLOAT", height, 5, -6, domain="FACE")
    parts = t.store(parts, ".cloth_tear_face", "INT", index, 6, -6, domain="FACE")
    parts = t.node(
        "GeometryNodeDeleteGeometry",
        7,
        -6,
        {"Geometry": parts, "Selection": t.math("GREATER_THAN", torn, 0.5, x=6, y=-7)},
        domain="FACE",
    ).outputs[0]
    part = t.node("GeometryNodeInputMeshIsland", 7, -8).outputs["Island Index"]
    parts = t.store(parts, ".cloth_tear_part", "INT", part, 8, -6, domain="FACE")
    island = t.attribute(".cloth_tear_island", "INT", 8, -9)
    parts = t.node(
        "GeometryNodeSortElements",
        9,
        -6,
        {
            "Geometry": parts,
            "Group ID": island,
            "Sort Weight": t.math(
                "MULTIPLY", t.attribute(".cloth_tear_height", "FLOAT", 8, -10), -1.0, x=9, y=-10
            ),
        },
        domain="FACE",
    ).outputs[0]
    # Supported when reaching the Anchor, or without it on their island the top of the island,
    # the height of its first face
    first = t.node(
        "GeometryNodeAccumulateField",
        10,
        -8,
        {"Value": 1.0, "Group ID": island},
        data_type="FLOAT",
        domain="FACE",
    ).outputs["Leading"]
    height = t.attribute(".cloth_tear_height", "FLOAT", 10, -9)
    top = t.node(
        "GeometryNodeAccumulateField",
        11,
        -8,
        {
            "Value": t.math(
                "MULTIPLY", height, t.math("COMPARE", first, 1.0, 0.5, x=11, y=-9), x=12, y=-9
            ),
            "Group ID": island,
        },
        data_type="FLOAT",
        domain="FACE",
    ).outputs["Total"]
    at_top = t.math(
        "GREATER_THAN", height, t.math("SUBTRACT", top, SUPPORT, x=12, y=-10), x=13, y=-10
    )
    # As a float, for the faces with any anchored point
    anchored = t.math(
        "GREATER_THAN", t.attribute(".cloth_tear_anchor", "FLOAT", 12, -12), 0.0, x=13, y=-12
    )
    part = t.attribute(".cloth_tear_part", "INT", 12, -11)
    grabbed, held = (
        t.math("GREATER_THAN", t.attribute(name, "FLOAT", 12, -13 - i), 0.0, x=13, y=-13 - i)
        for i, name in enumerate((".cloth_tear_grab", ".cloth_tear_held"))
    )
    part_top, part_anchored, island_anchored, part_grabbed, part_held = (
        t.node(
            "GeometryNodeAccumulateField",
            14,
            -9 - i,
            {"Value": value, "Group ID": group},
            data_type="FLOAT",
            domain="FACE",
        ).outputs["Total"]
        for i, (value, group) in enumerate(
            (
                (at_top, part),
                (anchored, part),
                (anchored, island),
                (grabbed, part),
                (held, part),
            )
        )
    )
    supported = t.node(
        "GeometryNodeSwitch",
        15,
        -8,
        {
            "Switch": t.math("GREATER_THAN", island_anchored, 0.0, x=15, y=-11),
            "False": part_top,
            "True": part_anchored,
        },
        input_type="FLOAT",
    ).outputs[0]
    # The parts grabbed by the Pulls ripped off once not held by the body anymore
    supported = t.node(
        "GeometryNodeSwitch",
        15.5,
        -8,
        {
            "Switch": t.math("GREATER_THAN", part_grabbed, 0.0, x=15, y=-13),
            "False": supported,
            "True": part_held,
        },
        input_type="FLOAT",
    ).outputs[0]
    loose = t.math("LESS_THAN", supported, 0.5, x=14, y=-8)
    parts = t.store(parts, ".cloth_piece_loose", "FLOAT", loose, 10, -6, domain="FACE")
    # Back in the order of the remaining faces
    parts = t.node(
        "GeometryNodeSortElements",
        11,
        -6,
        {"Geometry": parts, "Sort Weight": t.attribute(".cloth_tear_face", "INT", 11, -7)},
        domain="FACE",
    ).outputs[0]
    kept = t.math("SUBTRACT", 1.0, torn, x=5, y=-10)
    rank = t.node(
        "GeometryNodeAccumulateField", 6, -10, {"Value": kept}, data_type="FLOAT", domain="FACE"
    ).outputs["Trailing"]
    loose = t.node(
        "GeometryNodeSampleIndex",
        12,
        -6,
        {
            "Geometry": parts,
            "Value": t.attribute(".cloth_piece_loose", "FLOAT", 11, -8),
            "Index": rank,
        },
        data_type="FLOAT",
        domain="FACE",
    ).outputs[0]
    loose = t.math("MULTIPLY", loose, kept, x=9, y=-8)
    # Only computed on the frames tearing more faces
    tearing = t.node(
        "GeometryNodeAttributeStatistic",
        8,
        -11,
        {"Geometry": mesh, "Attribute": t.math("SUBTRACT", torn, was, x=7, y=-11)},
        data_type="FLOAT",
        domain="FACE",
    ).outputs["Sum"]
    loose = t.node(
        "GeometryNodeSwitch",
        10,
        -8,
        {"Switch": t.math("GREATER_THAN", tearing, 0.0, x=9, y=-11), "False": 0.0, "True": loose},
        input_type="FLOAT",
    ).outputs[0]
    mesh = t.store(mesh, ".cloth_piece_loose", "FLOAT", loose, 5, 0, domain="FACE")
    mesh = t.store(
        mesh,
        ".cloth_tear_torn",
        "FLOAT",
        t.math("MAXIMUM", torn, t.attribute(".cloth_piece_loose", "FLOAT", 5, -11), x=6, y=-11),
        6,
        0,
        domain="FACE",
    )
    mesh = t.store(
        mesh,
        ".cloth_tear_new",
        "FLOAT",
        t.math("SUBTRACT", t.attribute(".cloth_tear_torn", "FLOAT", 6, -12), was, x=7, y=-12),
        7,
        0,
        domain="FACE",
    )
    mesh = t.store(mesh, ".cloth_piece_random", "FLOAT", random, 6, 0, domain="FACE")
    mesh = t.store(mesh, ".cloth_piece_orig", "INT", index, 7, 0)
    posed = t.node(
        "FunctionNodeTransformPoint", 7, -2, {"Vector": position, "Transform": to_world}
    ).outputs[0]
    mesh = t.store(mesh, ".cloth_tear_posed", "FLOAT_VECTOR", posed, 7.5, 0)
    # How much it is simulated, smoothly less away from the jagged spheres of the Controls and the
    # spheres of the Pulls, from the Start Frame, never less than before
    near = [
        t.math(
            "MULTIPLY",
            t.node(
                "ShaderNodeMapRange",
                7,
                -18 - 3 * i,
                {
                    0: t.attribute(name, "FLOAT", 6, -18 - 3 * i),
                    2: t.math("MAXIMUM", reach, 1e-6, x=6, y=-19 - 3 * i),
                    3: 1.0,
                    4: 0.0,
                },
                interpolation_type="SMOOTHSTEP",
            ).outputs[0],
            t.math("GREATER_THAN", reach, 0.0, x=7, y=-20 - 3 * i),
            x=8,
            y=-18 - 3 * i,
        )
        for i, (name, reach) in enumerate(
            ((".cloth_tear_distance", inputs["Release"]), (".cloth_tear_pull", inputs["Reach"]))
        )
    ]
    near = t.math("MULTIPLY", t.math("MAXIMUM", *near, x=8.5, y=-18), started, x=8.7, y=-18)
    released = t.math("MAXIMUM", was_released, near, x=9, y=-17)
    mesh = t.store(mesh, ".cloth_tear_released", "FLOAT", released, 7.7, 0)
    mesh = t.store(mesh, ".cloth_tear_was", "FLOAT", was_released, 7.8, 0)
    mesh = t.store(mesh, ".cloth_tear_simulated", "FLOAT_VECTOR", simulated, 7.9, 0)
    mesh = t.store(mesh, ".cloth_tear_simulated_prev", "FLOAT_VECTOR", simulated_prev, 7.95, 0)
    world = t.node(
        "GeometryNodeSwitch",
        8,
        -2,
        {
            "Switch": t.math(
                "GREATER_THAN", t.attribute(".cloth_tear_was", "FLOAT", 7, -3), 0.0, x=8, y=-3
            ),
            "False": t.attribute(".cloth_tear_posed", "FLOAT_VECTOR", 7, -4),
            "True": t.attribute(".cloth_tear_simulated", "FLOAT_VECTOR", 7, -5),
        },
        input_type="VECTOR",
    ).outputs[0]
    # Where the Pull holding it is now, gathered to its center as a fist as it pulls away, to
    # less than a third two radii away
    holding = control_transform(t, pulls, t.attribute(".cloth_tear_grabber", "INT", 4, -7), 5, -7)
    offset = t.attribute(".cloth_tear_offset", "FLOAT_VECTOR", 4, -6)
    away = t.vmath(
        "DISTANCE",
        t.node(
            "FunctionNodeTransformPoint", 6, -6, {"Vector": offset, "Transform": holding}
        ).outputs[0],
        position,
        x=7,
        y=-5,
    )
    reach = t.vmath(
        "DOT_PRODUCT",
        t.node("FunctionNodeSeparateTransform", 6, -8, {0: holding}).outputs["Scale"],
        (2 / 3, 2 / 3, 2 / 3),
        x=7,
        y=-8,
    )
    gather = t.node("ShaderNodeMapRange", 8, -7, {0: away, 2: reach, 3: 1.0, 4: 0.3}).outputs[0]
    # The rim kept on the cloth around, the inside gathered and crumpled in folds, the most
    # halfway out
    radius = t.vmath("LENGTH", offset, x=5, y=-10)
    rim = t.node(
        "ShaderNodeMapRange", 6, -10, {0: radius, 1: 0.5, 2: 1.0}, interpolation_type="SMOOTHSTEP"
    ).outputs[0]
    gather = t.math(
        "MULTIPLY_ADD", t.math("SUBTRACT", 1.0, gather, x=7, y=-11), rim, gather, x=8, y=-11
    )
    folds = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", 1.0, gather, x=7, y=-12),
        t.math("MULTIPLY", radius, t.math("SUBTRACT", 1.0, radius, x=6, y=-13), x=7, y=-13),
        x=8,
        y=-12,
    )
    # Pleats along the normal of the cloth, around the center as gathered fabric, their height in
    # Pull radii
    pleats = t.math(
        "MULTIPLY",
        t.math(
            "SUBTRACT",
            t.node(
                "ShaderNodeTexNoise",
                5,
                -9,
                {
                    "Vector": t.vmath("NORMALIZE", offset, x=4, y=-9),
                    "Scale": CRUMPLE_SCALE,
                    "Detail": 0.0,
                },
                noise_dimensions="3D",
            ).outputs["Fac"],
            0.5,
            x=6,
            y=-9,
        ),
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", folds, 8.0 * CRUMPLE, x=7, y=-13),
            t.math("MULTIPLY", reach, 0.5, x=7, y=-14),
            x=8,
            y=-13,
        ),
        x=8,
        y=-9,
    )
    crumple = t.vmath(
        "SCALE",
        t.node("GeometryNodeInputNormal", 7, -10).outputs[0],
        pleats,
        x=9,
        y=-9,
    )
    held = t.node(
        "FunctionNodeTransformPoint",
        9,
        -6,
        {
            "Vector": t.vmath(
                "ADD",
                t.node(
                    "FunctionNodeTransformPoint",
                    8,
                    -6,
                    {
                        "Vector": t.vmath("SCALE", offset, gather, x=7, y=-7),
                        "Transform": holding,
                    },
                ).outputs[0],
                crumple,
                x=8.5,
                y=-6,
            ),
            "Transform": to_world,
        },
    ).outputs[0]
    world = t.node(
        "GeometryNodeSwitch",
        9,
        -2,
        {
            "Switch": t.math(
                "GREATER_THAN", t.attribute(".cloth_tear_grab", "FLOAT", 8, -7), 0.5, x=9, y=-7
            ),
            "False": world,
            "True": held,
        },
        input_type="VECTOR",
    ).outputs[0]
    mesh = t.store(mesh, ".cloth_tear_world", "FLOAT_VECTOR", world, 8, 0)
    # Pinned where a face is not torn, as a float for any face
    attached = t.math("LESS_THAN", t.attribute(".cloth_tear_torn", "FLOAT", 8, -3), 1.0, x=9, y=-3)
    pinned = t.math("MULTIPLY", attached, t.math("GREATER_THAN", hinge, 0.5, x=9, y=-4), x=10, y=-3)
    # Only on the points of the torn faces
    mesh = t.node(
        "GeometryNodeStoreNamedAttribute",
        10,
        0,
        {
            "Geometry": mesh,
            "Selection": t.math(
                "GREATER_THAN", t.attribute(".cloth_tear_torn", "FLOAT", 9, -5), 0.0, x=10, y=-5
            ),
            "Name": ".cloth_tear_pinned",
            "Value": pinned,
        },
        data_type="FLOAT",
    ).outputs[0]
    zone = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", t.attribute(".cloth_tear_released", "FLOAT", 9, 3), 0.0, x=10, y=3),
        t.math("LESS_THAN", t.attribute(".cloth_tear_torn", "FLOAT", 9, 4), 0.5, x=10, y=4),
        x=11,
        y=3,
    )
    mesh = t.store(mesh, ".cloth_tear_zone", "FLOAT", zone, 10.5, 0, domain="FACE")
    faces = t.node("GeometryNodeAttributeDomainSize", 10, 2, {"Geometry": mesh}).outputs
    state = t.node("GeometryNodePoints", 11, 2, {"Count": faces["Face Count"]}).outputs[0]
    state = t.store(
        state,
        "torn",
        "FLOAT",
        t.node(
            "GeometryNodeSampleIndex",
            11,
            3,
            {
                "Geometry": mesh,
                "Value": t.attribute(".cloth_tear_torn", "FLOAT", 10, 3),
                "Index": index,
            },
            data_type="FLOAT",
            domain="FACE",
        ).outputs[0],
        12,
        2,
    )

    # New pieces from the faces torn on this frame, apart from the other cells
    spawned = t.node(
        "GeometryNodeDeleteGeometry",
        11,
        0,
        {
            "Geometry": mesh,
            # The ripped faces opening up, not falling
            "Selection": t.math(
                "MAXIMUM",
                t.math(
                    "LESS_THAN", t.attribute(".cloth_tear_new", "FLOAT", 10, -1), 0.5, x=11, y=-1
                ),
                t.attribute(".cloth_tear_ripped", "FLOAT", 10, -2),
                x=11.5,
                y=-1,
            ),
        },
        domain="FACE",
    ).outputs[0]
    face_random = t.attribute(".cloth_piece_random", "FLOAT", 11, -3)
    means = [
        t.node(
            "GeometryNodeFieldOnDomain",
            12,
            -3 - i,
            {"Value": value},
            data_type="FLOAT",
            domain="FACE",
        ).outputs[0]
        for i, value in enumerate(
            (face_random, t.math("MULTIPLY", face_random, face_random, x=11, y=-4))
        )
    ]
    variance = t.math(
        "SUBTRACT", means[1], t.math("MULTIPLY", means[0], means[0], x=13, y=-3), x=14, y=-3
    )
    spawned = t.node(
        "GeometryNodeSplitEdges",
        12,
        0,
        {
            "Mesh": spawned,
            "Selection": t.math(
                "MULTIPLY",
                t.math("GREATER_THAN", variance, 1e-7, x=14, y=-4),
                # Not within the parts cut off, falling whole
                t.math(
                    "LESS_THAN",
                    t.attribute(".cloth_piece_loose", "FLOAT", 13, -5),
                    0.99,
                    x=14,
                    y=-5,
                ),
                x=15,
                y=-4,
            ),
        },
    ).outputs[0]
    spawned = t.node(
        "GeometryNodeTransform",
        13,
        0,
        {"Geometry": spawned, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    # Where the cloth is, simulated when released
    spawned = t.node(
        "GeometryNodeSetPosition",
        13.5,
        0,
        {
            "Geometry": spawned,
            "Position": t.attribute(".cloth_tear_world", "FLOAT_VECTOR", 13, -1),
        },
    ).outputs[0]
    # Pushed away from the Control, and randomly to tumble, as the previous position of a step
    center = t.node(
        "FunctionNodeSeparateTransform",
        13,
        -2,
        {
            0: control_transform(
                t, controls, t.attribute(".cloth_tear_control", "INT", 11, -2), 12, -2
            )
        },
    ).outputs["Translation"]
    center = t.node(
        "FunctionNodeTransformPoint", 13, -2.5, {"Vector": center, "Transform": to_world}
    ).outputs[0]
    away = t.vmath("NORMALIZE", t.vmath("SUBTRACT", position, center, x=13, y=-3), x=14, y=-3)
    jitter = t.node(
        "FunctionNodeRandomValue",
        13,
        -4,
        {"Min": (-0.5, -0.5, -0.5), "Max": (0.5, 0.5, 0.5), "Seed": frame},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    push = t.math(
        "MULTIPLY",
        inputs["Push"],
        t.math("DIVIDE", dt, inputs["Substeps"], x=14, y=-5),
        x=15,
        y=-5,
    )
    push = t.vmath("SCALE", t.vmath("ADD", away, jitter, x=15, y=-3), push, x=16, y=-3)
    prev = t.vmath("SUBTRACT", position, push, x=16, y=-4)
    spawned = t.store(spawned, ".cloth_piece_prev", "FLOAT_VECTOR", prev, 14, 0)
    spawned = t.store(spawned, ".cloth_piece_rest", "FLOAT", edge_length, 14.5, 0, domain="EDGE")
    # Rest length of the edge to the next corner
    corner = t.node("GeometryNodeInputIndex", 13, -6).outputs[0]
    ends = []
    for i, offset in enumerate((1, -1)):
        other = t.node(
            "GeometryNodeOffsetCornerInFace",
            14,
            -6 - 2 * i,
            {"Corner Index": corner, "Offset": offset},
        ).outputs[0]
        vertex = t.node("GeometryNodeVertexOfCorner", 15, -6 - 2 * i, {0: other}).outputs[0]
        ends.append(
            (
                other,
                vertex,
                t.node(
                    "GeometryNodeFieldAtIndex",
                    16,
                    -6 - 2 * i,
                    {"Value": position, "Index": vertex},
                    data_type="FLOAT_VECTOR",
                    domain="POINT",
                ).outputs[0],
            )
        )
    length = t.vmath("DISTANCE", ends[0][2], position, x=17, y=-6)
    spawned = t.store(spawned, ".cloth_piece_length", "FLOAT", length, 15, 0, domain="CORNER")
    # Rest lengths of the bending pairs, and of the diagonal for the shear
    diagonal = t.node(
        "GeometryNodeVertexOfCorner",
        15,
        -15,
        {
            0: t.node(
                "GeometryNodeOffsetCornerInFace",
                14,
                -15,
                {"Corner Index": corner, "Offset": 2},
            ).outputs[0]
        },
    ).outputs[0]
    bend = t.node(
        "ShaderNodeCombineXYZ",
        17,
        -12,
        {
            axis: t.vmath(
                "DISTANCE",
                t.node(
                    "GeometryNodeFieldAtIndex",
                    16,
                    -12 - i,
                    {"Value": position, "Index": partner},
                    data_type="FLOAT_VECTOR",
                    domain="POINT",
                ).outputs[0],
                position,
                x=16.5,
                y=-12 - i,
            )
            for i, (axis, partner) in enumerate(
                zip("XYZ", (*bend_partners(t, 7, -12), diagonal), strict=True)
            )
        },
    ).outputs[0]
    spawned = t.store(spawned, ".cloth_piece_bend", "FLOAT_VECTOR", bend, 15.5, 0, domain="CORNER")
    pieces_join = t.node("GeometryNodeJoinGeometry", 16, 0)
    t.connect(pieces, pieces_join.inputs[0])
    t.connect(spawned, pieces_join.inputs[0])
    pieces = pieces_join.outputs[0]

    # Pinned to the cloth unless ripped out
    orig = t.attribute(".cloth_piece_orig", "INT", 16, -3)
    # Attached to the released cloth they hang from as its points, in the same order before the
    # pieces when joined, to be solved together
    in_zone = t.math(
        "GREATER_THAN", t.attribute(".cloth_tear_zone", "FLOAT", 15, 5), 0.0, x=16, y=5
    )
    rank = t.node(
        "GeometryNodeAccumulateField",
        16,
        6,
        {"Value": in_zone},
        data_type="FLOAT",
        domain="POINT",
    ).outputs["Trailing"]
    linked, linked_rank = (
        t.node(
            "GeometryNodeSampleIndex",
            17,
            5 + i,
            {"Geometry": mesh, "Value": value, "Index": orig},
            data_type="FLOAT",
            domain="POINT",
        ).outputs[0]
        for i, value in enumerate((in_zone, rank))
    )
    for name, data_type, value in (
        (
            ".cloth_tear_target",
            "FLOAT_VECTOR",
            t.attribute(".cloth_tear_world", "FLOAT_VECTOR", 16, -4),
        ),
        (".cloth_tear_pin", "FLOAT", t.attribute(".cloth_tear_pinned", "FLOAT", 16, -5)),
        (
            ".cloth_tear_hold",
            "FLOAT",
            t.math(
                "MULTIPLY",
                t.attribute(".cloth_tear_grab", "FLOAT", 15, -6),
                inputs["In Hand"],
                x=16,
                y=-6,
            ),
        ),
    ):
        sampled = t.node(
            "GeometryNodeSampleIndex",
            17,
            -3,
            {"Geometry": mesh, "Value": value, "Index": orig},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
        pieces = t.store(pieces, name, data_type, sampled, 17, 0)
    # The parts cut off are ripped out too, as a float for any of their faces
    ripped = t.math(
        "MAXIMUM",
        t.math(
            "LESS_THAN",
            t.attribute(".cloth_piece_random", "FLOAT", 17, -6),
            inputs["Rip Out"],
            x=18,
            y=-6,
        ),
        t.math("GREATER_THAN", t.attribute(".cloth_piece_loose", "FLOAT", 17, -7), 0.0, x=18, y=-7),
        x=19,
        y=-7,
    )
    pin = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", t.attribute(".cloth_tear_pin", "FLOAT", 18, -5), 0.5, x=19, y=-5),
        t.math("SUBTRACT", 1.0, ripped, x=19, y=-6),
        x=20,
        y=-5,
    )
    # In the hand of the Pull grabbing them, not on the cloth
    hold = t.attribute(".cloth_tear_hold", "FLOAT", 19, -8)
    pin = t.math("MAXIMUM", pin, hold, x=20, y=-8)
    linked = t.math("MULTIPLY", linked, t.math("SUBTRACT", 1.0, hold, x=20, y=9), x=21, y=9)
    link = t.math(
        "MULTIPLY_ADD",
        t.math("MULTIPLY", pin, linked, x=20, y=8),
        t.math("ADD", linked_rank, 1.0, x=19, y=8),
        -1.0,
        x=21,
        y=8,
    )
    pieces = t.store(pieces, ".cloth_tear_link", "INT", link, 17.5, 0)
    # Pinned to the cloth not released, moving with it otherwise
    free = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", pin, t.math("SUBTRACT", 1.0, linked, x=20, y=-6), x=21, y=-6),
        x=22,
        y=-5,
    )
    pieces = t.store(pieces, ".cloth_tear_free", "FLOAT", free, 18, 0)
    free = t.attribute(".cloth_tear_free", "FLOAT", 19, -7)

    t.section("Released Cloth")
    # The faces of the cloth around the tear, the points still attached following it
    zone = t.attribute(".cloth_tear_zone", "FLOAT", 17, 5)
    released = t.node(
        "GeometryNodeDeleteGeometry",
        18,
        4,
        {"Geometry": mesh, "Selection": t.math("LESS_THAN", zone, 0.5, x=18, y=5)},
        domain="FACE",
    ).outputs[0]
    released = t.node(
        "GeometryNodeSetPosition",
        19,
        4,
        {"Geometry": released, "Position": t.attribute(".cloth_tear_posed", "FLOAT_VECTOR", 18, 6)},
    ).outputs[0]
    released = t.store(released, ".cloth_piece_length", "FLOAT", length, 20, 4, domain="CORNER")
    released = t.store(
        released, ".cloth_piece_bend", "FLOAT_VECTOR", bend, 20.2, 4, domain="CORNER"
    )
    released = t.store(released, ".cloth_piece_rest", "FLOAT", edge_length, 20.5, 4, domain="EDGE")
    # Following the body, or the Pull grabbing it
    grabbed = t.attribute(".cloth_tear_grab", "FLOAT", 20, 7)
    released = t.store(
        released,
        ".cloth_tear_target",
        "FLOAT_VECTOR",
        t.node(
            "GeometryNodeSwitch",
            21,
            7,
            {
                "Switch": t.math("GREATER_THAN", grabbed, 0.5, x=20.5, y=8),
                "False": position,
                "True": t.attribute(".cloth_tear_world", "FLOAT_VECTOR", 20, 9),
            },
            input_type="VECTOR",
        ).outputs[0],
        21,
        4,
    )
    influence = t.attribute(".cloth_tear_released", "FLOAT", 21, 6)
    released = t.store(
        released,
        ".cloth_tear_free",
        "FLOAT",
        t.math(
            "MULTIPLY",
            t.math("GREATER_THAN", influence, 0.0, x=21.5, y=6),
            t.math("SUBTRACT", 1.0, grabbed, x=21.5, y=7),
            x=22,
            y=6,
        ),
        22,
        4,
    )
    released = t.store(released, ".cloth_tear_influence", "FLOAT", influence, 22.2, 4)
    was = t.math("GREATER_THAN", t.attribute(".cloth_tear_was", "FLOAT", 21, 7), 0.0, x=22, y=7)
    # Where it was on the previous frame, at rest when just released
    released = t.store(released, ".cloth_piece_prev", "FLOAT_VECTOR", position, 23, 4)
    released = t.node(
        "GeometryNodeStoreNamedAttribute",
        24,
        4,
        {
            "Geometry": released,
            "Selection": was,
            "Name": ".cloth_piece_prev",
            "Value": t.attribute(".cloth_tear_simulated_prev", "FLOAT_VECTOR", 22, 8),
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    released = t.node(
        "GeometryNodeSetPosition",
        25,
        4,
        {
            "Geometry": released,
            "Selection": was,
            "Position": t.attribute(".cloth_tear_simulated", "FLOAT_VECTOR", 22, 9),
        },
    ).outputs[0]
    released = t.store(released, ".cloth_tear_released_part", "FLOAT", 1.0, 26, 4)
    released = t.store(released, ".cloth_tear_link", "INT", -1, 26.5, 4)
    solved = t.node("GeometryNodeJoinGeometry", 27, 0)
    t.connect(pieces, solved.inputs[0])
    t.connect(released, solved.inputs[0])
    pieces = solved.outputs[0]

    pieces = couple_groups(t, pieces, free, 26, -40)
    for i, partner in enumerate((*bend_partners(t, 20, -56), diagonal)):
        pieces = t.store(
            pieces, f".cloth_tear_bend_{i}", "INT", partner, 26.2 + 0.1 * i, 0, domain="CORNER"
        )
    # Where their point of the mesh is now, to tell its neighbors from the other cloth
    home = t.node(
        "GeometryNodeSampleIndex",
        26,
        -48,
        {
            "Geometry": mesh,
            "Value": t.attribute(".cloth_tear_posed", "FLOAT_VECTOR", 25, -48),
            "Index": t.attribute(".cloth_piece_orig", "INT", 25, -49),
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    pieces = t.store(pieces, ".cloth_tear_home", "FLOAT_VECTOR", home, 27, -48)
    piece = t.node("GeometryNodeInputMeshIsland", 26, -50).outputs["Island Index"]
    pieces = t.store(pieces, ".cloth_tear_piece", "INT", piece, 27.5, -48)

    t.section("Long Range Attachments")
    # The pinned point closest along the cloth at rest, and that distance, not to stretch away,
    # not the points held by the Pulls
    paths = t.node(
        "GeometryNodeInputShortestEdgePaths",
        27,
        -3,
        {
            "End Vertex": t.math(
                "MULTIPLY",
                t.math("LESS_THAN", free, 0.5, x=25, y=-3),
                t.math(
                    "LESS_THAN",
                    t.attribute(".cloth_tear_grab", "FLOAT", 24, -4),
                    0.5,
                    x=25,
                    y=-4,
                ),
                x=26,
                y=-3,
            ),
            "Edge Cost": t.attribute(".cloth_piece_rest", "FLOAT", 26, -4),
        },
    ).outputs
    pieces = t.store(pieces, ".cloth_tear_reach", "FLOAT", paths["Total Cost"], 28, 0)
    pieces = t.store(pieces, ".cloth_tear_end", "INT", paths["Next Vertex Index"], 28.5, 0)
    # Following the paths to their end, doubling the steps each time
    jumps_in = t.node("GeometryNodeRepeatInput", 29, 0, {"Iterations": 10})
    jumps_out = t.node("GeometryNodeRepeatOutput", 31, 0)
    jumps_in.pair_with_output(jumps_out)
    t.connect(pieces, jumps_in.inputs["Geometry"])
    end = t.attribute(".cloth_tear_end", "INT", 29, -2)
    jumped = t.node(
        "GeometryNodeSampleIndex",
        30,
        -2,
        {"Geometry": jumps_in.outputs["Geometry"], "Value": end, "Index": end},
        data_type="INT",
        domain="POINT",
    ).outputs[0]
    t.connect(
        t.store(jumps_in.outputs["Geometry"], ".cloth_tear_end", "INT", jumped, 30, 0),
        jumps_out.inputs["Geometry"],
    )
    pieces = jumps_out.outputs["Geometry"]

    t.section("Colliders")
    collider = t.node(
        "GeometryNodeCollectionInfo",
        17,
        -10,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    ).outputs[0]
    collider = t.node("GeometryNodeRealizeInstances", 18, -10, {"Geometry": collider}).outputs[0]
    collider = t.node(
        "GeometryNodeTransform",
        19,
        -10,
        {"Geometry": collider, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    has_collider = t.node(
        "GeometryNodeAttributeDomainSize", 20, -11, {"Geometry": collider}
    ).outputs["Face Count"]
    # The cloth left and not released, for the pieces to lie on it
    cloth = t.node(
        "GeometryNodeDeleteGeometry",
        18,
        -12,
        {
            "Geometry": mesh,
            "Selection": t.math(
                "MAXIMUM",
                t.math(
                    "GREATER_THAN",
                    t.attribute(".cloth_tear_torn", "FLOAT", 17, -13),
                    0.5,
                    x=18,
                    y=-13,
                ),
                t.attribute(".cloth_tear_zone", "FLOAT", 17, -14),
                x=18.5,
                y=-13,
            ),
        },
        domain="FACE",
    ).outputs[0]
    cloth = t.node(
        "GeometryNodeTransform",
        19,
        -12,
        {"Geometry": cloth, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]

    t.section("Substeps")
    # Verlet integration, with the pinned points following the cloth
    steps_in = t.node("GeometryNodeRepeatInput", 19, 0, {"Iterations": inputs["Substeps"]})
    steps_out = t.node("GeometryNodeRepeatOutput", 29, 0)
    steps_in.pair_with_output(steps_out)
    t.connect(pieces, steps_in.inputs["Geometry"])
    step = t.math("DIVIDE", dt, inputs["Substeps"], x=19, y=-3)
    old = t.node("GeometryNodeCaptureAttribute", 20, 0, {"Geometry": steps_in.outputs["Geometry"]})
    old.capture_items.new("VECTOR", "Position")
    t.connect(position, old.inputs["Position"])
    velocity = t.vmath(
        "SUBTRACT", position, t.attribute(".cloth_piece_prev", "FLOAT_VECTOR", 20, -3), x=21, y=-3
    )
    # Damped towards the velocity of the neighbors
    neighbors = t.node(
        "GeometryNodeBlurAttribute",
        21,
        -7,
        {"Value": velocity, "Iterations": 1},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    velocity = t.vmath(
        "ADD",
        velocity,
        t.vmath(
            "SCALE",
            t.vmath("SUBTRACT", neighbors, velocity, x=22, y=-7),
            inputs["Damping"],
            x=23,
            y=-7,
        ),
        x=24,
        y=-6,
    )
    drag = t.math(
        "MULTIPLY_ADD", inputs["Drag"], t.math("MULTIPLY", step, -1.0, x=20, y=-5), 1.0, x=21, y=-5
    )
    velocity = t.vmath("SCALE", velocity, t.math("MAXIMUM", drag, 0.0, x=22, y=-5), x=22, y=-3)
    fall = t.vmath(
        "SCALE", inputs["Gravity"], t.math("MULTIPLY", step, step, x=22, y=-6), x=23, y=-6
    )
    moved = t.vmath("ADD", position, t.vmath("ADD", velocity, fall, x=23, y=-3), x=24, y=-3)
    pieces = t.node(
        "GeometryNodeSetPosition",
        21,
        0,
        {"Geometry": old.outputs["Geometry"], "Selection": free, "Position": moved},
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeSetPosition",
        22,
        0,
        {
            "Geometry": pieces,
            "Selection": t.math("SUBTRACT", 1.0, free, x=21, y=-7),
            "Position": t.attribute(".cloth_tear_target", "FLOAT_VECTOR", 21, -8),
        },
    ).outputs[0]
    pieces = t.store(pieces, ".cloth_piece_prev", "FLOAT_VECTOR", old.outputs["Position"], 23, 0)

    t.section("Length Constraints")
    # The pairs across the edges through the corner for the Bending, compliant as it is lower,
    # and the diagonals against shearing
    bend = t.node(
        "ShaderNodeSeparateXYZ",
        21,
        -16,
        {0: t.attribute(".cloth_piece_bend", "FLOAT_VECTOR", 20, -16)},
    ).outputs
    pairs = []
    for i in range(3):
        vertex = t.attribute(f".cloth_tear_bend_{i}", "INT", 20, -17 - i)
        other = t.node(
            "GeometryNodeFieldAtIndex",
            21,
            -17 - i,
            {"Value": position, "Index": vertex},
            data_type="FLOAT_VECTOR",
            domain="POINT",
        ).outputs[0]
        pairs.append((vertex, other, bend[i]))
    # Infinite at no Bending, none at full, over the step squared
    softness = t.math(
        "SUBTRACT",
        t.math("DIVIDE", 1.0, t.math("MAXIMUM", inputs["Bending"], 1e-6, x=19, y=-23), x=20, y=-23),
        1.0,
        x=21,
        y=-23,
    )
    compliance = t.math(
        "DIVIDE",
        t.math("MULTIPLY", softness, BEND_COMPLIANCE, x=22, y=-23),
        t.math("MULTIPLY", step, step, x=22, y=-24),
        x=23,
        y=-23,
    )
    # Bending once per step, as small steps XPBD, its iterations not making it stiffer
    pieces = correction(
        t, pieces, [(*pair, 0.5, compliance) for pair in pairs[:2]], free, position, 21, -26
    )
    # Jacobi iterations of the edge lengths, from both edges of each corner
    iterations_in = t.node("GeometryNodeRepeatInput", 23, 0, {"Iterations": inputs["Iterations"]})
    iterations_out = t.node("GeometryNodeRepeatOutput", 26, 0)
    iterations_in.pair_with_output(iterations_out)
    t.connect(pieces, iterations_in.inputs["Geometry"])
    lengths = (
        t.attribute(".cloth_piece_length", "FLOAT", 23, -6),
        t.node(
            "GeometryNodeFieldAtIndex",
            23,
            -8,
            {"Value": t.attribute(".cloth_piece_length", "FLOAT", 22, -8), "Index": ends[1][0]},
            data_type="FLOAT",
            domain="CORNER",
        ).outputs[0],
    )
    # The edges, then apart not to overshoot, the diagonals
    edges = [
        (vertex, other, rest, 1.0, None)
        for (_, vertex, other), rest in zip(ends, lengths, strict=True)
    ]
    constrained = iterations_in.outputs["Geometry"]
    for i, constraints in enumerate((edges, [(*pairs[2], 1.0 / 3.0, None)])):
        constrained = correction(t, constrained, constraints, free, position, 24, -3 - 17 * i)
    t.connect(couple(t, constrained, free, 25.5, -32), iterations_out.inputs["Geometry"])
    pieces = iterations_out.outputs["Geometry"]
    # The released cloth pulled back to the body the less it is simulated, as a cube for the
    # pull of every step to stay low away from the outer edge, and by the Shape, per frame,
    # fading to the tear
    outer = t.math(
        "SUBTRACT", 1.0, t.attribute(".cloth_tear_influence", "FLOAT", 35, -52), x=36, y=-52
    )
    pull = t.math("POWER", outer, 3.0, x=36.5, y=-52)
    shape = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "POWER",
            t.math("SUBTRACT", 1.0, inputs["Shape"], x=35, y=-54),
            t.math("DIVIDE", 1.0, inputs["Substeps"], x=35, y=-55),
            x=36,
            y=-54,
        ),
        x=36.5,
        y=-54,
    )
    pull = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", 1.0, pull, x=37, y=-53),
        t.math("MULTIPLY", shape, outer, x=37, y=-54),
        pull,
        x=37.5,
        y=-53,
    )
    pieces = t.node(
        "GeometryNodeSetPosition",
        26.2,
        0,
        {
            "Geometry": pieces,
            "Selection": t.math(
                "MULTIPLY",
                t.attribute(".cloth_tear_released_part", "FLOAT", 35, -50),
                free,
                x=36,
                y=-50,
            ),
            "Offset": t.vmath(
                "SCALE",
                t.vmath(
                    "SUBTRACT",
                    t.attribute(".cloth_tear_target", "FLOAT_VECTOR", 35, -51),
                    position,
                    x=36,
                    y=-51,
                ),
                pull,
                x=38,
                y=-51,
            ),
        },
    ).outputs[0]
    # Within reach of their pinned point, those without one ending on themselves
    end = t.attribute(".cloth_tear_end", "INT", 36, -26)
    anchor = t.node(
        "GeometryNodeFieldAtIndex",
        37,
        -26,
        {"Value": position, "Index": end},
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    anchored = t.node(
        "GeometryNodeFieldAtIndex",
        37,
        -27,
        {"Value": free, "Index": end},
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    offset = t.vmath("SUBTRACT", position, anchor, x=38, y=-26)
    reach = t.attribute(".cloth_tear_reach", "FLOAT", 37, -28)
    current = t.math("MAXIMUM", t.vmath("LENGTH", offset, x=38, y=-27), 1e-9, x=39, y=-27)
    beyond = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", current, reach, x=39, y=-28),
        t.math("LESS_THAN", anchored, 0.5, x=38, y=-28),
        x=40,
        y=-28,
    )
    pieces = t.node(
        "GeometryNodeSetPosition",
        26.5,
        0,
        {
            "Geometry": pieces,
            "Selection": t.math("MULTIPLY", beyond, free, x=40, y=-29),
            "Position": t.vmath(
                "ADD",
                anchor,
                t.vmath(
                    "SCALE",
                    offset,
                    t.math("DIVIDE", reach, current, x=40, y=-27),
                    x=41,
                    y=-27,
                ),
                x=42,
                y=-26,
            ),
        },
    ).outputs[0]

    t.section("Self Collision")
    # Apart from the closest other point by half the overlap, a quarter when it is free too, not
    # to bounce, every other step, faster. Not from the points close on the mesh in the same
    # piece, nor from the attached points kept together. Found once, for the selection and offset
    found = t.node("GeometryNodeIndexOfNearest", 26, -36).outputs
    nearest = t.node("GeometryNodeCaptureAttribute", 26.6, 0, {"Geometry": pieces})
    for data_type, name in (("INT", "Index"), ("BOOLEAN", "Has Neighbor")):
        nearest.capture_items.new(data_type, name)
        t.connect(found[name], nearest.inputs[name])
    nearest = nearest.outputs
    home = t.attribute(".cloth_tear_home", "FLOAT_VECTOR", 30, -40)
    apart = t.vmath(
        "DISTANCE",
        home,
        t.node(
            "GeometryNodeFieldAtIndex",
            31,
            -40,
            {"Value": home, "Index": nearest["Index"]},
            data_type="FLOAT_VECTOR",
            domain="POINT",
        ).outputs[0],
        x=32,
        y=-40,
    )
    other = t.node(
        "GeometryNodeFieldAtIndex",
        31,
        -36,
        {"Value": position, "Index": nearest["Index"]},
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    other_free = t.node(
        "GeometryNodeFieldAtIndex",
        31,
        -37,
        {"Value": free, "Index": nearest["Index"]},
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    away = t.vmath("SUBTRACT", position, other, x=32, y=-36)
    gap = t.vmath("LENGTH", away, x=33, y=-36)
    close = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", gap, inputs["Self Collision"], x=33, y=-37),
        t.math("GREATER_THAN", gap, 1e-6, x=33, y=-38),
        x=34,
        y=-37,
    )
    close = t.math("MULTIPLY", close, nearest["Has Neighbor"], x=35, y=-37)

    def other_value(name, y):
        """Attribute of the closest other point"""
        return t.node(
            "GeometryNodeFieldAtIndex",
            31,
            y,
            {"Value": t.attribute(name, "INT", 30, y), "Index": nearest["Index"]},
            data_type="INT",
            domain="POINT",
        ).outputs[0]

    neighbors = t.math(
        "MULTIPLY",
        t.math(
            "LESS_THAN",
            apart,
            t.math("MULTIPLY", inputs["Self Collision"], 2.0, x=32, y=-41),
            x=33,
            y=-41,
        ),
        t.math(
            "COMPARE",
            t.attribute(".cloth_tear_piece", "INT", 32, -43),
            other_value(".cloth_tear_piece", -43),
            0.5,
            x=33,
            y=-43,
        ),
        x=34,
        y=-41,
    )
    together = t.math(
        "COMPARE",
        t.attribute(".cloth_tear_group", "INT", 32, -45),
        other_value(".cloth_tear_group", -45),
        0.5,
        x=33,
        y=-45,
    )
    close = t.math(
        "MULTIPLY",
        close,
        t.math("LESS_THAN", t.math("MAXIMUM", neighbors, together, x=34, y=-44), 0.5, x=35, y=-44),
        x=35.5,
        y=-37,
    )
    push = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", inputs["Self Collision"], gap, x=34, y=-36),
        t.math("MULTIPLY_ADD", other_free, -0.25, 0.5, x=34, y=-38),
        x=35,
        y=-36,
    )
    collided = t.node(
        "GeometryNodeSetPosition",
        26.8,
        0,
        {
            "Geometry": nearest["Geometry"],
            "Selection": t.math("MULTIPLY", close, free, x=36, y=-37),
            "Offset": t.vmath(
                "SCALE",
                t.vmath("NORMALIZE", away, x=35, y=-35),
                push,
                x=36,
                y=-36,
            ),
        },
    ).outputs[0]
    every = t.math(
        "COMPARE",
        t.math("FLOORED_MODULO", steps_in.outputs["Iteration"], 2.0, x=36, y=-40),
        0.0,
        0.5,
        x=37,
        y=-40,
    )
    every = t.math(
        "MULTIPLY",
        every,
        t.math("GREATER_THAN", inputs["Self Collision"], 0.0, x=37, y=-41),
        x=38,
        y=-40,
    )
    pieces = t.node(
        "GeometryNodeSwitch",
        27,
        0,
        {"Switch": every, "False": pieces, "True": collided},
        input_type="GEOMETRY",
    ).outputs[0]

    t.section("Collision")
    # Out of the collider surface, and resting on the floor
    nearest = [
        t.node(
            "GeometryNodeSampleNearestSurface",
            26,
            -10 - i,
            {"Mesh": collider, "Value": value, "Sample Position": position},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, value in enumerate((position, t.node("GeometryNodeInputNormal", 25, -11).outputs[0]))
    ]
    outward = t.vmath("NORMALIZE", nearest[1], x=27, y=-11)
    side = t.vmath(
        "DOT_PRODUCT", t.vmath("SUBTRACT", position, nearest[0], x=27, y=-9), outward, x=28, y=-9
    )
    hit = t.math("LESS_THAN", side, COLLISION, x=28, y=-8)
    deep = t.math("MULTIPLY", inputs["Piece Size"], -1.0, x=27, y=-12)
    hit = t.math("MULTIPLY", hit, t.math("GREATER_THAN", side, deep, x=28, y=-12), x=29, y=-8)
    hit = t.math(
        "MULTIPLY", hit, t.math("GREATER_THAN", has_collider, 0.0, x=28, y=-13), x=29, y=-9
    )
    pieces = settle(
        t,
        pieces,
        t.math("MULTIPLY", hit, free, x=29, y=-10),
        outward,
        t.vmath("ADD", nearest[0], t.vmath("SCALE", outward, COLLISION, x=28, y=-14), x=29, y=-14),
        inputs,
        30,
        -14,
    )
    # On the side of the cloth they come from, its normals often being inwards, and only on its
    # faces, not past its edges
    nearest = [
        t.node(
            "GeometryNodeSampleNearestSurface",
            26,
            -20 - i,
            {"Mesh": cloth, "Value": value, "Sample Position": position},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, value in enumerate((position, t.node("GeometryNodeInputNormal", 25, -21).outputs[0]))
    ]
    outward = t.vmath("NORMALIZE", nearest[1], x=27, y=-21)
    away = t.vmath("SUBTRACT", position, nearest[0], x=27, y=-19)
    side = t.vmath("DOT_PRODUCT", away, outward, x=28, y=-19)
    previous = t.vmath(
        "DOT_PRODUCT",
        t.vmath(
            "SUBTRACT",
            t.attribute(".cloth_piece_prev", "FLOAT_VECTOR", 26, -23),
            nearest[0],
            x=27,
            y=-23,
        ),
        outward,
        x=28,
        y=-23,
    )
    previous = t.math("SIGN", previous, x=29, y=-23)
    along = t.vmath(
        "LENGTH",
        t.vmath("SUBTRACT", away, t.vmath("SCALE", outward, side, x=28, y=-20), x=29, y=-20),
        x=30,
        y=-20,
    )
    hit = t.math(
        "LESS_THAN", t.math("MULTIPLY", side, previous, x=29, y=-19), COLLISION, x=30, y=-19
    )
    hit = t.math("MULTIPLY", hit, t.math("LESS_THAN", along, COLLISION, x=30, y=-21), x=31, y=-19)
    hit = t.math(
        "MULTIPLY",
        hit,
        t.math(
            "LESS_THAN",
            t.math("ABSOLUTE", side, x=29, y=-22),
            inputs["Piece Size"],
            x=30,
            y=-22,
        ),
        x=31,
        y=-20,
    )
    pieces = settle(
        t,
        pieces,
        t.math("MULTIPLY", hit, free, x=31, y=-21),
        outward,
        t.vmath(
            "ADD",
            nearest[0],
            t.vmath(
                "SCALE",
                outward,
                t.math("MULTIPLY", previous, COLLISION, x=30, y=-24),
                x=31,
                y=-24,
            ),
            x=32,
            y=-24,
        ),
        inputs,
        32,
        -26,
    )
    xyz = t.node("ShaderNodeSeparateXYZ", 26, -16, {0: position}).outputs
    ground = t.math("ADD", inputs["Floor"], COLLISION, x=26, y=-17)
    floored = t.math(
        "MULTIPLY", t.math("LESS_THAN", xyz["Z"], ground, x=27, y=-16), free, x=28, y=-16
    )
    pieces = t.node(
        "GeometryNodeSetPosition",
        28,
        0,
        {
            "Geometry": pieces,
            "Selection": floored,
            "Position": t.node(
                "ShaderNodeCombineXYZ", 27, -17, {"X": xyz["X"], "Y": xyz["Y"], "Z": ground}
            ).outputs[0],
        },
    ).outputs[0]
    # Without sliding on the floor once resting on it, friction holding them where they were
    before = t.node("ShaderNodeSeparateXYZ", 26, -19, {0: old.outputs["Position"]}).outputs
    resting = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", before["Z"], t.math("ADD", ground, 1e-4, x=26, y=-20), x=27, y=-19),
        t.math("LESS_THAN", xyz["Z"], t.math("ADD", ground, COLLISION, x=26, y=-21), x=27, y=-21),
        x=28,
        y=-19,
    )
    pieces = t.node(
        "GeometryNodeSetPosition",
        28.2,
        0,
        {
            "Geometry": pieces,
            "Selection": t.math("MULTIPLY", resting, free, x=29, y=-19),
            "Position": t.node(
                "ShaderNodeCombineXYZ",
                28,
                -20,
                {"X": before["X"], "Y": before["Y"], "Z": ground},
            ).outputs[0],
        },
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeStoreNamedAttribute",
        28.5,
        0,
        {
            "Geometry": pieces,
            "Selection": t.math("MAXIMUM", floored, resting, x=29, y=-20),
            "Name": ".cloth_piece_prev",
            "Value": position,
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    pieces = couple(t, pieces, free, 28.7, -32)
    t.connect(pieces, steps_out.inputs["Geometry"])
    pieces = steps_out.outputs["Geometry"]

    parts = t.node(
        "GeometryNodeSeparateGeometry",
        28.7,
        0,
        {
            "Geometry": pieces,
            "Selection": t.attribute(".cloth_tear_released_part", "FLOAT", 28.5, -1),
        },
        domain="POINT",
    ).outputs
    pieces = parts["Inverted"]
    # Torn out around the grip once stretched past the Strength around it: on a ragged line about
    # half the radius of the Pull out of its sphere, along weak lines along and across the Grain
    grain = t.vmath("NORMALIZE", inputs["Grain"], x=28, y=-12)
    along = t.vmath("SCALE", grain, t.vmath("DOT_PRODUCT", rest, grain, x=28, y=-13), x=29, y=-12)
    across = t.vmath("SUBTRACT", rest, along, x=29, y=-13)
    lines = [
        t.node(
            "ShaderNodeTexNoise",
            31,
            -12 - i,
            {
                "Vector": t.vmath(
                    "ADD",
                    t.vmath("SCALE", first, 25.0, x=30, y=-12 - i),
                    t.vmath("SCALE", second, 4.0, x=30, y=-12.5 - i),
                    x=30.5,
                    y=-12 - i,
                ),
                "Detail": 2.0,
            },
            noise_dimensions="3D",
        ).outputs["Fac"]
        for i, (first, second) in enumerate(((across, along), (along, across)))
    ]
    puller = t.attribute(".cloth_tear_puller", "INT", 30, -16)
    margin = t.math(
        "MULTIPLY",
        t.node(
            "ShaderNodeMapRange",
            32,
            -10,
            {0: t.math("MINIMUM", *lines, x=31.5, y=-10), 1: 0.25, 2: 0.6, 3: 0.2, 4: 0.8},
        ).outputs[0],
        t.vmath(
            "DOT_PRODUCT",
            t.node(
                "FunctionNodeSeparateTransform",
                31,
                -16,
                {0: control_transform(t, pulls, puller, 30, -17)},
            ).outputs["Scale"],
            (1 / 3, 1 / 3, 1 / 3),
            x=32,
            y=-16,
        ),
        x=33,
        y=-10,
    )
    # As a float for the faces across the line
    inside = t.node(
        "GeometryNodeFieldOnDomain",
        34,
        -10,
        {
            "Value": t.math(
                "LESS_THAN", t.attribute(".cloth_tear_grip", "FLOAT", 32, -11), margin, x=33, y=-11
            )
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    across_line = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", inside, 0.0, x=35, y=-10),
        t.math("LESS_THAN", inside, 1.0, x=35, y=-11),
        x=36,
        y=-10,
    )
    # Torn once stretched on average past the Strength along the line, or three times past it
    # anywhere within, as at the edge of the grip
    strain = t.node(
        "GeometryNodeFieldOnDomain",
        32,
        -8,
        {
            "Value": t.math(
                "DIVIDE",
                edge_length,
                t.math(
                    "MAXIMUM",
                    t.attribute(".cloth_piece_rest", "FLOAT", 29, -9),
                    1e-9,
                    x=30,
                    y=-9,
                ),
                x=31,
                y=-8,
            )
        },
        data_type="FLOAT",
        domain="EDGE",
    ).outputs[0]
    overstretched = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", inside, 0.0, x=33, y=-12),
        t.math(
            "GREATER_THAN",
            strain,
            t.math("MULTIPLY_ADD", inputs["Strength"], 3.0, 1.0, x=33, y=-13),
            x=34,
            y=-13,
        ),
        x=34,
        y=-12,
    )
    total, count, overstretched = (
        t.node(
            "GeometryNodeAccumulateField",
            35,
            -8 - i,
            {"Value": value, "Group ID": puller},
            data_type="FLOAT",
            domain="FACE",
        ).outputs["Total"]
        for i, value in enumerate(
            (t.math("MULTIPLY", strain, across_line, x=34, y=-8), across_line, overstretched)
        )
    )
    stretched = t.math(
        "MAXIMUM",
        t.math(
            "GREATER_THAN",
            t.math("DIVIDE", total, t.math("MAXIMUM", count, 1.0, x=35.5, y=-9), x=36, y=-8),
            t.math("ADD", inputs["Strength"], 1.0, x=35.5, y=-10),
            x=36.5,
            y=-8,
        ),
        t.math("GREATER_THAN", overstretched, 0.0, x=36.5, y=-10),
        x=37,
        y=-8,
    )
    ripping = t.store(
        parts["Selection"],
        ".cloth_tear_rip",
        "FLOAT",
        t.math(
            "MULTIPLY",
            across_line,
            stretched,
            x=37,
            y=-9,
        ),
        33,
        -6,
        domain="FACE",
    )

    # Aging, removed after their Lifetime
    age = t.math("ADD", t.attribute(".cloth_piece_age", "FLOAT", 28, -3), dt, x=29, y=-3)
    pieces = t.store(pieces, ".cloth_piece_age", "FLOAT", age, 29, 0)
    expired = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", inputs["Lifetime"], 0.0, x=29, y=-5),
        t.math(
            "GREATER_THAN",
            t.attribute(".cloth_piece_age", "FLOAT", 29, -6),
            inputs["Lifetime"],
            x=30,
            y=-6,
        ),
        x=30,
        y=-5,
    )
    pieces = t.node(
        "GeometryNodeDeleteGeometry",
        29.5,
        0,
        {"Geometry": pieces, "Selection": expired},
        domain="POINT",
    ).outputs[0]
    vertices = t.node("GeometryNodeAttributeDomainSize", 30, 3, {"Geometry": mesh}).outputs[
        "Point Count"
    ]
    cloth_state = t.node("GeometryNodePoints", 31, 3, {"Count": vertices}).outputs[0]
    for i, (name, value, data_type) in enumerate(
        (
            ("influence", t.attribute(".cloth_tear_released", "FLOAT", 30, 8), "FLOAT"),
            (".in_zone", in_zone, "FLOAT"),
            (".rank", rank, "FLOAT"),
            ("grab", t.attribute(".cloth_tear_grab", "FLOAT", 30, 9), "FLOAT"),
            ("grabber", t.attribute(".cloth_tear_grabber", "INT", 30, 10), "INT"),
            ("offset", t.attribute(".cloth_tear_offset", "FLOAT_VECTOR", 30, 11), "FLOAT_VECTOR"),
            ("grip", t.attribute(".cloth_tear_grip", "FLOAT", 30, 12), "FLOAT"),
        )
    ):
        cloth_state = t.store(
            cloth_state,
            name,
            data_type,
            t.node(
                "GeometryNodeSampleIndex",
                31 + i,
                5,
                {"Geometry": mesh, "Value": value, "Index": index},
                data_type=data_type,
                domain="POINT",
            ).outputs[0],
            32 + i,
            3,
        )
    solved = [
        t.node(
            "GeometryNodeSampleIndex",
            34,
            5 + i,
            {
                "Geometry": parts["Selection"],
                "Value": value,
                "Index": t.attribute(".rank", "FLOAT", 33, 7),
            },
            data_type="FLOAT_VECTOR",
            domain="POINT",
        ).outputs[0]
        for i, value in enumerate(
            (position, t.attribute(".cloth_piece_prev", "FLOAT_VECTOR", 33, 8))
        )
    ]
    has_zone = t.attribute(".in_zone", "FLOAT", 34, 9)
    cloth_state = t.store(cloth_state, "prev", "FLOAT_VECTOR", solved[1], 35, 3)
    cloth_state = t.node(
        "GeometryNodeSetPosition",
        36,
        3,
        {"Geometry": cloth_state, "Selection": has_zone, "Position": solved[0]},
    ).outputs[0]
    cloth_state = t.store(cloth_state, "valid", "FLOAT", has_zone, 37, 3)
    # The faces ripped, from the released cloth in the order of the zone
    in_zone_face, zone_rank = (
        t.node(
            "GeometryNodeSampleIndex",
            34,
            -6 - i,
            {"Geometry": mesh, "Value": value, "Index": index},
            data_type="FLOAT",
            domain="FACE",
        ).outputs[0]
        for i, value in enumerate(
            (
                zone,
                t.node(
                    "GeometryNodeAccumulateField",
                    33,
                    -7,
                    {"Value": zone},
                    data_type="FLOAT",
                    domain="FACE",
                ).outputs["Trailing"],
            )
        )
    )
    ripped = t.node(
        "GeometryNodeSampleIndex",
        35,
        -6,
        {
            "Geometry": ripping,
            "Value": t.attribute(".cloth_tear_rip", "FLOAT", 34, -9),
            "Index": zone_rank,
        },
        data_type="FLOAT",
        domain="FACE",
    ).outputs[0]
    # Only with Pulls, faster
    ripped = t.node(
        "GeometryNodeSwitch",
        36,
        -7,
        {
            "Switch": t.math("GREATER_THAN", pull_count, 0.0, x=35, y=-8),
            "False": 0.0,
            "True": t.math("MULTIPLY", ripped, in_zone_face, x=36, y=-6),
        },
        input_type="FLOAT",
    ).outputs[0]
    state = t.store(state, "ripped", "FLOAT", ripped, 36, 6)
    # Only what the next frame needs, the simulation cache storing every frame
    state, pieces, cloth_state = (
        remove(t, geometry, names, 37, 6 + i)
        for i, (geometry, names) in enumerate(
            (
                (state, ("radius",)),
                (pieces, (".cloth_tear_*",)),
                (cloth_state, ("radius", ".in_zone", ".rank")),
            )
        )
    )
    t.connect(state, sim_out.inputs["Geometry"])
    t.connect(pieces, sim_out.inputs["Pieces"])
    t.connect(cloth_state, sim_out.inputs["Cloth"])
    # The zone outputs after their last nodes
    steps_out.parent = iterations_out.parent = jumps_out.parent = sim_out.parent = t.frame

    t.section("Torn Cloth", row=True)
    torn = t.node(
        "GeometryNodeSampleIndex",
        31,
        -3,
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Value": t.attribute("torn", "FLOAT", 30, -4),
            "Index": index,
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    released = [
        t.node(
            "GeometryNodeSampleIndex",
            31,
            -6 - i,
            {"Geometry": sim_out.outputs["Cloth"], "Value": value, "Index": index},
            data_type=data_type,
            domain="POINT",
        ).outputs[0]
        for i, (value, data_type) in enumerate(
            ((t.attribute("valid", "FLOAT", 30, -6), "FLOAT"), (position, "FLOAT_VECTOR"))
        )
    ]
    cloth = t.node(
        "GeometryNodeSetPosition",
        31.5,
        0,
        {
            "Geometry": geometry,
            "Selection": released[0],
            "Position": t.node(
                "FunctionNodeTransformPoint",
                31,
                -8,
                {"Vector": released[1], "Transform": to_local},
            ).outputs[0],
        },
    ).outputs[0]
    cloth = t.store(cloth, ".cloth_tear_inside", "FLOAT", torn, 32, 0, domain="FACE")
    # As a float, for the points of any torn face
    cloth = t.store(
        cloth,
        ".cloth_tear_moved",
        "FLOAT",
        t.math("GREATER_THAN", t.attribute(".cloth_tear_inside", "FLOAT", 32, -2), 0.0, x=33, y=-2),
        33,
        0,
    )
    cloth = t.node(
        "GeometryNodeDeleteGeometry",
        34,
        0,
        {
            "Geometry": cloth,
            "Selection": t.math(
                "GREATER_THAN", t.attribute(".cloth_tear_inside", "FLOAT", 33, -3), 0.5, x=34, y=-3
            ),
        },
        domain="FACE",
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeTransform",
        32,
        2,
        {"Geometry": sim_out.outputs["Pieces"], "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    # All the borders of the pieces fray
    pieces = t.store(pieces, ".cloth_tear_moved", "FLOAT", 1.0, 33, 2)
    edges = t.node("GeometryNodeJoinGeometry", 37, -2)
    t.connect(border(t, pieces, 33, 4), edges.inputs[0])
    t.connect(border(t, cloth, 35, -3), edges.inputs[0])
    joined = t.node("GeometryNodeJoinGeometry", 37, 0)
    t.connect(pieces, joined.inputs[0])
    t.connect(cloth, joined.inputs[0])
    return joined.outputs[0], edges.outputs[0]


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(),))
