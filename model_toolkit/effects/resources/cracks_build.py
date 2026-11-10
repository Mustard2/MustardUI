# Build cracks.blend: the Cracks node group and its tint
# Usage: Blender --background --factory-startup --python cracks_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write
from dust_puff_build import along, positions, sample, surface, switch, velocity
from imprints_build import in_box, random

RESOURCE = "cracks.blend"
NODE_GROUP = "MustardUI Cracks"
TINT = "MustardUI Cracks Tint"
# Least upward part of the normal of the faces that break
UPWARD = 0.3
# Fastest hit, not to burst when the Colliders jump
MAX_SPEED = 10.0
GRAVITY = 9.81
# In plate sizes: depth under the mesh the Colliders still touch it from, and push the plates from
REACH = 4.0
# Plates of the lattice around the hits: those left out at its border, as their shape misses
# their neighbors, and those around the broken ones the faces are cut along
BORDER = 3
NEIGHBORS = 3.5
# Most plates along a side of the lattice
MAX_CELLS = 200
# Shards a plate breaks into, and how far the plates and the shards are from the lattice, in sizes
SHARDS = 3
JITTER = (0.7, 1.0)
# In plate sizes: closest plates told apart, heights of the mesh taken as the same level
SAME = 0.001
LEVEL = 2.0
# Longest edge of the faces cut along the plates, in plate sizes, and most subdivisions to it
REFINE = 0.5
MAX_LEVELS = 14
# Share the plates are shrunk by not to touch while cut, and distance in sizes welding them back
SHRINK = 0.0002
WELD = 0.001
# Depth of the pits under the plates, in thicknesses
PIT = 1.2
# Seconds the plates of 10 cm take to settle, by the square root of their size
SETTLE = 0.15
# Random turn of the tilt axis of the plates, share tilted the other way and by how much
AXIS_TURN = 0.8
BACK = (0.25, 0.6)
# Share of the plate size from the hits the plates start jumping at
JUMP_FROM = 0.25
# Pebbles: share thrown from right under the Colliders, shapes, dents and flattening of the
# spheres, turns per second, bounce and friction on the mesh
DEBRIS_UNDER = 0.3
DEBRIS_SHAPES = 4
DEBRIS_DENT = 0.35
DEBRIS_FLAT = ((0.6, 1.0), (0.4, 0.8))
DEBRIS_SPIN = 12.0
BOUNCE = 0.3
FRICTION = 0.4


def build_inputs(ng):
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects breaking the mesh where they hit it, e.g. the body and the shoes",
    )
    add_input(
        ng, "Start Frame", "NodeSocketInt", default_value=1, description="First simulated frame"
    )
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.12,
        min_value=0.005,
        description="Size of the plates the mesh breaks into, in average",
    )
    add_input(
        ng,
        "Shards",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.35,
        min_value=0.0,
        max_value=1.0,
        description="Share of the plates broken into smaller shards",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.025,
        min_value=0.0005,
        description="Thickness of the plates",
    )
    add_input(
        ng,
        "Gap",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.003,
        min_value=0.0,
        description="Width of the cracks between the plates",
    )
    add_input(
        ng,
        "Spread",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.15,
        min_value=0.0,
        description="Distance around the Colliders the mesh breaks at, the plates moving less "
        "the further from them",
    )
    add_input(
        ng,
        "Min Speed",
        "NodeSocketFloat",
        default_value=0.05,
        min_value=0.0,
        description="Speed of the Colliders into the mesh, in m/s, below which it does not break",
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
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the random plates")
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(0.05, 0.05, 0.05, 1.0),
        description="Color inside the mesh, of the sides of the plates and under them",
    )

    panel = ng.interface.new_panel("Plates")
    add_input(
        ng,
        "Lift",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.02,
        min_value=0.0,
        description="Height the plates are pushed up by, at most",
    )
    add_input(
        ng,
        "Tilt",
        "NodeSocketFloat",
        panel,
        subtype="ANGLE",
        default_value=0.4,
        min_value=0.0,
        max_value=1.5,
        description="Angle the plates are tilted by, at most",
    )
    add_input(
        ng,
        "Scatter",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.03,
        min_value=0.0,
        description="Distance the plates are pushed away from the Colliders by, at most",
    )
    add_input(
        ng,
        "Jolt",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Speed the plates around the Colliders jump with, growing with their hit",
    )

    panel = ng.interface.new_panel("Debris", default_closed=True)
    add_input(
        ng,
        "Debris",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Pebbles thrown up where the mesh breaks, with its material",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Debris Amount",
        "NodeSocketFloat",
        panel,
        default_value=600.0,
        min_value=0.0,
        description="Pebbles per square meter of the mesh breaking",
    )
    add_input(
        ng,
        "Debris Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.012,
        min_value=0.0001,
        description="Size of the pebbles, in average",
    )
    add_input(
        ng,
        "Debris Speed",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=3.0,
        min_value=0.0,
        max_value=20.0,
        description="Speed the pebbles are thrown with, growing with the hit",
    )


def separate(t, vector, x, y):
    return t.node("ShaderNodeSeparateXYZ", x, y, {0: vector}).outputs


def combine(t, x, y, **axes):
    return t.node("ShaderNodeCombineXYZ", x, y, axes).outputs[0]


def count(t, geometry, x, y, name="Point Count", component="MESH"):
    return t.node(
        "GeometryNodeAttributeDomainSize", x, y, {"Geometry": geometry}, component=component
    ).outputs[name]


def face_center(t, x, y, flat=False):
    """Center of the faces, at height 0 if flat"""
    center = t.node(
        "GeometryNodeFieldOnDomain",
        x,
        y,
        {"Value": t.node("GeometryNodeInputPosition", x - 1, y).outputs[0]},
        data_type="FLOAT_VECTOR",
        domain="FACE",
    ).outputs[0]
    return t.vmath("MULTIPLY", center, (1.0, 1.0, 0.0), x=x + 1, y=y) if flat else center


def face_radius(t, x, y):
    """Distance of the farthest corner of the faces from their center"""
    far = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 2,
        y,
        {
            "Value": t.vmath(
                "DISTANCE",
                t.node("GeometryNodeInputPosition", x, y).outputs[0],
                face_center(t, x, y - 1),
                x=x + 1,
                y=y,
            ),
            "Group ID": t.node(
                "GeometryNodeFaceOfCorner",
                x + 1,
                y - 2,
                {"Corner Index": t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]},
            ).outputs["Face Index"],
        },
        data_type="FLOAT",
        domain="CORNER",
    ).outputs["Max"]
    return t.node(
        "GeometryNodeFieldOnDomain", x + 3, y, {"Value": far}, data_type="FLOAT", domain="FACE"
    ).outputs[0]


def proximity(t, target, at, x, y, element="POINTS"):
    return t.node(
        "GeometryNodeProximity",
        x,
        y,
        {"Geometry": target, "Sample Position": at},
        target_element=element,
    ).outputs


def boolean(t, operation, a, b, x, y):
    return t.node("FunctionNodeBooleanMath", x, y, {0: a, 1: b}, operation=operation).outputs[0]


def all_of(t, *values, x, y):
    result = values[0]
    for i, value in enumerate(values[1:]):
        result = boolean(t, "AND", result, value, x + i * 0.5, y)
    return result


def keyed(t, value, x, y):
    """Point on the X axis at the value, to look up points by it"""
    return combine(t, x, y, X=value)


def contacts(t, colliders, ground, inputs, x, y):
    """Points of the Colliders near the ground, and the points of the ground they hit fast enough,
    with the square root of the speed of the hit"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    reach = t.math("MULTIPLY", inputs["Size"], REACH, x=x, y=y - 4)
    box = t.node("GeometryNodeBoundBox", x, y - 6, {"Geometry": ground}).outputs
    near = t.node(
        "GeometryNodeSeparateGeometry",
        x + 7,
        y,
        {
            "Geometry": colliders,
            "Selection": in_box(
                t,
                box,
                position,
                t.math("ADD", reach, inputs["Contact"], x=x + 1, y=y - 4),
                x,
                y - 8,
            ),
        },
        domain="POINT",
    ).outputs["Selection"]
    nearest, normal, offset, height = surface(t, ground, position, x + 7, y - 3)
    aside = t.vmath("LENGTH", along(t, offset, normal, x + 9, y - 5), x=x + 11, y=y - 5)
    into = t.math(
        "MULTIPLY",
        t.vmath(
            "DOT_PRODUCT",
            t.attribute(".dust_velocity", "FLOAT_VECTOR", x + 9, y - 7),
            normal,
            x=x + 10,
            y=y - 7,
        ),
        -1.0,
        x=x + 11,
        y=y - 7,
    )
    hitting = all_of(
        t,
        t.math("LESS_THAN", height, inputs["Contact"], x=x + 10, y=y - 3),
        t.math(
            "GREATER_THAN",
            height,
            t.math("MULTIPLY", reach, -1.0, x=x + 9, y=y - 4),
            x=x + 10,
            y=y - 4,
        ),
        t.math("LESS_THAN", aside, inputs["Contact"], x=x + 12, y=y - 5),
        t.math("GREATER_THAN", separate(t, normal, x + 9, y - 9)["Z"], UPWARD, x=x + 10, y=y - 9),
        t.math("GREATER_THAN", into, inputs["Min Speed"], x=x + 12, y=y - 7),
        x=x + 13,
        y=y - 3,
    )
    near = t.store(
        near,
        ".cracks_speed",
        "FLOAT",
        # Its square root, for slow hits to still throw the plates and the pebbles
        t.math("SQRT", t.math("MINIMUM", into, MAX_SPEED, x=x + 12, y=y - 8), x=x + 13, y=y - 8),
        x + 15,
        y,
    )
    near = t.store(near, ".cracks_height", "FLOAT", height, x + 15.5, y)
    hits = t.node(
        "GeometryNodeMeshToPoints",
        x + 16,
        y,
        {"Mesh": near, "Selection": hitting, "Position": nearest},
        mode="VERTICES",
    ).outputs[0]
    return near, hits


def lattice(t, hits, inputs, x, y):
    """Plates around the hits as flat faces, with their seed and whether they are whole: the cells
    of the random points of a lattice, the same at any frame, from the lower hull of the points
    lifted on a paraboloid"""
    size = inputs["Size"]
    box = t.node("GeometryNodeBoundBox", x, y, {"Geometry": hits}).outputs
    margin = t.math(
        "ADD",
        inputs["Spread"],
        t.math("MULTIPLY", size, NEIGHBORS + BORDER, x=x, y=y - 2),
        x=x + 1,
        y=y - 2,
    )
    per_size = t.math("DIVIDE", 1.0, size, x=x, y=y - 3)
    low = t.vmath(
        "FLOOR",
        t.vmath(
            "SCALE", t.vmath("SUBTRACT", box["Min"], margin, x=x + 2, y=y), per_size, x=x + 3, y=y
        ),
        x=x + 4,
        y=y,
    )
    high = t.vmath(
        "CEIL",
        t.vmath(
            "SCALE",
            t.vmath("ADD", box["Max"], margin, x=x + 2, y=y - 1),
            per_size,
            x=x + 3,
            y=y - 1,
        ),
        x=x + 4,
        y=y - 1,
    )
    cells = separate(
        t,
        t.vmath(
            "MINIMUM", t.vmath("SUBTRACT", high, low, x=x + 5, y=y), (MAX_CELLS,) * 3, x=x + 6, y=y
        ),
        x + 7,
        y,
    )
    middle = t.vmath(
        "MULTIPLY", t.vmath("ADD", low, high, x=x + 5, y=y - 1), (0.5, 0.5, 0.0), x=x + 6, y=y - 1
    )
    grid = t.node(
        "GeometryNodeMeshGrid",
        x + 9,
        y,
        {
            "Size X": cells["X"],
            "Size Y": cells["Y"],
            "Vertices X": t.math("ADD", cells["X"], 1, x=x + 8, y=y),
            "Vertices Y": t.math("ADD", cells["Y"], 1, x=x + 8, y=y - 1),
        },
    ).outputs["Mesh"]
    position = t.node("GeometryNodeInputPosition", x + 9, y - 3).outputs[0]
    # Whole numbers, the same from any box
    spot = t.vmath(
        "FLOOR",
        t.vmath(
            "ADD",
            t.vmath("ADD", position, middle, x=x + 10, y=y - 3),
            (0.5, 0.5, 0.0),
            x=x + 11,
            y=y - 3,
        ),
        x=x + 12,
        y=y - 3,
    )
    points = t.node(
        "GeometryNodeMeshToPoints", x + 13, y, {"Mesh": grid, "Position": spot}, mode="VERTICES"
    ).outputs[0]

    def noise(vector, xx, yy):
        return t.node(
            "ShaderNodeTexWhiteNoise",
            xx,
            yy,
            {"Vector": vector, "W": inputs["Seed"]},
            noise_dimensions="4D",
        ).outputs

    shard = t.math(
        "LESS_THAN", noise(position, x + 13, y - 3)["Value"], inputs["Shards"], x=x + 14, y=y - 3
    )
    points = t.store(points, ".cracks_shard", "BOOLEAN", shard, x + 15, y)
    copies = t.node(
        "GeometryNodeDuplicateElements",
        x + 16,
        y,
        {
            "Geometry": points,
            "Amount": switch(
                t,
                t.attribute(".cracks_shard", "BOOLEAN", x + 15, y - 2),
                1,
                SHARDS,
                "INT",
                x + 15.5,
                y - 2,
            ),
        },
        domain="POINT",
    ).outputs
    jitter = t.vmath(
        "SUBTRACT",
        noise(
            t.vmath(
                "ADD",
                position,
                combine(
                    t,
                    x + 16,
                    y - 4,
                    Z=t.math("ADD", copies["Duplicate Index"], 1, x=x + 15.5, y=y - 4),
                ),
                x=x + 17,
                y=y - 4,
            ),
            x + 18,
            y - 4,
        )["Color"],
        (0.5, 0.5, 0.5),
        x=x + 19,
        y=y - 4,
    )
    jitter = t.vmath(
        "MULTIPLY",
        t.vmath(
            "SCALE",
            jitter,
            switch(
                t,
                t.attribute(".cracks_shard", "BOOLEAN", x + 18, y - 6),
                JITTER[0],
                JITTER[1],
                "FLOAT",
                x + 19,
                y - 6,
            ),
            x=x + 20,
            y=y - 4,
        ),
        (1.0, 1.0, 0.0),
        x=x + 21,
        y=y - 4,
    )
    seeds = t.node(
        "GeometryNodeSetPosition", x + 22, y, {"Geometry": copies["Geometry"], "Offset": jitter}
    ).outputs[0]

    # From the middle, for the precision of the hull
    offset = separate(t, t.vmath("SUBTRACT", position, middle, x=x + 22, y=y - 3), x + 23, y - 3)
    lifted = combine(
        t,
        x + 25,
        y - 3,
        X=offset["X"],
        Y=offset["Y"],
        Z=t.math(
            "ADD",
            t.math("MULTIPLY", offset["X"], offset["X"], x=x + 24, y=y - 4),
            t.math("MULTIPLY", offset["Y"], offset["Y"], x=x + 24, y=y - 5),
            x=x + 24.5,
            y=y - 4,
        ),
    )
    hull = t.node(
        "GeometryNodeConvexHull",
        x + 27,
        y,
        {
            0: t.node(
                "GeometryNodeSetPosition", x + 26, y, {"Geometry": seeds, "Position": lifted}
            ).outputs[0]
        },
    ).outputs[0]
    normal = separate(
        t, t.node("GeometryNodeInputNormal", x + 27, y - 3).outputs["Normal"], x + 28, y - 3
    )
    hull = t.node(
        "GeometryNodeDeleteGeometry",
        x + 30,
        y,
        {
            "Geometry": hull,
            "Selection": t.math("GREATER_THAN", normal["Z"], -1e-9, x=x + 29, y=y - 3),
        },
        domain="FACE",
    ).outputs[0]
    # Center of the circle through the points of each face, where the cells meet
    half = t.math("DIVIDE", -0.5, normal["Z"], x=x + 29, y=y - 5)
    corner = t.vmath(
        "ADD",
        combine(
            t,
            x + 30.5,
            y - 5,
            X=t.math("MULTIPLY", normal["X"], half, x=x + 30, y=y - 5),
            Y=t.math("MULTIPLY", normal["Y"], half, x=x + 30, y=y - 6),
        ),
        middle,
        x=x + 31,
        y=y - 5,
    )
    hull = t.store(
        hull,
        ".cracks_corner",
        "FLOAT_VECTOR",
        t.vmath("SCALE", corner, size, x=x + 31.5, y=y - 5),
        x + 32,
        y,
        domain="FACE",
    )
    seed = t.vmath(
        "SCALE",
        t.vmath(
            "ADD",
            t.vmath("MULTIPLY", position, (1.0, 1.0, 0.0), x=x + 31, y=y - 8),
            middle,
            x=x + 32,
            y=y - 8,
        ),
        size,
        x=x + 32.5,
        y=y - 8,
    )
    hull = t.store(hull, ".cracks_seed", "FLOAT_VECTOR", seed, x + 33, y)
    plates = t.node("GeometryNodeDualMesh", x + 34, y, {"Mesh": hull}).outputs[0]
    plates = t.node(
        "GeometryNodeSetPosition",
        x + 35,
        y,
        {
            "Geometry": plates,
            "Position": t.attribute(".cracks_corner", "FLOAT_VECTOR", x + 34, y - 2),
        },
    ).outputs[0]
    # Whole away from the border of the lattice
    at = t.vmath(
        "SCALE",
        t.attribute(".cracks_seed", "FLOAT_VECTOR", x + 35, y - 3),
        per_size,
        x=x + 36,
        y=y - 3,
    )
    inside = separate(
        t,
        t.vmath(
            "MINIMUM",
            t.vmath("SUBTRACT", at, low, x=x + 37, y=y - 3),
            t.vmath("SUBTRACT", high, at, x=x + 37, y=y - 4),
            x=x + 38,
            y=y - 3,
        ),
        x + 39,
        y - 3,
    )
    whole = t.math(
        "GREATER_THAN",
        t.math("MINIMUM", inside["X"], inside["Y"], x=x + 40, y=y - 3),
        BORDER - 0.5,
        x=x + 41,
        y=y - 3,
    )
    return t.store(plates, ".cracks_whole", "BOOLEAN", whole, x + 42, y, domain="FACE")


def breaking(t, plates, hits, ground, records, inputs, x, y):
    """Whole plates within the Spread of the hits, not broken yet, with their record: its key at
    the seed, the speed of the hit and the distance from it"""
    size = inputs["Size"]
    flat = t.node(
        "GeometryNodeSetPosition",
        x,
        y - 2,
        {
            "Geometry": hits,
            "Position": t.vmath(
                "MULTIPLY",
                t.node("GeometryNodeInputPosition", x - 2, y - 3).outputs[0],
                (1.0, 1.0, 0.0),
                x=x - 1,
                y=y - 3,
            ),
        },
    ).outputs[0]
    seed = t.attribute(".cracks_seed", "FLOAT_VECTOR", x, y - 5)
    away = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT",
            proximity(t, flat, seed, x + 1, y - 5)["Distance"],
            t.math("MULTIPLY", size, 0.5, x=x + 1, y=y - 7),
            x=x + 2,
            y=y - 5,
        ),
        0.0,
        x=x + 3,
        y=y - 5,
    )
    hit = t.node(
        "GeometryNodeSampleNearest", x + 1, y - 9, {"Geometry": flat, "Sample Position": seed}
    ).outputs[0]
    level = separate(
        t,
        sample(
            t,
            hits,
            t.node("GeometryNodeInputPosition", x + 1, y - 11).outputs[0],
            hit,
            "FLOAT_VECTOR",
            x + 2,
            y - 9,
        ),
        x + 3,
        y - 9,
    )["Z"]
    at = separate(t, seed, x + 3, y - 11)
    # The height of the mesh at the seed, of the level of the hit
    ray = t.node(
        "GeometryNodeRaycast",
        x + 5,
        y - 9,
        {
            "Target Geometry": ground,
            "Source Position": combine(
                t,
                x + 4,
                y - 9,
                X=at["X"],
                Y=at["Y"],
                Z=t.math("MULTIPLY_ADD", size, LEVEL, level, x=x + 3.5, y=y - 13),
            ),
            "Ray Direction": (0.0, 0.0, -1.0),
            "Ray Length": t.math("MULTIPLY", size, 2.0 * LEVEL, x=x + 4, y=y - 13),
        },
    ).outputs
    height = switch(
        t,
        ray["Is Hit"],
        level,
        separate(t, ray["Hit Position"], x + 6, y - 10)["Z"],
        "FLOAT",
        x + 7,
        y - 9,
    )
    key = combine(t, x + 8, y - 9, X=at["X"], Y=at["Y"], Z=height)
    known = proximity(t, records, key, x + 9, y - 9)
    new = all_of(
        t,
        t.attribute(".cracks_whole", "BOOLEAN", x + 9, y - 5),
        t.math(
            "LESS_THAN",
            away,
            t.math("ADD", inputs["Spread"], 1e-6, x=x + 9, y=y - 6),
            x=x + 10,
            y=y - 6,
        ),
        t.node(
            "FunctionNodeBooleanMath",
            x + 11,
            y - 9,
            {
                0: boolean(
                    t,
                    "AND",
                    known["Is Valid"],
                    t.math(
                        "LESS_THAN",
                        known["Distance"],
                        t.math("MULTIPLY", size, SAME, x=x + 9, y=y - 12),
                        x=x + 10,
                        y=y - 11,
                    ),
                    x + 10.5,
                    y - 9,
                )
            },
            operation="NOT",
        ).outputs[0],
        x=x + 12,
        y=y - 5,
    )
    for i, (name, data_type, value) in enumerate(
        (
            (".cracks_key", "FLOAT_VECTOR", key),
            (".cracks_away", "FLOAT", away),
            (
                ".cracks_amount",
                "FLOAT",
                t.node(
                    "ShaderNodeMapRange",
                    x + 12,
                    y - 17,
                    {
                        "Value": away,
                        "From Min": 0.0,
                        "From Max": inputs["Spread"],
                        "To Min": 1.0,
                        "To Max": 0.0,
                    },
                    interpolation_type="SMOOTHSTEP",
                ).outputs[0],
            ),
            (".cracks_new", "BOOLEAN", new),
            (
                ".cracks_hit",
                "FLOAT",
                sample(
                    t,
                    hits,
                    t.attribute(".cracks_speed", "FLOAT", x + 2, y - 15),
                    hit,
                    "FLOAT",
                    x + 3,
                    y - 15,
                ),
            ),
        )
    ):
        plates = t.store(plates, name, data_type, value, x + 14 + i, y, domain="FACE")
    return plates


def recorded(t, plates, hits, inputs, x, y):
    """Records of the new plates, points at their keys with how they move: the pivot, the turn as
    an axis by the angle, the move, the speed of the jump, the time and the shrinking of the Gap"""
    size = inputs["Size"]
    new = t.node(
        "GeometryNodeSeparateGeometry",
        x,
        y,
        {"Geometry": plates, "Selection": t.attribute(".cracks_new", "BOOLEAN", x - 1, y - 2)},
        domain="FACE",
    ).outputs["Selection"]
    height = separate(t, t.attribute(".cracks_key", "FLOAT_VECTOR", x, y - 3), x + 1, y - 3)["Z"]
    new = t.store(
        new,
        ".cracks_pivot",
        "FLOAT_VECTOR",
        t.vmath(
            "ADD",
            face_center(t, x + 1, y - 5, flat=True),
            combine(t, x + 2, y - 3, Z=height),
            x=x + 3,
            y=y - 4,
        ),
        x + 4,
        y,
        domain="FACE",
    )
    radius = t.math(
        "SQRT",
        t.math(
            "DIVIDE",
            t.node("GeometryNodeInputMeshFaceArea", x + 2, y - 7).outputs[0],
            3.14159,
            x=x + 3,
            y=y - 7,
        ),
        x=x + 4,
        y=y - 7,
    )
    shrink = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT",
            1.0,
            t.math(
                "DIVIDE",
                t.math("MULTIPLY", inputs["Gap"], 0.5, x=x + 4, y=y - 8),
                radius,
                x=x + 5,
                y=y - 7,
            ),
            x=x + 6,
            y=y - 7,
        ),
        0.5,
        x=x + 7,
        y=y - 7,
    )
    new = t.store(new, ".cracks_shrink", "FLOAT", shrink, x + 8, y, domain="FACE")
    records = t.node(
        "GeometryNodeMeshToPoints",
        x + 9,
        y,
        {"Mesh": new, "Position": t.attribute(".cracks_key", "FLOAT_VECTOR", x + 8, y - 2)},
        mode="FACES",
    ).outputs[0]

    key = t.node("GeometryNodeInputPosition", x + 9, y - 4).outputs[0]
    randoms = [
        separate(
            t,
            t.node(
                "ShaderNodeTexWhiteNoise",
                x + 11,
                y - 4 - i * 2,
                {
                    "Vector": t.vmath(
                        "ADD",
                        t.vmath("SCALE", key, 1000.0, x=x + 9.5, y=y - 4),
                        (0.0, 0.0, 7.0 * i),
                        x=x + 10,
                        y=y - 4 - i * 2,
                    ),
                    "W": inputs["Seed"],
                },
                noise_dimensions="4D",
            ).outputs["Color"],
            x + 12,
            y - 4 - i * 2,
        )
        for i in range(2)
    ]
    center = t.node(
        "GeometryNodeAttributeStatistic",
        x + 9,
        y - 10,
        {
            "Geometry": hits,
            "Attribute": t.node("GeometryNodeInputPosition", x + 8, y - 10).outputs[0],
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs["Mean"]
    out = t.vmath(
        "NORMALIZE",
        t.vmath(
            "MULTIPLY",
            t.vmath(
                "SUBTRACT",
                t.attribute(".cracks_pivot", "FLOAT_VECTOR", x + 9, y - 12),
                center,
                x=x + 10,
                y=y - 10,
            ),
            (1.0, 1.0, 0.0),
            x=x + 11,
            y=y - 10,
        ),
        x=x + 12,
        y=y - 10,
    )
    away = t.attribute(".cracks_away", "FLOAT", x + 9, y - 14)
    amount = t.attribute(".cracks_amount", "FLOAT", x + 11, y - 14)
    # Tilted about the axis across the way out, their far side up, a few the other way
    axis = t.node(
        "ShaderNodeVectorRotate",
        x + 14,
        y - 10,
        {
            "Vector": t.vmath("CROSS_PRODUCT", out, (0.0, 0.0, 1.0), x=x + 13, y=y - 10),
            "Axis": (0.0, 0.0, 1.0),
            "Angle": t.math(
                "MULTIPLY",
                t.math("SUBTRACT", randoms[0]["X"], 0.5, x=x + 13, y=y - 12),
                2.0 * AXIS_TURN,
                x=x + 13.5,
                y=y - 12,
            ),
        },
        rotation_type="AXIS_ANGLE",
    ).outputs[0]
    angle = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", inputs["Tilt"], amount, x=x + 13, y=y - 14),
            t.math("MULTIPLY_ADD", randoms[0]["Y"], 0.7, 0.3, x=x + 13, y=y - 15),
            x=x + 14,
            y=y - 14,
        ),
        switch(
            t,
            t.math("LESS_THAN", randoms[0]["Z"], BACK[0], x=x + 13, y=y - 16),
            1.0,
            -BACK[1],
            "FLOAT",
            x + 14,
            y - 16,
        ),
        x=x + 15,
        y=y - 14,
    )
    move = t.vmath(
        "ADD",
        t.vmath(
            "SCALE",
            out,
            t.math(
                "MULTIPLY",
                t.math("MULTIPLY", inputs["Scatter"], amount, x=x + 13, y=y - 18),
                randoms[1]["X"],
                x=x + 14,
                y=y - 18,
            ),
            x=x + 15,
            y=y - 18,
        ),
        combine(
            t,
            x + 15,
            y - 20,
            Z=t.math(
                "MULTIPLY",
                t.math("MULTIPLY", inputs["Lift"], amount, x=x + 13, y=y - 20),
                randoms[1]["Y"],
                x=x + 14,
                y=y - 20,
            ),
        ),
        x=x + 16,
        y=y - 18,
    )
    # Not jumping right under the Colliders
    jump = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math(
                "MULTIPLY",
                inputs["Jolt"],
                t.attribute(".cracks_hit", "FLOAT", x + 12, y - 22),
                x=x + 13,
                y=y - 22,
            ),
            t.math("MULTIPLY", amount, randoms[1]["Z"], x=x + 13, y=y - 23),
            x=x + 14,
            y=y - 22,
        ),
        t.math(
            "DIVIDE",
            away,
            t.math("MULTIPLY", size, JUMP_FROM, x=x + 13, y=y - 25),
            x=x + 14,
            y=y - 24,
            clamp=True,
        ),
        x=x + 15,
        y=y - 22,
    )
    for i, (name, data_type, value) in enumerate(
        (
            (".cracks_turn", "FLOAT_VECTOR", t.vmath("SCALE", axis, angle, x=x + 16, y=y - 12)),
            (".cracks_move", "FLOAT_VECTOR", move),
            (".cracks_jump", "FLOAT", jump),
            (
                ".cracks_born",
                "FLOAT",
                t.node("GeometryNodeInputSceneTime", x + 15, y - 26).outputs["Seconds"],
            ),
            (".cracks_down", "FLOAT", 0.0),
            (".cracks_raised", "FLOAT", 1.0),
        )
    ):
        records = t.store(records, name, data_type, value, x + 17 + i, y)
    return new, records


def refined(t, pool, flat, size, x, y):
    """Faces subdivided where they reach the flat plates, until not longer than a share of them"""
    ends = t.node("GeometryNodeInputMeshEdgeVertices", x - 2, y - 3).outputs
    longest = t.node(
        "GeometryNodeAttributeStatistic",
        x,
        y - 3,
        {
            "Geometry": pool,
            "Attribute": t.vmath(
                "DISTANCE", ends["Position 1"], ends["Position 2"], x=x - 1, y=y - 3
            ),
        },
        domain="EDGE",
    ).outputs["Max"]
    levels = t.math(
        "MINIMUM",
        t.math(
            "CEIL",
            t.math(
                "LOGARITHM",
                t.math(
                    "MAXIMUM",
                    t.math(
                        "DIVIDE",
                        longest,
                        t.math("MULTIPLY", size, REFINE, x=x, y=y - 5),
                        x=x + 1,
                        y=y - 4,
                    ),
                    1.0,
                    x=x + 2,
                    y=y - 4,
                ),
                2.0,
                x=x + 3,
                y=y - 4,
            ),
            x=x + 4,
            y=y - 4,
        ),
        MAX_LEVELS,
        x=x + 5,
        y=y - 4,
    )
    start = t.node("GeometryNodeRepeatInput", x + 6, y)
    end = t.node("GeometryNodeRepeatOutput", x + 15, y)
    start.pair_with_output(end)
    t.connect(levels, start.inputs["Iterations"])
    t.connect(pool, start.inputs["Geometry"])
    # The faces still too long
    radius = face_radius(t, x + 7, y - 3)
    parts = t.node(
        "GeometryNodeSeparateGeometry",
        x + 12,
        y,
        {
            "Geometry": start.outputs["Geometry"],
            "Selection": boolean(
                t,
                "AND",
                t.math(
                    "LESS_THAN",
                    proximity(
                        t, flat, face_center(t, x + 7, y - 7, flat=True), x + 9, y - 7, "FACES"
                    )["Distance"],
                    radius,
                    x=x + 10,
                    y=y - 5,
                ),
                t.math(
                    "GREATER_THAN",
                    radius,
                    t.math("MULTIPLY", size, REFINE, x=x + 9, y=y - 9),
                    x=x + 10,
                    y=y - 9,
                ),
                x + 11,
                y - 5,
            ),
        },
        domain="FACE",
    ).outputs
    joined = t.node("GeometryNodeJoinGeometry", x + 14, y)
    t.connect(parts["Inverted"], joined.inputs[0])
    t.connect(
        t.node(
            "GeometryNodeSubdivideMesh", x + 13, y - 2, {"Mesh": parts["Selection"], "Level": 1}
        ).outputs[0],
        joined.inputs[0],
    )
    t.connect(joined.outputs[0], end.inputs["Geometry"])
    return end.outputs["Geometry"]


def face_prisms(t, faces, depth, x, y):
    """Closed solid under each face, to cut it: its sides, closed by a point under its center"""
    faces = t.node("GeometryNodeSplitEdges", x, y, {"Mesh": faces}).outputs[0]
    faces = t.store(faces, ".cracks_center", "FLOAT_VECTOR", face_center(t, x, y - 2), x + 1, y)
    faces = t.node(
        "GeometryNodeSetPosition",
        x + 3,
        y,
        {
            "Geometry": faces,
            "Offset": combine(
                t, x + 2, y - 2, Z=t.math("MULTIPLY", depth, -1.0, x=x + 1.5, y=y - 3)
            ),
        },
    ).outputs[0]
    faces = t.store(
        faces,
        ".cracks_rim",
        "FLOAT",
        separate(t, t.node("GeometryNodeInputPosition", x + 2, y - 4).outputs[0], x + 3, y - 4)[
            "Z"
        ],
        x + 4,
        y,
    )
    faces = t.node(
        "GeometryNodeExtrudeMesh",
        x + 5,
        y,
        {
            "Mesh": faces,
            "Offset": combine(t, x + 4, y - 2, Z=1.0),
            "Offset Scale": depth,
            "Individual": True,
        },
        mode="FACES",
    ).outputs["Mesh"]
    open_edge = t.node(
        "FunctionNodeCompare",
        x + 5,
        y - 3,
        {"A": t.node("GeometryNodeInputMeshEdgeNeighbors", x + 4, y - 3).outputs[0], "B": 1},
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    faces = t.node(
        "GeometryNodeExtrudeMesh",
        x + 6,
        y,
        {
            "Mesh": faces,
            "Selection": open_edge,
            "Offset": combine(t, x + 5, y - 5, Z=-0.5),
            "Offset Scale": depth,
        },
        mode="EDGES",
    ).outputs["Mesh"]
    under = t.math(
        "LESS_THAN",
        separate(t, t.node("GeometryNodeInputPosition", x + 5, y - 7).outputs[0], x + 6, y - 7)[
            "Z"
        ],
        t.math(
            "SUBTRACT",
            t.attribute(".cracks_rim", "FLOAT", x + 5, y - 8),
            t.math("MULTIPLY", depth, 0.25, x=x + 5, y=y - 9),
            x=x + 6,
            y=y - 8,
        ),
        x=x + 7,
        y=y - 7,
    )
    faces = t.store(faces, ".cracks_under", "BOOLEAN", under, x + 8, y)
    faces = t.node(
        "GeometryNodeSetPosition",
        x + 10,
        y,
        {
            "Geometry": faces,
            "Selection": t.attribute(".cracks_under", "BOOLEAN", x + 9, y - 2),
            "Position": t.vmath(
                "SUBTRACT",
                t.attribute(".cracks_center", "FLOAT_VECTOR", x + 8, y - 3),
                combine(t, x + 8, y - 4, Z=t.math("MULTIPLY", depth, 2.5, x=x + 7, y=y - 4)),
                x=x + 9,
                y=y - 3,
            ),
        },
    ).outputs[0]
    faces = t.node(
        "GeometryNodeMergeByDistance",
        x + 11,
        y,
        {
            "Geometry": faces,
            "Selection": t.attribute(".cracks_under", "BOOLEAN", x + 10, y - 2),
            "Distance": 1e-6,
        },
    ).outputs[0]
    cut = t.math(
        "LESS_THAN",
        separate(
            t, t.node("GeometryNodeInputNormal", x + 10, y - 4).outputs["Normal"], x + 11, y - 4
        )["Z"],
        UPWARD * 0.5,
        x=x + 12,
        y=y - 4,
    )
    return t.store(faces, ".cracks_cut", "FLOAT", cut, x + 13, y, domain="FACE")


def plate_prisms(t, plates, bottom, top, x, y):
    """Closed prism of each flat plate between the heights, a little smaller not to touch"""
    plates = t.store(
        plates,
        ".cracks_prism",
        "INT",
        t.node("GeometryNodeInputIndex", x - 1, y - 2).outputs[0],
        x,
        y,
        domain="FACE",
    )
    plates = t.node("GeometryNodeSplitEdges", x + 1, y, {"Mesh": plates}).outputs[0]
    plates = t.node(
        "GeometryNodeScaleElements",
        x + 2,
        y,
        {"Geometry": plates, "Scale": 1.0 - SHRINK},
        domain="FACE",
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", x + 4, y)
    for i, height in enumerate((bottom, top)):
        t.connect(
            t.node(
                "GeometryNodeSetPosition",
                x + 3,
                y - i * 2,
                {"Geometry": plates, "Offset": combine(t, x + 2, y - 2 - i * 2, Z=height)},
            ).outputs[0],
            joined.inputs[0],
        )
    points = t.node(
        "GeometryNodeMeshToPoints", x + 5, y, {"Mesh": joined.outputs[0]}, mode="VERTICES"
    ).outputs[0]
    prisms = t.node(
        "GeometryNodeSplitToInstances",
        x + 6,
        y,
        {"Geometry": points, "Group ID": t.attribute(".cracks_prism", "INT", x + 5, y - 2)},
        domain="POINT",
    ).outputs["Instances"]
    prisms = t.node("GeometryNodeConvexHull", x + 7, y, {0: prisms}).outputs[0]
    prisms = t.node("GeometryNodeRealizeInstances", x + 8, y, {"Geometry": prisms}).outputs[0]
    return t.store(prisms, ".cracks_cut", "FLOAT", 1.0, x + 9, y, domain="FACE")


def tiled(t, ground, patch, consumed, plates, inputs, x, y):
    """The patch with the faces reaching the new plates cut along the plates around, each piece
    with the seed of its plate, and the faces of the ground it replaces"""
    size = inputs["Size"]
    flat = t.node(
        "GeometryNodeSeparateGeometry",
        x,
        y - 4,
        {"Geometry": plates, "Selection": t.attribute(".cracks_new", "BOOLEAN", x - 1, y - 5)},
        domain="FACE",
    ).outputs["Selection"]
    # At the level of the new plates
    heights = t.node(
        "GeometryNodeAttributeStatistic",
        x,
        y - 7,
        {
            "Geometry": flat,
            "Attribute": separate(
                t, t.attribute(".cracks_key", "FLOAT_VECTOR", x - 2, y - 7), x - 1, y - 7
            )["Z"],
        },
        domain="FACE",
    ).outputs
    margin = t.math("MULTIPLY", size, LEVEL, x=x, y=y - 9)

    def reaching(xx, yy):
        center = face_center(t, xx, yy)
        height = separate(t, center, xx + 1, yy - 1)["Z"]
        return all_of(
            t,
            t.math(
                "LESS_THAN",
                proximity(
                    t,
                    flat,
                    t.vmath("MULTIPLY", center, (1.0, 1.0, 0.0), x=xx + 1, y=yy),
                    xx + 2,
                    yy,
                    "FACES",
                )["Distance"],
                face_radius(t, xx, yy - 3),
                x=xx + 4,
                y=yy,
            ),
            t.math(
                "GREATER_THAN",
                height,
                t.math("SUBTRACT", heights["Min"], margin, x=xx + 2, y=yy - 2),
                x=xx + 3,
                y=yy - 2,
            ),
            t.math(
                "LESS_THAN",
                height,
                t.math("ADD", heights["Max"], margin, x=xx + 2, y=yy - 3),
                x=xx + 3,
                y=yy - 3,
            ),
            x=xx + 5,
            y=yy,
        )

    face = t.attribute(".cracks_face", "INT", x + 1, y - 12)
    used = proximity(t, consumed, keyed(t, face, x + 2, y - 12), x + 3, y - 12)
    fresh = t.node(
        "GeometryNodeSeparateGeometry",
        x + 8,
        y,
        {
            "Geometry": ground,
            "Selection": all_of(
                t,
                reaching(x + 1, y - 2),
                t.math(
                    "GREATER_THAN",
                    separate(
                        t,
                        t.node("GeometryNodeInputNormal", x + 3, y - 10).outputs["Normal"],
                        x + 4,
                        y - 10,
                    )["Z"],
                    UPWARD,
                    x=x + 5,
                    y=y - 10,
                ),
                t.node(
                    "FunctionNodeBooleanMath",
                    x + 6,
                    y - 12,
                    {
                        0: boolean(
                            t,
                            "AND",
                            used["Is Valid"],
                            t.math("LESS_THAN", used["Distance"], 0.5, x=x + 4, y=y - 13),
                            x + 5,
                            y - 12,
                        )
                    },
                    operation="NOT",
                ).outputs[0],
                x=x + 7,
                y=y - 2,
            ),
        },
        domain="FACE",
    ).outputs["Selection"]
    # The faces taken from the ground, by their index
    taken = t.node(
        "GeometryNodePoints",
        x + 10,
        y - 14,
        {
            "Count": count(t, fresh, x + 9, y - 14, "Face Count"),
            "Position": keyed(
                t,
                t.node(
                    "GeometryNodeSampleIndex",
                    x + 9,
                    y - 16,
                    {
                        "Geometry": fresh,
                        "Value": face,
                        "Index": t.node("GeometryNodeInputIndex", x + 8, y - 17).outputs[0],
                    },
                    data_type="INT",
                    domain="FACE",
                ).outputs[0],
                x + 9.5,
                y - 16,
            ),
        },
    ).outputs[0]
    fresh = t.node("GeometryNodeTriangulate", x + 9, y, {"Mesh": fresh}).outputs[0]
    fresh = t.store(fresh, ".cracks_piece", "BOOLEAN", False, x + 10, y, domain="FACE")
    fresh = t.store(fresh, ".cracks_plate", "INT", -1, x + 11, y, domain="FACE")
    # With the faces of the patch not cut yet
    old = t.node(
        "GeometryNodeSeparateGeometry",
        x + 8,
        y + 4,
        {
            "Geometry": patch,
            "Selection": boolean(
                t,
                "AND",
                reaching(x + 1, y + 6),
                t.node(
                    "FunctionNodeBooleanMath",
                    x + 6,
                    y + 3,
                    {0: t.attribute(".cracks_piece", "BOOLEAN", x + 5, y + 3)},
                    operation="NOT",
                ).outputs[0],
                x + 7,
                y + 4,
            ),
        },
        domain="FACE",
    ).outputs
    pool = t.node("GeometryNodeJoinGeometry", x + 12, y)
    t.connect(fresh, pool.inputs[0])
    t.connect(old["Selection"], pool.inputs[0])
    pool = refined(t, pool.outputs[0], flat, size, x + 14, y)
    parts = t.node(
        "GeometryNodeSeparateGeometry",
        x + 30,
        y,
        {"Geometry": pool, "Selection": reaching(x + 24, y - 3)},
        domain="FACE",
    ).outputs

    # Cut along the plates around the new ones
    box = t.node("GeometryNodeBoundBox", x + 31, y - 6, {"Geometry": parts["Selection"]}).outputs
    around = t.node(
        "GeometryNodeSeparateGeometry",
        x + 31,
        y - 10,
        {
            "Geometry": plates,
            "Selection": boolean(
                t,
                "AND",
                t.attribute(".cracks_whole", "BOOLEAN", x + 29, y - 11),
                t.math(
                    "LESS_THAN",
                    t.attribute(".cracks_away", "FLOAT", x + 29, y - 12),
                    t.math("MULTIPLY_ADD", size, NEIGHBORS, inputs["Spread"], x=x + 29, y=y - 13),
                    x=x + 30,
                    y=y - 12,
                ),
                x + 30.5,
                y - 11,
            ),
        },
        domain="FACE",
    ).outputs["Selection"]
    pieces = t.node("GeometryNodeMeshBoolean", x + 46, y, operation="INTERSECT", solver="MANIFOLD")
    t.connect(face_prisms(t, parts["Selection"], size, x + 32, y), pieces.inputs["Mesh 2"])
    t.connect(
        plate_prisms(
            t,
            around,
            t.math(
                "SUBTRACT",
                separate(t, box["Min"], x + 32, y - 6)["Z"],
                t.math("MULTIPLY", size, 3.0, x=x + 32, y=y - 8),
                x=x + 33,
                y=y - 6,
            ),
            t.math("ADD", separate(t, box["Max"], x + 32, y - 7)["Z"], size, x=x + 33, y=y - 7),
            x + 34,
            y - 10,
        ),
        pieces.inputs["Mesh 2"],
    )
    pieces = t.node(
        "GeometryNodeDeleteGeometry",
        x + 47,
        y,
        {
            "Geometry": pieces.outputs["Mesh"],
            "Selection": t.math(
                "GREATER_THAN",
                t.attribute(".cracks_cut", "FLOAT", x + 46, y - 2),
                0.5,
                x=x + 46.5,
                y=y - 2,
            ),
        },
        domain="FACE",
    ).outputs[0]
    # Each piece is in the plate of the closest seed
    seeds = t.node(
        "GeometryNodeMeshToPoints",
        x + 46,
        y - 6,
        {"Mesh": plates, "Position": t.attribute(".cracks_seed", "FLOAT_VECTOR", x + 45, y - 7)},
        mode="FACES",
    ).outputs[0]
    closest = t.node(
        "GeometryNodeSampleNearest",
        x + 47,
        y - 4,
        {"Geometry": seeds, "Sample Position": face_center(t, x + 45, y - 4, flat=True)},
    ).outputs[0]
    pieces = t.store(
        pieces,
        ".cracks_seed",
        "FLOAT_VECTOR",
        sample(
            t,
            seeds,
            t.node("GeometryNodeInputPosition", x + 47, y - 6).outputs[0],
            closest,
            "FLOAT_VECTOR",
            x + 48,
            y - 4,
        ),
        x + 49,
        y,
        domain="FACE",
    )
    pieces = t.store(pieces, ".cracks_piece", "BOOLEAN", True, x + 50, y, domain="FACE")
    pieces = t.store(pieces, ".cracks_plate", "INT", -1, x + 51, y, domain="FACE")
    joined = t.node("GeometryNodeJoinGeometry", x + 52, y)
    for part in (pieces, parts["Inverted"], old["Inverted"]):
        t.connect(part, joined.inputs[0])
    patch = t.node(
        "GeometryNodeMergeByDistance",
        x + 53,
        y,
        {
            "Geometry": joined.outputs[0],
            "Distance": t.math("MULTIPLY", size, WELD, x=x + 52, y=y - 2),
        },
    ).outputs[0]
    return patch, taken


def numbered(t, patch, records, first, inputs, x, y):
    """The patch with the pieces of the new plates given the index of their records"""
    seed = t.attribute(".cracks_seed", "FLOAT_VECTOR", x, y - 2)
    flat = t.node(
        "GeometryNodeSetPosition",
        x,
        y - 5,
        {
            "Geometry": records,
            "Position": t.vmath(
                "MULTIPLY",
                t.node("GeometryNodeInputPosition", x - 2, y - 6).outputs[0],
                (1.0, 1.0, 0.0),
                x=x - 1,
                y=y - 6,
            ),
        },
    ).outputs[0]
    closest = t.node(
        "GeometryNodeSampleNearest", x + 1, y - 4, {"Geometry": flat, "Sample Position": seed}
    ).outputs[0]
    key = sample(
        t,
        records,
        t.node("GeometryNodeInputPosition", x + 1, y - 6).outputs[0],
        closest,
        "FLOAT_VECTOR",
        x + 2,
        y - 4,
    )
    apart = t.vmath(
        "ABSOLUTE",
        t.vmath(
            "SUBTRACT",
            key,
            t.vmath(
                "ADD",
                seed,
                combine(
                    t, x + 2, y - 8, Z=separate(t, face_center(t, x, y - 8), x + 1, y - 8)["Z"]
                ),
                x=x + 3,
                y=y - 7,
            ),
            x=x + 4,
            y=y - 4,
        ),
        x=x + 5,
        y=y - 4,
    )
    apart = separate(t, apart, x + 6, y - 4)
    size = inputs["Size"]
    same = t.math("MULTIPLY", size, SAME, x=x + 5, y=y - 6)
    match = all_of(
        t,
        t.attribute(".cracks_piece", "BOOLEAN", x + 6, y - 2),
        t.math("LESS_THAN", t.attribute(".cracks_plate", "INT", x + 6, y - 3), 0, x=x + 7, y=y - 3),
        t.math(
            "GREATER_THAN",
            count(t, records, x + 6, y - 9, component="POINTCLOUD"),
            0,
            x=x + 7,
            y=y - 9,
        ),
        t.math("LESS_THAN", apart["X"], same, x=x + 7, y=y - 4),
        t.math("LESS_THAN", apart["Y"], same, x=x + 7, y=y - 5),
        t.math(
            "LESS_THAN",
            apart["Z"],
            t.math("MULTIPLY", size, LEVEL, x=x + 6, y=y - 7),
            x=x + 7,
            y=y - 6,
        ),
        x=x + 8,
        y=y - 2,
    )
    return t.store(
        patch,
        ".cracks_plate",
        "INT",
        switch(
            t,
            match,
            t.attribute(".cracks_plate", "INT", x + 10, y - 3),
            t.math("ADD", first, closest, x=x + 10, y=y - 4),
            "INT",
            x + 11,
            y - 2,
        ),
        x + 12,
        y,
        domain="FACE",
    )


def solid(t, patch, first, thickness, x, y):
    """Plates of the pieces of the patch from the first index on, each a loose closed part, with
    the faces inside the mesh marked"""
    plate = t.attribute(".cracks_plate", "INT", x - 1, y - 2)
    tops = t.node(
        "GeometryNodeSeparateGeometry",
        x + 1,
        y,
        {
            "Geometry": patch,
            "Selection": t.math(
                "GREATER_THAN",
                plate,
                t.math("SUBTRACT", first, 0.5, x=x - 1, y=y - 3),
                x=x,
                y=y - 2,
            ),
        },
        domain="FACE",
    ).outputs["Selection"]
    tops = t.node(
        "GeometryNodeSplitToInstances",
        x + 2,
        y,
        {"Geometry": tops, "Group ID": plate},
        domain="FACE",
    ).outputs["Instances"]
    tops = t.node("GeometryNodeRealizeInstances", x + 3, y, {"Geometry": tops}).outputs[0]
    # Of the points, to move each plate as a whole
    tops = t.store(tops, ".cracks_record", "INT", plate, x + 4, y)
    sides = t.node(
        "GeometryNodeExtrudeMesh",
        x + 5,
        y,
        {
            "Mesh": tops,
            "Offset": combine(t, x + 4, y - 2, Z=1.0),
            "Offset Scale": thickness,
            "Individual": False,
        },
        mode="FACES",
    ).outputs
    inner = t.node(
        "FunctionNodeBooleanMath", x + 6, y - 2, {0: sides["Top"]}, operation="NOT"
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", x + 8, y)
    t.connect(
        t.store(sides["Mesh"], ".cracks_inner", "FLOAT", inner, x + 7, y, domain="FACE"),
        joined.inputs[0],
    )
    t.connect(
        t.store(
            t.node("GeometryNodeFlipFaces", x + 5, y - 4, {"Mesh": tops}).outputs[0],
            ".cracks_inner",
            "FLOAT",
            1.0,
            x + 7,
            y - 4,
            domain="FACE",
        ),
        joined.inputs[0],
    )
    return t.node(
        "GeometryNodeSetPosition",
        x + 10,
        y,
        {
            "Geometry": joined.outputs[0],
            "Offset": combine(
                t, x + 9, y - 2, Z=t.math("MULTIPLY", thickness, -1.0, x=x + 8, y=y - 3)
            ),
        },
    ).outputs[0]


def posed(t, records, inputs, x, y, settled=False, raised=None):
    """Position of the points of the plates, turned about their pivot and moved as their record
    tells, settling and jumping after they break if not settled already, flat if not raised"""
    record = t.attribute(".cracks_record", "INT", x, y)

    def of(name, data_type, yy):
        return sample(t, records, t.attribute(name, data_type, x, yy), record, data_type, x + 1, yy)

    pivot = of(".cracks_pivot", "FLOAT_VECTOR", y - 1)
    shrink = of(".cracks_shrink", "FLOAT", y - 2)
    turn = of(".cracks_turn", "FLOAT_VECTOR", y - 3)
    move = separate(t, of(".cracks_move", "FLOAT_VECTOR", y - 4), x + 2, y - 4)
    rise = t.math("MULTIPLY", of(".cracks_down", "FLOAT", y - 5), -1.0, x=x + 2, y=y - 5)
    if raised is None:
        raised = of(".cracks_raised", "FLOAT", y - 9)
    eased = 1.0
    if not settled:
        age = t.math(
            "SUBTRACT",
            t.node("GeometryNodeInputSceneTime", x, y - 8).outputs["Seconds"],
            of(".cracks_born", "FLOAT", y - 7),
            x=x + 2,
            y=y - 7,
        )
        time = t.math(
            "MULTIPLY",
            t.math("SQRT", t.math("DIVIDE", inputs["Size"], 0.1, x=x, y=y - 10), x=x + 1, y=y - 10),
            SETTLE,
            x=x + 2,
            y=y - 10,
        )
        left = t.math(
            "SUBTRACT",
            1.0,
            t.math("DIVIDE", age, time, x=x + 3, y=y - 8, clamp=True),
            x=x + 4,
            y=y - 8,
        )
        eased = t.math(
            "SUBTRACT", 1.0, t.math("MULTIPLY", left, left, x=x + 5, y=y - 8), x=x + 6, y=y - 8
        )
        jump = t.math(
            "MAXIMUM",
            t.math(
                "MULTIPLY",
                age,
                t.math(
                    "SUBTRACT",
                    of(".cracks_jump", "FLOAT", y - 6),
                    t.math("MULTIPLY", age, 0.5 * GRAVITY, x=x + 3, y=y - 7),
                    x=x + 4,
                    y=y - 6,
                ),
                x=x + 5,
                y=y - 6,
            ),
            0.0,
            x=x + 6,
            y=y - 6,
        )
        rise = t.math("MULTIPLY_ADD", jump, raised, rise, x=x + 7, y=y - 5)
    amount = t.math("MULTIPLY", eased, raised, x=x + 7, y=y - 9)
    offset = t.vmath(
        "MULTIPLY",
        t.vmath(
            "SUBTRACT",
            t.node("GeometryNodeInputPosition", x, y - 12).outputs[0],
            pivot,
            x=x + 2,
            y=y - 1,
        ),
        combine(t, x + 2, y - 2, X=shrink, Y=shrink, Z=1.0),
        x=x + 3,
        y=y - 1,
    )
    turned = t.node(
        "ShaderNodeVectorRotate",
        x + 8,
        y - 1,
        {
            "Vector": offset,
            "Axis": t.vmath("NORMALIZE", turn, x=x + 2, y=y - 3),
            "Angle": t.math(
                "MULTIPLY", t.vmath("LENGTH", turn, x=x + 2, y=y - 3.5), amount, x=x + 7, y=y - 3
            ),
        },
        rotation_type="AXIS_ANGLE",
    ).outputs[0]
    moved = combine(
        t,
        x + 9,
        y - 4,
        X=t.math("MULTIPLY", move["X"], eased, x=x + 8, y=y - 4),
        Y=t.math("MULTIPLY", move["Y"], eased, x=x + 8, y=y - 5),
        Z=t.math("MULTIPLY_ADD", move["Z"], amount, rise, x=x + 8, y=y - 6),
    )
    return t.vmath("ADD", t.vmath("ADD", pivot, turned, x=x + 9, y=y - 1), moved, x=x + 10, y=y - 1)


def over(t, records, plates, near, inputs, raised, x, y):
    """How far each plate, settled, is over the lowest side of the Colliders above it"""
    reach = t.math("MULTIPLY", inputs["Size"], REACH, x=x, y=y - 2)
    plates = t.node(
        "GeometryNodeSetPosition",
        x + 12,
        y,
        {
            "Geometry": plates,
            "Position": posed(t, records, inputs, x, y - 4, settled=True, raised=raised),
        },
    ).outputs[0]
    position = t.node("GeometryNodeInputPosition", x + 12, y - 3).outputs[0]
    record = t.attribute(".cracks_record", "INT", x + 12, y - 4)
    # The points of the plates over the Colliders
    ray = t.node(
        "GeometryNodeRaycast",
        x + 14,
        y - 2,
        {
            "Target Geometry": near,
            "Source Position": t.vmath(
                "SUBTRACT", position, combine(t, x + 12, y - 6, Z=reach), x=x + 13, y=y - 3
            ),
            "Ray Direction": (0.0, 0.0, 1.0),
            "Ray Length": reach,
        },
    ).outputs
    most = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", reach, ray["Hit Distance"], x=x + 15, y=y - 2),
        ray["Is Hit"],
        x=x + 16,
        y=y - 2,
    )
    plates = t.store(
        plates,
        ".cracks_over",
        "FLOAT",
        t.node(
            "GeometryNodeFieldMinAndMax",
            x + 17,
            y - 2,
            {"Value": most, "Group ID": record},
            data_type="FLOAT",
            domain="POINT",
        ).outputs["Max"],
        x + 18,
        y,
    )
    # The points of the Colliders under the top of the plates
    tops = t.node(
        "GeometryNodeSeparateGeometry",
        x + 19,
        y - 6,
        {
            "Geometry": plates,
            "Selection": t.math(
                "LESS_THAN",
                t.attribute(".cracks_inner", "FLOAT", x + 18, y - 7),
                0.5,
                x=x + 18.5,
                y=y - 7,
            ),
        },
        domain="FACE",
    ).outputs["Selection"]
    ray = t.node(
        "GeometryNodeRaycast",
        x + 20,
        y - 6,
        {
            "Target Geometry": tops,
            "Attribute": record,
            "Source Position": position,
            "Ray Direction": (0.0, 0.0, 1.0),
            "Ray Length": reach,
        },
        data_type="INT",
    ).outputs
    near = t.store(
        near,
        ".cracks_under",
        "INT",
        switch(t, ray["Is Hit"], -1, ray["Attribute"], "INT", x + 21, y - 6),
        x + 22,
        y - 6,
    )
    near = t.store(
        near,
        ".cracks_over",
        "FLOAT",
        t.node(
            "GeometryNodeFieldMinAndMax",
            x + 22,
            y - 8,
            {
                "Value": t.math("MULTIPLY", ray["Hit Distance"], ray["Is Hit"], x=x + 21, y=y - 8),
                "Group ID": t.attribute(".cracks_under", "INT", x + 21, y - 9),
            },
            data_type="FLOAT",
            domain="POINT",
        ).outputs["Max"],
        x + 23,
        y - 6,
    )

    index = t.node("GeometryNodeInputIndex", x + 24, y - 12).outputs[0]
    most = 0.0
    for i, (geometry, name) in enumerate(((plates, ".cracks_record"), (near, ".cracks_under"))):
        yy = y - 2 - i * 6
        # Any point of the plate, as they all have its most
        keys = t.node(
            "GeometryNodePoints",
            x + 25,
            yy,
            {
                "Count": count(t, geometry, x + 24, yy),
                "Position": keyed(
                    t,
                    sample(
                        t,
                        geometry,
                        t.attribute(name, "INT", x + 23, yy - 2),
                        t.node("GeometryNodeInputIndex", x + 23, yy - 3).outputs[0],
                        "INT",
                        x + 24,
                        yy - 2,
                    ),
                    x + 24.5,
                    yy - 2,
                ),
            },
        ).outputs[0]
        found = t.node(
            "GeometryNodeSampleNearest",
            x + 26,
            yy,
            {"Geometry": keys, "Sample Position": keyed(t, index, x + 25, yy - 3)},
        ).outputs[0]
        same = t.node(
            "FunctionNodeCompare",
            x + 28,
            yy,
            {
                "A": sample(
                    t, geometry, t.attribute(name, "INT", x + 26, yy - 2), found, "INT", x + 27, yy
                ),
                "B": index,
            },
            data_type="INT",
            operation="EQUAL",
        ).outputs[0]
        most = t.math(
            "MAXIMUM",
            most,
            t.math(
                "MULTIPLY",
                sample(
                    t,
                    geometry,
                    t.attribute(".cracks_over", "FLOAT", x + 26, yy - 3),
                    found,
                    "FLOAT",
                    x + 27,
                    yy - 2,
                ),
                boolean(
                    t,
                    "AND",
                    same,
                    t.math(
                        "GREATER_THAN", count(t, geometry, x + 27, yy - 4), 0, x=x + 28, y=yy - 4
                    ),
                    x + 28.5,
                    yy,
                ),
                x=x + 29,
                y=yy,
            ),
            x=x + 30 + i,
            y=y - 2,
        )
    return most


def pushed(t, records, plates, near, inputs, x, y):
    """Records with the plates under the Colliders flattened as much as needed to get under
    them, then pushed down, for good"""
    records = t.store(
        records,
        ".cracks_over",
        "FLOAT",
        over(t, records, plates, near, inputs, None, x, y),
        x + 34,
        y,
    )
    records = t.store(
        records,
        ".cracks_flat",
        "FLOAT",
        over(t, records, plates, near, inputs, 0.0, x, y - 20),
        x + 35,
        y,
    )
    most = t.attribute(".cracks_over", "FLOAT", x + 35, y - 2)
    flat = t.attribute(".cracks_flat", "FLOAT", x + 35, y - 3)
    raised = t.attribute(".cracks_raised", "FLOAT", x + 35, y - 4)
    # As over the Colliders as raised, about
    less = t.math(
        "MULTIPLY",
        raised,
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", flat, -1.0, x=x + 36, y=y - 3),
            t.math(
                "MAXIMUM",
                t.math("SUBTRACT", most, flat, x=x + 36, y=y - 4),
                1e-6,
                x=x + 37,
                y=y - 4,
            ),
            x=x + 38,
            y=y - 3,
            clamp=True,
        ),
        x=x + 39,
        y=y - 3,
    )
    touched = t.math("GREATER_THAN", most, 0.0, x=x + 36, y=y - 2)
    records = t.store(
        records,
        ".cracks_raised",
        "FLOAT",
        switch(t, touched, raised, less, "FLOAT", x + 40, y - 3),
        x + 41,
        y,
    )
    return t.store(
        records,
        ".cracks_down",
        "FLOAT",
        t.math(
            "ADD",
            t.attribute(".cracks_down", "FLOAT", x + 40, y - 6),
            t.math(
                "MULTIPLY",
                t.math("MAXIMUM", flat, 0.0, x=x + 39, y=y - 7),
                touched,
                x=x + 40,
                y=y - 7,
            ),
            x=x + 41,
            y=y - 6,
        ),
        x + 42,
        y,
    )


def thrown(t, new, hits, ground, inputs, x, y):
    """Pebbles on the new plates, thrown up and away from the hits, with the material of the
    ground there"""
    frame = t.node("GeometryNodeInputSceneTime", x - 2, y - 4).outputs["Frame"]
    seed = t.math("ADD", inputs["Seed"], frame, x=x - 1, y=y - 4)
    density = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            inputs["Debris Amount"],
            t.attribute(".cracks_amount", "FLOAT", x - 2, y - 2),
            x=x - 1,
            y=y - 2,
        ),
        switch(
            t,
            t.math(
                "GREATER_THAN",
                t.attribute(".cracks_away", "FLOAT", x - 2, y - 3),
                0.0,
                x=x - 1,
                y=y - 3,
            ),
            DEBRIS_UNDER,
            1.0,
            "FLOAT",
            x - 0.5,
            y - 3,
        ),
        x=x,
        y=y - 2,
    )
    points = t.node(
        "GeometryNodeDistributePointsOnFaces",
        x + 1,
        y,
        {"Mesh": new, "Density": density, "Seed": seed},
        distribute_method="RANDOM",
    ).outputs["Points"]
    ids = t.node("GeometryNodeInputIndex", x + 1, y - 4).outputs[0]

    def rand(low, high, offset, yy, data_type="FLOAT"):
        return random(
            t, low, high, ids, t.math("ADD", seed, offset, x=x + 1, y=yy), x + 2, yy, data_type
        )

    # Their radius
    size = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Debris Size"], 0.5, x=x + 3, y=y - 6),
        t.math("POWER", rand(0.6, 1.3, 1, y - 5), 2.0, x=x + 3, y=y - 5),
        x=x + 4,
        y=y - 5,
    )
    position = t.node("GeometryNodeInputPosition", x + 1, y - 7).outputs[0]
    at = t.vmath(
        "ADD",
        position,
        combine(
            t,
            x + 5,
            y - 7,
            Z=t.math(
                "ADD",
                separate(t, t.attribute(".cracks_key", "FLOAT_VECTOR", x + 3, y - 7), x + 4, y - 7)[
                    "Z"
                ],
                size,
                x=x + 4.5,
                y=y - 8,
            ),
        ),
        x=x + 6,
        y=y - 7,
    )
    center = t.node(
        "GeometryNodeAttributeStatistic",
        x + 3,
        y - 10,
        {
            "Geometry": hits,
            "Attribute": t.node("GeometryNodeInputPosition", x + 2, y - 10).outputs[0],
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs["Mean"]
    out = t.vmath(
        "NORMALIZE",
        t.vmath(
            "MULTIPLY",
            t.vmath("SUBTRACT", position, center, x=x + 4, y=y - 10),
            (1.0, 1.0, 0.0),
            x=x + 5,
            y=y - 10,
        ),
        x=x + 6,
        y=y - 10,
    )
    direction = t.vmath(
        "NORMALIZE",
        t.vmath(
            "ADD",
            t.vmath(
                "ADD",
                out,
                rand((-0.7, -0.7, 0.0), (0.7, 0.7, 0.0), 2, y - 12, "FLOAT_VECTOR"),
                x=x + 7,
                y=y - 10,
            ),
            combine(t, x + 7, y - 14, Z=rand(0.8, 2.5, 3, y - 14)),
            x=x + 8,
            y=y - 10,
        ),
        x=x + 9,
        y=y - 10,
    )
    speed = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.attribute(".cracks_hit", "FLOAT", x + 7, y - 16),
            inputs["Debris Speed"],
            x=x + 8,
            y=y - 16,
        ),
        rand(0.2, 1.0, 4, y - 17),
        x=x + 9,
        y=y - 16,
    )
    material = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 8,
        y - 28,
        {
            "Mesh": ground,
            "Value": t.node("GeometryNodeInputMaterialIndex", x + 7, y - 28).outputs[0],
            "Sample Position": at,
        },
        data_type="INT",
    ).outputs["Value"]
    points = t.node(
        "GeometryNodeSetPosition", x + 10, y, {"Geometry": points, "Position": at}
    ).outputs[0]
    for i, (name, data_type, value) in enumerate(
        (
            (
                ".cracks_velocity",
                "FLOAT_VECTOR",
                t.vmath("SCALE", direction, speed, x=x + 10, y=y - 10),
            ),
            (
                ".cracks_scale",
                "FLOAT_VECTOR",
                t.vmath(
                    "SCALE",
                    combine(
                        t,
                        x + 4,
                        y - 19,
                        X=1.0,
                        Y=rand(*DEBRIS_FLAT[0], 5, y - 19),
                        Z=rand(*DEBRIS_FLAT[1], 6, y - 20),
                    ),
                    size,
                    x=x + 5,
                    y=y - 19,
                ),
            ),
            (
                ".cracks_rotation",
                "FLOAT_VECTOR",
                rand((-3.1416,) * 3, (3.1416,) * 3, 7, y - 22, "FLOAT_VECTOR"),
            ),
            (
                ".cracks_spin",
                "FLOAT_VECTOR",
                rand((-DEBRIS_SPIN,) * 3, (DEBRIS_SPIN,) * 3, 8, y - 24, "FLOAT_VECTOR"),
            ),
            (".cracks_shape", "INT", rand(0, DEBRIS_SHAPES - 1, 9, y - 26, "INT")),
            (".cracks_material", "INT", material),
        )
    ):
        points = t.store(points, name, data_type, value, x + 11 + i, y)
    return points


def fallen(t, debris, mesh, bottom, fall, dt, x, y):
    """Pebbles falling, bouncing and coming to rest on the mesh, gone below the bottom"""
    position = t.node("GeometryNodeInputPosition", x, y - 6).outputs[0]
    moving = t.vmath(
        "ADD",
        t.attribute(".cracks_velocity", "FLOAT_VECTOR", x, y - 1),
        t.vmath("SCALE", fall, dt, x=x, y=y - 3),
        x=x + 1,
        y=y - 1,
    )
    radius = separate(t, t.attribute(".cracks_scale", "FLOAT_VECTOR", x, y - 10), x + 1, y - 10)[
        "Z"
    ]
    way = t.vmath("NORMALIZE", moving, x=x + 2, y=y - 3)
    # Along their way, from their size back as they rest on the mesh
    ray = t.node(
        "GeometryNodeRaycast",
        x + 5,
        y - 6,
        {
            "Target Geometry": mesh,
            "Source Position": t.vmath(
                "SUBTRACT",
                position,
                t.vmath("SCALE", way, radius, x=x + 3, y=y - 7),
                x=x + 4,
                y=y - 6,
            ),
            "Ray Direction": way,
            "Ray Length": t.math(
                "MULTIPLY_ADD",
                t.vmath("LENGTH", moving, x=x + 2, y=y - 9),
                dt,
                t.math("MULTIPLY", radius, 2.0, x=x + 3, y=y - 10),
                x=x + 4,
                y=y - 9,
            ),
        },
    ).outputs
    landed = ray["Is Hit"]
    # Towards the pebble, also for the faces hit from behind
    normal = t.vmath(
        "SCALE",
        ray["Hit Normal"],
        t.math(
            "SIGN",
            t.math(
                "MULTIPLY",
                t.vmath("DOT_PRODUCT", way, ray["Hit Normal"], x=x + 6, y=y - 8),
                -1.0,
                x=x + 7,
                y=y - 8,
            ),
            x=x + 8,
            y=y - 8,
        ),
        x=x + 9,
        y=y - 7,
    )
    point = switch(
        t,
        landed,
        t.vmath("ADD", position, t.vmath("SCALE", moving, dt, x=x + 2, y=y - 5), x=x + 3, y=y - 5),
        t.vmath(
            "ADD",
            ray["Hit Position"],
            t.vmath("SCALE", normal, radius, x=x + 10, y=y - 7),
            x=x + 11,
            y=y - 6,
        ),
        "VECTOR",
        x + 12,
        y - 5,
    )
    into = t.math(
        "MINIMUM",
        t.vmath("DOT_PRODUCT", moving, normal, x=x + 10, y=y - 14),
        0.0,
        x=x + 11,
        y=y - 14,
    )
    bounced = t.vmath(
        "SUBTRACT",
        t.vmath(
            "SCALE", along(t, moving, normal, x + 10, y - 16), 1.0 - FRICTION, x=x + 13, y=y - 16
        ),
        t.vmath(
            "SCALE",
            normal,
            t.math("MULTIPLY", into, BOUNCE, x=x + 12, y=y - 14),
            x=x + 13,
            y=y - 14,
        ),
        x=x + 14,
        y=y - 14,
    )
    # Resting below a bounce of their size
    resting = t.math(
        "LESS_THAN",
        t.vmath("LENGTH", bounced, x=x + 15, y=y - 15),
        t.math(
            "SQRT",
            t.math("MULTIPLY", radius, 2.0 * GRAVITY, x=x + 14, y=y - 17),
            x=x + 15,
            y=y - 17,
        ),
        x=x + 16,
        y=y - 15,
    )
    bounced = switch(t, resting, bounced, (0.0, 0.0, 0.0), "VECTOR", x + 17, y - 14)
    moving = switch(t, landed, moving, bounced, "VECTOR", x + 18, y - 2)
    turned = t.vmath(
        "ADD",
        t.attribute(".cracks_rotation", "FLOAT_VECTOR", x + 16, y - 19),
        t.vmath(
            "SCALE",
            t.attribute(".cracks_spin", "FLOAT_VECTOR", x + 16, y - 20),
            t.math(
                "MULTIPLY",
                dt,
                t.math("SUBTRACT", 1.0, landed, x=x + 16, y=y - 21),
                x=x + 17,
                y=y - 21,
            ),
            x=x + 18,
            y=y - 20,
        ),
        x=x + 19,
        y=y - 19,
    )
    debris = t.store(debris, ".cracks_velocity", "FLOAT_VECTOR", moving, x + 19, y)
    debris = t.store(debris, ".cracks_rotation", "FLOAT_VECTOR", turned, x + 20, y)
    debris = t.node(
        "GeometryNodeSetPosition", x + 21, y, {"Geometry": debris, "Position": point}
    ).outputs[0]
    return t.node(
        "GeometryNodeDeleteGeometry",
        x + 23,
        y,
        {
            "Geometry": debris,
            "Selection": t.math(
                "LESS_THAN",
                separate(
                    t, t.node("GeometryNodeInputPosition", x + 21, y - 2).outputs[0], x + 22, y - 2
                )["Z"],
                bottom,
                x=x + 22.5,
                y=y - 2,
            ),
        },
        domain="POINT",
    ).outputs[0]


def pebbles(t, debris, materials, color, x, y):
    """Dented spheres at the pebbles, with the material of the mesh where they come from, fully
    tinted, as an instance not to be changed by the modifiers after"""
    shapes = t.node("GeometryNodeGeometryToInstance", x + 2, y - 4)
    sphere = t.node(
        "GeometryNodeMeshIcoSphere", x - 1, y - 4, {"Radius": 1.0, "Subdivisions": 2}
    ).outputs["Mesh"]
    sphere = t.node(
        "GeometryNodeSetShadeSmooth", x, y - 4, {"Mesh": sphere}, domain="FACE"
    ).outputs[0]
    for i in range(DEBRIS_SHAPES):
        dent = t.node(
            "ShaderNodeTexNoise",
            x,
            y - 6 - i * 2,
            {
                "Vector": t.vmath(
                    "ADD",
                    t.node("GeometryNodeInputPosition", x - 2, y - 6 - i * 2).outputs[0],
                    (7.0 * i, 0.0, 0.0),
                    x=x - 1,
                    y=y - 6 - i * 2,
                ),
                "Scale": 1.2,
                "Detail": 1.0,
            },
        ).outputs["Fac"]
        t.connect(
            t.node(
                "GeometryNodeSetPosition",
                x + 1.5,
                y - 5 - i * 2,
                {
                    "Geometry": sphere,
                    "Offset": t.vmath(
                        "SCALE",
                        t.node("GeometryNodeInputPosition", x, y - 7 - i * 2).outputs[0],
                        t.math(
                            "MULTIPLY",
                            t.math("SUBTRACT", dent, 0.5, x=x + 0.5, y=y - 6 - i * 2),
                            2.0 * DEBRIS_DENT,
                            x=x + 1,
                            y=y - 6 - i * 2,
                        ),
                        x=x + 1.2,
                        y=y - 7 - i * 2,
                    ),
                },
            ).outputs[0],
            shapes.inputs[0],
        )
    chips = t.node(
        "GeometryNodeInstanceOnPoints",
        x + 4,
        y,
        {
            "Points": debris,
            "Instance": shapes.outputs[0],
            "Pick Instance": True,
            "Instance Index": t.attribute(".cracks_shape", "INT", x + 3, y - 2),
            "Rotation": t.node(
                "FunctionNodeEulerToRotation",
                x + 3,
                y - 3,
                {0: t.attribute(".cracks_rotation", "FLOAT_VECTOR", x + 2, y - 3)},
            ).outputs[0],
            "Scale": t.attribute(".cracks_scale", "FLOAT_VECTOR", x + 3, y - 5),
        },
    ).outputs[0]
    chips = t.node("GeometryNodeRealizeInstances", x + 5, y, {"Geometry": chips}).outputs[0]
    chips = t.store(chips, ".cracks_pebble", "BOOLEAN", True, x + 6, y)
    # The materials of the mesh from its loose points, linked last, without its attributes
    joined = t.node("GeometryNodeJoinGeometry", x + 8, y)
    t.connect(chips, joined.inputs[0])
    t.connect(
        t.strip(
            t.node(
                "GeometryNodeDeleteGeometry",
                x + 6,
                y - 6,
                {"Geometry": materials, "Selection": True},
                domain="FACE",
                mode="ONLY_FACE",
            ).outputs[0],
            x + 7,
            y - 6,
        ),
        joined.inputs[0],
    )
    chips = t.node(
        "GeometryNodeSetMaterialIndex",
        x + 9,
        y,
        {
            "Geometry": joined.outputs[0],
            "Material Index": t.attribute(".cracks_material", "INT", x + 8, y - 2),
        },
    ).outputs[0]
    chips = t.node(
        "GeometryNodeDeleteGeometry",
        x + 10,
        y,
        {
            "Geometry": chips,
            "Selection": t.node(
                "FunctionNodeBooleanMath",
                x + 9.5,
                y - 3,
                {0: t.attribute(".cracks_pebble", "BOOLEAN", x + 9, y - 3)},
                operation="NOT",
            ).outputs[0],
        },
    ).outputs[0]
    rgb = t.node("FunctionNodeSeparateColor", x + 9, y - 5, {0: color}).outputs
    tint = t.node(
        "FunctionNodeCombineColor",
        x + 10,
        y - 5,
        {"Red": rgb["Red"], "Green": rgb["Green"], "Blue": rgb["Blue"], "Alpha": 0.0},
    ).outputs[0]
    chips = t.store(chips, "cracks", "FLOAT_COLOR", tint, x + 11, y, domain="CORNER")
    chips = t.node(
        "GeometryNodeRemoveAttribute",
        x + 12,
        y,
        {"Geometry": chips, "Pattern Mode": "Wildcard", "Name": ".cracks_*"},
    ).outputs[0]
    return t.node("GeometryNodeGeometryToInstance", x + 13, y, {0: chips}).outputs[0]


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Break the mesh into plates where the Colliders hit it, as asphalt, concrete or ice, "
        "storing the cracks attribute read by the Cracks Tint shader"
    )
    add_output(ng, "Geometry", "NodeSocketGeometry")
    build_inputs(ng)

    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -14, 0).outputs
    self_object = t.node("GeometryNodeSelfObject", -14, -2).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -13, -2, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]

    t.section("Plane Space", row=True)
    parts = t.node(
        "GeometryNodeSeparateComponents", -13, 0, {"Geometry": inputs["Geometry"]}
    ).outputs
    # The side the mesh faces, up if closed, turned to Z
    normal = t.node(
        "FunctionNodeTransformDirection",
        -12,
        -4,
        {
            "Direction": t.node("GeometryNodeInputNormal", -13, -4).outputs["Normal"],
            "Transform": to_world,
        },
    ).outputs[0]
    area = t.node("GeometryNodeInputMeshFaceArea", -13, -6).outputs[0]
    facing = t.node(
        "GeometryNodeAttributeStatistic",
        -10,
        -4,
        {"Geometry": parts["Mesh"], "Attribute": t.vmath("SCALE", normal, area, x=-11, y=-4)},
        data_type="FLOAT_VECTOR",
        domain="FACE",
    ).outputs["Sum"]
    total = t.node(
        "GeometryNodeAttributeStatistic",
        -10,
        -6,
        {"Geometry": parts["Mesh"], "Attribute": area},
        domain="FACE",
    ).outputs["Sum"]
    is_open = t.math(
        "GREATER_THAN",
        t.vmath("LENGTH", facing, x=-9, y=-4),
        t.math("MULTIPLY", total, 0.5, x=-9, y=-6),
        x=-8,
        y=-4,
    )
    up = switch(
        t, is_open, (0.0, 0.0, 1.0), t.vmath("NORMALIZE", facing, x=-8, y=-5), "VECTOR", -7, -4
    )
    turn = t.node("FunctionNodeAlignRotationToVector", -6, -4, {"Vector": up}, axis="Z").outputs[0]
    back = t.node("FunctionNodeInvertRotation", -5, -4, {0: turn}).outputs[0]
    to_plane = t.node("FunctionNodeCombineTransform", -4, -4, {"Rotation": back}).outputs[0]
    fall = t.node(
        "FunctionNodeRotateVector", -4, -10, {"Vector": (0.0, 0.0, -GRAVITY), "Rotation": back}
    ).outputs[0]
    from_plane = t.node(
        "FunctionNodeMatrixMultiply",
        -2,
        -6,
        {
            0: t.node("FunctionNodeInvertMatrix", -3, -6, {0: to_world}).outputs[0],
            1: t.node("FunctionNodeCombineTransform", -4, -6, {"Rotation": turn}).outputs[0],
        },
    ).outputs[0]
    ground = t.node(
        "GeometryNodeTransform",
        -2,
        0,
        {
            "Geometry": t.store(
                parts["Mesh"],
                ".cracks_face",
                "INT",
                t.node("GeometryNodeInputIndex", -13, -8).outputs[0],
                -12,
                0,
                domain="FACE",
            ),
            "Mode": "Matrix",
            "Transform": t.node(
                "FunctionNodeMatrixMultiply", -3, -2, {0: to_plane, 1: to_world}
            ).outputs[0],
        },
    ).outputs[0]
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        -4,
        -8,
        {"Collection": inputs["Colliders"]},
        transform_space="ORIGINAL",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", -3, -8, {"Geometry": colliders}).outputs[0]
    colliders = t.node(
        "GeometryNodeTransform",
        -2,
        -8,
        {"Geometry": colliders, "Mode": "Matrix", "Transform": to_plane},
    ).outputs[0]

    t.section("Simulation", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -4).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-4)
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 120, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items[0].name = "Colliders"
    for name in ("Records", "Patch", "Plates", "Taken", "Debris"):
        sim_out.state_items.new("GEOMETRY", name)
    t.connect(positions(t, colliders, 0, -6), sim_in.inputs["Colliders"])
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=3, y=-4)
    colliders = velocity(t, colliders, sim_in.outputs["Colliders"], dt, 3, -6)
    t.connect(positions(t, colliders, 8, -6), sim_out.inputs["Colliders"])
    state = {name: sim_in.outputs[name] for name in ("Records", "Patch", "Plates", "Taken")}

    t.section("Hits", row=True)
    near, hits = contacts(t, colliders, ground, inputs, 0, 0)
    hitting = t.math("GREATER_THAN", count(t, hits, 18, -2, component="POINTCLOUD"), 0, x=19, y=-2)

    t.section("Plates", row=True)
    plates = breaking(
        t, lattice(t, hits, inputs, 0, 0), hits, ground, state["Records"], inputs, 44, 0
    )
    new, records = recorded(t, plates, hits, inputs, 64, 0)
    broken = t.math(
        "GREATER_THAN", count(t, records, 88, -2, component="POINTCLOUD"), 0, x=89, y=-2
    )
    # Only computed when breaking
    broken = switch(t, hitting, False, broken, "BOOLEAN", 90, -2)

    t.section("Patch", row=True)
    first = count(t, state["Records"], 0, -2, component="POINTCLOUD")
    patch, taken = tiled(t, ground, state["Patch"], state["Taken"], plates, inputs, 0, 0)
    patch = numbered(t, patch, records, first, inputs, 56, 0)
    # The last one linked comes first, keeping the indices of the old ones
    joined = {}
    for i, (name, added) in enumerate(
        (
            ("Records", records),
            ("Plates", solid(t, patch, first, inputs["Thickness"], 70, -8)),
            ("Taken", taken),
        )
    ):
        joined[name] = t.node("GeometryNodeJoinGeometry", 82, -i * 4)
        t.connect(added, joined[name].inputs[0])
        t.connect(state[name], joined[name].inputs[0])
    for i, (name, value) in enumerate(
        (("Patch", patch), *((k, v.outputs[0]) for k, v in joined.items()))
    ):
        state[name] = switch(t, broken, state[name], value, "GEOMETRY", 84, -i * 4)

    t.section("Push", row=True)
    # Only the Colliders as low as the plates get
    near = t.node(
        "GeometryNodeSeparateGeometry",
        -2,
        0,
        {
            "Geometry": near,
            "Selection": t.math(
                "LESS_THAN",
                t.attribute(".cracks_height", "FLOAT", -4, -2),
                t.math(
                    "ADD",
                    t.math("ADD", inputs["Size"], inputs["Lift"], x=-5, y=-3),
                    inputs["Contact"],
                    x=-4,
                    y=-3,
                ),
                x=-3,
                y=-2,
            ),
        },
        domain="POINT",
    ).outputs["Selection"]
    touching = boolean(
        t,
        "AND",
        t.math("GREATER_THAN", count(t, near, 0, -2), 0, x=1, y=-2),
        t.math(
            "GREATER_THAN", count(t, state["Records"], 0, -3, component="POINTCLOUD"), 0, x=1, y=-3
        ),
        2,
        -2,
    )
    state["Records"] = switch(
        t,
        touching,
        state["Records"],
        pushed(t, state["Records"], state["Plates"], near, inputs, 4, 0),
        "GEOMETRY",
        40,
        0,
    )
    for name, value in state.items():
        t.connect(value, sim_out.inputs[name])
    # The pebbles of the frame
    t.connect(
        switch(
            t,
            boolean(t, "AND", broken, inputs["Debris"], 42, -6),
            None,
            thrown(t, new, hits, ground, inputs, 44, -8),
            "GEOMETRY",
            62,
            -6,
        ),
        sim_out.inputs["Debris"],
    )

    t.section("Output", row=True)
    records = sim_out.outputs["Records"]
    face = t.attribute(".cracks_face", "INT", 0, -2)
    used = proximity(t, sim_out.outputs["Taken"], keyed(t, face, 1, -2), 2, -2)
    rest = t.node(
        "GeometryNodeDeleteGeometry",
        5,
        0,
        {
            "Geometry": ground,
            "Selection": boolean(
                t,
                "AND",
                used["Is Valid"],
                t.math("LESS_THAN", used["Distance"], 0.5, x=3, y=-3),
                4,
                -2,
            ),
        },
        domain="FACE",
    ).outputs[0]
    rest = t.store(rest, ".cracks_inner", "FLOAT", 0.0, 6, 0, domain="FACE")
    # Pits under the broken plates, as deep as they are pushed
    plate = t.attribute(".cracks_plate", "INT", 0, -8)
    is_broken = t.math("GREATER_THAN", plate, -0.5, x=1, y=-8)
    depth = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY_ADD",
            inputs["Thickness"],
            PIT,
            sample(
                t, records, t.attribute(".cracks_down", "FLOAT", 0, -10), plate, "FLOAT", 1, -10
            ),
            x=2,
            y=-10,
        ),
        is_broken,
        x=3,
        y=-10,
    )
    deepest = t.node(
        "GeometryNodeFieldMinAndMax",
        5,
        -10,
        {
            "Value": depth,
            "Group ID": t.node(
                "GeometryNodeVertexOfCorner",
                4,
                -12,
                {"Corner Index": t.node("GeometryNodeInputIndex", 3, -12).outputs[0]},
            ).outputs["Vertex Index"],
        },
        data_type="FLOAT",
        domain="CORNER",
    ).outputs["Max"]
    deepest = t.node(
        "GeometryNodeFieldOnDomain", 6, -10, {"Value": deepest}, data_type="FLOAT", domain="POINT"
    ).outputs[0]
    pits = t.node(
        "GeometryNodeExtrudeMesh",
        8,
        -6,
        {
            "Mesh": sim_out.outputs["Patch"],
            "Selection": is_broken,
            "Offset": combine(t, 7, -10, Z=t.math("MULTIPLY", deepest, -1.0, x=6.5, y=-11)),
            "Individual": False,
        },
        mode="FACES",
    ).outputs
    pits = t.store(
        pits["Mesh"],
        ".cracks_inner",
        "FLOAT",
        boolean(t, "OR", pits["Top"], pits["Side"], 9, -8),
        10,
        -6,
        domain="FACE",
    )
    moved = t.node(
        "GeometryNodeSetPosition",
        22,
        -14,
        {"Geometry": sim_out.outputs["Plates"], "Position": posed(t, records, inputs, 8, -16)},
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 24, 0)
    for part in (moved, pits, rest):
        t.connect(part, joined.inputs[0])
    mesh = joined.outputs[0]
    # Pebbles, landing on the plates and in the pits
    debris_in = t.node("GeometryNodeSimulationInput", 26, -30)
    debris_out = t.node("GeometryNodeSimulationOutput", 52, -30)
    debris_in.pair_with_output(debris_out)
    debris_out.state_items[0].name = "Debris"
    debris = t.node("GeometryNodeJoinGeometry", 28, -30)
    t.connect(sim_out.outputs["Debris"], debris.inputs[0])
    t.connect(debris_in.outputs["Debris"], debris.inputs[0])
    bottom = t.math(
        "SUBTRACT",
        separate(
            t, t.node("GeometryNodeBoundBox", 26, -34, {"Geometry": ground}).outputs["Min"], 27, -34
        )["Z"],
        t.math("MULTIPLY", inputs["Size"], 10.0, x=27, y=-36),
        x=28,
        y=-34,
    )
    t.connect(
        fallen(
            t,
            debris.outputs[0],
            mesh,
            bottom,
            fall,
            t.math("MULTIPLY", debris_in.outputs["Delta Time"], started, x=27, y=-32),
            30,
            -30,
        ),
        debris_out.inputs["Debris"],
    )
    chips = switch(
        t,
        t.math(
            "GREATER_THAN",
            count(t, debris_out.outputs["Debris"], 53, -34, component="POINTCLOUD"),
            0,
            x=54,
            y=-34,
        ),
        None,
        pebbles(t, debris_out.outputs["Debris"], ground, inputs["Color"], 54, -30),
        "GEOMETRY",
        70,
        -30,
    )
    chips = t.node(
        "GeometryNodeTransform",
        71,
        -30,
        {"Geometry": chips, "Mode": "Matrix", "Transform": from_plane},
    ).outputs[0]
    inner = t.attribute(".cracks_inner", "FLOAT", 24, -2)
    mesh = t.node(
        "GeometryNodeSetShadeSmooth",
        26,
        0,
        {
            "Mesh": mesh,
            "Selection": t.math("GREATER_THAN", inner, 0.5, x=25, y=-2),
            "Shade Smooth": False,
        },
        domain="FACE",
    ).outputs[0]
    rgb = t.node("FunctionNodeSeparateColor", 25, -4, {0: inputs["Color"]}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        26,
        -4,
        {
            "Red": rgb["Red"],
            "Green": rgb["Green"],
            "Blue": rgb["Blue"],
            "Alpha": t.math("SUBTRACT", 1.0, inner, x=25, y=-6),
        },
    ).outputs[0]
    mesh = t.store(mesh, "cracks", "FLOAT_COLOR", color, 27, 0, domain="CORNER")
    mesh = t.node(
        "GeometryNodeRemoveAttribute",
        28,
        0,
        {"Geometry": mesh, "Pattern Mode": "Wildcard", "Name": ".cracks_*"},
    ).outputs[0]
    mesh = t.node(
        "GeometryNodeTransform",
        29,
        0,
        {"Geometry": mesh, "Mode": "Matrix", "Transform": from_plane},
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 30, 0)
    for name in ("Instances", "Volume", "Grease Pencil", "Point Cloud", "Curve"):
        t.connect(parts[name], joined.inputs[0])
    t.connect(chips, joined.inputs[0])
    t.connect(mesh, joined.inputs[0])
    t.node("NodeGroupOutput", 31, 0, {0: joined.outputs[0]})
    t.arrange()
    return ng


def build_tint():
    """The color mixed to the color inside the cracks, from the attribute of the modifier"""
    ng = bpy.data.node_groups.new(TINT, "ShaderNodeTree")
    add_input(ng, "Color", "NodeSocketColor", default_value=(0.8, 0.8, 0.8, 1.0))
    add_output(ng, "Color", "NodeSocketColor")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    cracks = t.node(
        "ShaderNodeAttribute", 0, -2, attribute_type="GEOMETRY", attribute_name="cracks"
    ).outputs
    tinted = t.node(
        "ShaderNodeMix",
        2,
        0,
        {
            "Factor": t.math("SUBTRACT", 1.0, cracks["Alpha"], x=1, y=-3, clamp=True),
            "A": inputs["Color"],
            "B": cracks["Color"],
        },
        data_type="RGBA",
    ).outputs
    t.node("NodeGroupOutput", 3, 0, {"Color": next(s for s in tinted if s.type == "RGBA")})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_tint()), fake_user=True)
