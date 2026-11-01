# Build rain.blend: the Rain node group and material
# Usage: Blender --background --factory-startup --python rain_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "rain.blend"
NODE_GROUP = "MustardUI Rain"
MATERIAL = "MustardUI Rain"


def build_interface(ng):
    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Control",
        "NodeSocketObject",
        description="Empty whose cube is the volume of the rain, falling from its top face to the "
        "bottom one along its -Z axis",
    )
    add_input(
        ng,
        "Shape",
        "NodeSocketMenu",
        description="Shape of the volume in the cube of the Control: a box, a cylinder, or a "
        "cone cut at the top, e.g. for a shower",
    )
    add_input(
        ng,
        "Top Radius",
        "NodeSocketFloat",
        default_value=0.15,
        min_value=0.01,
        max_value=1.0,
        subtype="FACTOR",
        description="Radius of the top face of the Cone, relative to the bottom one",
    )
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Collection of the meshes the drops splash on",
    )
    add_input(ng, "Material", "NodeSocketMaterial", description="Material of the drops")

    panel = ng.interface.new_panel("Drops")
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        panel,
        default_value=1000.0,
        min_value=0.0,
        max_value=1e6,
        description="Drops falling each second per square meter of the bottom face",
    )
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        panel,
        default_value=0.0015,
        min_value=0.0,
        max_value=1.0,
        subtype="DISTANCE",
        description="Radius of the drops",
    )
    add_input(
        ng,
        "Stretch",
        "NodeSocketFloat",
        panel,
        default_value=25.0,
        min_value=1.0,
        max_value=1000.0,
        description="Length of the streaks the drops are blurred into by their motion, relative "
        "to their radius",
    )
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        panel,
        default_value=7.0,
        min_value=0.01,
        max_value=1000.0,
        description="Falling speed of the drops",
    )
    add_input(
        ng,
        "Wind",
        "NodeSocketVector",
        panel,
        default_value=(0.0, 0.0, 0.0),
        subtype="VELOCITY",
        description="Velocity added to the drops, in world space",
    )
    add_input(
        ng,
        "Randomness",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Variation of size and speed between drops",
    )
    add_input(
        ng,
        "Opacity",
        "NodeSocketFloat",
        panel,
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Visibility of the drops and droplets, reflecting the light around them, "
        "stored in the rain_opacity attribute",
    )
    add_input(
        ng,
        "Floor",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Splash on the bottom face of the Control, otherwise the drops fall through",
    )

    panel = ng.interface.new_panel("Splashes")
    add_input(
        ng,
        "Splashes",
        "NodeSocketInt",
        panel,
        default_value=4,
        min_value=0,
        max_value=64,
        description="Droplets bouncing off each drop hitting a collider or the floor",
    )
    add_input(
        ng,
        "Splash Speed",
        "NodeSocketFloat",
        panel,
        default_value=1.2,
        min_value=0.0,
        max_value=100.0,
        description="Speed of the droplets, away from the surface hit",
    )
    add_input(
        ng,
        "Splash Size",
        "NodeSocketFloat",
        panel,
        default_value=0.6,
        min_value=0.0,
        max_value=10.0,
        subtype="FACTOR",
        description="Radius of the droplets, relative to the drops",
    )
    add_input(
        ng,
        "Splash Lifetime",
        "NodeSocketFloat",
        panel,
        default_value=0.3,
        min_value=0.01,
        max_value=100.0,
        subtype="TIME_ABSOLUTE",
        description="Seconds before the droplets disappear",
    )
    add_input(
        ng,
        "Gravity",
        "NodeSocketVector",
        panel,
        default_value=(0.0, 0.0, -9.81),
        subtype="ACCELERATION",
        description="Acceleration of the droplets, in world space",
    )

    # Drops staying on the Colliders, sliding down and dripping, in the panel of their toggle
    add_input(
        ng,
        "Surface Drops",
        "NodeSocketBool",
        default_value=False,
        description="Drops hitting the Colliders stay on them, sliding down and dripping",
    )
    add_input(
        ng,
        "Surface Amount",
        "NodeSocketFloat",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Chance of each drop hitting the Colliders to stay on them",
    )
    add_input(
        ng,
        "Surface Size",
        "NodeSocketFloat",
        default_value=2.0,
        min_value=0.0,
        max_value=100.0,
        description="Radius of the drops on the surface, relative to the falling ones",
    )
    add_input(
        ng,
        "Slide Speed",
        "NodeSocketFloat",
        default_value=0.08,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the drops sliding down vertical surfaces, in m/s, the drops "
        "varying between still and this speed",
    )
    add_input(
        ng,
        "Surface Lifetime",
        "NodeSocketFloat",
        default_value=5.0,
        min_value=0.01,
        max_value=1000.0,
        subtype="TIME_ABSOLUTE",
        description="Seconds the drops stay on the surface, unless they drip before",
    )
    arrange_interface(
        ng,
        (
            (
                None,
                "Surface Drops",
                True,
                "Surface Drops",
                ("Surface Amount", "Surface Size", "Slide Speed", "Surface Lifetime"),
            ),
        ),
    )


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Rain falling in the box, cylinder or cone of the Control, splashing on the Colliders "
        "and the floor"
    )
    build_interface(ng)

    t = Tree(ng)
    t.section("Spaces", row=True)
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    time = t.node("GeometryNodeInputSceneTime", -2, -3).outputs

    # Control cube, from its local space to the one of the Rain object
    info = t.node(
        "GeometryNodeObjectInfo", 0, 0, {"Object": inputs["Control"]}, transform_space="RELATIVE"
    )
    control = info.outputs["Transform"]
    to_control = t.node("FunctionNodeInvertMatrix", 1, 0, {"Matrix": control}).outputs["Matrix"]

    # Velocities from world to object space
    self_object = t.node("GeometryNodeSelfObject", 0, -2).outputs[0]
    self_info = t.node(
        "GeometryNodeObjectInfo", 1, -2, {"Object": self_object}, transform_space="ORIGINAL"
    )
    to_self = t.node("FunctionNodeInvertMatrix", 2, -2, {0: self_info.outputs["Transform"]})

    def world_direction(vector, x, y):
        return t.node(
            "FunctionNodeTransformDirection",
            x,
            y,
            {"Transform": to_self.outputs[0], "Direction": vector},
        ).outputs[0]

    wind = world_direction(inputs["Wind"], 4, -4)
    gravity = world_direction(inputs["Gravity"], 4, -6)

    # Faces of the shape, of radius 1: a square, or a disc. The Cone top is smaller
    grid = t.node("GeometryNodeMeshGrid", 0, 4, {"Size X": 2.0, "Size Y": 2.0}).outputs["Mesh"]
    disc = t.node(
        "GeometryNodeMeshCircle", 0, 6, {"Vertices": 48, "Radius": 1.0}, fill_type="TRIANGLE_FAN"
    ).outputs["Mesh"]
    shape = t.node("GeometryNodeMenuSwitch", 1, 4, data_type="GEOMETRY")
    shape.enum_items.clear()
    for name, face in (("Box", grid), ("Cylinder", disc), ("Cone", disc)):
        shape.enum_items.new(name)
        t.connect(face, shape.inputs[name])
    t.connect(inputs["Shape"], shape.inputs["Menu"])
    top_radius = t.node(
        "GeometryNodeSwitch",
        2,
        6,
        {"Switch": shape.outputs["Cone"], "False": 1.0, "True": inputs["Top Radius"]},
        input_type="FLOAT",
    ).outputs[0]
    top_scale = t.node(
        "ShaderNodeCombineXYZ", 3, 6, {"X": top_radius, "Y": top_radius, "Z": 1.0}
    ).outputs[0]

    def face(geometry, z, scale, x, y):
        geometry = t.node(
            "GeometryNodeTransform",
            x,
            y,
            {"Geometry": geometry, "Translation": (0, 0, z), "Scale": scale},
        )
        return t.node(
            "GeometryNodeTransform",
            x + 1,
            y,
            {"Geometry": geometry.outputs[0], "Mode": "Matrix", "Transform": control},
        ).outputs[0]

    # The drops keep the spot of the unit face they start from, to fall to the same spot of the
    # bottom face, spreading in the Cone
    position = t.node("GeometryNodeInputPosition", 2, 3).outputs[0]
    spots = t.store(shape.outputs["Output"], "spot", "FLOAT_VECTOR", position, 2, 4)
    top = face(spots, 1.0, top_scale, 4, 4)
    floor = face(shape.outputs["Output"], -1.0, (1.0, 1.0, 1.0), 4, 7)

    # Outline of the shape in the viewport, edges only not to render
    ring = t.node(
        "GeometryNodeSwitch",
        2,
        10,
        {
            "Switch": shape.outputs["Box"],
            "False": t.node(
                "GeometryNodeCurvePrimitiveCircle", 1, 11, {"Resolution": 48, "Radius": 1.0}
            ).outputs["Curve"],
            "True": t.node(
                "GeometryNodeCurvePrimitiveQuadrilateral", 1, 10, {"Width": 2.0, "Height": 2.0}
            ).outputs["Curve"],
        },
        input_type="GEOMETRY",
    ).outputs[0]
    edges = t.node("GeometryNodeCurveToMesh", 3, 10, {"Curve": ring}).outputs[0]
    sides = t.node("GeometryNodeCurveToPoints", 3, 12, {"Curve": ring, "Count": 4}, mode="COUNT")
    sides = t.node("GeometryNodePointsToVertices", 4, 12, {"Points": sides.outputs["Points"]})
    sides = t.node(
        "GeometryNodeSetPosition",
        5,
        12,
        {"Geometry": sides.outputs[0], "Offset": (0.0, 0.0, -1.0)},
    ).outputs[0]
    # From the bottom to the top, narrower in the Cone
    narrow = t.math("SUBTRACT", top_radius, 1.0, x=5, y=14)
    rise = t.vmath(
        "MULTIPLY",
        t.node("GeometryNodeInputPosition", 5, 15).outputs[0],
        t.node("ShaderNodeCombineXYZ", 6, 14, {"X": narrow, "Y": narrow}).outputs[0],
        x=6,
        y=15,
    )
    rise = t.vmath("ADD", rise, (0.0, 0.0, 2.0), x=7, y=15)
    sides = t.node(
        "GeometryNodeExtrudeMesh", 7, 12, {"Mesh": sides, "Offset": rise}, mode="VERTICES"
    ).outputs["Mesh"]
    outline = t.node("GeometryNodeJoinGeometry", 8, 10)
    t.connect(face(edges, 1.0, top_scale, 5, 9), outline.inputs[0])
    t.connect(face(edges, -1.0, (1.0, 1.0, 1.0), 5, 11), outline.inputs[0])
    t.connect(
        t.node(
            "GeometryNodeTransform",
            8,
            12,
            {"Geometry": sides, "Mode": "Matrix", "Transform": control},
        ).outputs[0],
        outline.inputs[0],
    )
    outline = outline.outputs[0]

    # Seconds to fall through the middle, to fill the shape at the start
    def corner(z, x, y):
        return t.node(
            "FunctionNodeTransformPoint", x, y, {"Vector": (0, 0, z), "Transform": control}
        ).outputs[0]

    height = t.vmath("DISTANCE", corner(1.0, 0, -8), corner(-1.0, 0, -9), x=1, y=-8)
    fall_time = t.math("DIVIDE", height, inputs["Speed"], x=2, y=-8)
    # Drops per square meter of the bottom face, on the top one smaller in the Cone
    area = t.math("MULTIPLY", top_radius, top_radius, x=2, y=-10)
    density = t.math("DIVIDE", inputs["Density"], area, x=3, y=-10)

    def emit(density, seed, frame, x, y):
        """Drops on the top face, with their velocity, size and lifetime, emitted during the
        frame of the given seconds, or filling the shape without"""
        drops = t.node(
            "GeometryNodeDistributePointsOnFaces",
            x,
            y,
            {"Mesh": top, "Density": density, "Seed": seed},
            distribute_method="RANDOM",
        ).outputs["Points"]
        random = t.node(
            "FunctionNodeRandomValue", x, y - 3, {"Seed": seed}, data_type="FLOAT_VECTOR"
        )
        spread = t.vmath("SCALE", random.outputs[0], inputs["Randomness"], x=x + 1, y=y - 3)
        variation = t.node(
            "ShaderNodeSeparateXYZ",
            x + 2,
            y - 3,
            {0: t.vmath("SUBTRACT", (1.0, 1.0, 1.0), spread, x=x + 1.5, y=y - 3)},
        ).outputs

        # Path from the spot of the top face to the one of the bottom face
        spot = t.attribute("spot", "FLOAT_VECTOR", x, y - 6)
        path = t.vmath(
            "SCALE", spot, t.math("SUBTRACT", 1.0, top_radius, x=x, y=y - 7), x=x + 1, y=y - 6
        )
        path = t.vmath("ADD", path, (0.0, 0.0, -2.0), x=x + 2, y=y - 6)
        path = t.node(
            "FunctionNodeTransformDirection",
            x + 3,
            y - 6,
            {"Transform": control, "Direction": path},
        ).outputs[0]
        speed = t.math("MULTIPLY", inputs["Speed"], variation[0], x=x + 3, y=y - 4)
        velocity = t.vmath(
            "SCALE", t.vmath("NORMALIZE", path, x=x + 4, y=y - 6), speed, x=x + 5, y=y - 6
        )
        velocity = t.vmath("ADD", velocity, wind, x=x + 6, y=y - 6)
        size = t.math("MULTIPLY", inputs["Size"], variation[1], x=x + 3, y=y - 5)
        seconds = t.math(
            "DIVIDE", t.vmath("LENGTH", path, x=x + 4, y=y - 8), speed, x=x + 5, y=y - 8
        )
        lifetime = t.math("MULTIPLY_ADD", seconds, 2.0, 1.0, x=x + 6, y=y - 8)
        drops = t.store(drops, "velocity", "FLOAT_VECTOR", velocity, x + 7, y)
        drops = t.store(drops, "size", "FLOAT", size, x + 8, y)
        drops = t.store(drops, "lifetime", "FLOAT", lifetime, x + 9, y)
        # Spread along their path, as if it had been raining before the start, or as if they
        # were emitted during the frame, not to fall in a sheet each frame
        along = t.node("ShaderNodeSeparateXYZ", x + 7, y - 9, {0: random.outputs[0]}).outputs[2]
        if frame is None:
            offset = t.vmath("SCALE", path, along, x=x + 8, y=y - 9)
        else:
            along = t.math("MULTIPLY", along, frame, x=x + 8, y=y - 10)
            offset = t.vmath("SCALE", velocity, along, x=x + 8, y=y - 9)
        drops = t.node(
            "GeometryNodeSetPosition", x + 10, y, {"Geometry": drops, "Offset": offset}
        ).outputs[0]
        return drops

    t.section("Start", row=True)
    start = emit(t.math("MULTIPLY", density, fall_time, x=0, y=1), 0, None, 1, 0)

    t.section("Simulation", row=True)
    sim_in = t.node("GeometryNodeSimulationInput", 0, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 30, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(start, sim_in.inputs["Geometry"])
    dt = sim_in.outputs["Delta Time"]

    new = emit(t.math("MULTIPLY", density, dt, x=0, y=-3), time["Frame"], dt, 1, -3)
    drops = t.node("GeometryNodeJoinGeometry", 9, 0)
    t.connect(new, drops.inputs[0])
    t.connect(sim_in.outputs["Geometry"], drops.inputs[0])

    # Gravity only on the splashes, the drops already fall at their final speed
    splash = t.attribute("splash", "BOOLEAN", 9, -3)
    acceleration = t.vmath("SCALE", gravity, t.math("MULTIPLY", dt, splash, x=9, y=-4), x=10, y=-3)
    velocity = t.vmath(
        "ADD", t.attribute("velocity", "FLOAT_VECTOR", 10, -2), acceleration, x=11, y=-2
    )
    drops = t.store(drops.outputs[0], "velocity", "FLOAT_VECTOR", velocity, 11, 0)

    # Colliders, with the frames of their faces for the Surface Drops, only computed with them
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        9,
        -7,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    )
    colliders = t.node(
        "GeometryNodeRealizeInstances", 10, -7, {"Geometry": colliders.outputs[0]}
    ).outputs[0]
    frames = t.node("GeometryNodeCaptureAttribute", 11, -9, domain="FACE")
    for name in ("Center", "Normal", "Tangent"):
        frames.capture_items.new("VECTOR", name)
    t.connect(colliders, frames.inputs["Geometry"])
    # The center, the normal, and the direction to the first corner of each face
    center = t.node("GeometryNodeInputPosition", 9, -10).outputs[0]
    corner = t.node("GeometryNodeCornersOfFace", 9, -12, {"Sort Index": 0}).outputs["Corner Index"]
    vertex = t.node("GeometryNodeVertexOfCorner", 10, -12, {"Corner Index": corner}).outputs[0]
    first = t.node(
        "GeometryNodeSampleIndex",
        10,
        -11,
        {"Geometry": colliders, "Value": center, "Index": vertex},
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    tangent = t.vmath("NORMALIZE", t.vmath("SUBTRACT", first, center, x=11, y=-11), x=11.5, y=-11)
    t.connect(center, frames.inputs["Center"])
    t.connect(t.node("GeometryNodeInputNormal", 10, -13).outputs["Normal"], frames.inputs["Normal"])
    t.connect(tangent, frames.inputs["Tangent"])
    target = t.node(
        "GeometryNodeSwitch",
        12,
        -7,
        {"Switch": inputs["Surface Drops"], "False": colliders, "True": frames.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    floor = t.node(
        "GeometryNodeSwitch",
        10,
        -9,
        {"Switch": inputs["Floor"], "True": floor},
        input_type="GEOMETRY",
    ).outputs[0]

    # The drops on the surface do not fly
    stuck = t.attribute("stuck", "BOOLEAN", 11, -3)
    parts = t.node(
        "GeometryNodeSeparateGeometry",
        12,
        0,
        {"Geometry": drops, "Selection": stuck},
        domain="POINT",
    )

    # Collisions: the motion of this frame, cast against the colliders and the floor apart, not to
    # copy the colliders in a mesh with the floor each frame
    velocity = t.attribute("velocity", "FLOAT_VECTOR", 12, -4)
    length = t.math("MULTIPLY", t.vmath("LENGTH", velocity, x=12, y=-6), dt, x=13, y=-6)
    rays = [
        t.node(
            "GeometryNodeRaycast",
            14,
            y,
            {"Target Geometry": geometry, "Ray Direction": velocity, "Ray Length": length},
        ).outputs
        for geometry, y in ((target, -4), (floor, -7))
    ]
    nearer = t.math("LESS_THAN", rays[1]["Hit Distance"], rays[0]["Hit Distance"], x=15, y=-7)
    nearer = t.node(
        "FunctionNodeBooleanMath", 15.5, -7, {0: rays[1]["Is Hit"], 1: nearer}, operation="AND"
    ).outputs[0]
    on_collider = t.node(
        "FunctionNodeBooleanMath", 16, -6, {0: rays[0]["Is Hit"], 1: nearer}, operation="NIMPLY"
    ).outputs[0]
    capture = t.node("GeometryNodeCaptureAttribute", 17, 0, domain="POINT")
    for data_type, name in (
        ("BOOLEAN", "Is Hit"),
        ("VECTOR", "Hit Position"),
        ("VECTOR", "Hit Normal"),
        ("BOOLEAN", "Collider"),
    ):
        capture.capture_items.new(data_type, name)
    t.connect(
        t.node(
            "FunctionNodeBooleanMath",
            16,
            -3,
            {0: rays[0]["Is Hit"], 1: rays[1]["Is Hit"]},
            operation="OR",
        ).outputs[0],
        capture.inputs["Is Hit"],
    )
    hit = {
        name: t.node(
            "GeometryNodeSwitch",
            16,
            y,
            {"Switch": on_collider, "False": rays[1][name], "True": rays[0][name]},
            input_type="VECTOR",
        ).outputs[0]
        for name, y in (("Hit Position", -4), ("Hit Normal", -5))
    }
    # Facing the drops, on the side they hit of single sided or flipped faces
    back = t.math(
        "GREATER_THAN",
        t.vmath("DOT_PRODUCT", hit["Hit Normal"], velocity, x=16, y=-8),
        0.0,
        x=17,
        y=-8,
    )
    hit["Hit Normal"] = t.node(
        "GeometryNodeSwitch",
        17,
        -5,
        {
            "Switch": back,
            "False": hit["Hit Normal"],
            "True": t.vmath("SCALE", hit["Hit Normal"], -1.0, x=16.5, y=-6),
        },
        input_type="VECTOR",
    ).outputs[0]
    for name, value in hit.items():
        t.connect(value, capture.inputs[name])
    t.connect(on_collider, capture.inputs["Collider"])
    t.connect(parts.outputs["Inverted"], capture.inputs["Geometry"])
    separate = t.node(
        "GeometryNodeSeparateGeometry",
        18,
        0,
        {"Geometry": capture.outputs["Geometry"], "Selection": capture.outputs["Is Hit"]},
        domain="POINT",
    )

    # Drops hitting become droplets, bouncing away from the surface; droplets hitting vanish
    not_splash = t.node(
        "FunctionNodeBooleanMath",
        16,
        -3,
        {0: t.attribute("splash", "BOOLEAN", 15, -3)},
        operation="NOT",
    ).outputs[0]
    droplets = t.node(
        "GeometryNodeDuplicateElements",
        17,
        -2,
        {
            "Geometry": separate.outputs["Selection"],
            "Selection": not_splash,
            "Amount": inputs["Splashes"],
        },
        domain="POINT",
    ).outputs["Geometry"]
    hit_normal = capture.outputs["Hit Normal"]
    above = t.vmath("SCALE", hit_normal, inputs["Size"], x=17, y=-5)
    droplets = t.node(
        "GeometryNodeSetPosition",
        18,
        -2,
        {
            "Geometry": droplets,
            "Position": t.vmath("ADD", capture.outputs["Hit Position"], above, x=18, y=-5),
        },
    ).outputs[0]
    seed = t.math("ADD", time["Frame"], 0.5, x=17, y=-8)
    direction = t.node(
        "FunctionNodeRandomValue",
        18,
        -8,
        {"Min": (-0.8, -0.8, -0.8), "Max": (0.8, 0.8, 0.8), "Seed": seed},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    direction = t.vmath("NORMALIZE", t.vmath("ADD", hit_normal, direction, x=19, y=-8), x=20, y=-8)
    strength = t.node(
        "FunctionNodeRandomValue",
        18,
        -10,
        {"Min": 0.3, "Max": 1.0, "Seed": seed},
        data_type="FLOAT",
    ).outputs[0]
    speed = t.math("MULTIPLY", inputs["Splash Speed"], strength, x=20, y=-10)
    droplets = t.store(
        droplets, "velocity", "FLOAT_VECTOR", t.vmath("SCALE", direction, speed, x=21, y=-8), 19, -2
    )
    droplets = t.store(droplets, "splash", "BOOLEAN", True, 20, -2)
    droplets = t.store(droplets, "age", "FLOAT", 0.0, 21, -2)
    droplets = t.store(
        droplets,
        "lifetime",
        "FLOAT",
        t.math("MULTIPLY", inputs["Splash Lifetime"], strength, x=22, y=-10),
        22,
        -2,
    )
    size = t.math(
        "MULTIPLY", t.attribute("size", "FLOAT", 22, -6), inputs["Splash Size"], x=23, y=-6
    )
    droplets = t.store(
        droplets, "size", "FLOAT", t.math("MULTIPLY", size, strength, x=24, y=-6), 23, -2
    )

    # The rest moves, aging, until it expires or falls out of the cube
    offset = t.vmath("SCALE", t.attribute("velocity", "FLOAT_VECTOR", 17, 2), dt, x=18, y=2)
    move = t.node(
        "GeometryNodeSetPosition",
        19,
        1,
        {"Geometry": separate.outputs["Inverted"], "Offset": offset},
    )
    age = t.math("ADD", t.attribute("age", "FLOAT", 19, 3), dt, x=20, y=3)
    rest = t.store(move.outputs[0], "age", "FLOAT", age, 21, 1)
    expired = t.math(
        "GREATER_THAN",
        t.attribute("age", "FLOAT", 22, 3),
        t.attribute("lifetime", "FLOAT", 22, 4),
        x=23,
        y=3,
    )
    position = t.node("GeometryNodeInputPosition", 22, 6).outputs[0]
    local = t.node(
        "FunctionNodeTransformPoint", 23, 6, {"Vector": position, "Transform": to_control}
    ).outputs[0]
    below = t.math(
        "LESS_THAN", t.node("ShaderNodeSeparateXYZ", 24, 6, {0: local}).outputs[2], -1.0, x=25, y=6
    )
    lost = t.node("FunctionNodeBooleanMath", 26, 4, {0: expired, 1: below}, operation="OR")
    rest = t.node(
        "GeometryNodeDeleteGeometry",
        27,
        1,
        {"Geometry": rest, "Selection": lost.outputs[0]},
        domain="POINT",
    ).outputs[0]
    surface = surface_drops(
        t, inputs, time, dt, gravity, frames, parts.outputs["Selection"], separate, capture
    )
    result = t.node("GeometryNodeJoinGeometry", 28, 0)
    t.connect(rest, result.inputs[0])
    t.connect(droplets, result.inputs[0])
    t.connect(surface, result.inputs[0])
    t.connect(result.outputs[0], sim_out.inputs["Geometry"])

    # Drops as streaks along their motion, droplets as points
    t.section("Output", row=True)
    separate = t.node(
        "GeometryNodeSeparateGeometry",
        0,
        0,
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Selection": t.attribute("splash", "BOOLEAN", -1, -2),
        },
        domain="POINT",
    )
    falling = t.node(
        "GeometryNodeSeparateGeometry",
        1,
        -1,
        {
            "Geometry": separate.outputs["Inverted"],
            "Selection": t.attribute("stuck", "BOOLEAN", 0, -2),
        },
        domain="POINT",
    )
    # Thin streak blurred by the motion, its head on the drop and trailing behind it, with the
    # position along it for the material to fade its ends
    shape = t.node(
        "GeometryNodeMeshUVSphere", -2, -4, {"Segments": 12, "Rings": 8, "Radius": 1.0}
    ).outputs["Mesh"]
    shape = t.node("GeometryNodeSetShadeSmooth", -1, -4, {"Geometry": shape}).outputs[0]
    along = t.node(
        "ShaderNodeSeparateXYZ", -1, -6, {0: t.node("GeometryNodeInputPosition", -2, -6).outputs[0]}
    ).outputs["Z"]
    shape = t.store(shape, "rain_streak", "FLOAT", along, 0, -4)
    shape = t.node(
        "GeometryNodeSetPosition", 0.5, -4, {"Geometry": shape, "Offset": (0.0, 0.0, -1.0)}
    ).outputs[0]
    shape = t.store(shape, "rain_opacity", "FLOAT", inputs["Opacity"], 0.5, -4)
    shape = t.node(
        "GeometryNodeSetMaterial",
        1,
        -4,
        {"Geometry": shape, "Material": inputs["Material"]},
    )
    rotation = t.node(
        "FunctionNodeAlignRotationToVector",
        1,
        -6,
        {"Vector": t.attribute("velocity", "FLOAT_VECTOR", 0, -6)},
        axis="Z",
    )
    size = t.attribute("size", "FLOAT", 0, -8)
    scale = t.node(
        "ShaderNodeCombineXYZ",
        2,
        -8,
        {"X": size, "Y": size, "Z": t.math("MULTIPLY", size, inputs["Stretch"], x=1, y=-9)},
    )
    streaks = t.node(
        "GeometryNodeInstanceOnPoints",
        3,
        0,
        {
            "Points": falling.outputs["Inverted"],
            "Instance": shape.outputs[0],
            "Rotation": rotation.outputs[0],
            "Scale": scale.outputs[0],
        },
    )
    droplets = t.node(
        "GeometryNodeSetPointRadius",
        2,
        2,
        {"Points": separate.outputs["Selection"], "Radius": t.attribute("size", "FLOAT", 1, 3)},
    )
    droplets = t.store(droplets.outputs[0], "rain_opacity", "FLOAT", inputs["Opacity"], 2.5, 2)
    droplets = t.node(
        "GeometryNodeSetMaterial",
        3,
        2,
        {"Geometry": droplets, "Material": inputs["Material"]},
    )
    # Drops on the surface: flattened on it, stretched along their sliding, shrinking at the end
    blob = t.node(
        "GeometryNodeMeshUVSphere", 0, -12, {"Segments": 10, "Rings": 6, "Radius": 1.0}
    ).outputs["Mesh"]
    blob = t.node("GeometryNodeSetShadeSmooth", 1, -12, {"Geometry": blob}).outputs[0]
    # More visible than the streaks, as beads on the surface
    beads = t.math("MULTIPLY", inputs["Opacity"], 2.5, x=1, y=-13, clamp=True)
    blob = t.store(blob, "rain_opacity", "FLOAT", beads, 1.5, -12)
    blob = t.node(
        "GeometryNodeSetMaterial", 2, -12, {"Geometry": blob, "Material": inputs["Material"]}
    ).outputs[0]
    velocity = t.attribute("velocity", "FLOAT_VECTOR", 0, -16)
    rotation = t.node(
        "FunctionNodeAlignRotationToVector",
        1,
        -14,
        {"Vector": t.attribute("normal", "FLOAT_VECTOR", 0, -14)},
        axis="Z",
    ).outputs[0]
    rotation = t.node(
        "FunctionNodeAlignRotationToVector",
        2,
        -14,
        {"Rotation": rotation, "Vector": velocity},
        axis="X",
        pivot_axis="Z",
    ).outputs[0]
    stretch = t.math("DIVIDE", t.vmath("LENGTH", velocity, x=1, y=-16), 0.05, x=2, y=-16)
    stretch = t.math("MINIMUM", stretch, 2.0, x=3, y=-16)
    stretch = t.math("ADD", stretch, 1.0, x=4, y=-16)
    progress = t.math(
        "DIVIDE",
        t.attribute("age", "FLOAT", 0, -18),
        t.attribute("lifetime", "FLOAT", 0, -19),
        x=1,
        y=-18,
    )
    shrink = t.math(
        "SUBTRACT", 1.0, t.math("POWER", progress, 3.0, x=2, y=-18), x=3, y=-18, clamp=True
    )
    radius = t.math("MULTIPLY", t.attribute("size", "FLOAT", 3, -19), shrink, x=4, y=-18)
    scale = t.node(
        "ShaderNodeCombineXYZ",
        5,
        -16,
        {
            "X": t.math("MULTIPLY", radius, stretch, x=5, y=-17),
            "Y": radius,
            "Z": t.math("MULTIPLY", radius, 0.5, x=5, y=-18),
        },
    ).outputs[0]
    surface = t.node(
        "GeometryNodeInstanceOnPoints",
        6,
        -12,
        {
            "Points": falling.outputs["Selection"],
            "Instance": blob,
            "Rotation": rotation,
            "Scale": scale,
        },
    ).outputs[0]

    output = t.node("GeometryNodeJoinGeometry", 4, 0)
    t.connect(surface, output.inputs[0])
    t.connect(streaks.outputs[0], output.inputs[0])
    t.connect(droplets.outputs[0], output.inputs[0])
    t.connect(outline, output.inputs[0])
    t.node("NodeGroupOutput", 5, 0, {0: output.outputs[0]})

    t.arrange()
    return ng


def surface_drops(t, inputs, time, dt, gravity, frames, stuck, hits, capture):
    """Drops staying on the Colliders where they hit them, following the faces they are on as the
    Colliders move, sliding down, and dripping from the edges and the surfaces facing down. Only
    computed with the Surface Drops on, the one costly step being the nearest face of each drop"""
    t.section("Surface Drops", row=True)
    faces = frames.outputs["Geometry"]

    def frame(x, y):
        """Center, normal, tangent and side of the face of each drop"""
        face = t.attribute("face", "INT", x, y)
        center, normal, tangent = (
            t.node(
                "GeometryNodeSampleIndex",
                x + 1,
                y - i,
                {"Geometry": faces, "Value": frames.outputs[name], "Index": face},
                data_type="FLOAT_VECTOR",
                domain="FACE",
            ).outputs[0]
            for i, name in enumerate(("Center", "Normal", "Tangent"))
        )
        # On the side of the face the drop hit, of single sided or flipped faces
        normal = t.node(
            "GeometryNodeSwitch",
            x + 2,
            y - 1,
            {
                "Switch": t.attribute("flip", "BOOLEAN", x + 1, y - 4),
                "False": normal,
                "True": t.vmath("SCALE", normal, -1.0, x=x + 1.5, y=y - 4),
            },
            input_type="VECTOR",
        ).outputs[0]
        return center, normal, tangent, t.vmath("CROSS_PRODUCT", normal, tangent, x=x + 2, y=y)

    def attach(geometry, x, y):
        """The face nearest to the drops, stored once, and their spot in its frame, with the
        height above it in Z"""
        face = t.node(
            "GeometryNodeSampleNearest", x, y - 1, {"Geometry": faces}, domain="FACE"
        ).outputs[0]
        geometry = t.store(geometry, "face", "INT", face, x + 1, y)
        center, normal, tangent, side = frame(x + 1, y - 2)
        position = t.node("GeometryNodeInputPosition", x + 2, y - 6).outputs[0]
        offset = t.vmath("SUBTRACT", position, center, x=x + 3, y=y - 6)
        spot = t.node(
            "ShaderNodeCombineXYZ",
            x + 4,
            y - 3,
            {
                "X": t.vmath("DOT_PRODUCT", offset, tangent, x=x + 3.5, y=y - 3),
                "Y": t.vmath("DOT_PRODUCT", offset, side, x=x + 3.5, y=y - 4),
                "Z": t.vmath("DOT_PRODUCT", offset, normal, x=x + 3.5, y=y - 5),
            },
        ).outputs[0]
        return t.store(geometry, "spot", "FLOAT_VECTOR", spot, x + 5, y)

    def place(lift, x, y):
        """Position of the spot on the face of each drop, lifted along its normal"""
        center, normal, tangent, side = frame(x, y)
        spot = t.node(
            "ShaderNodeSeparateXYZ",
            x,
            y - 5,
            {0: t.attribute("spot", "FLOAT_VECTOR", x - 1, y - 5)},
        ).outputs
        position = t.vmath(
            "ADD", center, t.vmath("SCALE", tangent, spot["X"], x=x + 2, y=y - 4), x=x + 3, y=y - 4
        )
        position = t.vmath(
            "ADD", position, t.vmath("SCALE", side, spot["Y"], x=x + 3, y=y - 5), x=x + 4, y=y - 4
        )
        position = t.vmath(
            "ADD", position, t.vmath("SCALE", normal, lift, x=x + 4, y=y - 6), x=x + 5, y=y - 4
        )
        return position, normal

    # Some of the drops hitting the Colliders stay where they hit
    seed = t.math("ADD", time["Frame"], 0.25, x=0, y=-3)
    random = t.node("FunctionNodeRandomValue", 1, -3, {"Seed": seed}, data_type="FLOAT_VECTOR")
    random = t.node("ShaderNodeSeparateXYZ", 2, -3, {0: random.outputs[0]}).outputs
    chance = t.math("LESS_THAN", random["X"], inputs["Surface Amount"], x=3, y=-3)
    stay = t.node(
        "FunctionNodeBooleanMath",
        4,
        -2,
        {0: capture.outputs["Collider"], 1: chance},
        operation="AND",
    ).outputs[0]
    stay = t.node(
        "FunctionNodeBooleanMath",
        5,
        -2,
        {0: stay, 1: t.attribute("splash", "BOOLEAN", 4, -4)},
        operation="NIMPLY",
    ).outputs[0]
    new = t.node(
        "GeometryNodeSeparateGeometry",
        6,
        0,
        {"Geometry": hits.outputs["Selection"], "Selection": stay},
        domain="POINT",
    ).outputs["Selection"]
    new = t.node(
        "GeometryNodeSetPosition",
        7,
        0,
        {"Geometry": new, "Position": capture.outputs["Hit Position"]},
    ).outputs[0]
    new = t.store(new, "stuck", "BOOLEAN", True, 8, 0)
    new = t.store(new, "age", "FLOAT", 0.0, 9, 0)
    size = t.math("MULTIPLY_ADD", random["Y"], 0.4, 0.6, x=8, y=-3)
    size = t.math("MULTIPLY", size, inputs["Surface Size"], x=9, y=-3)
    size = t.math("MULTIPLY", size, t.attribute("size", "FLOAT", 9, -4), x=10, y=-3)
    new = t.store(new, "size", "FLOAT", size, 10, 0)
    lifetime = t.math("MULTIPLY_ADD", random["Z"], 0.5, 0.5, x=10, y=-5)
    lifetime = t.math("MULTIPLY", lifetime, inputs["Surface Lifetime"], x=11, y=-5)
    new = t.store(new, "lifetime", "FLOAT", lifetime, 11, 0)
    # Most of them barely sliding, some running down
    slide = t.node(
        "FunctionNodeRandomValue",
        11,
        -7,
        {"Seed": t.math("ADD", seed, 0.5, x=10, y=-7)},
        data_type="FLOAT",
    ).outputs[0]
    new = t.store(new, "slide", "FLOAT", t.math("MULTIPLY", slide, slide, x=12, y=-7), 12, 0)
    new = attach(new, 13, 0)
    _, normal, _, _ = frame(18, -3)
    falling = t.vmath(
        "DOT_PRODUCT", normal, t.attribute("velocity", "FLOAT_VECTOR", 18, -6), x=19, y=-6
    )
    new = t.store(new, "flip", "BOOLEAN", t.math("GREATER_THAN", falling, 0.0, x=19, y=-5), 18.5, 0)
    drops = t.node("GeometryNodeJoinGeometry", 19, 0)
    t.connect(new, drops.inputs[0])
    t.connect(stuck, drops.inputs[0])

    # Sliding along the gravity on their face, from its spot on it as the Colliders moved
    position, normal = place(0.0, 19, -3)
    along = t.vmath(
        "SCALE",
        normal,
        t.vmath("DOT_PRODUCT", gravity, normal, x=21, y=-10),
        x=22,
        y=-10,
    )
    slope = t.vmath("SUBTRACT", gravity, along, x=23, y=-10)
    weight = t.math("MAXIMUM", t.vmath("LENGTH", gravity, x=21, y=-12), 1e-4, x=22, y=-12)
    speed = t.math("DIVIDE", inputs["Slide Speed"], weight, x=23, y=-12)
    speed = t.math("MULTIPLY", speed, t.attribute("slide", "FLOAT", 23, -13), x=24, y=-12)
    drops = t.store(
        drops.outputs[0],
        "velocity",
        "FLOAT_VECTOR",
        t.vmath("SCALE", slope, speed, x=25, y=-10),
        25,
        0,
    )
    motion = t.vmath("SCALE", t.attribute("velocity", "FLOAT_VECTOR", 25, -4), dt, x=26, y=-4)
    drops = t.node(
        "GeometryNodeSetPosition",
        26,
        0,
        {"Geometry": drops, "Position": t.vmath("ADD", position, motion, x=27, y=-4)},
    ).outputs[0]
    drops = attach(drops, 27, 0)

    # On the surface, a little above it, facing its normal
    size = t.attribute("size", "FLOAT", 32, -3)
    position, normal = place(t.math("MULTIPLY", size, 0.3, x=32, y=-4), 33, -3)
    drops = t.store(drops, "normal", "FLOAT_VECTOR", normal, 33, 0)
    drops = t.node("GeometryNodeSetPosition", 34, 0, {"Geometry": drops, "Position": position})
    age = t.math("ADD", t.attribute("age", "FLOAT", 34, -2), dt, x=35, y=-2)
    drops = t.store(drops.outputs[0], "age", "FLOAT", age, 35, 0)

    # Dripping from the surfaces facing down, and off the edges, or away from the Colliders
    down = t.vmath("NORMALIZE", gravity, x=35, y=-6)
    facing = t.vmath("DOT_PRODUCT", t.attribute("normal", "FLOAT_VECTOR", 35, -7), down, x=36, y=-6)
    drip = t.math("GREATER_THAN", facing, 0.5, x=37, y=-6)
    height = t.node(
        "ShaderNodeSeparateXYZ", 36, -8, {0: t.attribute("spot", "FLOAT_VECTOR", 35, -8)}
    ).outputs["Z"]
    height = t.math("ABSOLUTE", height, x=37, y=-8)
    reach = t.math("MAXIMUM", t.math("MULTIPLY", size, 5.0, x=36, y=-9), 0.005, x=37, y=-9)
    off = t.math("GREATER_THAN", height, reach, x=38, y=-8)
    fall = t.node("FunctionNodeBooleanMath", 39, -6, {0: drip, 1: off}, operation="OR")
    split = t.node(
        "GeometryNodeSeparateGeometry",
        40,
        0,
        {"Geometry": drops, "Selection": fall.outputs[0]},
        domain="POINT",
    )
    away = t.vmath(
        "SCALE",
        t.attribute("normal", "FLOAT_VECTOR", 40, -3),
        t.math("MULTIPLY", t.attribute("size", "FLOAT", 40, -5), 2.0, x=41, y=-5),
        x=41,
        y=-3,
    )
    falling = t.node(
        "GeometryNodeSetPosition", 41, -1, {"Geometry": split.outputs["Selection"], "Offset": away}
    ).outputs[0]
    falling = t.store(falling, "stuck", "BOOLEAN", False, 42, -1)
    falling = t.store(falling, "splash", "BOOLEAN", True, 43, -1)
    falling = t.store(falling, "age", "FLOAT", 0.0, 44, -1)
    falling = t.store(falling, "lifetime", "FLOAT", 2.0, 45, -1)
    expired = t.math(
        "GREATER_THAN",
        t.attribute("age", "FLOAT", 41, 2),
        t.attribute("lifetime", "FLOAT", 41, 3),
        x=42,
        y=2,
    )
    staying = t.node(
        "GeometryNodeDeleteGeometry",
        43,
        1,
        {"Geometry": split.outputs["Inverted"], "Selection": expired},
        domain="POINT",
    ).outputs[0]
    surface = t.node("GeometryNodeJoinGeometry", 46, 0)
    t.connect(staying, surface.inputs[0])
    t.connect(falling, surface.inputs[0])
    # Lazy: nothing above is computed without the Surface Drops
    return t.node(
        "GeometryNodeSwitch",
        47,
        0,
        {"Switch": inputs["Surface Drops"], "True": surface.outputs[0]},
        input_type="GEOMETRY",
    ).outputs[0]


def build_material():
    material = bpy.data.materials.new(MATERIAL)
    # Light passing through the drops, not their shadows
    material.use_transparent_shadow = True
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree)

    # Clear water: what is behind shows through, with the reflections of the lights and the
    # world added, stronger at the edges. No diffuse color to look white, nor refraction that is
    # dark in EEVEE on drops this small
    opacity = t.node("ShaderNodeAttribute", -6, 0, attribute_name="rain_opacity").outputs["Fac"]
    streak = t.node("ShaderNodeAttribute", -6, -2, attribute_name="rain_streak").outputs["Fac"]
    # Fading at the ends of the streaks, the droplets without the attribute not fading
    fade = t.math("SUBTRACT", 1.0, t.math("MULTIPLY", streak, streak, x=-5, y=-2), x=-4, y=-2)
    visible = t.math("MULTIPLY", opacity, fade, x=-3, y=-1)

    fresnel = t.node("ShaderNodeLayerWeight", -6, 2, {"Blend": 0.3}).outputs["Fresnel"]
    reflection = t.math("MULTIPLY_ADD", fresnel, 0.85, 0.15, x=-4, y=2)
    reflection = t.math("MULTIPLY", reflection, visible, x=-2, y=2)
    glossy = t.node(
        "ShaderNodeBsdfAnisotropic", 0, 2, {"Color": reflection, "Roughness": 0.05}
    ).outputs[0]
    # A little darker through the drops, to see them where nothing reflects
    through = t.math("MULTIPLY_ADD", visible, -0.15, 1.0, x=-2, y=-1)
    transparent = t.node("ShaderNodeBsdfTransparent", 0, 0, {"Color": through}).outputs[0]
    shader = t.node("ShaderNodeAddShader", 2, 1, {0: transparent, 1: glossy})
    t.node("ShaderNodeOutputMaterial", 4, 1, {"Surface": shader.outputs[0]})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material()))
