# Build dust_puff.blend: the Dust Puff node group and its dust material
# Usage: Blender --background --factory-startup --python dust_puff_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write

RESOURCE = "dust_puff.blend"
NODE_GROUP = "MustardUI Dust Puff"
DUST = "MustardUI Dust Puff Dust"
# Depth under the mesh the Colliders still touch it from
REACH = 0.1
# Fastest hit, not to burst when the Colliders jump
MAX_SPEED = 10.0
GRAVITY = 9.81
# Upward share of the direction of the dust blown out, and share of the Colliders speed carried
LIFT = 0.3
CARRIED = 0.2
# Share of the lift and scatter, and of the drag, taken off in a Ring, and seconds the puffs
# travel before feeding the dust
RING_FLAT = 0.8
RING_GLIDE = 0.5
RING_DELAY = 0.08
# Slowing of the puffs by the air per second, and seconds they feed the dust for
AIR_DRAG = 6.0
FEED_TIME = 0.25
# Lifetimes the puffs are kept, giving the floor under the dust until it fades
PUFF_LIVES = 10.0
# Grains: air drag per second, bounce and friction on the mesh, speed they rest below
GRAIN_DRAG = 0.5
BOUNCE = 0.2
FRICTION = 0.5
REST_SPEED = 0.2
# Share of the grain lifetime they shrink away in
SHRINK = 0.2
# Size past which the dust gets thinner per meter, by the square root, for large clouds
# not to render solid
THIN_SIZE = 0.1


def build_inputs(ng):
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects kicking up dust where they hit the mesh, e.g. the body and the shoes",
    )
    add_input(
        ng, "Start Frame", "NodeSocketInt", default_value=1, description="First simulated frame"
    )
    add_input(
        ng,
        "Amount",
        "NodeSocketFloat",
        default_value=3000.0,
        min_value=0.0,
        description="Puffs of dust per square meter of the Colliders hitting the mesh at 1 m/s",
    )
    add_input(
        ng,
        "Min Speed",
        "NodeSocketFloat",
        default_value=0.15,
        min_value=0.0,
        description="Speed of the Colliders, in m/s, below which they kick up nothing",
    )
    add_input(
        ng,
        "Scuff",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Share of the speed of the Colliders sliding on the mesh kicking up dust",
    )
    add_input(
        ng,
        "Contact",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.01,
        min_value=0.0,
        description="Distance from the mesh the Colliders touch it at",
    )
    add_input(
        ng,
        "Burst",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the dust and the grains blown out from under the Colliders, "
        "relative to their hit",
    )
    add_input(
        ng,
        "Ring",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.0,
        min_value=0.0,
        max_value=1.0,
        description="Dust blown out flat at even speeds, opening in a ring around the Colliders, "
        "instead of billowing around them",
    )
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the random puffs and grains")

    panel = ng.interface.new_panel("Dust")
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.06,
        min_value=0.001,
        description="Size of the puffs of dust, growing with their age",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=2.0,
        min_value=0.01,
        description="Seconds the dust lasts, in average",
    )
    add_input(
        ng,
        "Rise",
        "NodeSocketFloat",
        panel,
        default_value=0.02,
        description="Speed of the dust rising, in m/s, settling to the mesh when negative",
    )
    add_input(
        ng,
        "Swirl",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Turbulence of the air carrying the dust",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        panel,
        default_value=64,
        min_value=16,
        max_value=256,
        description="Cells of the dust along its largest side, more for finer and slower dust",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        panel,
        default_value=(0.6, 0.55, 0.5, 1.0),
        description="Color of the dust",
    )
    add_input(
        ng,
        "Dust Material",
        "NodeSocketMaterial",
        panel,
        description="Volume material of the dust",
    ).default_value = bpy.data.materials.get(DUST)

    panel = ng.interface.new_panel("Grains", default_closed=True)
    add_input(
        ng,
        "Grains",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Grains thrown up with the dust, with the material of the mesh",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Grain Amount",
        "NodeSocketFloat",
        panel,
        default_value=1500.0,
        min_value=0.0,
        description="Grains per square meter of the Colliders hitting the mesh at 1 m/s",
    )
    add_input(
        ng,
        "Grain Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.004,
        min_value=0.0001,
        description="Size of the grains, in average",
    )
    add_input(
        ng,
        "Grain Lifetime",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=4.0,
        min_value=0.01,
        description="Seconds the grains stay, in average, shrinking away at the end",
    )


def sample(t, geometry, value, index, data_type, x, y):
    return t.node(
        "GeometryNodeSampleIndex",
        x,
        y,
        {"Geometry": geometry, "Value": value, "Index": index},
        data_type=data_type,
    ).outputs[0]


def switch(t, condition, false, true, input_type, x, y):
    return t.node(
        "GeometryNodeSwitch",
        x,
        y,
        {"Switch": condition, "False": false, "True": true},
        input_type=input_type,
    ).outputs[0]


def positions(t, mesh, x, y):
    """Points at the vertices of the mesh without attributes, the state kept for the velocities"""
    count = t.node("GeometryNodeAttributeDomainSize", x, y - 1, {"Geometry": mesh}).outputs[
        "Point Count"
    ]
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    index = t.node("GeometryNodeInputIndex", x, y - 3).outputs[0]
    position = sample(t, mesh, position, index, "FLOAT_VECTOR", x + 1, y - 2)
    return t.node("GeometryNodePoints", x + 2, y, {"Count": count, "Position": position}).outputs[0]


def velocity(t, geometry, previous, dt, x, y):
    """Geometry with the velocity of its points from their previous positions"""
    position = t.node("GeometryNodeInputPosition", x, y - 1).outputs[0]
    index = t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]
    moved = t.vmath(
        "SUBTRACT",
        position,
        sample(t, previous, position, index, "FLOAT_VECTOR", x + 1, y - 2),
        x=x + 2,
        y=y - 1,
    )
    # Not when the points changed
    counts = [
        t.node(
            "GeometryNodeAttributeDomainSize", x, y - 4 - i, {"Geometry": g}, component=component
        ).outputs["Point Count"]
        for i, (g, component) in enumerate(((geometry, "MESH"), (previous, "POINTCLOUD")))
    ]
    same = t.node(
        "FunctionNodeCompare",
        x + 1,
        y - 4,
        {"A": counts[0], "B": counts[1]},
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    scale = t.math("MULTIPLY", t.math("DIVIDE", 1.0, dt, x=x + 2, y=y - 3), same, x=x + 3, y=y - 3)
    moving = t.vmath("SCALE", moved, scale, x=x + 3, y=y - 1)
    return t.store(geometry, ".dust_velocity", "FLOAT_VECTOR", moving, x + 4, y)


def surface(t, ground, at, x, y):
    """Closest point of the ground to the position, its normal there and the height above it"""
    nearest = t.node(
        "GeometryNodeProximity",
        x,
        y,
        {"Geometry": ground, "Sample Position": at},
        target_element="FACES",
    ).outputs["Position"]
    normal = t.node(
        "GeometryNodeSampleNearestSurface",
        x,
        y - 2,
        {
            "Mesh": ground,
            "Value": t.node("GeometryNodeInputNormal", x - 1, y - 3).outputs["Normal"],
            "Sample Position": at,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    offset = t.vmath("SUBTRACT", at, nearest, x=x + 1, y=y)
    height = t.vmath("DOT_PRODUCT", offset, normal, x=x + 2, y=y)
    return nearest, normal, offset, height


def along(t, vector, normal, x, y):
    """The vector without its part along the normal"""
    return t.vmath(
        "SUBTRACT",
        vector,
        t.vmath(
            "SCALE", normal, t.vmath("DOT_PRODUCT", vector, normal, x=x, y=y - 1), x=x + 1, y=y
        ),
        x=x + 2,
        y=y,
    )


def randomized(t, inputs, x, y):
    """Random values by the seed and an offset of it"""

    def random(low, high, seed, yy, data_type="FLOAT_VECTOR"):
        node = t.node(
            "FunctionNodeRandomValue",
            x + 1,
            y - yy,
            {"Min": low, "Max": high, "Seed": t.math("ADD", inputs["Seed"], seed, x=x, y=y - yy)},
            data_type=data_type,
        )
        return socket(node.outputs, "Value")

    return random


def contacts(t, colliders, ground, inputs, x, y):
    """Faces of the Colliders touching the ground with the speed of their hit, the closest point
    and normal of the ground, and the center of their patch"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    # Only the faces near the ground
    box = t.node("GeometryNodeBoundBox", x, y - 4, {"Geometry": ground}).outputs
    margin = t.math("ADD", inputs["Contact"], REACH, x=x, y=y - 6)
    low = t.vmath(
        "SUBTRACT",
        position,
        t.vmath("SUBTRACT", box["Min"], margin, x=x + 1, y=y - 4),
        x=x + 2,
        y=y - 4,
    )
    high = t.vmath(
        "SUBTRACT", t.vmath("ADD", box["Max"], margin, x=x + 1, y=y - 5), position, x=x + 2, y=y - 5
    )
    xyz = t.node(
        "ShaderNodeSeparateXYZ", x + 3, y - 4, {0: t.vmath("MINIMUM", low, high, x=x + 3, y=y - 5)}
    ).outputs
    outside = t.math(
        "LESS_THAN",
        t.math(
            "MINIMUM",
            t.math("MINIMUM", xyz["X"], xyz["Y"], x=x + 4, y=y - 4),
            xyz["Z"],
            x=x + 5,
            y=y - 4,
        ),
        0.0,
        x=x + 6,
        y=y - 4,
    )
    near = t.node(
        "GeometryNodeDeleteGeometry",
        x + 7,
        y,
        {"Geometry": colliders, "Selection": outside},
        domain="POINT",
    ).outputs[0]

    # Touching from under the ground to the Contact, not past its edges
    nearest, normal, offset, height = surface(t, ground, position, x + 7, y - 3)
    aside = t.vmath("LENGTH", along(t, offset, normal, x + 9, y - 5), x=x + 11, y=y - 5)
    touching = t.node(
        "FunctionNodeBooleanMath",
        x + 12,
        y - 3,
        {
            0: t.math("LESS_THAN", height, inputs["Contact"], x=x + 10, y=y - 3),
            1: t.math("GREATER_THAN", height, -REACH, x=x + 10, y=y - 4),
        },
        operation="AND",
    ).outputs[0]
    touching = t.node(
        "FunctionNodeBooleanMath",
        x + 13,
        y - 3,
        {0: touching, 1: t.math("LESS_THAN", aside, inputs["Contact"], x=x + 12, y=y - 5)},
        operation="AND",
    ).outputs[0]
    # The speed into the ground, and a share of the speed along it
    moving = t.attribute(".dust_velocity", "FLOAT_VECTOR", x + 9, y - 7)
    into = t.math(
        "MAXIMUM",
        t.math(
            "MULTIPLY",
            t.vmath("DOT_PRODUCT", moving, normal, x=x + 10, y=y - 7),
            -1.0,
            x=x + 11,
            y=y - 7,
        ),
        0.0,
        x=x + 12,
        y=y - 7,
    )
    sliding = t.vmath("LENGTH", along(t, moving, normal, x + 10, y - 8), x=x + 12, y=y - 8)
    hit = t.math(
        "MINIMUM",
        t.math("MULTIPLY_ADD", sliding, inputs["Scuff"], into, x=x + 13, y=y - 7),
        MAX_SPEED,
        x=x + 14,
        y=y - 7,
    )
    hit = t.math("MULTIPLY", hit, touching, x=x + 15, y=y - 6)
    near = t.store(near, ".dust_hit", "FLOAT", hit, x + 16, y)
    near = t.store(near, ".dust_ground", "FLOAT_VECTOR", nearest, x + 17, y)
    near = t.store(near, ".dust_normal", "FLOAT_VECTOR", normal, x + 18, y)
    # Faces with a point hitting fast enough
    strength = t.math(
        "SUBTRACT",
        t.attribute(".dust_hit", "FLOAT", x + 18, y - 3),
        inputs["Min Speed"],
        x=x + 19,
        y=y - 3,
    )
    near = t.node(
        "GeometryNodeDeleteGeometry",
        x + 20,
        y,
        {
            "Geometry": near,
            "Selection": t.math("LESS_THAN", strength, 0.0, x=x + 19.5, y=y - 3),
        },
        domain="FACE",
    ).outputs[0]
    near = t.store(
        near,
        ".dust_strength",
        "FLOAT",
        t.math("MAXIMUM", strength, 0.0, x=x + 20, y=y - 3),
        x + 21,
        y,
    )

    # Center of each patch, as each foot, the dust blown out from under it
    island = t.node("GeometryNodeInputMeshIsland", x + 21, y - 4).outputs["Island Index"]
    total = t.node(
        "GeometryNodeAccumulateField",
        x + 22,
        y - 3,
        {"Value": position, "Group ID": island},
        data_type="FLOAT_VECTOR",
    ).outputs["Total"]
    count = t.node(
        "GeometryNodeAccumulateField", x + 22, y - 5, {"Value": 1.0, "Group ID": island}
    ).outputs["Total"]
    center = t.vmath("DIVIDE", total, count, x=x + 23, y=y - 3)
    return t.store(near, ".dust_center", "FLOAT_VECTOR", center, x + 24, y)


def scattered(t, near, amount, seed, inputs, x, y):
    """Points on the hitting faces, as many as their strength, on the ground under them, with the
    direction out from under their patch"""
    points = t.node(
        "GeometryNodeDistributePointsOnFaces",
        x + 1,
        y,
        {
            "Mesh": near,
            "Density": t.math(
                "MULTIPLY",
                t.attribute(".dust_strength", "FLOAT", x, y - 3),
                amount,
                x=x + 0.5,
                y=y - 3,
            ),
            "Seed": t.math(
                "ADD",
                t.math("ADD", inputs["Seed"], seed, x=x - 1, y=y - 4),
                t.node("GeometryNodeInputSceneTime", x - 1, y - 5).outputs["Frame"],
                x=x,
                y=y - 4,
            ),
        },
        distribute_method="RANDOM",
    ).outputs["Points"]
    normal = t.attribute(".dust_normal", "FLOAT_VECTOR", x + 1, y - 6)
    out = along(
        t,
        t.vmath(
            "SUBTRACT",
            t.node("GeometryNodeInputPosition", x + 1, y - 7).outputs[0],
            t.attribute(".dust_center", "FLOAT_VECTOR", x + 1, y - 8),
            x=x + 2,
            y=y - 7,
        ),
        normal,
        x + 3,
        y - 7,
    )
    points = t.store(
        points, ".dust_out", "FLOAT_VECTOR", t.vmath("NORMALIZE", out, x=x + 5, y=y - 7), x + 6, y
    )
    return t.node(
        "GeometryNodeSetPosition",
        x + 7,
        y,
        {"Geometry": points, "Position": t.attribute(".dust_ground", "FLOAT_VECTOR", x + 6, y - 2)},
    ).outputs[0]


def thrown(t, random, lift, spread, seed, x, y):
    """Direction out from under the patch, spread at random along the ground, lifted"""
    normal = t.attribute(".dust_normal", "FLOAT_VECTOR", x, y - 1)
    scatter = along(t, random((-1, -1, -1), (1, 1, 1), seed, 0), normal, x + 1, y - 2)
    direction = t.vmath(
        "ADD",
        t.attribute(".dust_out", "FLOAT_VECTOR", x + 2, y),
        t.vmath("SCALE", scatter, spread, x=x + 3, y=y - 2),
        x=x + 4,
        y=y,
    )
    direction = t.vmath(
        "ADD", direction, t.vmath("SCALE", normal, lift, x=x + 4, y=y - 1), x=x + 5, y=y
    )
    return t.vmath("NORMALIZE", direction, x=x + 6, y=y)


def emit_puffs(t, near, ground, inputs, x, y):
    """Puffs of dust blown out from under the patches, faster the harder they hit"""
    random = randomized(t, inputs, x + 8, y - 8)
    puffs = scattered(t, near, inputs["Amount"], 10, inputs, x, y)
    # Flatter and less scattered in a ring
    flat = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", inputs["Ring"], RING_FLAT, x=x + 6, y=y - 5),
        x=x + 7,
        y=y - 5,
    )
    direction = thrown(
        t,
        random,
        t.math("MULTIPLY", flat, LIFT, x=x + 7, y=y - 6),
        t.math("MULTIPLY", flat, 0.7, x=x + 7, y=y - 7),
        11,
        x + 8,
        y - 4,
    )
    # Most near the patch, some blown far, not as a shell, or all fast, the puffs from the middle
    # trailing those from the rim in a ring
    billow = t.math("POWER", random(0.2, 1.0, 12, 2, "FLOAT"), 2.0, x=x + 10, y=y - 10)
    burst = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", random(0.7, 1.0, 14, 3, "FLOAT"), billow, x=x + 10, y=y - 9),
        inputs["Ring"],
        billow,
        x=x + 11,
        y=y - 9,
    )
    speed = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.attribute(".dust_hit", "FLOAT", x + 9, y - 11),
            inputs["Burst"],
            x=x + 10,
            y=y - 11,
        ),
        burst,
        x=x + 11,
        y=y - 10,
    )
    carried = t.vmath(
        "SCALE",
        along(
            t,
            t.attribute(".dust_velocity", "FLOAT_VECTOR", x + 9, y - 13),
            t.attribute(".dust_normal", "FLOAT_VECTOR", x + 9, y - 14),
            x + 10,
            y - 13,
        ),
        CARRIED,
        x=x + 12,
        y=y - 13,
    )
    moving = t.vmath(
        "ADD", t.vmath("SCALE", direction, speed, x=x + 12, y=y - 4), carried, x=x + 13, y=y - 4
    )
    # Lifted by half their size, over the ground
    lifted = t.vmath(
        "SCALE",
        t.attribute(".dust_normal", "FLOAT_VECTOR", x + 9, y - 16),
        t.math("MULTIPLY", inputs["Size"], 0.5, x=x + 9, y=y - 17),
        x=x + 10,
        y=y - 16,
    )
    puffs = t.node(
        "GeometryNodeSetPosition", x + 13, y, {"Geometry": puffs, "Offset": lifted}
    ).outputs[0]
    puffs = t.store(puffs, ".dust_velocity", "FLOAT_VECTOR", moving, x + 14, y)
    life = t.math(
        "MULTIPLY", random(0.6, 1.4, 13, 4, "FLOAT"), inputs["Lifetime"], x=x + 14, y=y - 12
    )
    puffs = t.store(puffs, ".dust_life", "FLOAT", life, x + 15, y)
    return t.store(puffs, ".dust_age", "FLOAT", 0.0, x + 16, y)


def emit_grains(t, near, ground, inputs, x, y):
    """Grains thrown up from under the patches, with the material of the ground there"""
    random = randomized(t, inputs, x + 8, y - 8)
    grains = scattered(t, near, inputs["Grain Amount"], 20, inputs, x, y)
    direction = thrown(
        t,
        random,
        t.math("ADD", 1.0, random(0.0, 1.0, 21, 6, "FLOAT"), x=x + 9, y=y - 3),
        0.5,
        22,
        x + 8,
        y - 4,
    )
    speed = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.attribute(".dust_hit", "FLOAT", x + 9, y - 11),
            inputs["Burst"],
            x=x + 10,
            y=y - 11,
        ),
        random(0.3, 1.0, 23, 2, "FLOAT"),
        x=x + 11,
        y=y - 10,
    )
    grains = t.store(
        grains,
        ".dust_velocity",
        "FLOAT_VECTOR",
        t.vmath("SCALE", direction, speed, x=x + 12, y=y - 4),
        x + 13,
        y,
    )
    # Flat chips of random sizes and turns
    size = t.math(
        "MULTIPLY", random(0.5, 1.5, 24, 4, "FLOAT"), inputs["Grain Size"], x=x + 12, y=y - 12
    )
    scale = t.vmath(
        "SCALE", random((0.8, 0.8, 0.4), (1.2, 1.2, 0.8), 25, 10), size, x=x + 13, y=y - 12
    )
    grains = t.store(grains, ".dust_scale", "FLOAT_VECTOR", scale, x + 14, y)
    grains = t.store(
        grains,
        ".dust_rotation",
        "QUATERNION",
        t.node(
            "FunctionNodeEulerToRotation",
            x + 14,
            y - 14,
            {0: random((0.0, 0.0, 0.0), (6.3, 6.3, 6.3), 26, 14)},
        ).outputs[0],
        x + 15,
        y,
    )
    material = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 14,
        y - 14,
        {
            "Mesh": ground,
            "Value": t.node("GeometryNodeInputMaterialIndex", x + 13, y - 15).outputs[0],
            "Sample Position": t.node("GeometryNodeInputPosition", x + 13, y - 16).outputs[0],
        },
        data_type="INT",
    ).outputs["Value"]
    grains = t.store(grains, ".dust_material", "INT", material, x + 16, y)
    life = t.math(
        "MULTIPLY", random(0.7, 1.3, 27, 16, "FLOAT"), inputs["Grain Lifetime"], x=x + 16, y=y - 12
    )
    grains = t.store(grains, ".dust_life", "FLOAT", life, x + 17, y)
    return t.store(grains, ".dust_age", "FLOAT", 0.0, x + 18, y)


def aged(t, points, lives, dt, x, y):
    """Points older by the frame, without those past their life times the lives"""
    age = t.math("ADD", t.attribute(".dust_age", "FLOAT", x, y - 2), dt, x=x + 1, y=y - 2)
    points = t.store(points, ".dust_age", "FLOAT", age, x + 1, y)
    old = t.math(
        "GREATER_THAN",
        t.attribute(".dust_age", "FLOAT", x + 1, y - 3),
        t.math(
            "MULTIPLY", t.attribute(".dust_life", "FLOAT", x + 1, y - 4), lives, x=x + 2, y=y - 4
        ),
        x=x + 3,
        y=y - 3,
    )
    return t.node(
        "GeometryNodeDeleteGeometry", x + 4, y, {"Geometry": points, "Selection": old}
    ).outputs[0]


def puff_step(t, puffs, ground, inputs, dt, x, y):
    """Puffs slowed by the air and rising with it, spreading along the ground they reach, with
    the height of the ground under them"""
    position = t.node("GeometryNodeInputPosition", x, y - 6).outputs[0]
    moving = t.attribute(".dust_velocity", "FLOAT_VECTOR", x, y - 1)
    up = t.node("ShaderNodeCombineXYZ", x, y - 3, {"Z": inputs["Rise"]}).outputs[0]
    # Gliding further in a Ring
    drag = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", dt, AIR_DRAG, x=x - 1, y=y - 4),
        t.math(
            "SUBTRACT",
            1.0,
            t.math("MULTIPLY", inputs["Ring"], RING_GLIDE, x=x - 1, y=y - 5),
            x=x - 0.5,
            y=y - 5,
        ),
        x=x,
        y=y - 4,
        clamp=True,
    )
    moving = t.vmath(
        "ADD",
        moving,
        t.vmath("SCALE", t.vmath("SUBTRACT", up, moving, x=x + 1, y=y - 3), drag, x=x + 2, y=y - 3),
        x=x + 3,
        y=y - 1,
    )
    point = t.vmath(
        "ADD", position, t.vmath("SCALE", moving, dt, x=x + 3, y=y - 5), x=x + 4, y=y - 5
    )
    nearest, normal, _, height = surface(t, ground, point, x + 5, y - 7)
    landed = t.math("LESS_THAN", height, 0.0, x=x + 8, y=y - 7)
    point = t.vmath(
        "SUBTRACT",
        point,
        t.vmath(
            "SCALE", normal, t.math("MINIMUM", height, 0.0, x=x + 8, y=y - 8), x=x + 9, y=y - 8
        ),
        x=x + 10,
        y=y - 6,
    )
    # On the ground, the speed into it turned along it, away at random
    sliding = along(t, moving, normal, x + 8, y - 10)
    scatter = along(
        t,
        socket(
            t.node(
                "FunctionNodeRandomValue",
                x + 8,
                y - 13,
                {"Min": (-1, -1, -1), "Max": (1, 1, 1), "Seed": inputs["Seed"]},
                data_type="FLOAT_VECTOR",
            ).outputs,
            "Value",
        ),
        normal,
        x + 9,
        y - 13,
    )
    away = t.vmath(
        "NORMALIZE", t.vmath("ADD", sliding, scatter, x=x + 11, y=y - 12), x=x + 12, y=y - 12
    )
    fall = t.math(
        "ABSOLUTE",
        t.math(
            "MINIMUM",
            t.vmath("DOT_PRODUCT", moving, normal, x=x + 10, y=y - 14),
            0.0,
            x=x + 11,
            y=y - 14,
        ),
        x=x + 12,
        y=y - 14,
    )
    spread = t.vmath(
        "ADD", sliding, t.vmath("SCALE", away, fall, x=x + 13, y=y - 13), x=x + 14, y=y - 11
    )
    moving = switch(t, landed, moving, spread, "VECTOR", x + 15, y - 2)
    puffs = t.store(puffs, ".dust_velocity", "FLOAT_VECTOR", moving, x + 16, y)
    floor = socket(t.node("ShaderNodeSeparateXYZ", x + 15, y - 5, {0: nearest}).outputs, "Z")
    puffs = t.store(puffs, ".dust_floor", "FLOAT", floor, x + 17, y)
    puffs = t.node(
        "GeometryNodeSetPosition", x + 18, y, {"Geometry": puffs, "Position": point}
    ).outputs[0]
    return aged(t, puffs, PUFF_LIVES, dt, x + 19, y)


def grain_step(t, grains, ground, dt, x, y):
    """Grains falling, bouncing and sliding to rest on the ground"""
    position = t.node("GeometryNodeInputPosition", x, y - 6).outputs[0]
    moving = t.attribute(".dust_velocity", "FLOAT_VECTOR", x, y - 1)
    moving = t.vmath(
        "SCALE",
        t.vmath(
            "ADD",
            moving,
            t.node(
                "ShaderNodeCombineXYZ",
                x,
                y - 3,
                {"Z": t.math("MULTIPLY", dt, -GRAVITY, x=x - 1, y=y - 3)},
            ).outputs[0],
            x=x + 1,
            y=y - 1,
        ),
        t.math(
            "SUBTRACT",
            1.0,
            t.math("MULTIPLY", dt, GRAIN_DRAG, x=x, y=y - 4),
            x=x + 1,
            y=y - 4,
            clamp=True,
        ),
        x=x + 2,
        y=y - 1,
    )
    point = t.vmath(
        "ADD", position, t.vmath("SCALE", moving, dt, x=x + 2, y=y - 5), x=x + 3, y=y - 5
    )
    _, normal, _, height = surface(t, ground, point, x + 4, y - 7)
    # Resting on their flat side
    radius = socket(
        t.node(
            "ShaderNodeSeparateXYZ",
            x + 5,
            y - 10,
            {0: t.attribute(".dust_scale", "FLOAT_VECTOR", x + 4, y - 10)},
        ).outputs,
        "Z",
    )
    under = t.math("SUBTRACT", radius, height, x=x + 7, y=y - 9)
    point = t.vmath(
        "ADD",
        point,
        t.vmath("SCALE", normal, t.math("MAXIMUM", under, 0.0, x=x + 8, y=y - 9), x=x + 9, y=y - 8),
        x=x + 10,
        y=y - 6,
    )
    into = t.math(
        "MINIMUM", t.vmath("DOT_PRODUCT", moving, normal, x=x + 7, y=y - 12), 0.0, x=x + 8, y=y - 12
    )
    bounced = t.vmath(
        "SUBTRACT",
        t.vmath(
            "SCALE", along(t, moving, normal, x + 8, y - 14), 1.0 - FRICTION, x=x + 11, y=y - 14
        ),
        t.vmath(
            "SCALE", normal, t.math("MULTIPLY", into, BOUNCE, x=x + 9, y=y - 12), x=x + 10, y=y - 12
        ),
        x=x + 12,
        y=y - 12,
    )
    resting = t.math(
        "LESS_THAN", t.vmath("LENGTH", bounced, x=x + 13, y=y - 13), REST_SPEED, x=x + 14, y=y - 13
    )
    bounced = switch(t, resting, bounced, (0.0, 0.0, 0.0), "VECTOR", x + 15, y - 12)
    moving = switch(
        t,
        t.math("GREATER_THAN", under, 0.0, x=x + 14, y=y - 9),
        moving,
        bounced,
        "VECTOR",
        x + 16,
        y - 2,
    )
    grains = t.store(grains, ".dust_velocity", "FLOAT_VECTOR", moving, x + 17, y)
    grains = t.node(
        "GeometryNodeSetPosition", x + 18, y, {"Geometry": grains, "Position": point}
    ).outputs[0]
    return aged(t, grains, 1.0, dt, x + 19, y)


def dust_solver(t, dust, puffs, inputs, dt, x, y):
    """Dust carried by the air rising and swirling as the curl of a noise, fed by the young
    puffs, fading over its lifetime, on a grid around them and the dust"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    size = inputs["Size"]
    # Around the puffs and the dust carried away from them, not its faded cells, still active,
    # else the grid grows every frame
    old = t.node(
        "GeometryNodeGetNamedGrid",
        x - 2,
        y - 6,
        {"Volume": dust, "Name": "density"},
        data_type="FLOAT",
    ).outputs["Grid"]
    dense = t.node("GeometryNodeGridToPoints", x - 1, y - 6, {"Grid": old}, data_type="FLOAT")
    dense = t.node(
        "GeometryNodeDeleteGeometry",
        x - 0.5,
        y - 6,
        {
            "Geometry": dense.outputs["Points"],
            "Selection": t.math("LESS_THAN", dense.outputs["Value"], 0.005, x=x - 1, y=y - 7),
        },
    ).outputs[0]
    around = t.node("GeometryNodeJoinGeometry", x, y - 4)
    t.connect(dense, around.inputs[0])
    t.connect(puffs, around.inputs[0])
    bounds = t.node("GeometryNodeBoundBox", x + 1, y - 4, {"Geometry": around.outputs[0]}).outputs
    margin = t.math("MULTIPLY", size, 2.0, x=x + 1, y=y - 6)
    low = t.vmath("SUBTRACT", bounds["Min"], margin, x=x + 2, y=y - 4)
    extent = t.vmath(
        "SUBTRACT", t.vmath("ADD", bounds["Max"], margin, x=x + 2, y=y - 5), low, x=x + 3, y=y - 5
    )
    # Cubic voxels, at most the Resolution along each side
    sides = t.node("ShaderNodeSeparateXYZ", x + 3, y - 7, {0: extent}).outputs
    largest = t.math(
        "MAXIMUM",
        t.math("MAXIMUM", socket(sides, "X"), socket(sides, "Y"), x=x + 4, y=y - 7),
        socket(sides, "Z"),
        x=x + 5,
        y=y - 7,
    )
    voxel = t.math(
        "MAXIMUM",
        t.math("MULTIPLY", size, 0.3, x=x + 4, y=y - 3),
        t.math("DIVIDE", largest, inputs["Resolution"], x=x + 5, y=y - 8),
        x=x + 6,
        y=y - 3,
    )
    cells = t.vmath("CEIL", t.vmath("DIVIDE", extent, voxel, x=x + 6, y=y - 5), x=x + 7, y=y - 5)
    high = t.vmath("ADD", low, t.vmath("SCALE", cells, voxel, x=x + 8, y=y - 6), x=x + 9, y=y - 4)
    cells = t.node("ShaderNodeSeparateXYZ", x + 8, y - 5, {0: cells}).outputs
    topology = t.node(
        "GeometryNodeCubeGridTopology",
        x + 8,
        y - 4,
        {
            "Bounds Min": low,
            "Bounds Max": high,
            "Resolution X": socket(cells, "X"),
            "Resolution Y": socket(cells, "Y"),
            "Resolution Z": socket(cells, "Z"),
        },
    ).outputs[0]

    def to_grid(value, data_type, name, xx, yy):
        node = t.node(
            "GeometryNodeFieldToGrid", xx, yy, {"Topology": topology}, data_type="BOOLEAN"
        )
        node.grid_items.new(data_type, name)
        t.connect(value, node.inputs[name])
        return node.outputs[name]

    def sampled(grid, data_type, xx, yy):
        return t.node(
            "GeometryNodeSampleGrid",
            xx,
            yy,
            {"Grid": grid, "Position": position},
            data_type=data_type,
        ).outputs[0]

    # Air: eddies about twice the size of the puffs, turning at the Swirl, rising
    time = t.node("GeometryNodeInputSceneTime", x + 8, y - 8).outputs["Seconds"]
    eddy = t.math("MULTIPLY", size, 2.0, x=x + 8, y=y - 9)
    noise = t.node(
        "ShaderNodeTexNoise",
        x + 9,
        y - 8,
        {
            "Vector": t.vmath("DIVIDE", position, eddy, x=x + 9, y=y - 9),
            "W": t.math("MULTIPLY", time, 0.5, x=x + 9, y=y - 10),
        },
        noise_dimensions="4D",
    ).outputs["Color"]
    potential = to_grid(
        t.vmath("SUBTRACT", noise, (0.5,) * 3, x=x + 10, y=y - 8),
        "VECTOR",
        "Potential",
        x + 11,
        y - 8,
    )
    curl = t.node("GeometryNodeGridCurl", x + 12, y - 8, {"Grid": potential}).outputs[0]
    swirl = t.math(
        "MULTIPLY",
        inputs["Swirl"],
        t.math("MULTIPLY", eddy, 0.25, x=x + 11, y=y - 11),
        x=x + 12,
        y=y - 10,
    )
    air = t.vmath("SCALE", sampled(curl, "VECTOR", x + 13, y - 8), swirl, x=x + 14, y=y - 8)
    # The nearest puff, blowing the air, with the ground under it
    closest = t.node(
        "GeometryNodeSampleNearest",
        x + 12,
        y - 12,
        {"Geometry": puffs, "Sample Position": position},
    ).outputs[0]
    floor = sample(
        t,
        puffs,
        t.attribute(".dust_floor", "FLOAT", x + 12, y - 16),
        closest,
        "FLOAT",
        x + 13,
        y - 16,
    )
    # Slowing down on the ground, settling there
    height = t.math(
        "SUBTRACT",
        socket(t.node("ShaderNodeSeparateXYZ", x + 12, y - 15, {0: position}).outputs, "Z"),
        floor,
        x=x + 13,
        y=y - 15,
    )
    landing = t.math(
        "DIVIDE",
        height,
        t.math("MULTIPLY", size, 2.0, x=x + 13, y=y - 17),
        x=x + 14,
        y=y - 15,
        clamp=True,
    )
    up = t.node(
        "ShaderNodeCombineXYZ",
        x + 14,
        y - 10,
        {"Z": t.math("MULTIPLY", inputs["Rise"], landing, x=x + 14, y=y - 11)},
    ).outputs[0]
    air = t.vmath("ADD", air, up, x=x + 15, y=y - 8)
    puff = sample(t, puffs, position, closest, "FLOAT_VECTOR", x + 13, y - 12)
    blown = sample(
        t,
        puffs,
        t.attribute(".dust_velocity", "FLOAT_VECTOR", x + 12, y - 13),
        closest,
        "FLOAT_VECTOR",
        x + 13,
        y - 13,
    )
    near = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "DIVIDE",
            t.vmath("DISTANCE", position, puff, x=x + 14, y=y - 12),
            t.math("MULTIPLY", size, 2.0, x=x + 14, y=y - 14),
            x=x + 15,
            y=y - 12,
        ),
        x=x + 16,
        y=y - 12,
        clamp=True,
    )
    air = t.vmath("ADD", air, t.vmath("SCALE", blown, near, x=x + 17, y=y - 12), x=x + 18, y=y - 9)
    air = to_grid(air, "VECTOR", "Air", x + 19, y - 8)

    # Carried and fading, fed by the puffs in the first part of their life
    carried = t.node(
        "GeometryNodeGridAdvect",
        x + 17,
        y - 13,
        # Less diffusing than the default, not to blur the dust in a ball
        {"Grid": old, "Velocity": air, "Time Step": dt, "Integration Scheme": "MacCormack"},
        data_type="FLOAT",
    ).outputs[0]
    # Thinning from the top of the dust, over half the Lifetime there and one and a half at the
    # bottom
    top = t.node("GeometryNodeBoundBox", x + 14, y - 19, {"Geometry": dense}).outputs
    top = [
        socket(t.node("ShaderNodeSeparateXYZ", x + 15, y - 19 - i, {0: top[name]}).outputs, "Z")
        for i, name in enumerate(("Min", "Max"))
    ]
    above = t.math(
        "DIVIDE",
        t.math(
            "SUBTRACT",
            socket(t.node("ShaderNodeSeparateXYZ", x + 15, y - 21, {0: position}).outputs, "Z"),
            top[0],
            x=x + 16,
            y=y - 19,
        ),
        t.math(
            "MAXIMUM",
            t.math("SUBTRACT", top[1], top[0], x=x + 16, y=y - 20),
            1e-3,
            x=x + 17,
            y=y - 20,
        ),
        x=x + 17,
        y=y - 19,
        clamp=True,
    )
    fade = t.math(
        "EXPONENT",
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", dt, -1.0, x=x + 16, y=y - 17),
            t.math(
                "MULTIPLY",
                inputs["Lifetime"],
                t.math("SUBTRACT", 1.5, above, x=x + 17, y=y - 18),
                x=x + 18,
                y=y - 18,
            ),
            x=x + 17,
            y=y - 17,
        ),
        x=x + 18,
        y=y - 17,
    )
    # Fed by the puffs in a burst, right after they are blown out, or once away in a Ring
    feeding = t.math(
        "SUBTRACT",
        t.attribute(".dust_age", "FLOAT", x + 8, y - 22),
        t.math("MULTIPLY", inputs["Ring"], RING_DELAY, x=x + 8, y=y - 23),
        x=x + 9,
        y=y - 22,
    )
    young = t.node(
        "GeometryNodeDeleteGeometry",
        x + 10,
        y - 21,
        {
            "Geometry": puffs,
            "Selection": t.math(
                "GREATER_THAN",
                t.math(
                    "ABSOLUTE",
                    t.math("SUBTRACT", feeding, FEED_TIME / 2, x=x + 9.5, y=y - 22),
                    x=x + 10,
                    y=y - 22,
                ),
                FEED_TIME / 2,
                x=x + 10.5,
                y=y - 22,
            ),
        },
    ).outputs[0]
    # With a puff of no size, for the grid to exist without young puffs
    dummy = t.node(
        "GeometryNodePoints", x + 9, y - 24, {"Count": 1, "Position": low, "Radius": 0.0}
    ).outputs[0]
    dummy = t.store(dummy, ".dust_life", "FLOAT", -1.0, x + 10, y - 24)
    joined = t.node("GeometryNodeJoinGeometry", x + 11, y - 21)
    t.connect(dummy, joined.inputs[0])
    t.connect(young, joined.inputs[0])
    young = joined.outputs[0]
    # At least a voxel, else the grid misses them
    radius = t.math("MAXIMUM", size, voxel, x=x + 11, y=y - 23)
    real = t.attribute(".dust_life", "FLOAT", x + 10, y - 25)
    radius = t.math(
        "MULTIPLY",
        radius,
        t.math("GREATER_THAN", real, 0.0, x=x + 11, y=y - 25),
        x=x + 12,
        y=y - 23,
    )
    source = t.node(
        "GeometryNodePointsToVolume",
        x + 12,
        y - 21,
        {
            "Points": young,
            "Density": 1.0,
            "Resolution Mode": "Size",
            "Voxel Size": voxel,
            "Radius": radius,
        },
    ).outputs[0]
    source = t.node(
        "GeometryNodeGetNamedGrid",
        x + 13,
        y - 21,
        {"Volume": source, "Name": "density"},
        data_type="FLOAT",
    ).outputs["Grid"]
    density = t.math(
        "MULTIPLY_ADD",
        sampled(source, "FLOAT", x + 15, y - 21),
        t.math("DIVIDE", dt, FEED_TIME, x=x + 14, y=y - 23),
        t.math("MULTIPLY", sampled(carried, "FLOAT", x + 18, y - 13), fade, x=x + 19, y=y - 13),
        x=x + 20,
        y=y - 14,
    )
    density = t.math("MINIMUM", density, 1.0, x=x + 21, y=y - 14)
    # Not under the ground
    density = t.math(
        "MULTIPLY",
        density,
        t.math("GREATER_THAN", height, 0.0, x=x + 21, y=y - 16),
        x=x + 21.5,
        y=y - 14,
    )
    density = to_grid(density, "FLOAT", "Density", x + 22, y - 14)
    # Without the faded cells, not to grow the grid
    density = t.node(
        "GeometryNodeGridPrune",
        x + 23.5,
        y - 14,
        {"Grid": density, "Mode": "Threshold", "Threshold": 0.005},
        data_type="FLOAT",
    ).outputs[0]
    return stored(t, density, x + 23, y - 12)


def stored(t, density, x, y):
    """Volume with only the density grid"""
    volume = t.node(
        "GeometryNodeVolumeCube",
        x,
        y,
        {"Resolution X": 2, "Resolution Y": 2, "Resolution Z": 2},
    ).outputs[0]
    volume = t.node(
        "GeometryNodeGetNamedGrid",
        x + 1,
        y,
        {"Volume": volume, "Name": "density", "Remove": True},
        data_type="FLOAT",
    ).outputs["Volume"]
    return t.node(
        "GeometryNodeStoreNamedGrid",
        x + 2,
        y,
        {"Volume": volume, "Name": "density", "Grid": density},
        data_type="FLOAT",
    ).outputs[0]


def rendered(t, dust, inputs, x, y):
    """Dust billowing by a noise slowly changing, blurred for soft edges, with its color and the
    coordinates in Size for the details of the material"""
    grid = t.node(
        "GeometryNodeGetNamedGrid", x, y, {"Volume": dust, "Name": "density"}, data_type="FLOAT"
    ).outputs
    position = t.node("GeometryNodeInputPosition", x, y - 4).outputs[0]
    weight = t.node(
        "GeometryNodeSampleGrid",
        x + 0.5,
        y - 3,
        {"Grid": grid["Grid"], "Position": position},
        data_type="FLOAT",
    ).outputs[0]
    coordinates = t.vmath("DIVIDE", position, inputs["Size"], x=x + 1, y=y - 4)
    time = t.node("GeometryNodeInputSceneTime", x, y - 6).outputs["Seconds"]
    # Billows: the edge of the dust pushed in and out by the noise
    noise = t.node(
        "ShaderNodeTexNoise",
        x + 1.5,
        y - 6,
        {
            "Vector": coordinates,
            "W": t.math("MULTIPLY", time, 0.3, x=x + 1, y=y - 6),
            "Scale": 1.0,
            "Detail": 3.0,
        },
        noise_dimensions="4D",
    ).outputs["Fac"]
    billows = t.node(
        "ShaderNodeMapRange",
        x + 2.5,
        y - 5,
        {
            0: t.math(
                "MULTIPLY", weight, t.math("ADD", noise, 0.5, x=x + 2, y=y - 6), x=x + 2, y=y - 5
            ),
            1: 0.15,
            2: 0.5,
        },
        interpolation_type="SMOOTHSTEP",
        clamp=True,
    ).outputs[0]
    thin = t.math(
        "SQRT",
        t.math("DIVIDE", THIN_SIZE, inputs["Size"], x=x + 2.5, y=y - 7),
        x=x + 3,
        y=y - 7,
        clamp=True,
    )
    billows = t.math("MULTIPLY", billows, thin, x=x + 3, y=y - 6)
    grids = t.node("GeometryNodeFieldToGrid", x + 3.5, y - 3, {"Topology": grid["Grid"]})
    for data_type, name, value in (
        ("FLOAT", "Density", billows),
        ("VECTOR", "Rest", coordinates),
        ("VECTOR", "Color", inputs["Color"]),
    ):
        grids.grid_items.new(data_type, name)
        t.connect(value, grids.inputs[name])
    soft = t.node(
        "GeometryNodeGridMean",
        x + 4.5,
        y - 1,
        {"Grid": grids.outputs["Density"], "Width": 1, "Iterations": 1},
        data_type="FLOAT",
    ).outputs[0]
    volume = t.node(
        "GeometryNodeStoreNamedGrid",
        x + 5,
        y,
        {"Volume": grid["Volume"], "Name": "density", "Grid": soft},
        data_type="FLOAT",
    ).outputs[0]
    for i, name in enumerate(("Rest", "Color")):
        volume = t.node(
            "GeometryNodeStoreNamedGrid",
            x + 6 + i,
            y,
            {"Volume": volume, "Name": name.lower(), "Grid": grids.outputs[name]},
            data_type="VECTOR_FLOAT",
        ).outputs[0]
    return volume


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Kick up dust and grains where the Colliders hit the mesh, as a dirt floor, sand or snow"
    )
    add_output(ng, "Geometry", "NodeSocketGeometry")
    build_inputs(ng)

    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -12, 0).outputs
    self_object = t.node("GeometryNodeSelfObject", -12, -2).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -11, -2, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", -10, -2, {0: to_world}).outputs[0]

    t.section("World Space", row=True)
    ground = t.node(
        "GeometryNodeTransform",
        -9,
        0,
        {"Geometry": inputs["Geometry"], "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        -9,
        -2,
        {"Collection": inputs["Colliders"]},
        transform_space="ORIGINAL",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", -8, -2, {"Geometry": colliders}).outputs[0]

    t.section("Simulation", row=True)
    frame = t.node("GeometryNodeInputSceneTime", -7, -4).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=-6, y=-4)
    sim_in = t.node("GeometryNodeSimulationInput", -6, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 0, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items[0].name = "Colliders"
    for name in ("Puffs", "Grains", "Dust"):
        sim_out.state_items.new("GEOMETRY", name)
    t.connect(positions(t, colliders, -8, -3), sim_in.inputs["Colliders"])
    # An empty grid of dust to start from
    empty = t.node(
        "GeometryNodeVolumeCube",
        -8,
        -8,
        {
            "Density": 0.0,
            "Min": (0.0, 0.0, 0.0),
            "Max": (0.001, 0.001, 0.001),
            "Resolution X": 2,
            "Resolution Y": 2,
            "Resolution Z": 2,
        },
    ).outputs[0]
    t.connect(empty, sim_in.inputs["Dust"])
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=-5, y=-4)
    colliders = velocity(t, colliders, sim_in.outputs["Colliders"], dt, -5, -6)
    t.connect(positions(t, colliders, -1, -6), sim_out.inputs["Colliders"])

    t.section("Contact", row=True)
    near = contacts(t, colliders, ground, inputs, 0, 0)
    hitting = t.node("GeometryNodeAttributeDomainSize", 25, -2, {"Geometry": near}).outputs[
        "Face Count"
    ]
    hitting = t.math("GREATER_THAN", hitting, 0, x=26, y=-2)

    t.section("Puffs and Grains", row=True)
    states = {}
    for i, (name, emitted, enabled) in enumerate(
        (
            ("Puffs", emit_puffs(t, near, ground, inputs, 0, 0), True),
            ("Grains", emit_grains(t, near, ground, inputs, 0, -24), inputs["Grains"]),
        )
    ):
        joined = t.node("GeometryNodeJoinGeometry", 20, -i * 24)
        t.connect(sim_in.outputs[name], joined.inputs[0])
        # Only computed when hitting
        t.connect(switch(t, hitting, None, emitted, "GEOMETRY", 19, -i * 24), joined.inputs[0])
        states[name] = switch(t, enabled, None, joined.outputs[0], "GEOMETRY", 21, -i * 24)
    puffs = puff_step(t, states["Puffs"], ground, inputs, dt, 22, 0)
    t.connect(puffs, sim_out.inputs["Puffs"])
    t.connect(grain_step(t, states["Grains"], ground, dt, 22, -24), sim_out.inputs["Grains"])
    # Only while there are puffs, outliving their dust
    puffing = t.node(
        "GeometryNodeAttributeDomainSize", 42, -50, {"Geometry": puffs}, component="POINTCLOUD"
    ).outputs["Point Count"]
    puffing = t.math("GREATER_THAN", puffing, 0, x=43, y=-50)
    dust = dust_solver(t, sim_in.outputs["Dust"], puffs, inputs, dt, 22, -50)
    t.connect(switch(t, puffing, empty, dust, "GEOMETRY", 48, -48), sim_out.inputs["Dust"])

    t.section("Output", row=True)
    # Flat chips with the material of the ground they come from
    chip = t.node("GeometryNodeMeshIcoSphere", 0, -4, {"Radius": 1.0, "Subdivisions": 1}).outputs[0]
    chip = t.store(chip, ".dust_grain", "BOOLEAN", True, 1, -4)
    chip = t.node(
        "GeometryNodeSetShadeSmooth", 2, -4, {"Mesh": chip, "Shade Smooth": False}
    ).outputs[0]
    grains = sim_out.outputs["Grains"]
    left = t.math(
        "DIVIDE",
        t.math(
            "SUBTRACT",
            t.attribute(".dust_life", "FLOAT", 0, -8),
            t.attribute(".dust_age", "FLOAT", 0, -9),
            x=1,
            y=-8,
        ),
        t.math("MULTIPLY", t.attribute(".dust_life", "FLOAT", 0, -10), SHRINK, x=1, y=-10),
        x=2,
        y=-8,
        clamp=True,
    )
    chips = t.node(
        "GeometryNodeInstanceOnPoints",
        3,
        -3,
        {
            "Points": grains,
            "Instance": chip,
            "Rotation": t.attribute(".dust_rotation", "QUATERNION", 2, -6),
            "Scale": t.vmath(
                "SCALE", t.attribute(".dust_scale", "FLOAT_VECTOR", 2, -7), left, x=3, y=-7
            ),
        },
    ).outputs[0]
    chips = t.node("GeometryNodeRealizeInstances", 4, -3, {"Geometry": chips}).outputs[0]
    chips = t.node(
        "GeometryNodeTransform",
        5,
        -3,
        {"Geometry": chips, "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    # The ground materials from its loose points, linked last, without its attributes
    ground_materials = t.node(
        "GeometryNodeDeleteGeometry",
        5,
        -6,
        {"Geometry": inputs["Geometry"], "Selection": True},
        domain="FACE",
        mode="ONLY_FACE",
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 6, -3)
    t.connect(chips, joined.inputs[0])
    t.connect(t.strip(ground_materials, 6, -6), joined.inputs[0])
    chips = t.node(
        "GeometryNodeSetMaterialIndex",
        7,
        -3,
        {
            "Geometry": joined.outputs[0],
            "Material Index": t.attribute(".dust_material", "INT", 6, -4),
        },
    ).outputs[0]
    chips = t.node(
        "GeometryNodeDeleteGeometry",
        7.5,
        -3,
        {
            "Geometry": chips,
            "Selection": t.node(
                "FunctionNodeBooleanMath",
                7,
                -5,
                {0: t.attribute(".dust_grain", "BOOLEAN", 6.5, -5)},
                operation="NOT",
            ).outputs[0],
        },
    ).outputs[0]
    chips = t.node(
        "GeometryNodeRemoveAttribute",
        8,
        -3,
        {"Geometry": chips, "Pattern Mode": "Wildcard", "Name": ".dust_*"},
    ).outputs[0]
    # As an instance, not subdivided after
    chips = t.node("GeometryNodeGeometryToInstance", 9, -3, {0: chips}).outputs[0]
    count = t.node(
        "GeometryNodeAttributeDomainSize", 8, -6, {"Geometry": grains}, component="POINTCLOUD"
    ).outputs["Point Count"]
    chips = switch(t, t.math("GREATER_THAN", count, 0, x=9, y=-6), None, chips, "GEOMETRY", 10, -3)
    # The dust while there are puffs, after the attributes, as they warn on volumes
    puffing = t.node(
        "GeometryNodeAttributeDomainSize",
        6,
        -12,
        {"Geometry": sim_out.outputs["Puffs"]},
        component="POINTCLOUD",
    ).outputs["Point Count"]
    dust = t.node(
        "GeometryNodeSetMaterial",
        7,
        -10,
        {
            "Geometry": switch(
                t,
                t.math("GREATER_THAN", puffing, 0, x=7, y=-12),
                None,
                rendered(t, sim_out.outputs["Dust"], inputs, 0, -12),
                "GEOMETRY",
                6.5,
                -10,
            ),
            "Material": inputs["Dust Material"],
        },
    ).outputs[0]
    dust = t.node(
        "GeometryNodeTransform",
        8,
        -10,
        {"Geometry": dust, "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 10, 0)
    for geometry in (dust, chips, inputs["Geometry"]):
        t.connect(geometry, joined.inputs[0])
    geometry = joined.outputs[0]
    t.node("NodeGroupOutput", 10, 0, {0: geometry})
    t.arrange()
    return ng


def build_dust_material():
    """Dust of the color of the grid, its shape from the grid, finer wisps by a noise moving
    with it"""
    material = bpy.data.materials.new(DUST)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))
    density = t.node("ShaderNodeAttribute", -1000, 0, attribute_name="density").outputs["Fac"]
    color = t.node("ShaderNodeAttribute", -300, 200, attribute_name="color").outputs["Color"]
    # In Size, for the details to scale with the dust
    space = t.node("ShaderNodeAttribute", -1000, -200, attribute_name="rest").outputs["Vector"]
    noise = t.node(
        "ShaderNodeTexNoise",
        -800,
        -200,
        {"Vector": space, "Scale": 1.5, "Detail": 1.0, "Roughness": 0.6},
    ).outputs["Fac"]
    wisps = t.node("ShaderNodeMapRange", -550, -200, {0: noise, 1: 0.1, 2: 0.9}, clamp=True)
    density = t.math("MULTIPLY", density, wisps.outputs[0], x=-300, y=0)
    density = t.math("MULTIPLY", density, 15.0, x=-150, y=0)
    volume = t.node(
        "ShaderNodeVolumePrincipled",
        0,
        0,
        {
            "Color": color,
            "Density": density,
            "Anisotropy": 0.3,
            # Read above, not to square it
            "Density Attribute": "",
        },
    )
    t.node("ShaderNodeOutputMaterial", 300, 0, {"Volume": volume.outputs[0]})
    return material


if __name__ == "__main__":
    dust = build_dust_material()
    write(RESOURCE, (build_node_group(), dust))
