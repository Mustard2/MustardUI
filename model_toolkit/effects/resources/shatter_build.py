# Build shatter.blend: the Shatter node group
# Usage: Blender --background --factory-startup --python shatter_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write

RESOURCE = "shatter.blend"
NODE_GROUP = "MustardUI Shatter"
DUST = "MustardUI Shatter Dust"


def build_inputs(ng):
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects breaking the mesh when they hit it, and pushing the pieces",
    )
    add_input(
        ng,
        "Start Frame",
        "NodeSocketInt",
        default_value=1,
        description="Frame from which the mesh can break",
    )

    panel = ng.interface.new_panel("Pieces")
    add_input(
        ng,
        "Pieces",
        "NodeSocketInt",
        panel,
        default_value=40,
        min_value=1,
        max_value=1000,
        description="Pieces the mesh breaks into, smaller around the impact",
    )
    add_input(
        ng,
        "Spread",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.3,
        min_value=0.001,
        description="Distance from the impact of the cracks, larger pieces past it",
    )
    add_input(
        ng,
        "Break Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.3,
        min_value=0.0,
        description="Distance from the impact of the pieces coming loose, the others staying "
        "until a Collider hits them",
    )
    add_input(
        ng,
        "Floor Support",
        "NodeSocketBool",
        panel,
        description="The pieces of a still mesh touching the floor staying, the others only while "
        "held by them through staying pieces, as in a building",
    )
    add_input(ng, "Seed", "NodeSocketInt", panel, description="Random pattern of the cracks")

    panel = ng.interface.new_panel("Inner Faces", default_closed=True)
    add_input(
        ng,
        "Inner Faces",
        "NodeSocketBool",
        panel,
        description="Use the Material on the faces inside the pieces, else the one of the "
        "closest outer face",
    ).is_panel_toggle = True
    add_input(
        ng, "Material", "NodeSocketMaterial", panel, description="Material of the inner faces"
    )

    panel = ng.interface.new_panel("Impact")
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.0,
        description="Speed of the hit breaking the mesh, in m/s",
    )
    add_input(
        ng,
        "Push",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=2.0,
        description="Share of the speed of the Collider given to the loose pieces",
    )
    add_input(
        ng,
        "Scatter",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
        min_value=0.0,
        description="Speed of the loose pieces away from the impact, as a share of the speed of "
        "the hit, and their spin",
    )

    panel = ng.interface.new_panel("Physics")
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
        "Floor",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0,
        description="Height of the floor stopping the pieces, in world space",
    )
    add_input(
        ng,
        "Bounce",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Speed kept bouncing off the floor and the Colliders, by the small pieces",
    )
    add_input(
        ng,
        "Heavy Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.3,
        min_value=0.0,
        description="Radius of the pieces landing without bouncing, the smaller ones bouncing more",
    )
    add_input(
        ng,
        "Friction",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=2.0,
        description="Friction of the pieces sliding on the floor and the Colliders",
    )
    add_input(
        ng,
        "Drag",
        "NodeSocketFloat",
        panel,
        default_value=0.1,
        min_value=0.0,
        max_value=100.0,
        description="Air slowing the pieces, per second",
    )
    add_input(
        ng,
        "Margin",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.002,
        min_value=0.0,
        max_value=1.0,
        description="Distance kept from the Colliders",
    )
    add_input(
        ng,
        "Piece Collisions",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Pieces colliding with each other, slower with many pieces",
    )
    add_input(
        ng,
        "Substeps",
        "NodeSocketInt",
        panel,
        default_value=4,
        min_value=1,
        max_value=50,
        description="Simulation steps per frame",
    )
    add_input(
        ng,
        "Time Scale",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the simulation",
    )

    panel = ng.interface.new_panel("Breakup", default_closed=True)
    add_input(
        ng,
        "Breakup",
        "NodeSocketBool",
        panel,
        description="Large loose pieces breaking again when hit hard enough, of closed meshes",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Breakup Chance",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Chance of a piece hit by the floor or the Colliders faster than the Strength "
        "to break",
    )
    add_input(
        ng,
        "Breakup Pieces",
        "NodeSocketInt",
        panel,
        default_value=4,
        min_value=2,
        max_value=100,
        description="Pieces a piece breaks into",
    )
    add_input(
        ng,
        "Breakup Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.1,
        min_value=0.0,
        description="Radius under which the pieces do not break again",
    )

    panel = ng.interface.new_panel("Debris", default_closed=True)
    add_input(
        ng,
        "Debris",
        "NodeSocketBool",
        panel,
        description="Small chips thrown from the cuts of the loose pieces",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Debris Amount",
        "NodeSocketInt",
        panel,
        default_value=150,
        min_value=0,
        max_value=10000,
        description="Chips thrown by the pieces as they get loose, all of them once all the "
        "mesh is",
    )
    add_input(
        ng,
        "Debris Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.01,
        min_value=0.0,
        description="Size of the largest chips",
    )
    add_input(
        ng,
        "Debris Speed",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.6,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the chips thrown out of the cuts, as a share of the speed of the "
        "hit, the smaller ones faster",
    )
    add_input(
        ng,
        "Debris Rise",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=10.0,
        description="Upward throw of the chips",
    )

    panel = ng.interface.new_panel("Smoke", default_closed=True)
    add_input(
        ng,
        "Smoke",
        "NodeSocketBool",
        panel,
        description="Dust blown out of the impact, as a volume",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Smoke Amount",
        "NodeSocketInt",
        panel,
        default_value=100,
        min_value=0,
        max_value=10000,
        description="Puffs of dust out of the pieces as they get loose, all of them once all the "
        "mesh is",
    )
    add_input(
        ng,
        "Smoke Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.1,
        min_value=0.001,
        description="Size of the dust cloud, growing with its age",
    )
    add_input(
        ng,
        "Smoke Lifetime",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=3.0,
        min_value=0.0,
        description="Seconds the dust lasts, in average",
    )
    add_input(
        ng,
        "Smoke Rise",
        "NodeSocketFloat",
        panel,
        default_value=-0.1,
        description="Speed of the dust rising, in m/s, settling to the floor when negative",
    )
    add_input(
        ng,
        "Smoke Swirl",
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
        "Smoke Material",
        "NodeSocketMaterial",
        panel,
        description="Volume material of the dust",
    ).default_value = bpy.data.materials.get(DUST)


def sample(t, geometry, value, index, data_type, x, y, domain="POINT"):
    return t.node(
        "GeometryNodeSampleIndex",
        x,
        y,
        {"Geometry": geometry, "Value": value, "Index": index},
        data_type=data_type,
        domain=domain,
    ).outputs[0]


def nearest(t, mesh, value, data_type, at, x, y):
    """Value at the closest point of the mesh surface, and whether there is one"""
    return t.node(
        "GeometryNodeSampleNearestSurface",
        x,
        y,
        {"Mesh": mesh, "Value": value, "Sample Position": at},
        data_type=data_type,
    ).outputs


def statistic(t, geometry, value, selection, data_type, x, y, domain="POINT"):
    return t.node(
        "GeometryNodeAttributeStatistic",
        x,
        y,
        {"Geometry": geometry, "Selection": selection, "Attribute": value},
        data_type=data_type,
        domain=domain,
    ).outputs


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
    return t.store(geometry, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 4, y)


def crop(t, mesh, low, high, speed, dt, margin, x, y):
    """Faces of the mesh with points that can reach the box in the frame, moving at their speed
    plus the given one"""
    position = t.node("GeometryNodeInputPosition", x, y - 1).outputs[0]
    moving = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x, y - 2)
    inside = t.vmath(
        "MAXIMUM", t.vmath("MINIMUM", position, high, x=x + 1, y=y - 1), low, x=x + 2, y=y - 1
    )
    reach = t.math("ADD", t.vmath("LENGTH", moving, x=x + 1, y=y - 2), speed, x=x + 2, y=y - 2)
    reach = t.math("MULTIPLY_ADD", reach, dt, margin, x=x + 3, y=y - 2)
    near = t.math(
        "LESS_THAN",
        t.vmath("DISTANCE", position, inside, x=x + 3, y=y - 1),
        reach,
        x=x + 4,
        y=y - 1,
    )
    # As a float, for the faces with any point near
    mesh = t.store(mesh, ".shatter_near", "FLOAT", near, x + 4, y)
    far = t.math(
        "LESS_THAN", t.attribute(".shatter_near", "FLOAT", x + 4, y - 3), 1e-6, x=x + 5, y=y - 3
    )
    return t.node(
        "GeometryNodeDeleteGeometry", x + 6, y, {"Geometry": mesh, "Selection": far}, domain="FACE"
    ).outputs[0]


def contact(t, surface, margin, dt, x, y):
    """Whether the points touch the surface or passed through it in the last frame, and their
    velocity relative to it"""
    position = t.node("GeometryNodeInputPosition", x, y - 1).outputs[0]
    normal = t.node("GeometryNodeInputNormal", x, y - 2).outputs[0]
    moving = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x, y - 3)
    closest = nearest(t, surface, position, "FLOAT_VECTOR", position, x + 1, y - 1)
    side = nearest(t, surface, normal, "FLOAT_VECTOR", position, x + 1, y - 2)[0]
    relative = t.vmath(
        "SUBTRACT",
        moving,
        nearest(t, surface, moving, "FLOAT_VECTOR", position, x + 1, y - 3)[0],
        x=x + 2,
        y=y - 3,
    )
    offset = t.vmath("SUBTRACT", position, closest[0], x=x + 2, y=y - 1)
    distance = t.vmath("LENGTH", offset, x=x + 3, y=y - 4)
    signed = t.vmath("DOT_PRODUCT", offset, side, x=x + 3, y=y - 1)
    travel = t.vmath("SCALE", relative, dt, x=x + 3, y=y - 3)
    before = t.math(
        "SUBTRACT",
        signed,
        t.vmath("DOT_PRODUCT", travel, side, x=x + 4, y=y - 3),
        x=x + 5,
        y=y - 2,
    )
    # Changed side, close enough to have gone through
    crossed = t.math(
        "MULTIPLY",
        t.math(
            "LESS_THAN", t.math("MULTIPLY", signed, before, x=x + 6, y=y - 2), 0.0, x=x + 7, y=y - 2
        ),
        t.math(
            "LESS_THAN",
            distance,
            t.math("ADD", t.vmath("LENGTH", travel, x=x + 4, y=y - 5), margin, x=x + 5, y=y - 5),
            x=x + 6,
            y=y - 4,
        ),
        x=x + 8,
        y=y - 3,
    )
    touching = t.math("LESS_THAN", distance, margin, x=x + 6, y=y - 6)
    touched = t.math(
        "MULTIPLY",
        t.math("MAXIMUM", touching, crossed, x=x + 9, y=y - 3),
        closest[1],
        x=x + 10,
        y=y - 3,
    )
    return touched, relative


def detect(t, mesh, colliders, inputs, dt, x, y):
    """Whether points of the mesh and of the Colliders hit each other fast enough, or the mesh hit
    the floor, the mean of these points and the mean velocity of the Colliders there"""
    position = t.node("GeometryNodeInputPosition", x + 12, y - 3).outputs[0]
    hits = t.node("GeometryNodeJoinGeometry", x + 13, y)
    for i, (points, surface) in enumerate(((mesh, colliders), (colliders, mesh))):
        yy = y - i * 8
        touched, relative = contact(t, surface, inputs["Margin"], dt, x, yy)
        speed = t.vmath("LENGTH", relative, x=x + 9, y=yy - 5)
        fast = t.math("GREATER_THAN", speed, inputs["Strength"], x=x + 10, y=yy - 5)
        hit = t.math("MULTIPLY", touched, fast, x=x + 11, y=yy - 4)
        stored = t.store(points, ".shatter_hit", "FLOAT", hit, x + 11, yy)
        # Velocity of the Colliders relative to the mesh
        push = t.vmath("SCALE", relative, 1.0 - 2.0 * (i == 0), x=x + 11, y=yy - 6)
        stored = t.store(stored, ".shatter_push", "FLOAT_VECTOR", push, x + 12, yy)
        t.connect(stored, hits.inputs[0])

    moving = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x, y - 17)
    height = socket(t.node("ShaderNodeSeparateXYZ", x + 1, y - 16, {0: position}).outputs, "Z")
    below = t.math(
        "LESS_THAN",
        height,
        t.math("ADD", inputs["Floor"], inputs["Margin"], x=x + 1, y=y - 18),
        x=x + 2,
        y=y - 16,
    )
    fast = t.math(
        "GREATER_THAN",
        t.vmath("LENGTH", moving, x=x + 1, y=y - 17),
        inputs["Strength"],
        x=x + 2,
        y=y - 17,
    )
    hit = t.math("MULTIPLY", below, fast, x=x + 3, y=y - 16)
    floor = t.store(mesh, ".shatter_hit", "FLOAT", hit, x + 11, y - 16)
    # The floor pushing back
    floor = t.store(
        floor,
        ".shatter_push",
        "FLOAT_VECTOR",
        t.vmath("SCALE", moving, -1.0, x=x + 11, y=y - 17),
        x + 12,
        y - 16,
    )
    t.connect(floor, hits.inputs[0])

    hits = hits.outputs[0]
    hit = t.attribute(".shatter_hit", "FLOAT", x + 13, y - 2)
    selection = t.math("GREATER_THAN", hit, 0.5, x=x + 14, y=y - 2)
    push = t.attribute(".shatter_push", "FLOAT_VECTOR", x + 14, y - 4)
    impact = statistic(t, hits, position, selection, "FLOAT_VECTOR", x + 15, y)["Mean"]
    push = statistic(t, hits, push, selection, "FLOAT_VECTOR", x + 15, y - 3)["Mean"]
    count = statistic(t, hits, hit, True, "FLOAT", x + 15, y - 6)["Sum"]
    return t.math("GREATER_THAN", count, 0.5, x=x + 16, y=y - 6), impact, push


def is_closed(t, mesh, x, y):
    """Whether all the edges of the mesh have two faces"""
    faces = t.node("GeometryNodeInputMeshEdgeNeighbors", x, y).outputs["Face Count"]
    faces = statistic(t, mesh, faces, True, "FLOAT", x + 1, y, "EDGE")
    return t.node(
        "FunctionNodeBooleanMath",
        x + 2,
        y,
        {
            0: t.math("COMPARE", faces["Min"], 2.0, 0.1, x=x + 2, y=y - 1),
            1: t.math("COMPARE", faces["Max"], 2.0, 0.1, x=x + 2, y=y - 2),
        },
        operation="AND",
    ).outputs[0]


def fracture(t, mesh, impact, inputs, x, y, count=None, spread=None, seed=None):
    """Zone splitting the mesh in the Voronoi cells of seeds around the impact, the pieces as
    instances around their centers, by default as many as the Pieces over the Spread"""
    count = inputs["Pieces"] if count is None else count
    spread = inputs["Spread"] if spread is None else spread
    seed = inputs["Seed"] if seed is None else seed
    index = t.node("GeometryNodeInputIndex", x, y - 3).outputs[0]
    position = t.node("GeometryNodeInputPosition", x, y - 4).outputs[0]
    bounds = t.node("GeometryNodeBoundBox", x, y - 2, {"Geometry": mesh})
    low, high = bounds.outputs["Min"], bounds.outputs["Max"]
    size = t.vmath("LENGTH", t.vmath("SUBTRACT", high, low, x=x, y=y - 6), x=x + 1, y=y - 6)
    margin = t.math("MULTIPLY_ADD", size, 0.05, 0.001, x=x + 2, y=y - 6)

    closed = is_closed(t, mesh, x, y - 8)

    # Seeds denser at the impact
    direction = t.node(
        "FunctionNodeRandomValue",
        x + 1,
        y - 2,
        {"Min": (-1, -1, -1), "Max": (1, 1, 1), "Seed": seed},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    distance = t.node(
        "FunctionNodeRandomValue",
        x + 1,
        y - 3,
        {"Seed": t.math("ADD", seed, 1, x=x, y=y - 5)},
        data_type="FLOAT",
    ).outputs
    distance = t.math(
        "MULTIPLY",
        t.math("POWER", socket(distance, "Value"), 2.0, x=x + 2, y=y - 3),
        spread,
        x=x + 3,
        y=y - 3,
    )
    direction = t.vmath("NORMALIZE", direction, x=x + 2, y=y - 2)
    point = t.vmath("MULTIPLY_ADD", direction, distance, impact, x=x + 4, y=y - 2)
    # On the surface, for each cell to cut some of the mesh, also of hollow ones
    point = nearest(t, mesh, position, "FLOAT_VECTOR", point, x + 5, y - 2)[0]
    seeds = t.node("GeometryNodePoints", x + 7, y, {"Count": count, "Position": point}).outputs[0]
    # Not too close, the cells of close seeds failing
    spacing = t.math("MULTIPLY", size, 0.01, x=x + 7, y=y - 6)
    seeds = t.node(
        "GeometryNodeMergeByDistance", x + 8, y, {"Geometry": seeds, "Distance": spacing}
    ).outputs[0]

    # Each cell as the half spaces closer to its seed than to the others and to its mirrors through
    # the faces of the box: the dual of the convex hull of the points 2 (p - s) / |p - s|^2
    each_in = t.node("GeometryNodeForeachGeometryElementInput", x + 9, y, {"Geometry": seeds})
    each_out = t.node("GeometryNodeForeachGeometryElementOutput", x + 26, y, domain="POINT")
    each_in.pair_with_output(each_out)
    each_out.main_items.new("VECTOR", "Center")
    each_out.main_items.new("INT", "Faces")
    each_out.main_items.new("FLOAT", "Inertia")
    s = sample(t, each_in.outputs["Element"], position, 0, "FLOAT_VECTOR", x + 10, y - 1)
    axis = t.math("FLOORED_MODULO", index, 3, x=x + 10, y=y - 4)
    unit = t.node(
        "ShaderNodeCombineXYZ",
        x + 11,
        y - 4,
        {i: t.math("COMPARE", axis, i, 0.1, x=x + 10.5, y=y - 5 - i) for i in range(3)},
    ).outputs[0]
    face = switch(
        t,
        t.math("LESS_THAN", index, 3, x=x + 10.5, y=y - 3),
        t.vmath("SUBTRACT", low, margin, x=x + 10, y=y - 3),
        t.vmath("ADD", high, margin, x=x + 10, y=y - 2),
        "VECTOR",
        x + 11,
        y - 3,
    )
    mirror = t.vmath(
        "MULTIPLY_ADD",
        t.vmath("SUBTRACT", face, s, x=x + 12, y=y - 3),
        t.vmath("SCALE", unit, 2.0, x=x + 12, y=y - 4),
        s,
        x=x + 13,
        y=y - 3,
    )
    mirrors = t.node("GeometryNodePoints", x + 14, y - 2, {"Count": 6, "Position": mirror}).outputs[
        0
    ]
    others = t.node("GeometryNodeJoinGeometry", x + 15, y)
    t.connect(mirrors, others.inputs[0])
    t.connect(seeds, others.inputs[0])
    offset = t.vmath("SUBTRACT", position, s, x=x + 15, y=y - 2)
    squared = t.vmath("DOT_PRODUCT", offset, offset, x=x + 16, y=y - 2)
    others = t.node(
        "GeometryNodeDeleteGeometry",
        x + 16,
        y,
        {
            "Geometry": others.outputs[0],
            "Selection": t.math("LESS_THAN", squared, 1e-10, x=x + 16, y=y - 3),
        },
    ).outputs[0]
    dual = t.vmath(
        "SCALE", offset, t.math("DIVIDE", 2.0, squared, x=x + 17, y=y - 2), x=x + 17, y=y - 3
    )
    dual = t.node(
        "GeometryNodeSetPosition", x + 17, y, {"Geometry": others, "Position": dual}
    ).outputs[0]
    hull = t.node("GeometryNodeConvexHull", x + 18, y, {"Geometry": dual}).outputs[0]
    # Each face n.p = d of the hull is the vertex n / d of the cell
    normal = t.node("GeometryNodeInputNormal", x + 18, y - 2).outputs[0]
    plane = t.vmath("DOT_PRODUCT", normal, position, x=x + 18, y=y - 3)
    vertex = t.vmath(
        "SCALE", normal, t.math("DIVIDE", 1.0, plane, x=x + 19, y=y - 3), x=x + 19, y=y - 2
    )
    hull = t.store(hull, ".shatter_vertex", "FLOAT_VECTOR", vertex, x + 19, y, domain="FACE")
    cell = t.node("GeometryNodeDualMesh", x + 20, y, {"Mesh": hull}).outputs[0]
    vertex = t.vmath(
        "ADD",
        t.attribute(".shatter_vertex", "FLOAT_VECTOR", x + 20, y - 2),
        s,
        x=x + 21,
        y=y - 2,
    )
    cell = t.node(
        "GeometryNodeSetPosition", x + 21, y, {"Geometry": cell, "Position": vertex}
    ).outputs[0]
    # The vertices of the triangles of a hull face in the same place
    cell = t.node(
        "GeometryNodeMergeByDistance",
        x + 22,
        y,
        {"Geometry": cell, "Mode": "Connected", "Distance": 1e-6},
    ).outputs[0]
    cell = t.store(cell, ".shatter_inner", "BOOLEAN", True, x + 22.5, y, domain="FACE")

    def intersect(solver, xx, yy):
        boolean = t.node(
            "GeometryNodeMeshBoolean",
            xx,
            yy,
            {"Hole Tolerant": True},
            operation="INTERSECT",
            solver=solver,
        )
        # The last linked first, for the materials of the mesh to keep their indices
        t.connect(cell, boolean.inputs["Mesh 2"])
        t.connect(mesh, boolean.inputs["Mesh 2"])
        return boolean.outputs["Mesh"]

    # Manifold for closed meshes, else Exact, Float where it fails on cells cutting the mesh
    exact = intersect("EXACT", x + 23, y - 1)
    failed = t.node(
        "GeometryNodeAttributeDomainSize", x + 23, y - 2, {"Geometry": exact}, component="MESH"
    ).outputs["Face Count"]
    failed = t.math("LESS_THAN", failed, 1, x=x + 23.5, y=y - 2)
    piece = switch(t, failed, exact, intersect("FLOAT", x + 23, y - 3), "GEOMETRY", x + 23.7, y - 1)
    piece = switch(t, closed, piece, intersect("MANIFOLD", x + 23, y), "GEOMETRY", x + 23.9, y)

    # Inner faces flat, with the material of the closest outer face or the inner one
    inner = t.attribute(".shatter_inner", "BOOLEAN", x + 23, y - 2)
    material = t.node("GeometryNodeInputMaterialIndex", x + 23, y - 3).outputs[0]
    material = nearest(t, mesh, material, "INT", position, x + 23.5, y - 3)[0]
    piece = t.node(
        "GeometryNodeSetMaterialIndex",
        x + 24,
        y,
        {"Geometry": piece, "Selection": inner, "Material Index": material},
    ).outputs[0]
    selection = t.node(
        "FunctionNodeBooleanMath",
        x + 24,
        y - 4,
        {0: inner, 1: inputs["Inner Faces"]},
        operation="AND",
    ).outputs[0]
    piece = t.node(
        "GeometryNodeSetMaterial",
        x + 24.3,
        y,
        {"Geometry": piece, "Selection": selection, "Material": inputs["Material"]},
    ).outputs[0]
    piece = t.node(
        "GeometryNodeSetShadeSmooth",
        x + 24.6,
        y,
        {"Mesh": piece, "Selection": inner, "Shade Smooth": False},
    ).outputs[0]
    # Center of mass and radius of gyration squared of the surface, by the area of the faces
    area = t.node("GeometryNodeInputMeshFaceArea", x + 24, y - 6).outputs[0]
    total = statistic(t, piece, area, True, "FLOAT", x + 24.6, y - 6, "FACE")["Sum"]
    center = t.vmath("SCALE", position, area, x=x + 24.3, y=y - 2)
    center = statistic(t, piece, center, True, "FLOAT_VECTOR", x + 24.6, y - 2, "FACE")["Sum"]
    center = t.vmath("DIVIDE", center, total, x=x + 25, y=y - 2)
    arm = t.vmath("SUBTRACT", position, center, x=x + 25, y=y - 7)
    inertia = t.math(
        "MULTIPLY", t.vmath("DOT_PRODUCT", arm, arm, x=x + 25.3, y=y - 7), area, x=x + 25.6, y=y - 7
    )
    inertia = statistic(t, piece, inertia, True, "FLOAT", x + 26, y - 7, "FACE")["Sum"]
    inertia = t.math(
        "DIVIDE", t.math("MULTIPLY", inertia, 0.5, x=x + 26.3, y=y - 7), total, x=x + 26.6, y=y - 7
    )
    piece = t.node(
        "GeometryNodeTransform",
        x + 25,
        y,
        {"Geometry": piece, "Translation": t.vmath("SCALE", center, -1.0, x=x + 25, y=y - 3)},
    ).outputs[0]
    faces = t.node(
        "GeometryNodeAttributeDomainSize", x + 25, y - 4, {"Geometry": piece}, component="MESH"
    ).outputs["Face Count"]
    piece = t.node("GeometryNodeGeometryToInstance", x + 25.5, y, {"Geometry": piece}).outputs[0]
    t.connect(piece, each_out.inputs["Geometry"])
    t.connect(center, each_out.inputs["Center"])
    t.connect(faces, each_out.inputs["Faces"])
    t.connect(inertia, each_out.inputs["Inertia"])
    return each_out


def cells(t, each, x, y):
    """Pieces of the fracture zone and their points at their centers, without the cells out of
    the mesh"""
    index = t.node("GeometryNodeInputIndex", x, y - 3).outputs[0]
    empty = t.math("LESS_THAN", each.outputs["Faces"], 1, x=x, y=y - 2)
    bodies = t.node(
        "GeometryNodeDeleteGeometry",
        x + 1,
        y,
        {"Geometry": each.outputs["Geometry"], "Selection": empty},
    ).outputs[0]
    faces = sample(t, each.outputs["Geometry"], each.outputs["Faces"], index, "INT", x, y + 2)
    pieces = t.node(
        "GeometryNodeDeleteGeometry",
        x + 1,
        y + 2,
        {
            "Geometry": each.outputs["Generation_0"],
            "Selection": t.math("LESS_THAN", faces, 1, x=x + 1, y=y + 3),
        },
        domain="INSTANCE",
    ).outputs[0]
    bodies = t.node(
        "GeometryNodeSetPosition",
        x + 2,
        y,
        {"Geometry": bodies, "Position": each.outputs["Center"]},
    ).outputs[0]
    inertia = t.math("MAXIMUM", each.outputs["Inertia"], 1e-8, x=x + 2, y=y - 2)
    return pieces, t.store(bodies, ".shatter_inertia", "FLOAT", inertia, x + 3, y)


def hulls(t, pieces, bodies, x, y):
    """Convex hull points and face planes of each piece, around its center, for the collisions,
    with their first index and count, and the radius of the piece, on the points of the pieces"""
    index = t.node("GeometryNodeInputIndex", x, y - 3).outputs[0]
    hull_in = t.node("GeometryNodeForeachGeometryElementInput", x + 2, y + 2, {"Geometry": pieces})
    hull_out = t.node("GeometryNodeForeachGeometryElementOutput", x + 5, y + 2, domain="INSTANCE")
    hull_in.pair_with_output(hull_out)
    hull_out.main_items.new("INT", "Count")
    hull_out.main_items.new("FLOAT", "Radius")
    hull_out.main_items.new("INT", "Plane Count")
    hull_out.generation_items.new("GEOMETRY", "Planes")
    hull = t.node(
        "GeometryNodeRealizeInstances", x + 2.5, y + 2, {"Geometry": hull_in.outputs["Element"]}
    ).outputs[0]
    hull = t.node("GeometryNodeConvexHull", x + 3, y + 2, {"Geometry": hull}).outputs[0]
    # The planes of the faces, the coplanar triangles as one
    normal = t.node("GeometryNodeInputNormal", x + 3, y + 7).outputs[0]
    offset = t.vmath(
        "DOT_PRODUCT",
        normal,
        t.node("GeometryNodeInputPosition", x + 3, y + 8).outputs[0],
        x=x + 3.5,
        y=y + 8,
    )
    planes = t.store(hull, ".shatter_offset", "FLOAT", offset, x + 3.5, y + 6, domain="FACE")
    planes = t.store(
        planes, ".shatter_plane", "FLOAT_VECTOR", normal, x + 3.7, y + 6, domain="FACE"
    )
    planes = t.node(
        "GeometryNodeMeshToPoints", x + 3.9, y + 6, {"Mesh": planes}, mode="FACES"
    ).outputs[0]
    planes = t.node(
        "GeometryNodeSetPosition",
        x + 4.1,
        y + 6,
        {
            "Geometry": planes,
            "Position": t.attribute(".shatter_plane", "FLOAT_VECTOR", x + 3.9, y + 7),
        },
    ).outputs[0]
    planes = t.node(
        "GeometryNodeMergeByDistance", x + 4.3, y + 6, {"Geometry": planes, "Distance": 1e-4}
    ).outputs[0]
    t.connect(planes, hull_out.inputs["Planes"])
    t.connect(
        t.node(
            "GeometryNodeAttributeDomainSize",
            x + 4.5,
            y + 7,
            {"Geometry": planes},
            component="POINTCLOUD",
        ).outputs["Point Count"],
        hull_out.inputs["Plane Count"],
    )
    hull = t.node("GeometryNodeMeshToPoints", x + 3.5, y + 2, {"Mesh": hull}).outputs[0]
    radius = t.vmath(
        "LENGTH", t.node("GeometryNodeInputPosition", x + 3, y + 5).outputs[0], x=x + 3.5, y=y + 5
    )
    radius = statistic(t, hull, radius, True, "FLOAT", x + 4, y + 5)["Max"]
    hull = t.store(hull, ".shatter_piece", "INT", hull_in.outputs["Index"], x + 4.5, y + 2)
    t.connect(hull, hull_out.inputs["Geometry"])
    count = t.node(
        "GeometryNodeAttributeDomainSize",
        x + 4.5,
        y + 4,
        {"Geometry": hull},
        component="POINTCLOUD",
    ).outputs["Point Count"]
    t.connect(count, hull_out.inputs["Count"])
    t.connect(radius, hull_out.inputs["Radius"])
    hull = hull_out.outputs["Generation_0"]
    planes = hull_out.outputs["Planes"]
    count = sample(
        t,
        hull_out.outputs["Geometry"],
        hull_out.outputs["Count"],
        index,
        "INT",
        x + 5,
        y - 2,
        "INSTANCE",
    )
    first = t.node(
        "GeometryNodeAccumulateField", x + 6, y - 2, {"Value": count}, data_type="INT"
    ).outputs["Trailing"]
    bodies = t.store(bodies, ".shatter_first", "INT", first, x + 6, y)
    bodies = t.store(bodies, ".shatter_count", "INT", count, x + 6.3, y)
    count = sample(
        t,
        hull_out.outputs["Geometry"],
        hull_out.outputs["Plane Count"],
        index,
        "INT",
        x + 5,
        y - 4,
        "INSTANCE",
    )
    first = t.node(
        "GeometryNodeAccumulateField", x + 6, y - 4, {"Value": count}, data_type="INT"
    ).outputs["Trailing"]
    bodies = t.store(bodies, ".shatter_plane_first", "INT", first, x + 6.6, y)
    bodies = t.store(bodies, ".shatter_plane_count", "INT", count, x + 6.9, y)
    radius = sample(
        t,
        hull_out.outputs["Geometry"],
        hull_out.outputs["Radius"],
        index,
        "FLOAT",
        x + 6,
        y - 3,
        "INSTANCE",
    )
    return t.store(bodies, ".shatter_radius", "FLOAT", radius, x + 7, y), hull, planes


def bodies_of(t, each, mesh, impact, push, inputs, x, y):
    """Pieces and their hull points, and the points of the pieces, with their state"""
    position = t.node("GeometryNodeInputPosition", x, y - 4).outputs[0]
    pieces, bodies = cells(t, each, x, y)
    bodies, hull, planes = hulls(t, pieces, bodies, x + 4, y)
    x += 3
    radius = t.attribute(".shatter_radius", "FLOAT", x + 11, y - 13)

    # Loose around the impact, with the velocity of the mesh, the push of the Colliders and a
    # scatter away from the impact, fading with the distance
    falloff = t.math(
        "DIVIDE",
        t.vmath("DISTANCE", position, impact, x=x + 7, y=y - 5),
        t.math("MAXIMUM", inputs["Break Radius"], 1e-6, x=x + 7, y=y - 6),
        x=x + 8,
        y=y - 5,
    )
    loose = t.math("LESS_THAN", falloff, 1.0, x=x + 9, y=y - 5)
    # All of a moving mesh, only a still one holding its pieces
    carried = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 7, y - 15)
    carried = nearest(t, mesh, carried, "FLOAT_VECTOR", position, x + 8, y - 15)[0]
    moving_mesh = t.math(
        "GREATER_THAN",
        t.vmath("LENGTH", carried, x=x + 9, y=y - 15),
        STILL_SPEED,
        x=x + 10,
        y=y - 15,
    )
    loose = t.math("MAXIMUM", loose, moving_mesh, x=x + 10, y=y - 5)
    fade = t.math("SUBTRACT", 1.0, falloff, x=x + 9, y=y - 6, clamp=True)
    speed = t.math(
        "MULTIPLY", t.vmath("LENGTH", push, x=x + 9, y=y - 7), inputs["Scatter"], x=x + 10, y=y - 7
    )
    random = t.node(
        "FunctionNodeRandomValue",
        x + 8,
        y - 8,
        {"Min": (-1, -1, -1), "Max": (1, 1, 1), "Seed": inputs["Seed"]},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    away = t.vmath(
        "NORMALIZE", t.vmath("SUBTRACT", position, impact, x=x + 8, y=y - 10), x=x + 9, y=y - 10
    )
    away = t.vmath("NORMALIZE", t.vmath("ADD", away, random, x=x + 10, y=y - 9), x=x + 11, y=y - 9)
    added = t.vmath(
        "ADD",
        t.vmath("SCALE", push, inputs["Push"], x=x + 11, y=y - 7),
        t.vmath("SCALE", away, speed, x=x + 12, y=y - 9),
        x=x + 12,
        y=y - 8,
    )
    added = t.vmath("SCALE", added, fade, x=x + 13, y=y - 8)
    moving = t.vmath("ADD", carried, added, x=x + 14, y=y - 8)
    bodies = t.store(bodies, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 14, y)
    # Spinning with the scatter speed at their radius, not too fast for the tiny pieces
    radius = t.math("MAXIMUM", radius, 0.05, x=x + 12, y=y - 12)
    spin = t.math(
        "DIVIDE", t.math("MULTIPLY", speed, fade, x=x + 12, y=y - 13), radius, x=x + 13, y=y - 12
    )
    spin = t.vmath("SCALE", random, spin, x=x + 14, y=y - 12)
    bodies = t.store(bodies, ".shatter_spin", "FLOAT_VECTOR", spin, x + 14.5, y)
    bodies = t.store(bodies, ".shatter_loose", "FLOAT", loose, x + 15, y)
    bodies = t.store(bodies, ".shatter_rotation", "QUATERNION", None, x + 16, y)
    # Breaking up only solid pieces, the cuts of open ones adding faces
    solid = is_closed(t, mesh, x + 15, y - 14)
    bodies = t.store(bodies, ".shatter_solid", "FLOAT", solid, x + 17, y)
    return pieces, bodies, hull, planes


def anchored(t, bodies, hull, mesh, inputs, x, y):
    """Bodies with the pieces of a still mesh touching the floor anchored by the Floor Support,
    not loose"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    piece = t.attribute(".shatter_piece", "INT", x, y - 3)
    height = socket(
        t.node(
            "ShaderNodeSeparateXYZ",
            x + 2,
            y - 2,
            {
                0: t.vmath(
                    "ADD",
                    position,
                    sample(t, bodies, position, piece, "FLOAT_VECTOR", x + 1, y - 3),
                    x=x + 1,
                    y=y - 2,
                )
            },
        ).outputs,
        "Z",
    )
    lowest = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 3,
        y - 2,
        {"Value": height, "Group ID": piece},
        data_type="FLOAT",
    ).outputs["Min"]
    first = t.attribute(".shatter_first", "INT", x + 3, y - 4)
    lowest = sample(t, hull, lowest, first, "FLOAT", x + 4, y - 2)
    floor = t.math("MULTIPLY_ADD", inputs["Margin"], 2.0, inputs["Floor"], x=x + 4, y=y - 4)
    grounded = t.math(
        "LESS_THAN", lowest, t.math("ADD", floor, 0.001, x=x + 5, y=y - 4), x=x + 6, y=y - 2
    )
    carried = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 4, y - 6)
    carried = nearest(t, mesh, carried, "FLOAT_VECTOR", position, x + 5, y - 6)[0]
    still = t.math(
        "LESS_THAN", t.vmath("LENGTH", carried, x=x + 6, y=y - 6), STILL_SPEED, x=x + 7, y=y - 6
    )
    held = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", grounded, still, x=x + 7, y=y - 3),
        inputs["Floor Support"],
        x=x + 8,
        y=y - 3,
    )
    bodies = t.store(bodies, ".shatter_anchored", "FLOAT", held, x + 8, y)
    loose = t.math(
        "MULTIPLY",
        t.attribute(".shatter_loose", "FLOAT", x + 8, y - 5),
        t.math("SUBTRACT", 1.0, held, x=x + 9, y=y - 4),
        x=x + 10,
        y=y - 4,
    )
    return t.store(bodies, ".shatter_loose", "FLOAT", loose, x + 10, y)


def breakup(t, bodies, pieces, inputs, x, y):
    """Bodies and pieces with the large loose pieces hit hard enough in the frame broken once,
    by the Breakup Chance, around their lowest point, the hulls of all the pieces, and whether
    any broke"""
    index = t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]
    position = t.node("GeometryNodeInputPosition", x, y - 3).outputs[0]
    frame = t.node("GeometryNodeInputSceneTime", x, y - 4).outputs["Frame"]
    chance = t.node(
        "FunctionNodeRandomValue",
        x + 1,
        y - 5,
        {"Seed": t.math("ADD", inputs["Seed"], frame, x=x, y=y - 5)},
        data_type="FLOAT",
    ).outputs
    conditions = (
        t.math("LESS_THAN", socket(chance, "Value"), inputs["Breakup Chance"], x=x + 2, y=y - 5),
        t.math(
            "GREATER_THAN",
            t.attribute(".shatter_radius", "FLOAT", x + 1, y - 6),
            inputs["Breakup Size"],
            x=x + 2,
            y=y - 6,
        ),
        t.math(
            "GREATER_THAN",
            t.attribute(".shatter_impact", "FLOAT", x + 1, y - 7),
            inputs["Strength"],
            x=x + 2,
            y=y - 7,
        ),
        t.attribute(".shatter_loose", "FLOAT", x + 1, y - 8),
        t.attribute(".shatter_solid", "FLOAT", x + 1, y - 10),
        # Once, the new pieces would keep breaking in the same hit
        t.math(
            "SUBTRACT", 1.0, t.attribute(".shatter_parted", "FLOAT", x + 1, y - 9), x=x + 2, y=y - 9
        ),
    )
    breaking = conditions[0]
    for i, condition in enumerate(conditions[1:]):
        breaking = t.math("MULTIPLY", breaking, condition, x=x + 3 + i * 0.3, y=y - 5)
    breaking = t.math("GREATER_THAN", breaking, 0.5, x=x + 4, y=y - 5)
    bodies = t.store(bodies, ".shatter_breaking", "BOOLEAN", breaking, x + 4, y)
    breaking = t.attribute(".shatter_breaking", "BOOLEAN", x + 4, y - 7)
    any_breaking = statistic(
        t,
        bodies,
        t.attribute(".shatter_breaking", "FLOAT", x + 4, y - 9),
        True,
        "FLOAT",
        x + 5,
        y - 9,
    )["Max"]
    any_breaking = t.math("GREATER_THAN", any_breaking, 0.5, x=x + 6, y=y - 9)

    # Each breaking piece where it is, cut around its lowest point
    each_in = t.node(
        "GeometryNodeForeachGeometryElementInput",
        x + 5,
        y,
        {"Geometry": bodies, "Selection": breaking},
    )
    each_out = t.node("GeometryNodeForeachGeometryElementOutput", x + 30, y, domain="POINT")
    each_in.pair_with_output(each_out)
    each_out.generation_items.new("GEOMETRY", "Pieces")
    element = each_in.outputs["Element"]

    def of(name, data_type, yy):
        value = position if name is None else t.attribute(name, data_type, x + 6, y - yy)
        return sample(t, element, value, 0, data_type, x + 7, y - yy)

    center = of(None, "FLOAT_VECTOR", 2)
    rotation = of(".shatter_rotation", "QUATERNION", 3)
    moving = of(".shatter_velocity", "FLOAT_VECTOR", 4)
    spin = of(".shatter_spin", "FLOAT_VECTOR", 5)
    piece = t.node(
        "GeometryNodeDeleteGeometry",
        x + 7,
        y,
        {
            "Geometry": pieces,
            "Selection": t.node(
                "FunctionNodeCompare",
                x + 6,
                y - 7,
                {"A": index, "B": each_in.outputs["Index"]},
                data_type="INT",
                operation="NOT_EQUAL",
            ).outputs[0],
        },
        domain="INSTANCE",
    ).outputs[0]
    piece = t.node("GeometryNodeRealizeInstances", x + 8, y, {"Geometry": piece}).outputs[0]
    piece = t.node(
        "GeometryNodeTransform",
        x + 9,
        y,
        {"Geometry": piece, "Translation": center, "Rotation": rotation},
    ).outputs[0]
    lowest = statistic(
        t,
        piece,
        socket(t.node("ShaderNodeSeparateXYZ", x + 8, y - 9, {0: position}).outputs, "Z"),
        True,
        "FLOAT",
        x + 9,
        y - 9,
    )["Min"]
    xyz = t.node("ShaderNodeSeparateXYZ", x + 9, y - 11, {0: center}).outputs
    impact = t.node(
        "ShaderNodeCombineXYZ",
        x + 10,
        y - 10,
        {0: socket(xyz, "X"), 1: socket(xyz, "Y"), 2: lowest},
    ).outputs[0]
    seed = t.math(
        "MULTIPLY_ADD",
        each_in.outputs["Index"],
        13,
        t.math("ADD", inputs["Seed"], frame, x=x + 9, y=y - 13),
        x=x + 10,
        y=y - 12,
    )
    zone = fracture(
        t,
        piece,
        impact,
        inputs,
        x + 11,
        y - 20,
        count=inputs["Breakup Pieces"],
        spread=of(".shatter_radius", "FLOAT", 6),
        seed=seed,
    )
    parts, points = cells(t, zone, x + 26, y)
    # Moving and spinning as the piece
    arm = t.vmath("SUBTRACT", position, center, x=x + 27, y=y - 3)
    points = t.store(
        points,
        ".shatter_velocity",
        "FLOAT_VECTOR",
        t.vmath(
            "ADD",
            moving,
            t.vmath("CROSS_PRODUCT", spin, arm, x=x + 28, y=y - 3),
            x=x + 29,
            y=y - 3,
        ),
        x + 28,
        y,
    )
    for i, (name, data_type, value) in enumerate(
        (
            (".shatter_spin", "FLOAT_VECTOR", spin),
            (".shatter_loose", "FLOAT", 1.0),
            (".shatter_awake", "FLOAT", 1.0),
            (".shatter_parted", "FLOAT", 1.0),
            (".shatter_shed", "FLOAT", 0.0),
            (".shatter_rotation", "QUATERNION", None),
        )
    ):
        points = t.store(points, name, data_type, value, x + 28.5 + i * 0.3, y)
    t.connect(points, each_out.inputs["Geometry"])
    t.connect(parts, each_out.inputs["Pieces"])

    # The other pieces with the new ones, linked in the same order
    breaking_piece = sample(t, bodies, breaking, index, "BOOLEAN", x + 30, y + 3, "POINT")
    kept_pieces = t.node(
        "GeometryNodeDeleteGeometry",
        x + 31,
        y + 2,
        {"Geometry": pieces, "Selection": breaking_piece},
        domain="INSTANCE",
    ).outputs[0]
    kept = t.node(
        "GeometryNodeDeleteGeometry", x + 31, y, {"Geometry": bodies, "Selection": breaking}
    ).outputs[0]
    joined_bodies = t.node("GeometryNodeJoinGeometry", x + 32, y)
    joined_pieces = t.node("GeometryNodeJoinGeometry", x + 32, y + 2)
    for target, kept_geometry, new in (
        (joined_bodies, kept, each_out.outputs["Generation_0"]),
        (joined_pieces, kept_pieces, each_out.outputs["Pieces"]),
    ):
        t.connect(kept_geometry, target.inputs[0])
        t.connect(new, target.inputs[0])
    pieces = joined_pieces.outputs[0]
    bodies, hull, planes = hulls(t, pieces, joined_bodies.outputs[0], x + 33, y)
    return bodies, pieces, hull, planes, any_breaking


def rehit(t, bodies, pieces, hull, planes, colliders, inputs, dt, x, y):
    """Bodies, pieces and hulls with the still piece the Colliders hit fast enough broken as the
    mesh at the first hit, or only loose when small, and whether it was hit"""
    index = t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]
    placed = cuts(t, pieces, bodies, x, y)[0]
    placed = t.node(
        "GeometryNodeDeleteGeometry",
        x + 7,
        y,
        {
            "Geometry": placed,
            "Selection": t.math(
                "GREATER_THAN",
                t.attribute(".shatter_loose", "FLOAT", x + 6, y - 2),
                0.5,
                x=x + 7,
                y=y - 2,
            ),
        },
    ).outputs[0]
    hit, impact, push = detect(t, placed, colliders, inputs, dt, x + 8, y)
    # The still piece closest to the hit
    struck = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 26,
        y - 4,
        {
            "Mesh": placed,
            "Value": t.attribute(".shatter_body", "INT", x + 25, y - 5),
            "Sample Position": impact,
        },
        data_type="INT",
    ).outputs["Value"]
    other = t.node(
        "FunctionNodeCompare",
        x + 27,
        y - 6,
        {"A": t.attribute(".shatter_body", "INT", x + 26, y - 6), "B": struck},
        data_type="INT",
        operation="NOT_EQUAL",
    ).outputs[0]
    mesh = t.node(
        "GeometryNodeDeleteGeometry", x + 28, y, {"Geometry": placed, "Selection": other}
    ).outputs[0]

    def of_struck(name, yy):
        return t.node(
            "GeometryNodeSampleNearestSurface",
            x + 26,
            y - yy,
            {
                "Mesh": placed,
                "Value": t.attribute(name, "FLOAT", x + 25, y - yy - 1),
                "Sample Position": impact,
            },
            data_type="FLOAT",
        ).outputs["Value"]

    # Broken when larger than the Break Radius, or anchored on the floor and not tiny by the
    # Spread, its parts on the floor staying, in a share of the Pieces; else only getting loose,
    # when not anchored
    radius = of_struck(".shatter_radius", 8)
    anchored_struck = t.math(
        "GREATER_THAN", of_struck(".shatter_anchored", 10), 0.5, x=x + 27, y=y - 10
    )
    large = t.node(
        "FunctionNodeBooleanMath",
        x + 28,
        y - 8,
        {
            0: t.math("GREATER_THAN", radius, inputs["Break Radius"], x=x + 27, y=y - 8),
            1: t.node(
                "FunctionNodeBooleanMath",
                x + 27.5,
                y - 9,
                {
                    0: anchored_struck,
                    1: t.math(
                        "GREATER_THAN",
                        radius,
                        t.math("MULTIPLY", inputs["Spread"], 0.1, x=x + 26, y=y - 12),
                        x=x + 27,
                        y=y - 12,
                    ),
                },
                operation="AND",
            ).outputs[0],
        },
        operation="OR",
    ).outputs[0]
    count = t.math(
        "MAXIMUM",
        t.math("DIVIDE", inputs["Pieces"], 4.0, x=x + 27, y=y - 11),
        4.0,
        x=x + 28,
        y=y - 11,
    )
    each = fracture(t, mesh, impact, inputs, x + 29, y, count=count)
    new_pieces, new_bodies, new_hull, _ = bodies_of(t, each, mesh, impact, push, inputs, x + 56, y)
    new_bodies = anchored(t, new_bodies, new_hull, mesh, inputs, x + 74, y)

    # The other pieces with the new ones, linked in the same order
    gone = t.node(
        "FunctionNodeCompare",
        x + 84,
        y - 3,
        {"A": index, "B": struck},
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    joined = {}
    for i, (old, new, domain) in enumerate(
        ((bodies, new_bodies, "POINT"), (pieces, new_pieces, "INSTANCE"))
    ):
        kept = t.node(
            "GeometryNodeDeleteGeometry",
            x + 85,
            y + i * 2,
            {"Geometry": old, "Selection": gone},
            domain=domain,
        ).outputs[0]
        join = t.node("GeometryNodeJoinGeometry", x + 86, y + i * 2)
        t.connect(kept, join.inputs[0])
        t.connect(new, join.inputs[0])
        joined[domain] = join.outputs[0]
    broken = hulls(t, joined["INSTANCE"], joined["POINT"], x + 87, y)

    freed = t.math(
        "MULTIPLY",
        gone,
        t.math(
            "SUBTRACT",
            1.0,
            t.attribute(".shatter_anchored", "FLOAT", x + 83, y - 10),
            x=x + 84,
            y=y - 10,
        ),
        x=x + 84.5,
        y=y - 9,
    )
    loose = bodies
    for i, name in enumerate((".shatter_loose", ".shatter_awake")):
        value = t.math(
            "MAXIMUM", t.attribute(name, "FLOAT", x + 84, y - 8 - i), freed, x=x + 85, y=y - 8 - i
        )
        loose = t.store(loose, name, "FLOAT", value, x + 86 + i * 0.5, y - 8)
    outputs = [
        switch(t, large, kept, new, "GEOMETRY", x + 95, y - i)
        for i, (kept, new) in enumerate(
            (
                (loose, broken[0]),
                (pieces, joined["INSTANCE"]),
                (hull, broken[1]),
                (planes, broken[2]),
            )
        )
    ]
    return (*outputs, hit)


def support_graph(t, placed, bodies, x, y):
    """Graph of the pieces, at their centers, linked where they share a cut, with the ones
    anchored on the floor"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    index = t.node("GeometryNodeInputIndex", x, y - 3).outputs[0]
    body = t.attribute(".shatter_body", "INT", x, y - 4)
    # A point of another piece in the same place: the pieces share a cut there
    closest = t.node("GeometryNodeIndexOfNearest", x + 1, y - 2, {"Position": position}).outputs[
        "Index"
    ]
    other = sample(t, placed, body, closest, "INT", x + 2, y - 4)
    apart = t.vmath(
        "DISTANCE",
        position,
        sample(t, placed, position, closest, "FLOAT_VECTOR", x + 2, y - 2),
        x=x + 3,
        y=y - 2,
    )
    shared = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", apart, 1e-4, x=x + 4, y=y - 2),
        t.math(
            "SUBTRACT", 1.0, t.math("COMPARE", body, other, 0.5, x=x + 3, y=y - 5), x=x + 4, y=y - 5
        ),
        x=x + 5,
        y=y - 3,
    )
    links = t.node("GeometryNodeMeshToPoints", x + 2, y, {"Mesh": placed}).outputs[0]
    links = t.store(links, ".shatter_other", "INT", other, x + 3, y)
    links = t.node(
        "GeometryNodeDeleteGeometry",
        x + 6,
        y,
        {"Geometry": links, "Selection": t.math("LESS_THAN", shared, 0.5, x=x + 6, y=y - 3)},
    ).outputs[0]
    # An edge between the centers of the two pieces of each link
    line = t.node("GeometryNodeMeshLine", x + 6, y - 6, {"Count": 2}).outputs[0]
    links = t.node(
        "GeometryNodeInstanceOnPoints", x + 7, y, {"Points": links, "Instance": line}
    ).outputs[0]
    links = t.node("GeometryNodeRealizeInstances", x + 8, y, {"Geometry": links}).outputs[0]
    end = t.node(
        "GeometryNodeSwitch",
        x + 9,
        y - 3,
        {
            "Switch": t.math("FLOORED_MODULO", index, 2, x=x + 8, y=y - 3),
            "False": body,
            "True": t.attribute(".shatter_other", "INT", x + 8, y - 4),
        },
        input_type="INT",
    ).outputs[0]
    links = t.node(
        "GeometryNodeSetPosition",
        x + 10,
        y,
        {
            "Geometry": links,
            "Position": sample(t, bodies, position, end, "FLOAT_VECTOR", x + 9, y - 5),
        },
    ).outputs[0]
    # Each piece a vertex, also without links
    graph = t.node("GeometryNodeJoinGeometry", x + 11, y)
    t.connect(links, graph.inputs[0])
    t.connect(
        t.node("GeometryNodePointsToVertices", x + 10, y - 7, {"Points": bodies}).outputs[0],
        graph.inputs[0],
    )
    graph = t.node(
        "GeometryNodeMergeByDistance", x + 12, y, {"Geometry": graph.outputs[0], "Distance": 1e-5}
    ).outputs[0]
    piece = t.node(
        "GeometryNodeSampleNearest",
        x + 12,
        y - 3,
        {"Geometry": bodies, "Sample Position": position},
    ).outputs[0]
    anchored = sample(
        t,
        bodies,
        t.attribute(".shatter_anchored", "FLOAT", x + 12, y - 4),
        piece,
        "FLOAT",
        x + 13,
        y - 3,
    )
    return t.store(graph, ".shatter_anchored", "FLOAT", anchored, x + 14, y)


def supported(t, bodies, graph, x, y):
    """Bodies with the still pieces not held by an anchored one through still pieces loose"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]

    def matching(geometry, target, xx, yy):
        """Index of the closest point of the target, and whether it is in the same place"""
        closest = t.node(
            "GeometryNodeSampleNearest", xx, yy, {"Geometry": target, "Sample Position": position}
        ).outputs[0]
        apart = t.vmath(
            "DISTANCE",
            position,
            sample(t, target, position, closest, "FLOAT_VECTOR", xx + 1, yy),
            x=xx + 2,
            y=yy,
        )
        return closest, t.math("LESS_THAN", apart, 1e-4, x=xx + 3, y=yy)

    # The graph of the still pieces
    piece, same = matching(graph, bodies, x, y - 3)
    loose = sample(
        t,
        bodies,
        t.attribute(".shatter_loose", "FLOAT", x + 3, y - 5),
        piece,
        "FLOAT",
        x + 4,
        y - 5,
    )
    still = t.math(
        "MULTIPLY", same, t.math("LESS_THAN", loose, 0.5, x=x + 5, y=y - 5), x=x + 6, y=y - 4
    )
    graph = t.node(
        "GeometryNodeDeleteGeometry",
        x + 7,
        y - 1,
        {"Geometry": graph, "Selection": t.math("LESS_THAN", still, 0.5, x=x + 7, y=y - 4)},
    ).outputs[0]
    island = t.node("GeometryNodeInputMeshIsland", x + 7, y - 6).outputs["Island Index"]
    held = t.node(
        "GeometryNodeAccumulateField",
        x + 8,
        y - 5,
        {"Value": t.attribute(".shatter_anchored", "FLOAT", x + 7, y - 7), "Group ID": island},
        data_type="FLOAT",
    ).outputs["Total"]
    graph = t.store(
        graph,
        ".shatter_held",
        "FLOAT",
        t.math("GREATER_THAN", held, 0.5, x=x + 9, y=y - 5),
        x + 9,
        y - 1,
    )

    # Loose where not held
    vertex, same = matching(bodies, graph, x + 10, y - 3)
    held = sample(
        t,
        graph,
        t.attribute(".shatter_held", "FLOAT", x + 13, y - 5),
        vertex,
        "FLOAT",
        x + 14,
        y - 5,
    )
    dropped = t.math(
        "MULTIPLY", same, t.math("SUBTRACT", 1.0, held, x=x + 15, y=y - 5), x=x + 16, y=y - 4
    )
    for i, name in enumerate((".shatter_loose", ".shatter_awake")):
        value = t.math(
            "MAXIMUM", t.attribute(name, "FLOAT", x + 16, y - 6 - i), dropped, x=x + 17, y=y - 5 - i
        )
        bodies = t.store(bodies, name, "FLOAT", value, x + 18 + i * 0.5, y)
    return bodies


def turned(t, rotation, spin, scale, x, y):
    """Rotation turned in world space by the spin vector times the scale"""
    angle = t.math("MULTIPLY", t.vmath("LENGTH", spin, x=x, y=y - 1), scale, x=x + 1, y=y - 1)
    turn = t.node(
        "FunctionNodeAxisAngleToRotation", x + 1, y, {"Axis": spin, "Angle": angle}
    ).outputs[0]
    return t.node(
        "FunctionNodeRotateRotation",
        x + 2,
        y,
        {"Rotation": rotation, "Rotate By": turn},
        rotation_space="GLOBAL",
    ).outputs[0]


def matrix(t, columns, x, y):
    """Matrix with the 3x3 block of the column vectors"""
    node = t.node("FunctionNodeCombineMatrix", x, y)
    for c, column in enumerate(columns):
        xyz = t.node("ShaderNodeSeparateXYZ", x - 1, y - c, {0: column}).outputs
        for r in range(3):
            t.connect(xyz[r], node.inputs[c * 4 + r])
    return node.outputs[0]


def times(t, transform, vector, x, y):
    return t.node(
        "FunctionNodeTransformDirection", x, y, {"Direction": vector, "Transform": transform}
    ).outputs[0]


AXES = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
# Speed of the mesh under which it holds the pieces outside the Break Radius, in m/s
STILL_SPEED = 0.2
# Cells of the dust grid along each side, at most
MAX_CELLS = 96
# Speed under which the touching pieces rest, in m/s
REST_SPEED = 0.1
# Frames at rest before a piece sleeps, not moving until woken by a hit at the speed, in m/s
SLEEP_FRAMES = 10
WAKE_SPEED = 0.5
# Drift, as a share of the radius of the piece, and turn, in radians, still counted as still
SLEEP_DRIFT = 0.1
SLEEP_TURN = 0.2
# Fastest push out of overlapping pieces, in m/s
PUSH_OUT_SPEED = 0.25
# Regularization of the rigid solves, for pieces with too few contacts
REGULARIZATION = 1e-1


def rigid_solve(t, sources, project, target, x, y):
    """Move (translation, rotation vector) of each piece fitting at best the targets of its
    contacts, in the (geometry, index of the first contact of the piece) sources, along the
    directions selected by the projection of each contact, with the least move of the unit mass
    and inertia of the piece otherwise"""
    arm = t.attribute(".shatter_arm", "FLOAT_VECTOR", x, y - 1)
    piece = t.attribute(".shatter_piece", "INT", x, y - 2)
    row = [y]

    def total(value):
        row[0] -= 1
        summed = t.node(
            "GeometryNodeAccumulateField",
            x + 4,
            row[0],
            {"Value": value, "Group ID": piece},
            data_type="FLOAT_VECTOR",
        ).outputs["Total"]
        totals = [
            sample(t, geometry, summed, first, "FLOAT_VECTOR", x + 5, row[0] - i * 0.5)
            for i, (geometry, first) in enumerate(sources)
        ]
        return t.vmath("ADD", *totals, x=x + 5.5, y=row[0]) if len(totals) > 1 else totals[0]

    # Normal equations [A T; T' D] of the moves of the points: translation + rotation x arm
    twists = [
        t.vmath("CROSS_PRODUCT", arm, axis, x=x + 1, y=y - 4 - i) for i, axis in enumerate(AXES)
    ]
    a = [total(project(axis, x + 2, y - 4 - i)) for i, axis in enumerate(AXES)]
    twisted = [project(twist, x + 2, y - 8 - i) for i, twist in enumerate(twists)]
    side = [total(t.vmath("SCALE", p, -1.0, x=x + 3, y=y - 8 - i)) for i, p in enumerate(twisted)]
    d = [
        total(t.vmath("CROSS_PRODUCT", p, arm, x=x + 3, y=y - 12 - i))
        for i, p in enumerate(twisted)
    ]
    projected = project(target, x + 2, y - 16)
    b1 = total(projected)
    b2 = total(t.vmath("CROSS_PRODUCT", arm, projected, x=x + 3, y=y - 17))

    x += 6
    inertia = t.attribute(".shatter_inertia", "FLOAT", x, y - 20)
    damping = t.math("MULTIPLY", inertia, REGULARIZATION, x=x + 1, y=y - 20)
    a = [
        t.vmath("MULTIPLY_ADD", axis, (REGULARIZATION,) * 3, c, x=x, y=y - 1 - i)
        for i, (axis, c) in enumerate(zip(AXES, a, strict=True))
    ]
    d = [
        t.vmath("MULTIPLY_ADD", axis, damping, c, x=x + 2, y=y - 8 - i)
        for i, (axis, c) in enumerate(zip(AXES, d, strict=True))
    ]
    inverse_a = t.node(
        "FunctionNodeInvertMatrix", x + 3, y - 1, {0: matrix(t, a, x + 2, y - 1)}
    ).outputs[0]
    side = matrix(t, side, x + 2, y - 4)
    flipped = t.node("FunctionNodeTransposeMatrix", x + 3, y - 4, {0: side}).outputs[0]
    # Schur complement of A
    reduced = t.node(
        "FunctionNodeMatrixMultiply",
        x + 5,
        y - 4,
        {
            0: flipped,
            1: t.node("FunctionNodeMatrixMultiply", x + 4, y - 3, {0: inverse_a, 1: side}).outputs[
                0
            ],
        },
    ).outputs[0]
    reduced = [
        t.vmath("SUBTRACT", c, times(t, reduced, axis, x + 6, y - 8 - i), x=x + 7, y=y - 8 - i)
        for i, (axis, c) in enumerate(zip(AXES, d, strict=True))
    ]
    inverse_s = t.node(
        "FunctionNodeInvertMatrix", x + 9, y - 8, {0: matrix(t, reduced, x + 8, y - 8)}
    ).outputs[0]
    spin = t.vmath(
        "SUBTRACT",
        b2,
        times(t, flipped, times(t, inverse_a, b1, x + 6, y - 14), x + 7, y - 14),
        x=x + 8,
        y=y - 14,
    )
    spin = times(t, inverse_s, spin, x + 10, y - 14)
    move = times(
        t,
        inverse_a,
        t.vmath("SUBTRACT", b1, times(t, side, spin, x + 11, y - 15), x=x + 12, y=y - 15),
        x + 13,
        y - 15,
    )
    return move, spin


def resistance(t, arm, inertia, direction, x, y):
    """Inverse effective mass of the point at the arm along the direction, for a unit mass"""
    twist = t.vmath("CROSS_PRODUCT", arm, direction, x=x, y=y)
    twist = t.vmath("DOT_PRODUCT", twist, twist, x=x + 1, y=y)
    return t.math("ADD", 1.0, t.math("DIVIDE", twist, inertia, x=x + 2, y=y), x=x + 3, y=y)


class Hull:
    """Fields of the hull points from the state of their piece"""

    def __init__(self, t, bodies, x, y):
        self.t, self.bodies, self.x, self.y = t, bodies, x, y
        self.piece = t.attribute(".shatter_piece", "INT", x, y)

    def body(self, name, data_type):
        t = self.t
        self.y -= 1
        value = t.node("GeometryNodeInputPosition", self.x, self.y).outputs[0]
        if name is not None:
            value = t.attribute(name, data_type, self.x, self.y)
        return sample(t, self.bodies, value, self.piece, data_type, self.x + 1, self.y)

    def point(self, position, rotation):
        """Arm from the center of the piece, and point in world space"""
        t = self.t
        self.y -= 1
        local = t.node("GeometryNodeInputPosition", self.x + 1, self.y).outputs[0]
        arm = t.node(
            "FunctionNodeRotateVector",
            self.x + 2,
            self.y,
            {"Vector": local, "Rotation": self.body(rotation, "QUATERNION")},
        ).outputs[0]
        return arm, t.vmath("ADD", self.body(position, "FLOAT_VECTOR"), arm, x=self.x + 3, y=self.y)

    def velocity(self, arm):
        t = self.t
        spin = t.vmath(
            "CROSS_PRODUCT", self.body(".shatter_spin", "FLOAT_VECTOR"), arm, x=self.x + 2, y=self.y
        )
        moving = self.body(".shatter_velocity", "FLOAT_VECTOR")
        return t.vmath("ADD", moving, spin, x=self.x + 3, y=self.y)


def contacts(t, bodies, hull, colliders, inputs, h, x, y):
    """Hull points with their deepest contact with the Colliders or the floor at the predicted
    pose, and their slide in the substep"""
    fields = Hull(t, bodies, x, y)
    arm, point = fields.point(None, ".shatter_rotation")
    _, before = fields.point(".shatter_prev", ".shatter_prev_rotation")
    moving = fields.velocity(arm)
    loose = fields.body(".shatter_awake", "FLOAT")
    x += 4

    side = t.attribute(".shatter_side", "FLOAT_VECTOR", x, y - 3)
    surface = t.attribute(".shatter_surface", "FLOAT_VECTOR", x, y - 4)
    closest = t.node(
        "GeometryNodeProximity", x + 1, y - 2, {"Geometry": colliders, "Sample Position": point}
    ).outputs
    offset = t.vmath("SUBTRACT", point, closest["Position"], x=x + 2, y=y - 2)
    # Toward the point, flipped inside the Colliders by their normal at the start of the frame
    normal = switch(
        t,
        t.math("GREATER_THAN", closest["Distance"], 1e-6, x=x + 2, y=y - 3),
        side,
        t.vmath("NORMALIZE", offset, x=x + 2, y=y - 4),
        "VECTOR",
        x + 3,
        y - 3,
    )
    normal = t.vmath(
        "SCALE",
        normal,
        t.math("SIGN", t.vmath("DOT_PRODUCT", normal, side, x=x + 3, y=y - 5), x=x + 4, y=y - 5),
        x=x + 4,
        y=y - 3,
    )
    signed = t.vmath("DOT_PRODUCT", offset, normal, x=x + 3, y=y - 2)
    # Not deeper than the point could go in a substep, not to be pushed through thin Colliders
    relative = t.vmath("SUBTRACT", moving, surface, x=x + 2, y=y - 5)
    reach = t.math(
        "MULTIPLY_ADD",
        t.vmath("LENGTH", relative, x=x + 3, y=y - 5),
        t.math("MULTIPLY", h, -2.0, x=x + 3, y=y - 6),
        t.math("MULTIPLY", inputs["Margin"], -1.0, x=x + 3, y=y - 7),
        x=x + 4,
        y=y - 5,
    )
    valid = t.math(
        "MULTIPLY",
        closest["Is Valid"],
        t.math("GREATER_THAN", signed, reach, x=x + 5, y=y - 5),
        x=x + 6,
        y=y - 4,
    )
    depth = t.math("SUBTRACT", inputs["Margin"], signed, x=x + 4, y=y - 2)
    depth = switch(t, valid, -1.0, depth, "FLOAT", x + 7, y - 2)
    height = socket(t.node("ShaderNodeSeparateXYZ", x + 2, y - 8, {0: point}).outputs, "Z")
    floor = t.math("ADD", inputs["Floor"], inputs["Margin"], x=x + 2, y=y - 9)
    floor = t.math("SUBTRACT", floor, height, x=x + 3, y=y - 8)
    on_collider = t.math("GREATER_THAN", depth, floor, x=x + 8, y=y - 4)
    normal = switch(t, on_collider, (0.0, 0.0, 1.0), normal, "VECTOR", x + 9, y - 3)
    surface = switch(t, on_collider, (0.0, 0.0, 0.0), surface, "VECTOR", x + 9, y - 4)
    depth = t.math("MAXIMUM", depth, floor, x=x + 9, y=y - 2)
    inside = t.math("GREATER_THAN", depth, 0.0, x=x + 10, y=y - 5)
    touching = t.math("MULTIPLY", inside, loose, x=x + 11, y=y - 5)

    # Slide of the point across the surface in the substep
    slide = t.vmath(
        "SUBTRACT",
        t.vmath("SUBTRACT", point, before, x=x + 10, y=y - 9),
        t.vmath("SCALE", surface, h, x=x + 10, y=y - 10),
        x=x + 11,
        y=y - 9,
    )
    along = t.vmath("DOT_PRODUCT", slide, normal, x=x + 11, y=y - 10)
    across = t.vmath(
        "SUBTRACT", slide, t.vmath("SCALE", normal, along, x=x + 12, y=y - 10), x=x + 13, y=y - 9
    )
    # Fixed pieces come loose when a Collider hits them fast enough
    fast = t.math(
        "GREATER_THAN",
        t.vmath("LENGTH", relative, x=x + 9, y=y - 6),
        inputs["Strength"],
        x=x + 10,
        y=y - 6,
    )
    hit = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", on_collider, inside, x=x + 11, y=y - 6),
        fast,
        x=x + 12,
        y=y - 6,
    )

    # Sleeping pieces wake when a Collider hits them
    wake = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", on_collider, inside, x=x + 11, y=y - 7),
        t.math(
            "GREATER_THAN",
            t.vmath("LENGTH", relative, x=x + 9, y=y - 7),
            WAKE_SPEED,
            x=x + 10,
            y=y - 7,
        ),
        x=x + 12,
        y=y - 7,
    )
    approach = t.vmath("DOT_PRODUCT", relative, normal, x=x + 10, y=y - 3)
    # Not pushed out more than the Collider or the floor came in over the substep, else thrown far
    coming = t.math(
        "MAXIMUM", t.math("MULTIPLY", along, -1.0, x=x + 11, y=y - 9), 0.0, x=x + 12, y=y - 9
    )
    depth = t.math(
        "MINIMUM",
        depth,
        t.math(
            "ADD",
            coming,
            t.math("MULTIPLY_ADD", h, PUSH_OUT_SPEED, inputs["Margin"], x=x + 12, y=y - 10),
            x=x + 13,
            y=y - 10,
        ),
        x=x + 12,
        y=y - 1,
    )
    depth = t.math("MULTIPLY", depth, touching, x=x + 12, y=y - 2)
    for i, (name, data_type, value) in enumerate(
        (
            (".shatter_arm", "FLOAT_VECTOR", arm),
            (".shatter_normal", "FLOAT_VECTOR", normal),
            (".shatter_surface", "FLOAT_VECTOR", surface),
            (".shatter_approach", "FLOAT", approach),
            (".shatter_depth", "FLOAT", depth),
            (".shatter_touching", "FLOAT", touching),
            (".shatter_slide", "FLOAT_VECTOR", across),
            (".shatter_hit", "FLOAT", hit),
            (".shatter_wake", "FLOAT", wake),
        )
    ):
        hull = t.store(hull, name, data_type, value, x + 14 + i * 0.5, y)
    return hull


def inverse_rotate(t, vector, rotation, x, y):
    rotation = t.node("FunctionNodeInvertRotation", x, y - 1, {0: rotation}).outputs[0]
    return t.node(
        "FunctionNodeRotateVector", x + 1, y, {"Vector": vector, "Rotation": rotation}
    ).outputs[0]


def pairs(t, bodies, hull, planes, inputs, dt, x, y):
    """Contacts to check in the frame between the hull points of the pieces and the closest face
    plane of the convex hull of the pieces they can reach, for both pieces, sorted by piece, and
    the bodies with the index of their first contact"""
    index = t.node("GeometryNodeInputIndex", x, y - 1).outputs[0]
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    count = t.node(
        "GeometryNodeAttributeDomainSize", x, y - 3, {"Geometry": bodies}, component="POINTCLOUD"
    ).outputs["Point Count"]

    def of(which, name, data_type, yy):
        value = position if name is None else t.attribute(name, data_type, x + 1, y - yy)
        return sample(t, bodies, value, which, data_type, x + 2, y - yy)

    def speed(which, yy):
        """Fastest speed of the points of the piece"""
        spin = t.vmath("LENGTH", of(which, ".shatter_spin", "FLOAT_VECTOR", yy), x=x + 3, y=y - yy)
        spin = t.math(
            "MULTIPLY", spin, of(which, ".shatter_radius", "FLOAT", yy + 1), x=x + 4, y=y - yy
        )
        moving = t.vmath(
            "LENGTH", of(which, ".shatter_velocity", "FLOAT_VECTOR", yy + 2), x=x + 3, y=y - yy - 2
        )
        return t.math("ADD", spin, moving, x=x + 5, y=y - yy)

    # Pairs of pieces close enough to touch in the frame, one of them loose
    a = t.math("FLOOR", t.math("DIVIDE", index, count, x=x + 1, y=y - 5), x=x + 2, y=y - 5)
    b = t.math("FLOORED_MODULO", index, count, x=x + 1, y=y - 6)
    reach = t.math("ADD", speed(a, 8), speed(b, 12), x=x + 6, y=y - 10)
    reach = t.math("MULTIPLY_ADD", reach, dt, inputs["Margin"], x=x + 7, y=y - 10)
    apart = t.vmath(
        "DISTANCE",
        of(a, None, "FLOAT_VECTOR", 16),
        of(b, None, "FLOAT_VECTOR", 17),
        x=x + 3,
        y=y - 16,
    )
    room = t.math(
        "ADD",
        t.math(
            "ADD",
            of(a, ".shatter_radius", "FLOAT", 18),
            of(b, ".shatter_radius", "FLOAT", 19),
            x=x + 3,
            y=y - 18,
        ),
        reach,
        x=x + 8,
        y=y - 18,
    )
    loose = t.math(
        "ADD",
        of(a, ".shatter_awake", "FLOAT", 20),
        of(b, ".shatter_awake", "FLOAT", 21),
        x=x + 3,
        y=y - 20,
    )
    keep = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", apart, room, x=x + 9, y=y - 16),
        t.math("GREATER_THAN", loose, 0.5, x=x + 4, y=y - 20),
        x=x + 10,
        y=y - 16,
    )
    other = t.math(
        "SUBTRACT", 1.0, t.math("COMPARE", a, b, 0.5, x=x + 3, y=y - 7), x=x + 4, y=y - 7
    )
    keep = t.math("MULTIPLY", keep, other, x=x + 11, y=y - 16)
    candidates = t.node(
        "GeometryNodePoints",
        x + 3,
        y,
        {"Count": t.math("MULTIPLY", count, count, x=x + 2, y=y - 4)},
    ).outputs[0]
    candidates = t.store(candidates, ".shatter_a", "INT", a, x + 4, y)
    candidates = t.store(candidates, ".shatter_b", "INT", b, x + 5, y)
    candidates = t.store(candidates, ".shatter_reach", "FLOAT", reach, x + 8, y)
    candidates = t.node(
        "GeometryNodeDeleteGeometry",
        x + 12,
        y,
        {"Geometry": candidates, "Selection": t.math("LESS_THAN", keep, 0.5, x=x + 11, y=y - 17)},
    ).outputs[0]

    # Each hull point of the first piece reaching the second, in the space of the second
    x += 13
    a = t.attribute(".shatter_a", "INT", x, y - 4)
    b = t.attribute(".shatter_b", "INT", x, y - 5)
    reach = t.attribute(".shatter_reach", "FLOAT", x, y - 6)
    rows = t.node(
        "GeometryNodeDuplicateElements",
        x + 2,
        y,
        {"Geometry": candidates, "Amount": of(a, ".shatter_count", "INT", 30)},
        domain="POINT",
    ).outputs
    point = t.math(
        "ADD", of(a, ".shatter_first", "INT", 31), rows["Duplicate Index"], x=x + 3, y=y - 31
    )
    local = sample(t, hull, position, point, "FLOAT_VECTOR", x + 4, y - 31)
    rows = t.store(rows["Geometry"], ".shatter_local", "FLOAT_VECTOR", local, x + 5, y)
    world = t.node(
        "FunctionNodeRotateVector",
        x + 3,
        y - 33,
        {
            "Vector": t.attribute(".shatter_local", "FLOAT_VECTOR", x + 2, y - 33),
            "Rotation": of(a, ".shatter_rotation", "QUATERNION", 34),
        },
    ).outputs[0]
    world = t.vmath("ADD", world, of(a, None, "FLOAT_VECTOR", 35), x=x + 4, y=y - 33)
    inside = inverse_rotate(
        t,
        t.vmath("SUBTRACT", world, of(b, None, "FLOAT_VECTOR", 36), x=x + 5, y=y - 33),
        of(b, ".shatter_rotation", "QUATERNION", 37),
        x + 6,
        y - 33,
    )
    rows = t.store(rows, ".shatter_inside", "FLOAT_VECTOR", inside, x + 8, y)
    far = t.math(
        "GREATER_THAN",
        t.vmath(
            "LENGTH",
            t.attribute(".shatter_inside", "FLOAT_VECTOR", x + 8, y - 38),
            x=x + 9,
            y=y - 38,
        ),
        t.math("ADD", of(b, ".shatter_radius", "FLOAT", 39), reach, x=x + 9, y=y - 39),
        x=x + 10,
        y=y - 38,
    )
    rows = t.node(
        "GeometryNodeDeleteGeometry", x + 10, y, {"Geometry": rows, "Selection": far}
    ).outputs[0]
    rows = t.store(rows, ".shatter_row", "INT", index, x + 11, y)

    # The plane of the second piece the point is the least inside, if it can reach it
    x += 12
    rows = t.node(
        "GeometryNodeDuplicateElements",
        x,
        y,
        {"Geometry": rows, "Amount": of(b, ".shatter_plane_count", "INT", 42)},
        domain="POINT",
    ).outputs
    plane = t.math(
        "ADD", of(b, ".shatter_plane_first", "INT", 43), rows["Duplicate Index"], x=x + 1, y=y - 43
    )
    rows = t.store(
        rows["Geometry"],
        ".shatter_plane",
        "FLOAT_VECTOR",
        sample(t, planes, position, plane, "FLOAT_VECTOR", x + 2, y - 44),
        x + 3,
        y,
    )
    rows = t.store(
        rows,
        ".shatter_offset",
        "FLOAT",
        sample(
            t,
            planes,
            t.attribute(".shatter_offset", "FLOAT", x + 1, y - 46),
            plane,
            "FLOAT",
            x + 2,
            y - 46,
        ),
        x + 4,
        y,
    )
    signed = t.math(
        "SUBTRACT",
        t.vmath(
            "DOT_PRODUCT",
            t.attribute(".shatter_plane", "FLOAT_VECTOR", x + 4, y - 48),
            t.attribute(".shatter_inside", "FLOAT_VECTOR", x + 4, y - 49),
            x=x + 5,
            y=y - 48,
        ),
        t.attribute(".shatter_offset", "FLOAT", x + 4, y - 50),
        x=x + 6,
        y=y - 48,
    )
    row = t.attribute(".shatter_row", "INT", x + 5, y - 51)
    # Ties, as on the faces along the cuts, broken by the planes facing the first piece
    toward = t.vmath(
        "SUBTRACT",
        of(a, None, "FLOAT_VECTOR", 53),
        of(b, None, "FLOAT_VECTOR", 54),
        x=x + 3,
        y=y - 53,
    )
    toward = inverse_rotate(t, toward, of(b, ".shatter_rotation", "QUATERNION", 55), x + 4, y - 53)
    toward = t.vmath(
        "DOT_PRODUCT",
        t.attribute(".shatter_plane", "FLOAT_VECTOR", x + 5, y - 55),
        t.vmath("NORMALIZE", toward, x=x + 6, y=y - 53),
        x=x + 7,
        y=y - 53,
    )
    score = t.math(
        "MULTIPLY_ADD",
        toward,
        t.math("MULTIPLY", inputs["Margin"], 0.5, x=x + 7, y=y - 54),
        signed,
        x=x + 8,
        y=y - 53,
    )
    closest = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 9,
        y - 50,
        {"Value": score, "Group ID": row},
        data_type="FLOAT",
    ).outputs["Max"]
    limit = t.math("ADD", reach, inputs["Margin"], x=x + 7, y=y - 52)
    keep = t.math(
        "MULTIPLY",
        t.math(
            "GREATER_THAN",
            score,
            t.math("SUBTRACT", closest, 1e-7, x=x + 10, y=y - 49),
            x=x + 11,
            y=y - 48,
        ),
        t.math(
            "LESS_THAN",
            t.math("ABSOLUTE", signed, x=x + 8, y=y - 51),
            limit,
            x=x + 9,
            y=y - 51,
        ),
        x=x + 12,
        y=y - 48,
    )
    rows = t.node(
        "GeometryNodeDeleteGeometry",
        x + 11,
        y,
        {"Geometry": rows, "Selection": t.math("LESS_THAN", keep, 0.5, x=x + 10, y=y - 49)},
    ).outputs[0]
    # One plane per point
    rank = t.node(
        "GeometryNodeAccumulateField",
        x + 11,
        y - 52,
        {"Value": 1, "Group ID": row},
        data_type="INT",
    ).outputs["Leading"]
    rows = t.node(
        "GeometryNodeDeleteGeometry",
        x + 12,
        y,
        {"Geometry": rows, "Selection": t.math("GREATER_THAN", rank, 1, x=x + 12, y=y - 52)},
    ).outputs[0]
    rows = t.store(rows, ".shatter_valid", "FLOAT", 1.0, x + 13, y)

    # For both pieces, with one empty contact per piece, sorted by piece
    x += 14
    joined = t.node("GeometryNodeJoinGeometry", x + 3, y)
    for i, (owner, sign) in enumerate(((".shatter_a", 1.0), (".shatter_b", -1.0))):
        side = t.store(
            rows, ".shatter_piece", "INT", t.attribute(owner, "INT", x, y - 2 - i), x + 1, y - i
        )
        t.connect(t.store(side, ".shatter_sign", "FLOAT", sign, x + 2, y - i), joined.inputs[0])
    empty = t.node("GeometryNodePoints", x + 1, y - 3, {"Count": count}).outputs[0]
    t.connect(t.store(empty, ".shatter_piece", "INT", index, x + 2, y - 3), joined.inputs[0])
    piece = t.attribute(".shatter_piece", "INT", x + 3, y - 4)
    contacts = t.node(
        "GeometryNodeSortElements",
        x + 4,
        y,
        {"Geometry": joined.outputs[0], "Sort Weight": piece},
        domain="POINT",
    ).outputs[0]
    contacts = t.store(contacts, ".shatter_index", "INT", index, x + 5, y)
    before = t.node(
        "GeometryNodeFieldAtIndex",
        x + 5,
        y - 5,
        {"Value": piece, "Index": t.math("SUBTRACT", index, 1, x=x + 4, y=y - 6)},
        data_type="INT",
    ).outputs[0]
    later = t.node(
        "FunctionNodeCompare",
        x + 6,
        y - 5,
        {"A": piece, "B": before},
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    later = t.math(
        "MULTIPLY", later, t.math("GREATER_THAN", index, 0, x=x + 6, y=y - 6), x=x + 7, y=y - 5
    )
    heads = t.node(
        "GeometryNodeDeleteGeometry", x + 8, y - 2, {"Geometry": contacts, "Selection": later}
    ).outputs[0]
    first = sample(
        t, heads, t.attribute(".shatter_index", "INT", x + 8, y - 4), index, "INT", x + 9, y - 4
    )
    bodies = t.store(bodies, ".shatter_pair_first", "INT", first, x + 10, y - 4)
    return contacts, bodies


def pair_contacts(t, bodies, contacts, inputs, h, x, y):
    """Contacts between pieces at the predicted pose: the hull point of one in the closest face
    plane of the other, for the piece owning the contact, shared when both are loose"""
    position = t.node("GeometryNodeInputPosition", x, y - 1).outputs[0]
    a = t.attribute(".shatter_a", "INT", x, y - 2)
    b = t.attribute(".shatter_b", "INT", x, y - 3)

    def of(which, name, data_type, yy):
        value = position if name is None else t.attribute(name, data_type, x + 1, y - yy)
        return sample(t, bodies, value, which, data_type, x + 2, y - yy)

    center_a, center_b = of(a, None, "FLOAT_VECTOR", 4), of(b, None, "FLOAT_VECTOR", 5)
    point = t.node(
        "FunctionNodeRotateVector",
        x + 3,
        y - 6,
        {
            "Vector": t.attribute(".shatter_local", "FLOAT_VECTOR", x + 2, y - 6),
            "Rotation": of(a, ".shatter_rotation", "QUATERNION", 7),
        },
    ).outputs[0]
    point = t.vmath("ADD", point, center_a, x=x + 4, y=y - 6)
    normal = t.node(
        "FunctionNodeRotateVector",
        x + 3,
        y - 8,
        {
            "Vector": t.attribute(".shatter_plane", "FLOAT_VECTOR", x + 2, y - 8),
            "Rotation": of(b, ".shatter_rotation", "QUATERNION", 9),
        },
    ).outputs[0]
    signed = t.math(
        "SUBTRACT",
        t.vmath(
            "DOT_PRODUCT",
            normal,
            t.vmath("SUBTRACT", point, center_b, x=x + 4, y=y - 9),
            x=x + 5,
            y=y - 8,
        ),
        t.attribute(".shatter_offset", "FLOAT", x + 4, y - 10),
        x=x + 6,
        y=y - 8,
    )

    def velocity(which, center, yy):
        spin = t.vmath(
            "CROSS_PRODUCT",
            of(which, ".shatter_spin", "FLOAT_VECTOR", yy),
            t.vmath("SUBTRACT", point, center, x=x + 3, y=y - yy - 1),
            x=x + 4,
            y=y - yy,
        )
        return t.vmath(
            "ADD", of(which, ".shatter_velocity", "FLOAT_VECTOR", yy + 1), spin, x=x + 5, y=y - yy
        )

    moving_a, moving_b = velocity(a, center_a, 12), velocity(b, center_b, 15)
    relative = t.vmath("SUBTRACT", moving_a, moving_b, x=x + 6, y=y - 13)
    # Not deeper than the point could go in a substep, ignoring the hulls overlapping from the start
    reach = t.math(
        "MULTIPLY_ADD",
        t.vmath("LENGTH", relative, x=x + 7, y=y - 14),
        t.math("MULTIPLY", h, 2.0, x=x + 7, y=y - 15),
        inputs["Margin"],
        x=x + 8,
        y=y - 14,
    )
    valid = t.math(
        "MULTIPLY",
        t.attribute(".shatter_valid", "FLOAT", x + 8, y - 16),
        t.math(
            "GREATER_THAN",
            signed,
            t.math("MULTIPLY", reach, -1.0, x=x + 9, y=y - 15),
            x=x + 10,
            y=y - 15,
        ),
        x=x + 11,
        y=y - 15,
    )
    # Inside the sphere of the other piece, not by the plane extending past it
    near = t.math(
        "LESS_THAN",
        t.vmath("DISTANCE", point, center_b, x=x + 9, y=y - 17),
        t.math("ADD", of(b, ".shatter_radius", "FLOAT", 17), inputs["Margin"], x=x + 9, y=y - 18),
        x=x + 10,
        y=y - 17,
    )
    valid = t.math("MULTIPLY", valid, near, x=x + 12, y=y - 16)
    depth = t.math("SUBTRACT", inputs["Margin"], signed, x=x + 7, y=y - 8)

    # For the owner: the first piece, or the second with everything mirrored
    sign = t.attribute(".shatter_sign", "FLOAT", x + 7, y - 18)
    mine = t.math("GREATER_THAN", sign, 0.0, x=x + 8, y=y - 18)

    def pick(first, second, yy, vector=True):
        """The first value for the first piece, the second for the second one"""
        if vector:
            return t.vmath(
                "MULTIPLY_ADD",
                t.vmath("SUBTRACT", first, second, x=x + 9, y=y - yy),
                mine,
                second,
                x=x + 10,
                y=y - yy,
            )
        return t.math(
            "MULTIPLY_ADD",
            t.math("SUBTRACT", first, second, x=x + 9, y=y - yy),
            mine,
            second,
            x=x + 10,
            y=y - yy,
        )

    loose_a, loose_b = of(a, ".shatter_awake", "FLOAT", 20), of(b, ".shatter_awake", "FLOAT", 21)
    touching = t.math(
        "MULTIPLY", t.math("GREATER_THAN", depth, 0.0, x=x + 8, y=y - 8), valid, x=x + 12, y=y - 8
    )
    touching = t.math("MULTIPLY", touching, pick(loose_a, loose_b, 20, False), x=x + 13, y=y - 8)
    normal = t.vmath("SCALE", normal, sign, x=x + 11, y=y - 18)
    arm = t.vmath("SUBTRACT", point, pick(center_a, center_b, 22), x=x + 11, y=y - 22)
    relative = t.vmath("SCALE", relative, sign, x=x + 11, y=y - 13)
    slide = t.vmath("SCALE", relative, h, x=x + 12, y=y - 13)
    slide = t.vmath(
        "SUBTRACT",
        slide,
        t.vmath(
            "SCALE",
            normal,
            t.vmath("DOT_PRODUCT", slide, normal, x=x + 12, y=y - 12),
            x=x + 13,
            y=y - 12,
        ),
        x=x + 14,
        y=y - 12,
    )
    # Overlaps pushed out at most at a speed, not to throw the pieces apart, not at all at rest:
    # there they are from the convex hulls covering the hollows of the pieces
    speed = t.math(
        "DIVIDE",
        t.vmath("LENGTH", relative, x=x + 10, y=y - 10),
        REST_SPEED,
        x=x + 11,
        y=y - 10,
        clamp=True,
    )
    pushed = t.math(
        "MINIMUM",
        depth,
        t.math(
            "MULTIPLY_ADD",
            t.math("MULTIPLY", h, speed, x=x + 11, y=y - 9),
            PUSH_OUT_SPEED,
            inputs["Margin"],
            x=x + 12,
            y=y - 9,
        ),
        x=x + 13,
        y=y - 9,
    )
    # Sleeping pieces wake when another piece hits them
    wake = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("GREATER_THAN", depth, 0.0, x=x + 10, y=y - 26),
            valid,
            x=x + 11,
            y=y - 26,
        ),
        t.math(
            "LESS_THAN",
            t.vmath("DOT_PRODUCT", relative, normal, x=x + 11, y=y - 27),
            -WAKE_SPEED,
            x=x + 12,
            y=y - 27,
        ),
        x=x + 13,
        y=y - 26,
    )
    # With the other piece moving too, the push given to the upper one, shared from the side:
    # pushing a lower piece down only fights the floor or the pieces under it
    up = t.vmath(
        "NORMALIZE",
        t.vmath("SCALE", inputs["Gravity"], -1.0, x=x + 9, y=y - 25),
        x=x + 10,
        y=y - 25,
    )
    above = t.math(
        "ADD",
        t.vmath("DOT_PRODUCT", normal, up, x=x + 11, y=y - 25),
        0.5,
        x=x + 12,
        y=y - 25,
        clamp=True,
    )
    # Only resting, halves when moving: squeezed by a Collider, the pieces would be thrown
    above = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", 0.5, above, x=x + 12, y=y - 26),
        speed,
        above,
        x=x + 13,
        y=y - 26,
    )
    shared = t.math(
        "MULTIPLY",
        pick(loose_b, loose_a, 24, False),
        t.math("SUBTRACT", 1.0, above, x=x + 13, y=y - 25),
        x=x + 14,
        y=y - 24,
    )
    for i, (name, data_type, value) in enumerate(
        (
            (".shatter_arm", "FLOAT_VECTOR", arm),
            (".shatter_normal", "FLOAT_VECTOR", normal),
            (".shatter_surface", "FLOAT_VECTOR", pick(moving_b, moving_a, 26)),
            (
                ".shatter_approach",
                "FLOAT",
                t.vmath("DOT_PRODUCT", relative, normal, x=x + 12, y=y - 14),
            ),
            (".shatter_depth", "FLOAT", t.math("MULTIPLY", pushed, touching, x=x + 14, y=y - 8)),
            (".shatter_touching", "FLOAT", touching),
            (".shatter_slide", "FLOAT_VECTOR", slide),
            (".shatter_shared", "FLOAT", shared),
            (".shatter_pair", "FLOAT", 1.0),
            (".shatter_wake", "FLOAT", wake),
            (".shatter_other", "INT", pick(b, a, 28, False)),
            (".shatter_point", "FLOAT_VECTOR", point),
        )
    ):
        contacts = t.store(contacts, name, data_type, value, x + 15 + i * 0.5, y)
    return contacts


def moved_surface(t, bodies, contacts, x, y):
    """Contacts with the velocity of the other piece at their point, after the move"""
    other = t.attribute(".shatter_other", "INT", x, y - 1)
    point = t.attribute(".shatter_point", "FLOAT_VECTOR", x, y - 2)
    position = t.node("GeometryNodeInputPosition", x, y - 3).outputs[0]

    def of(name, data_type, yy):
        value = position if name is None else t.attribute(name, data_type, x + 1, y - yy)
        return sample(t, bodies, value, other, data_type, x + 2, y - yy)

    arm = t.vmath("SUBTRACT", point, of(None, "FLOAT_VECTOR", 3), x=x + 3, y=y - 3)
    spin = t.vmath("CROSS_PRODUCT", of(".shatter_spin", "FLOAT_VECTOR", 4), arm, x=x + 4, y=y - 3)
    surface = t.vmath("ADD", of(".shatter_velocity", "FLOAT_VECTOR", 5), spin, x=x + 5, y=y - 4)
    return t.store(contacts, ".shatter_surface", "FLOAT_VECTOR", surface, x + 6, y)


def step(t, bodies, hull, planes, colliders, inputs, dt, x, y):
    """Bodies moved by the gravity over the substeps, their hull points pushed out of the floor
    and the Colliders by the rigid move of each piece fitting its contacts, as XPBD"""
    h = t.math("DIVIDE", dt, inputs["Substeps"], x=x, y=y - 2)
    # Normal and velocity of the Colliders closest to the hull points at the start of the frame
    fields = Hull(t, bodies, x - 6, y - 12)
    _, point = fields.point(None, ".shatter_rotation")
    normal = t.node("GeometryNodeInputNormal", x - 3, y - 13).outputs[0]
    surface = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x - 3, y - 14)
    normal = nearest(t, colliders, normal, "FLOAT_VECTOR", point, x - 2, y - 13)[0]
    surface = nearest(t, colliders, surface, "FLOAT_VECTOR", point, x - 2, y - 14)[0]
    hull = t.store(hull, ".shatter_side", "FLOAT_VECTOR", normal, x - 1, y - 10)
    hull = t.store(hull, ".shatter_surface", "FLOAT_VECTOR", surface, x - 0.5, y - 10)
    # Awake unless still for a while
    still = t.attribute(".shatter_still", "INT", x - 6, y - 50)
    awake = t.math(
        "MULTIPLY",
        t.attribute(".shatter_loose", "FLOAT", x - 6, y - 51),
        t.math("LESS_THAN", still, SLEEP_FRAMES, x=x - 5, y=y - 50),
        x=x - 4,
        y=y - 50,
    )
    bodies = t.store(bodies, ".shatter_awake", "FLOAT", awake, x - 3, y - 48)
    bodies = t.store(bodies, ".shatter_was_awake", "FLOAT", awake, x - 2.5, y - 48)
    bodies = t.store(bodies, ".shatter_impact", "FLOAT", 0.0, x - 2, y - 48)
    # Contacts between the pieces to check in the frame
    found, found_bodies = pairs(t, bodies, hull, planes, inputs, dt, x - 80, y - 40)
    enabled = inputs["Piece Collisions"]
    found = switch(t, enabled, None, found, "GEOMETRY", x - 1, y - 30)
    bodies = switch(t, enabled, bodies, found_bodies, "GEOMETRY", x - 1, y - 28)
    steps_in = t.node("GeometryNodeRepeatInput", x + 1, y, {"Iterations": inputs["Substeps"]})
    steps_out = t.node("GeometryNodeRepeatOutput", x + 90, y)
    steps_in.pair_with_output(steps_out)
    t.connect(bodies, steps_in.inputs["Geometry"])
    bodies = steps_in.outputs["Geometry"]
    position = t.node("GeometryNodeInputPosition", x + 1, y - 2).outputs[0]
    rotation = t.attribute(".shatter_rotation", "QUATERNION", x + 1, y - 3)
    loose = t.attribute(".shatter_awake", "FLOAT", x + 1, y - 4)
    moving = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 1, y - 5)
    spin = t.attribute(".shatter_spin", "FLOAT_VECTOR", x + 1, y - 6)
    first = t.attribute(".shatter_first", "INT", x + 1, y - 7)
    pair_first = t.attribute(".shatter_pair_first", "INT", x + 1, y - 8)

    # Predicted pose
    bodies = t.store(bodies, ".shatter_prev", "FLOAT_VECTOR", position, x + 2, y)
    bodies = t.store(bodies, ".shatter_prev_rotation", "QUATERNION", rotation, x + 3, y)
    gravity = t.vmath(
        "SCALE", inputs["Gravity"], t.math("MULTIPLY", h, loose, x=x + 2, y=y - 9), x=x + 3, y=y - 8
    )
    drag = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", inputs["Drag"], h, x=x + 2, y=y - 10),
        x=x + 3,
        y=y - 10,
        clamp=True,
    )
    moving = t.vmath(
        "SCALE", t.vmath("ADD", moving, gravity, x=x + 4, y=y - 5), drag, x=x + 5, y=y - 5
    )
    bodies = t.store(bodies, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 6, y)
    step_scale = t.math("MULTIPLY", h, loose, x=x + 6, y=y - 7)
    bodies = t.node(
        "GeometryNodeSetPosition",
        x + 7,
        y,
        {"Geometry": bodies, "Offset": t.vmath("SCALE", moving, step_scale, x=x + 7, y=y - 5)},
    ).outputs[0]
    bodies = t.store(
        bodies,
        ".shatter_rotation",
        "QUATERNION",
        turned(t, rotation, spin, step_scale, x + 7, y - 6),
        x + 10,
        y,
    )

    # Positions: out of the surfaces, without sliding while the friction holds
    hull = contacts(t, bodies, hull, colliders, inputs, h, x + 11, y - 12)
    found = pair_contacts(t, bodies, found, inputs, h, x + 11, y - 40)
    sources = ((hull, first), (found, pair_first))
    # Halved where the other piece moves too
    share = t.math(
        "SUBTRACT", 1.0, t.attribute(".shatter_shared", "FLOAT", x + 30, y - 7), x=x + 31, y=y - 7
    )
    normal = t.attribute(".shatter_normal", "FLOAT_VECTOR", x + 30, y - 2)
    touching = t.attribute(".shatter_touching", "FLOAT", x + 30, y - 3)
    depth = t.attribute(".shatter_depth", "FLOAT", x + 30, y - 4)
    slide = t.attribute(".shatter_slide", "FLOAT_VECTOR", x + 30, y - 5)
    sticking = t.math(
        "LESS_THAN",
        t.vmath("LENGTH", slide, x=x + 31, y=y - 5),
        t.math("MULTIPLY", depth, inputs["Friction"], x=x + 31, y=y - 6),
        x=x + 32,
        y=y - 5,
    )
    sticking = t.math("MULTIPLY", sticking, touching, x=x + 33, y=y - 5)
    # Between pieces only pushing apart: holding the other piece, it would resist the moves both
    # pieces make together, as each piece is solved with the other where it was
    pair = t.attribute(".shatter_pair", "FLOAT", x + 32, y - 7)
    sticking = t.math(
        "MULTIPLY", sticking, t.math("SUBTRACT", 1.0, pair, x=x + 33, y=y - 7), x=x + 34, y=y - 5
    )

    def stuck(vector, xx, yy):
        """Normal part of the vector at the touching points, all of it where they stick"""
        normal_part = t.vmath(
            "SCALE",
            normal,
            t.vmath("DOT_PRODUCT", normal, vector, x=xx, y=yy - 0.5),
            x=xx + 0.5,
            y=yy - 0.5,
        )
        part = t.vmath(
            "ADD",
            t.vmath(
                "SCALE",
                normal_part,
                t.math("SUBTRACT", touching, sticking, x=xx, y=yy - 1),
                x=xx + 1,
                y=yy - 0.5,
            ),
            t.vmath("SCALE", vector, sticking, x=xx + 0.5, y=yy),
            x=xx + 1.5,
            y=yy,
        )
        return part

    target = t.vmath(
        "SUBTRACT", t.vmath("SCALE", normal, depth, x=x + 33, y=y - 2), slide, x=x + 34, y=y - 2
    )
    target = t.vmath("SCALE", target, share, x=x + 34.5, y=y - 2)
    move, turn = rigid_solve(t, sources, stuck, target, x + 35, y - 20)
    bodies = t.node(
        "GeometryNodeSetPosition",
        x + 56,
        y,
        {"Geometry": bodies, "Offset": t.vmath("SCALE", move, loose, x=x + 55, y=y - 2)},
    ).outputs[0]
    rotation = turned(t, rotation, turn, loose, x + 55, y - 6)
    bodies = t.store(bodies, ".shatter_rotation", "QUATERNION", rotation, x + 58, y)
    # Out of the floor, the other pieces pushing down from above
    fields = Hull(t, bodies, x + 58, y - 40)
    _, point = fields.point(None, ".shatter_rotation")
    lowest = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 59,
        y - 42,
        {
            "Value": socket(
                t.node("ShaderNodeSeparateXYZ", x + 58, y - 43, {0: point}).outputs, "Z"
            ),
            "Group ID": t.attribute(".shatter_piece", "INT", x + 58, y - 44),
        },
        data_type="FLOAT",
    ).outputs["Min"]
    lowest = sample(t, hull, lowest, first, "FLOAT", x + 60, y - 42)
    lift = t.math("SUBTRACT", inputs["Floor"], lowest, x=x + 61, y=y - 42)
    lift = t.math(
        "MULTIPLY", t.math("MAXIMUM", lift, 0.0, x=x + 62, y=y - 42), loose, x=x + 63, y=y - 42
    )
    lift = t.node("ShaderNodeCombineXYZ", x + 63, y - 43, {"Z": lift}).outputs[0]
    bodies = t.node(
        "GeometryNodeSetPosition", x + 64, y - 40, {"Geometry": bodies, "Offset": lift}
    ).outputs[0]
    # Without speed, not to throw the pieces up
    before = t.vmath(
        "ADD",
        t.attribute(".shatter_prev", "FLOAT_VECTOR", x + 64, y - 44),
        lift,
        x=x + 65,
        y=y - 43,
    )
    bodies = t.store(bodies, ".shatter_prev", "FLOAT_VECTOR", before, x + 65, y - 40)

    # Velocities from the moves
    inverse = t.math("DIVIDE", 1.0, h, x=x + 58, y=y - 3)
    moved = t.vmath(
        "SUBTRACT",
        position,
        t.attribute(".shatter_prev", "FLOAT_VECTOR", x + 58, y - 4),
        x=x + 59,
        y=y - 4,
    )
    moved = t.vmath("SCALE", moved, inverse, x=x + 60, y=y - 4)
    bodies = t.store(bodies, ".shatter_velocity", "FLOAT_VECTOR", moved, x + 60, y)
    change = t.node(
        "FunctionNodeRotateRotation",
        x + 59,
        y - 8,
        {
            "Rotation": t.node(
                "FunctionNodeInvertRotation",
                x + 58,
                y - 9,
                {0: t.attribute(".shatter_prev_rotation", "QUATERNION", x + 57, y - 9)},
            ).outputs[0],
            "Rotate By": rotation,
        },
        rotation_space="GLOBAL",
    ).outputs[0]
    change = t.node("FunctionNodeRotationToAxisAngle", x + 60, y - 8, {0: change}).outputs
    spin = t.vmath(
        "SCALE",
        change["Axis"],
        t.math("MULTIPLY", change["Angle"], inverse, x=x + 60, y=y - 10),
        x=x + 61,
        y=y - 8,
    )
    bodies = t.store(bodies, ".shatter_spin", "FLOAT_VECTOR", spin, x + 61, y)

    # Bounce and sliding friction on the velocities of the touching points, the other pieces
    # moved too
    found = moved_surface(t, bodies, found, x + 61, y - 40)
    sources = ((hull, first), (found, pair_first))
    fields = Hull(t, bodies, x + 62, y - 12)
    arm = t.attribute(".shatter_arm", "FLOAT_VECTOR", x + 62, y - 14)
    relative = t.vmath(
        "SUBTRACT",
        fields.velocity(arm),
        t.attribute(".shatter_surface", "FLOAT_VECTOR", x + 64, y - 14),
        x=x + 66,
        y=y - 13,
    )
    approach = t.attribute(".shatter_approach", "FLOAT", x + 64, y - 16)
    speed = t.vmath("DOT_PRODUCT", relative, normal, x=x + 67, y=y - 13)
    resting = t.math(
        "MULTIPLY",
        t.vmath("LENGTH", inputs["Gravity"], x=x + 64, y=y - 17),
        t.math("MULTIPLY", h, -2.0, x=x + 64, y=y - 18),
        x=x + 65,
        y=y - 17,
    )
    bounce = t.math(
        "MAXIMUM",
        t.math(
            "MULTIPLY",
            approach,
            t.math(
                "MULTIPLY",
                inputs["Bounce"],
                t.math(
                    "SUBTRACT",
                    t.math(
                        "DIVIDE",
                        fields.body(".shatter_radius", "FLOAT"),
                        t.math("MAXIMUM", inputs["Heavy Size"], 1e-6, x=x + 63, y=y - 21),
                        x=x + 64,
                        y=y - 20,
                    ),
                    1.0,
                    x=x + 64.5,
                    y=y - 20,
                    clamp=True,
                ),
                x=x + 65,
                y=y - 19,
            ),
            x=x + 66,
            y=y - 18,
        ),
        0.0,
        x=x + 67,
        y=y - 18,
    )
    bounce = t.math(
        "MULTIPLY",
        bounce,
        t.math("LESS_THAN", approach, resting, x=x + 66, y=y - 17),
        x=x + 68,
        y=y - 17,
    )
    across = t.vmath(
        "SUBTRACT",
        relative,
        t.vmath("SCALE", normal, speed, x=x + 67, y=y - 12),
        x=x + 68,
        y=y - 12,
    )
    sliding = t.vmath("LENGTH", across, x=x + 69, y=y - 12)
    # Slowed by the friction of the normal speed removed by the push out
    friction = t.math(
        "MINIMUM",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", depth, inverse, x=x + 68, y=y - 22),
            inputs["Friction"],
            x=x + 69,
            y=y - 22,
        ),
        sliding,
        x=x + 70,
        y=y - 12,
    )
    friction = t.math(
        "DIVIDE", friction, t.math("MAXIMUM", sliding, 1e-9, x=x + 70, y=y - 13), x=x + 71, y=y - 12
    )
    target = t.vmath(
        "SUBTRACT",
        t.vmath(
            "SCALE",
            normal,
            t.math("SUBTRACT", bounce, speed, x=x + 69, y=y - 14),
            x=x + 70,
            y=y - 14,
        ),
        t.vmath("SCALE", across, friction, x=x + 72, y=y - 12),
        x=x + 73,
        y=y - 13,
    )

    # Between pieces only along the normal, the friction as an impulse after: as a target it
    # would hold their moves together
    def touching_part(vector, xx, yy):
        along = t.vmath(
            "SCALE",
            normal,
            t.math(
                "MULTIPLY",
                t.vmath("DOT_PRODUCT", normal, vector, x=xx, y=yy - 1),
                pair,
                x=xx + 0.3,
                y=yy - 1,
            ),
            x=xx + 0.6,
            y=yy - 1,
        )
        part = t.vmath(
            "MULTIPLY_ADD",
            vector,
            t.math("SUBTRACT", 1.0, pair, x=xx, y=yy - 3),
            along,
            x=xx + 1,
            y=yy,
        )
        return t.vmath("SCALE", part, touching, x=xx + 1.5, y=yy)

    target = t.vmath("SCALE", target, share, x=x + 73.5, y=y - 13)
    impulse, twist = rigid_solve(t, sources, touching_part, target, x + 74, y - 20)
    moving = t.vmath(
        "ADD",
        t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 87, y - 2),
        t.vmath("SCALE", impulse, loose, x=x + 87, y=y - 3),
        x=x + 88,
        y=y - 2,
    )
    spin = t.vmath(
        "ADD",
        t.attribute(".shatter_spin", "FLOAT_VECTOR", x + 87, y - 5),
        t.vmath("SCALE", twist, loose, x=x + 87, y=y - 6),
        x=x + 88,
        y=y - 5,
    )
    # Friction between pieces, the mean impulse slowing the sliding of their touching points
    rubbing = t.math("MULTIPLY", touching, pair, x=x + 75, y=y - 30)
    slowing = t.vmath(
        "SCALE",
        across,
        t.math(
            "DIVIDE",
            t.math(
                "MULTIPLY",
                t.math("MULTIPLY", friction, share, x=x + 75, y=y - 31),
                rubbing,
                x=x + 76,
                y=y - 31,
            ),
            resistance(
                t,
                arm,
                fields.body(".shatter_inertia", "FLOAT"),
                t.vmath("NORMALIZE", across, x=x + 75, y=y - 33),
                x + 76,
                y - 33,
            ),
            x=x + 80,
            y=y - 31,
        ),
        x=x + 81,
        y=y - 30,
    )
    slowing = t.vmath("SCALE", slowing, -1.0, x=x + 82, y=y - 30)

    def pair_total(value, data_type, yy):
        summed = t.node(
            "GeometryNodeAccumulateField",
            x + 83,
            y - yy,
            {"Value": value, "Group ID": t.attribute(".shatter_piece", "INT", x + 82, y - yy - 1)},
            data_type=data_type,
        ).outputs["Total"]
        return sample(t, found, summed, pair_first, data_type, x + 84, y - yy)

    count = pair_total(rubbing, "FLOAT", 32)
    rubbed = t.math(
        "DIVIDE", loose, t.math("MAXIMUM", count, 1.0, x=x + 85, y=y - 32), x=x + 86, y=y - 32
    )
    slowed = t.vmath("SCALE", pair_total(slowing, "FLOAT_VECTOR", 30), rubbed, x=x + 86, y=y - 30)
    moving = t.vmath("ADD", moving, slowed, x=x + 87, y=y - 30)
    twisting = pair_total(
        t.vmath("CROSS_PRODUCT", arm, slowing, x=x + 82, y=y - 34), "FLOAT_VECTOR", 34
    )
    twisting = t.vmath(
        "DIVIDE",
        t.vmath("SCALE", twisting, rubbed, x=x + 86, y=y - 34),
        t.attribute(".shatter_inertia", "FLOAT", x + 86, y - 35),
        x=x + 87,
        y=y - 34,
    )
    spin = t.vmath("ADD", spin, twisting, x=x + 88, y=y - 34)
    # Resting when touching and slow, as the friction between pieces only slows their sliding
    fastest = t.math(
        "MULTIPLY_ADD",
        t.vmath("LENGTH", spin, x=x + 88, y=y - 38),
        t.attribute(".shatter_radius", "FLOAT", x + 88, y - 39),
        t.vmath("LENGTH", moving, x=x + 88, y=y - 37),
        x=x + 89,
        y=y - 37,
    )
    touched = t.node(
        "GeometryNodeAccumulateField",
        x + 86,
        y - 40,
        {
            "Value": t.attribute(".shatter_touching", "FLOAT", x + 85, y - 40),
            "Group ID": t.attribute(".shatter_piece", "INT", x + 85, y - 41),
        },
        data_type="FLOAT",
    ).outputs["Total"]
    touched = t.math(
        "ADD", count, sample(t, hull, touched, first, "FLOAT", x + 87, y - 40), x=x + 89, y=y - 40
    )
    moving_on = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "MULTIPLY",
            t.math("GREATER_THAN", touched, 0.5, x=x + 90, y=y - 40),
            t.math("LESS_THAN", fastest, REST_SPEED, x=x + 90, y=y - 37),
            x=x + 91,
            y=y - 38,
        ),
        x=x + 92,
        y=y - 38,
    )
    moving = t.vmath("SCALE", moving, moving_on, x=x + 92, y=y - 30)
    spin = t.vmath("SCALE", spin, moving_on, x=x + 92, y=y - 34)
    bodies = t.store(bodies, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 88, y)
    bodies = t.store(bodies, ".shatter_spin", "FLOAT_VECTOR", spin, x + 89, y)
    hit = t.node(
        "GeometryNodeAccumulateField",
        x + 86,
        y - 8,
        {
            "Value": t.attribute(".shatter_hit", "FLOAT", x + 85, y - 8),
            "Group ID": t.attribute(".shatter_piece", "INT", x + 85, y - 9),
        },
        data_type="FLOAT",
    ).outputs["Total"]
    hit = t.math(
        "GREATER_THAN", sample(t, hull, hit, first, "FLOAT", x + 87, y - 8), 0.5, x=x + 88, y=y - 8
    )
    # Not the ones anchored on the floor, as the ground
    hit = t.math(
        "MULTIPLY",
        hit,
        t.math(
            "SUBTRACT",
            1.0,
            t.attribute(".shatter_anchored", "FLOAT", x + 87, y - 10),
            x=x + 88,
            y=y - 10,
        ),
        x=x + 88.5,
        y=y - 8,
    )
    stays = t.attribute(".shatter_loose", "FLOAT", x + 88, y - 9)
    bodies = t.store(
        bodies,
        ".shatter_loose",
        "FLOAT",
        t.math("MAXIMUM", stays, hit, x=x + 89, y=y - 9),
        x + 89.5,
        y,
    )
    wake = t.node(
        "GeometryNodeAccumulateField",
        x + 86,
        y - 11,
        {
            "Value": t.attribute(".shatter_wake", "FLOAT", x + 85, y - 11),
            "Group ID": t.attribute(".shatter_piece", "INT", x + 85, y - 12),
        },
        data_type="FLOAT",
    ).outputs["Total"]
    wake = t.math(
        "ADD",
        sample(t, hull, wake, first, "FLOAT", x + 87, y - 11),
        sample(t, found, wake, pair_first, "FLOAT", x + 87, y - 12),
        x=x + 88,
        y=y - 11,
    )
    wake = t.math(
        "MAXIMUM", hit, t.math("GREATER_THAN", wake, 0.5, x=x + 88, y=y - 12), x=x + 89, y=y - 11
    )
    wake = t.math(
        "MULTIPLY", wake, t.attribute(".shatter_loose", "FLOAT", x + 88, y - 13), x=x + 89, y=y - 12
    )
    bodies = t.store(
        bodies,
        ".shatter_awake",
        "FLOAT",
        t.math("MAXIMUM", loose, wake, x=x + 90, y=y - 11),
        x + 90,
        y,
    )
    # Hardest hit by the floor or the Colliders in the frame, for the breakup
    hit = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.attribute(".shatter_approach", "FLOAT", x + 85, y - 15),
            -1.0,
            x=x + 86,
            y=y - 15,
        ),
        t.attribute(".shatter_touching", "FLOAT", x + 85, y - 16),
        x=x + 87,
        y=y - 15,
    )
    hit = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 88,
        y - 15,
        {"Value": hit, "Group ID": t.attribute(".shatter_piece", "INT", x + 87, y - 16)},
        data_type="FLOAT",
    ).outputs["Max"]
    hit = t.math(
        "MAXIMUM",
        t.attribute(".shatter_impact", "FLOAT", x + 89, y - 16),
        sample(t, hull, hit, first, "FLOAT", x + 89, y - 15),
        x=x + 90,
        y=y - 15,
    )
    bodies = t.store(bodies, ".shatter_impact", "FLOAT", hit, x + 91, y)
    t.connect(bodies, steps_out.inputs["Geometry"])

    # Frames still: near where the piece was at the start of the count, which restarts when it
    # leaves or is woken, the slow rocking of a balanced piece counting as still
    bodies = steps_out.outputs["Geometry"]
    position = t.node("GeometryNodeInputPosition", x + 91, y - 2).outputs[0]
    rotation = t.attribute(".shatter_rotation", "QUATERNION", x + 91, y - 3)
    anchor = t.attribute(".shatter_anchor", "FLOAT_VECTOR", x + 91, y - 4)
    anchor_rotation = t.attribute(".shatter_anchor_rotation", "QUATERNION", x + 91, y - 5)
    moved = t.vmath("DISTANCE", position, anchor, x=x + 92, y=y - 4)
    turn = t.node(
        "FunctionNodeRotateRotation",
        x + 92,
        y - 5,
        {
            "Rotation": t.node(
                "FunctionNodeInvertRotation", x + 91.5, y - 6, {0: anchor_rotation}
            ).outputs[0],
            "Rotate By": rotation,
        },
        rotation_space="GLOBAL",
    ).outputs[0]
    turn = t.node("FunctionNodeRotationToAxisAngle", x + 93, y - 5, {0: turn}).outputs["Angle"]
    near = t.math(
        "MULTIPLY",
        t.math(
            "LESS_THAN",
            moved,
            t.math(
                "MULTIPLY",
                t.attribute(".shatter_radius", "FLOAT", x + 92, y - 7),
                SLEEP_DRIFT,
                x=x + 93,
                y=y - 7,
            ),
            x=x + 94,
            y=y - 4,
        ),
        t.math("LESS_THAN", turn, SLEEP_TURN, x=x + 94, y=y - 5),
        x=x + 95,
        y=y - 4,
    )
    woken = t.math(
        "GREATER_THAN",
        t.attribute(".shatter_awake", "FLOAT", x + 93, y - 8),
        t.attribute(".shatter_was_awake", "FLOAT", x + 93, y - 9),
        x=x + 94,
        y=y - 8,
    )
    near = t.math(
        "MULTIPLY", near, t.math("SUBTRACT", 1.0, woken, x=x + 95, y=y - 8), x=x + 96, y=y - 4
    )
    still = t.math(
        "MULTIPLY",
        t.math("ADD", t.attribute(".shatter_still", "INT", x + 95, y - 3), 1, x=x + 96, y=y - 3),
        near,
        x=x + 97,
        y=y - 3,
    )
    bodies = t.store(bodies, ".shatter_still", "INT", still, x + 97, y)
    bodies = t.store(
        bodies,
        ".shatter_anchor",
        "FLOAT_VECTOR",
        switch(t, near, position, anchor, "VECTOR", x + 97, y - 4),
        x + 98,
        y,
    )
    anchor_rotation = switch(t, near, rotation, anchor_rotation, "ROTATION", x + 97, y - 5)
    return t.store(bodies, ".shatter_anchor_rotation", "QUATERNION", anchor_rotation, x + 99, y)


def cuts(t, pieces, bodies, x, y):
    """The pieces where they are with the inner faces of the ones just loose selected, the area
    of all the inner faces, and the velocity, spin and center of the piece on its points"""
    index = t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]
    position = t.node("GeometryNodeInputPosition", x, y - 3).outputs[0]
    bodies = t.store(bodies, ".shatter_center", "FLOAT_VECTOR", position, x + 1, y)
    bodies = t.store(bodies, ".shatter_body", "INT", index, x + 1.5, y)
    placed = t.node(
        "GeometryNodeInstanceOnPoints",
        x + 2,
        y,
        {
            "Points": bodies,
            "Instance": pieces,
            "Pick Instance": True,
            "Instance Index": index,
            "Rotation": t.attribute(".shatter_rotation", "QUATERNION", x + 1, y - 4),
        },
    ).outputs[0]
    placed = t.node("GeometryNodeRealizeInstances", x + 3, y, {"Geometry": placed}).outputs[0]
    material = t.node("GeometryNodeInputMaterialIndex", x + 3, y - 2).outputs[0]
    placed = t.store(placed, ".shatter_material", "INT", material, x + 4, y, domain="FACE")
    inner = t.attribute(".shatter_inner", "BOOLEAN", x + 3, y - 3)
    selection = t.node(
        "FunctionNodeBooleanMath",
        x + 4,
        y - 3,
        {0: inner, 1: shedding(t, x + 3, y - 4)},
        operation="AND",
    ).outputs[0]
    area = t.node("GeometryNodeInputMeshFaceArea", x + 4, y - 5).outputs[0]
    area = statistic(t, placed, area, inner, "FLOAT", x + 5, y - 5, "FACE")["Sum"]
    return placed, selection, t.math("MAXIMUM", area, 1e-6, x=x + 6, y=y - 5)


def shedding(t, x, y):
    """Whether the piece is loose and did not shed its debris and dust yet"""
    return t.math(
        "GREATER_THAN",
        t.math(
            "SUBTRACT",
            t.attribute(".shatter_loose", "FLOAT", x, y),
            t.attribute(".shatter_shed", "FLOAT", x, y - 1),
            x=x + 0.5,
            y=y,
        ),
        0.5,
        x=x + 1,
        y=y,
    )


def scattered(t, placed, selection, area, amount, seed, x, y):
    """Points on the cuts, with the velocity of their piece there"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    points = t.node(
        "GeometryNodeDistributePointsOnFaces",
        x + 1,
        y,
        {
            "Mesh": placed,
            "Selection": selection,
            "Density": t.math("DIVIDE", amount, area, x=x, y=y - 3),
            "Seed": t.math(
                "ADD",
                seed,
                t.node("GeometryNodeInputSceneTime", x - 1, y - 5).outputs["Frame"],
                x=x,
                y=y - 4,
            ),
        },
        distribute_method="RANDOM",
    ).outputs
    points = t.store(points["Points"], ".shatter_out", "FLOAT_VECTOR", points["Normal"], x + 1.5, y)
    center = t.attribute(".shatter_center", "FLOAT_VECTOR", x + 1, y - 4)
    spin = t.vmath(
        "CROSS_PRODUCT",
        t.attribute(".shatter_spin", "FLOAT_VECTOR", x + 2, y - 6),
        t.vmath("SUBTRACT", position, center, x=x + 2, y=y - 4),
        x=x + 3,
        y=y - 5,
    )
    moving = t.vmath(
        "ADD",
        t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 2, y - 5),
        spin,
        x=x + 4,
        y=y - 5,
    )
    return t.store(points, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 4, y)


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


def emit_debris(t, placed, selection, area, push, inputs, x, y):
    """Chips on the cuts of the loose pieces, with the velocity of their piece and a scatter,
    spinning, as flat stones of different sizes"""
    random = randomized(t, inputs, x + 8, y - 8)
    chips = scattered(t, placed, selection, area, inputs["Debris Amount"], inputs["Seed"], x, y)
    # Thrown out of the cut, up by the Debris Rise, faster for the smaller ones
    shrink = random(0.4, 1.0, 15, 19, "FLOAT")
    speed = t.math(
        "MULTIPLY_ADD",
        t.vmath("LENGTH", push, x=x + 10, y=y - 11),
        inputs["Debris Speed"],
        0.5,
        x=x + 11,
        y=y - 11,
    )
    speed = t.math("DIVIDE", speed, t.math("SQRT", shrink, x=x + 11, y=y - 12), x=x + 12, y=y - 11)
    away = t.vmath(
        "ADD",
        t.attribute(".shatter_out", "FLOAT_VECTOR", x + 9, y - 13),
        t.vmath("SCALE", random((-1, -1, -1), (1, 1, 1), 11, 12), 0.7, x=x + 10, y=y - 12),
        x=x + 11,
        y=y - 13,
    )
    up = t.node("ShaderNodeCombineXYZ", x + 10, y - 14, {"Z": inputs["Debris Rise"]}).outputs[0]
    away = t.vmath("NORMALIZE", t.vmath("ADD", away, up, x=x + 12, y=y - 13), x=x + 13, y=y - 13)
    moving = t.vmath(
        "ADD",
        t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 12, y - 9),
        t.vmath("SCALE", away, speed, x=x + 13, y=y - 11),
        x=x + 14,
        y=y - 9,
    )
    chips = t.store(chips, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 13, y)
    spin = random((-30, -30, -30), (30, 30, 30), 12, 14)
    chips = t.store(chips, ".shatter_spin", "FLOAT_VECTOR", spin, x + 14, y)
    rotation = t.node(
        "FunctionNodeEulerToRotation",
        x + 10,
        y - 16,
        {0: random((0, 0, 0), (6.3, 6.3, 6.3), 13, 16)},
    ).outputs[0]
    chips = t.store(chips, ".shatter_rotation", "QUATERNION", rotation, x + 15, y)
    size = t.math("MULTIPLY", shrink, inputs["Debris Size"], x=x + 10, y=y - 19)
    scale = t.vmath(
        "MULTIPLY", random((1.0, 0.5, 0.25), (1.0, 1.0, 0.6), 14, 18), size, x=x + 11, y=y - 18
    )
    return t.store(chips, ".shatter_scale", "FLOAT_VECTOR", scale, x + 16, y)


def debris_step(t, debris, colliders, inputs, dt, x, y):
    """Chips moved by the gravity over the substeps, out of the Colliders and bouncing on the
    floor, resting there"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    h = t.math("DIVIDE", dt, inputs["Substeps"], x=x, y=y - 3)
    steps_in = t.node("GeometryNodeRepeatInput", x + 1, y, {"Iterations": inputs["Substeps"]})
    steps_out = t.node("GeometryNodeRepeatOutput", x + 30, y)
    steps_in.pair_with_output(steps_out)
    t.connect(debris, steps_in.inputs["Geometry"])
    debris = steps_in.outputs["Geometry"]
    scale = t.attribute(".shatter_scale", "FLOAT_VECTOR", x + 1, y - 4)
    turn = t.attribute(".shatter_rotation", "QUATERNION", x + 1, y - 5)

    def extent(direction, xx, yy):
        """Reach of the chip along the direction, from its center"""
        local = inverse_rotate(t, direction, turn, xx, yy)
        return t.vmath("LENGTH", t.vmath("MULTIPLY", local, scale, x=xx + 2, y=yy), x=xx + 3, y=yy)

    moving = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 1, y - 2)
    gravity = t.vmath("SCALE", inputs["Gravity"], h, x=x + 2, y=y - 3)
    moving = t.vmath("ADD", moving, gravity, x=x + 3, y=y - 2)
    drag = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", inputs["Drag"], h, x=x + 3, y=y - 4),
        x=x + 4,
        y=y - 4,
        clamp=True,
    )
    moving = t.vmath("SCALE", moving, drag, x=x + 4, y=y - 2)
    point = t.vmath(
        "ADD", position, t.vmath("SCALE", moving, h, x=x + 4, y=y - 5), x=x + 5, y=y - 2
    )

    # Out of the Colliders, bouncing off them
    closest = t.node(
        "GeometryNodeProximity", x + 6, y - 6, {"Geometry": colliders, "Sample Position": point}
    ).outputs
    normal = nearest(
        t,
        colliders,
        t.node("GeometryNodeInputNormal", x + 5, y - 8).outputs[0],
        "FLOAT_VECTOR",
        point,
        x + 6,
        y - 8,
    )[0]
    size = extent(normal, x + 6, y - 14)
    signed = t.vmath(
        "DOT_PRODUCT",
        t.vmath("SUBTRACT", point, closest["Position"], x=x + 7, y=y - 6),
        normal,
        x=x + 8,
        y=y - 6,
    )
    reach = t.math(
        "MULTIPLY_ADD",
        t.vmath("LENGTH", moving, x=x + 7, y=y - 9),
        t.math("MULTIPLY", h, -2.0, x=x + 7, y=y - 10),
        t.math("MULTIPLY", size, -1.0, x=x + 7, y=y - 11),
        x=x + 8,
        y=y - 9,
    )
    inside = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            closest["Is Valid"],
            t.math("LESS_THAN", signed, size, x=x + 9, y=y - 7),
            x=x + 10,
            y=y - 7,
        ),
        t.math("GREATER_THAN", signed, reach, x=x + 9, y=y - 9),
        x=x + 11,
        y=y - 7,
    )
    point = t.vmath(
        "ADD",
        point,
        t.vmath(
            "SCALE",
            normal,
            t.math(
                "MULTIPLY",
                t.math("SUBTRACT", size, signed, x=x + 10, y=y - 6),
                inside,
                x=x + 11,
                y=y - 6,
            ),
            x=x + 12,
            y=y - 6,
        ),
        x=x + 13,
        y=y - 5,
    )
    approach = t.math(
        "MINIMUM",
        t.vmath("DOT_PRODUCT", moving, normal, x=x + 10, y=y - 12),
        0.0,
        x=x + 11,
        y=y - 12,
    )
    bounce = t.math("ADD", inputs["Bounce"], 1.0, x=x + 11, y=y - 13)
    moving = t.vmath(
        "SUBTRACT",
        moving,
        t.vmath(
            "SCALE",
            normal,
            t.math(
                "MULTIPLY",
                t.math("MULTIPLY", approach, bounce, x=x + 12, y=y - 12),
                inside,
                x=x + 13,
                y=y - 12,
            ),
            x=x + 14,
            y=y - 12,
        ),
        x=x + 15,
        y=y - 2,
    )

    # Bouncing on the floor, sliding to a stop
    xyz = t.node("ShaderNodeSeparateXYZ", x + 14, y - 5, {0: point}).outputs
    floor = t.math(
        "ADD", inputs["Floor"], extent((0.0, 0.0, 1.0), x + 12, y - 16), x=x + 14, y=y - 7
    )
    on_floor = t.math("LESS_THAN", socket(xyz, "Z"), floor, x=x + 15, y=y - 7)
    point = t.node(
        "ShaderNodeCombineXYZ",
        x + 16,
        y - 5,
        {
            0: socket(xyz, "X"),
            1: socket(xyz, "Y"),
            2: t.math("MAXIMUM", socket(xyz, "Z"), floor, x=x + 15, y=y - 6),
        },
    ).outputs[0]
    velocity = t.node("ShaderNodeSeparateXYZ", x + 16, y - 9, {0: moving}).outputs
    falling = t.math("LESS_THAN", socket(velocity, "Z"), 0.0, x=x + 17, y=y - 10)
    rising = t.math(
        "MULTIPLY",
        socket(velocity, "Z"),
        t.math("MULTIPLY", inputs["Bounce"], -1.0, x=x + 17, y=y - 12),
        x=x + 18,
        y=y - 11,
    )
    flip = t.math("MULTIPLY", on_floor, falling, x=x + 18, y=y - 10)
    up = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", rising, socket(velocity, "Z"), x=x + 19, y=y - 11),
        flip,
        socket(velocity, "Z"),
        x=x + 20,
        y=y - 10,
    )
    grip = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "MULTIPLY",
            on_floor,
            t.math(
                "MULTIPLY",
                inputs["Friction"],
                t.math("MULTIPLY", h, 20.0, x=x + 18, y=y - 14),
                x=x + 19,
                y=y - 14,
            ),
            x=x + 20,
            y=y - 14,
        ),
        x=x + 21,
        y=y - 14,
        clamp=True,
    )
    moving = t.node(
        "ShaderNodeCombineXYZ",
        x + 22,
        y - 9,
        {
            0: t.math("MULTIPLY", socket(velocity, "X"), grip, x=x + 21, y=y - 8),
            1: t.math("MULTIPLY", socket(velocity, "Y"), grip, x=x + 21, y=y - 9),
            2: up,
        },
    ).outputs[0]
    # Resting when slow on the floor
    still = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "MULTIPLY",
            on_floor,
            t.math(
                "LESS_THAN", t.vmath("LENGTH", moving, x=x + 22, y=y - 11), 0.05, x=x + 23, y=y - 11
            ),
            x=x + 24,
            y=y - 11,
        ),
        x=x + 25,
        y=y - 11,
    )
    moving = t.vmath("SCALE", moving, still, x=x + 25, y=y - 9)
    spin = t.attribute(".shatter_spin", "FLOAT_VECTOR", x + 22, y - 16)
    spin = t.vmath(
        "SCALE",
        spin,
        t.math(
            "MULTIPLY",
            still,
            t.math(
                "SUBTRACT",
                1.0,
                t.math("MULTIPLY", on_floor, 0.3, x=x + 23, y=y - 17),
                x=x + 24,
                y=y - 17,
            ),
            x=x + 25,
            y=y - 17,
        ),
        x=x + 26,
        y=y - 16,
    )
    debris = t.node(
        "GeometryNodeSetPosition", x + 26, y, {"Geometry": debris, "Position": point}
    ).outputs[0]
    debris = t.store(debris, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 27, y)
    debris = t.store(debris, ".shatter_spin", "FLOAT_VECTOR", spin, x + 28, y)
    rotation = turned(
        t, t.attribute(".shatter_rotation", "QUATERNION", x + 26, y - 18), spin, h, x + 26, y - 18
    )
    debris = t.store(debris, ".shatter_rotation", "QUATERNION", rotation, x + 29, y)
    t.connect(debris, steps_out.inputs["Geometry"])
    return steps_out.outputs["Geometry"]


def emit_smoke(t, placed, selection, area, push, inputs, x, y):
    """Puffs of dust blown out of the cuts, with a part of the velocity of their piece"""
    random = randomized(t, inputs, x + 5, y - 8)
    seed = t.math("ADD", inputs["Seed"], 20, x=x, y=y - 1)
    puff = scattered(t, placed, selection, area, inputs["Smoke Amount"], seed, x, y)
    # Out of the cuts, as the debris
    direction = t.vmath(
        "ADD",
        t.attribute(".shatter_out", "FLOAT_VECTOR", x + 5, y - 7),
        t.vmath("SCALE", random((-1, -1, -1), (1, 1, 1), 21, 0), 0.7, x=x + 6, y=y - 8),
        x=x + 7,
        y=y - 7,
    )
    direction = t.vmath("NORMALIZE", direction, x=x + 7, y=y - 8)
    speed = t.math("MULTIPLY", t.vmath("LENGTH", push, x=x + 6, y=y - 10), 0.4, x=x + 7, y=y - 10)
    # Most near the cut, some blown far, not as a shell
    burst = t.math("POWER", random(0.2, 1.0, 24, 3, "FLOAT"), 2.0, x=x + 7, y=y - 12)
    speed = t.math("MULTIPLY", speed, burst, x=x + 8, y=y - 10)
    carried = t.vmath(
        "SCALE",
        t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 6, y - 11),
        0.3,
        x=x + 7,
        y=y - 11,
    )
    moving = t.vmath(
        "ADD", carried, t.vmath("SCALE", direction, speed, x=x + 8, y=y - 9), x=x + 9, y=y - 9
    )
    puff = t.store(puff, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 9, y)
    life = t.math(
        "MULTIPLY", random(0.6, 1.4, 23, 2, "FLOAT"), inputs["Smoke Lifetime"], x=x + 8, y=y - 12
    )
    puff = t.store(puff, ".shatter_life", "FLOAT", life, x + 10, y)
    return t.store(puff, ".shatter_age", "FLOAT", 0.0, x + 11, y)


def smoke_step(t, smoke, inputs, dt, x, y):
    """Puffs slowed by the air and rising with it, spreading along the floor they reach, kept
    while their dust is there"""
    position = t.node("GeometryNodeInputPosition", x, y - 6).outputs[0]
    moving = t.attribute(".shatter_velocity", "FLOAT_VECTOR", x, y - 1)
    up = t.node("ShaderNodeCombineXYZ", x, y - 3, {"Z": inputs["Smoke Rise"]}).outputs[0]
    drag = t.math("MULTIPLY", dt, 2.0, x=x, y=y - 4, clamp=True)
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
    # On the floor, the speed down turned along it
    xyz = t.node("ShaderNodeSeparateXYZ", x + 4, y - 7, {0: point}).outputs
    landed = t.math("LESS_THAN", socket(xyz, "Z"), inputs["Floor"], x=x + 5, y=y - 7)
    velocity = t.node("ShaderNodeSeparateXYZ", x + 4, y - 9, {0: moving}).outputs
    along = t.node(
        "ShaderNodeCombineXYZ", x + 5, y - 9, {0: socket(velocity, "X"), 1: socket(velocity, "Y")}
    ).outputs[0]
    scatter = socket(
        t.node(
            "FunctionNodeRandomValue",
            x + 4,
            y - 11,
            {"Min": (-1, -1, 0), "Max": (1, 1, 0), "Seed": inputs["Seed"]},
            data_type="FLOAT_VECTOR",
        ).outputs,
        "Value",
    )
    away = t.vmath(
        "NORMALIZE", t.vmath("ADD", along, scatter, x=x + 6, y=y - 10), x=x + 7, y=y - 10
    )
    fall = t.math(
        "ABSOLUTE",
        t.math("MINIMUM", socket(velocity, "Z"), 0.0, x=x + 5, y=y - 12),
        x=x + 6,
        y=y - 12,
    )
    spread = t.vmath(
        "ADD", along, t.vmath("SCALE", away, fall, x=x + 8, y=y - 11), x=x + 9, y=y - 10
    )
    moving = switch(t, landed, moving, spread, "VECTOR", x + 10, y - 2)
    point = t.node(
        "ShaderNodeCombineXYZ",
        x + 6,
        y - 6,
        {
            0: socket(xyz, "X"),
            1: socket(xyz, "Y"),
            2: t.math("MAXIMUM", socket(xyz, "Z"), inputs["Floor"], x=x + 5, y=y - 8),
        },
    ).outputs[0]
    smoke = t.store(smoke, ".shatter_velocity", "FLOAT_VECTOR", moving, x + 11, y)
    smoke = t.node(
        "GeometryNodeSetPosition", x + 12, y, {"Geometry": smoke, "Position": point}
    ).outputs[0]
    age = t.math("ADD", t.attribute(".shatter_age", "FLOAT", x + 12, y - 3), dt, x=x + 13, y=y - 3)
    smoke = t.store(smoke, ".shatter_age", "FLOAT", age, x + 13, y)
    old = t.math(
        "GREATER_THAN",
        t.attribute(".shatter_age", "FLOAT", x + 13, y - 4),
        t.math(
            "MULTIPLY", t.attribute(".shatter_life", "FLOAT", x + 13, y - 5), 3.0, x=x + 14, y=y - 5
        ),
        x=x + 15,
        y=y - 4,
    )
    return t.node(
        "GeometryNodeDeleteGeometry", x + 16, y, {"Geometry": smoke, "Selection": old}
    ).outputs[0]


def smoke_solver(t, dust, puffs, debris, inputs, dt, x, y):
    """Dust carried by the air rising and swirling as the curl of a noise, fed by the young
    puffs over their life and the flying debris, fading over its lifetime, on a grid around them
    and the dust"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    size = inputs["Smoke Size"]
    # The flying debris trailing dust
    flying = t.node(
        "GeometryNodeDeleteGeometry",
        x - 4,
        y - 9,
        {
            "Geometry": debris,
            "Selection": t.math(
                "LESS_THAN",
                t.vmath(
                    "LENGTH",
                    t.attribute(".shatter_velocity", "FLOAT_VECTOR", x - 6, y - 10),
                    x=x - 5,
                    y=y - 10,
                ),
                1.0,
                x=x - 5,
                y=y - 9,
            ),
        },
    ).outputs[0]
    movers = t.node("GeometryNodeJoinGeometry", x - 1, y - 9)
    t.connect(flying, movers.inputs[0])
    t.connect(puffs, movers.inputs[0])
    movers = movers.outputs[0]
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
    t.connect(movers, around.inputs[0])
    bounds = t.node("GeometryNodeBoundBox", x + 1, y - 4, {"Geometry": around.outputs[0]}).outputs
    margin = t.math("MULTIPLY", size, 2.0, x=x + 1, y=y - 6)
    low = t.vmath("SUBTRACT", bounds["Min"], margin, x=x + 2, y=y - 4)
    extent = t.vmath(
        "SUBTRACT", t.vmath("ADD", bounds["Max"], margin, x=x + 2, y=y - 5), low, x=x + 3, y=y - 5
    )
    # Cubic voxels, at most MAX_CELLS along each side
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
        t.math("DIVIDE", largest, MAX_CELLS, x=x + 5, y=y - 8),
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

    # Air: eddies about twice the size of the puffs, turning at the Smoke Swirl, rising
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
        inputs["Smoke Swirl"],
        t.math("MULTIPLY", eddy, 0.25, x=x + 11, y=y - 11),
        x=x + 12,
        y=y - 10,
    )
    air = t.vmath("SCALE", sampled(curl, "VECTOR", x + 13, y - 8), swirl, x=x + 14, y=y - 8)
    # Slowing down on the floor, settling there
    height = socket(t.node("ShaderNodeSeparateXYZ", x + 12, y - 15, {0: position}).outputs, "Z")
    landing = t.math(
        "DIVIDE",
        t.math("SUBTRACT", height, inputs["Floor"], x=x + 13, y=y - 15),
        t.math("MULTIPLY", size, 2.0, x=x + 13, y=y - 16),
        x=x + 14,
        y=y - 15,
        clamp=True,
    )
    up = t.node(
        "ShaderNodeCombineXYZ",
        x + 14,
        y - 10,
        {"Z": t.math("MULTIPLY", inputs["Smoke Rise"], landing, x=x + 14, y=y - 11)},
    ).outputs[0]
    air = t.vmath("ADD", air, up, x=x + 15, y=y - 8)
    # Blown by the puffs and the debris near them
    closest = t.node(
        "GeometryNodeSampleNearest",
        x + 12,
        y - 12,
        {"Geometry": movers, "Sample Position": position},
    ).outputs[0]
    puff = sample(t, movers, position, closest, "FLOAT_VECTOR", x + 13, y - 12)
    blown = sample(
        t,
        movers,
        t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 12, y - 13),
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

    # Carried and fading, fed by the puffs in the first half of their life
    carried = t.node(
        "GeometryNodeGridAdvect",
        x + 17,
        y - 13,
        # Less diffusing than the default, not to blur the dust in a ball
        {"Grid": old, "Velocity": air, "Time Step": dt, "Integration Scheme": "MacCormack"},
        data_type="FLOAT",
    ).outputs[0]
    # Thinning from the top of the dust, over half the Smoke Lifetime there and one and a half
    # at the bottom
    top = t.node("GeometryNodeBoundBox", x + 14, y - 17, {"Geometry": dense}).outputs
    top = [
        socket(t.node("ShaderNodeSeparateXYZ", x + 15, y - 17 - i, {0: top[name]}).outputs, "Z")
        for i, name in enumerate(("Min", "Max"))
    ]
    above = t.math(
        "DIVIDE",
        t.math("SUBTRACT", height, top[0], x=x + 16, y=y - 17),
        t.math(
            "MAXIMUM",
            t.math("SUBTRACT", top[1], top[0], x=x + 16, y=y - 18),
            1e-3,
            x=x + 17,
            y=y - 18,
        ),
        x=x + 17,
        y=y - 17,
        clamp=True,
    )
    fade = t.math(
        "EXPONENT",
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", dt, -1.0, x=x + 16, y=y - 15),
            t.math(
                "MULTIPLY",
                inputs["Smoke Lifetime"],
                t.math("SUBTRACT", 1.5, above, x=x + 17, y=y - 16),
                x=x + 18,
                y=y - 16,
            ),
            x=x + 17,
            y=y - 15,
        ),
        x=x + 18,
        y=y - 15,
    )
    life = t.math(
        "DIVIDE",
        t.attribute(".shatter_age", "FLOAT", x + 8, y - 17),
        t.attribute(".shatter_life", "FLOAT", x + 8, y - 18),
        x=x + 9,
        y=y - 17,
    )
    young = t.node(
        "GeometryNodeDeleteGeometry",
        x + 10,
        y - 16,
        {"Geometry": puffs, "Selection": t.math("GREATER_THAN", life, 1.0, x=x + 10, y=y - 17)},
    ).outputs[0]
    # With a puff of no size, for the grid to exist without young puffs
    dummy = t.node(
        "GeometryNodePoints", x + 9, y - 19, {"Count": 1, "Position": low, "Radius": 0.0}
    ).outputs[0]
    dummy = t.store(dummy, ".shatter_life", "FLOAT", -1.0, x + 10, y - 19)
    joined = t.node("GeometryNodeJoinGeometry", x + 11, y - 16)
    t.connect(dummy, joined.inputs[0])
    t.connect(young, joined.inputs[0])
    young = joined.outputs[0]
    # Feeding less and less as the puffs age
    radius = t.math("MULTIPLY_ADD", life, -0.7, 1.0, x=x + 10, y=y - 18)
    # At least a voxel, else the grid misses them
    radius = t.math(
        "MAXIMUM",
        t.math("MULTIPLY", radius, size, x=x + 11, y=y - 17),
        voxel,
        x=x + 11,
        y=y - 18,
    )
    real = t.attribute(".shatter_life", "FLOAT", x + 10, y - 20)
    radius = t.math(
        "MULTIPLY",
        radius,
        t.math("GREATER_THAN", real, 0.0, x=x + 11, y=y - 20),
        x=x + 12,
        y=y - 18,
    )
    source = t.node(
        "GeometryNodePointsToVolume",
        x + 12,
        y - 16,
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
        y - 16,
        {"Volume": source, "Name": "density"},
        data_type="FLOAT",
    ).outputs["Grid"]
    # Streaks along the way of the debris over the frame, fed more
    streaks = t.node(
        "GeometryNodeDuplicateElements", x + 10, y - 22, {"Geometry": flying, "Amount": 3}
    ).outputs
    back = t.vmath(
        "SCALE",
        t.attribute(".shatter_velocity", "FLOAT_VECTOR", x + 10, y - 24),
        t.math(
            "MULTIPLY",
            dt,
            t.math("DIVIDE", streaks["Duplicate Index"], -3.0, x=x + 10, y=y - 25),
            x=x + 11,
            y=y - 25,
        ),
        x=x + 12,
        y=y - 24,
    )
    streaks = t.node(
        "GeometryNodeSetPosition", x + 12, y - 22, {"Geometry": streaks["Geometry"], "Offset": back}
    ).outputs[0]
    with_dummy = t.node("GeometryNodeJoinGeometry", x + 12.5, y - 21)
    t.connect(dummy, with_dummy.inputs[0])
    t.connect(streaks, with_dummy.inputs[0])
    trails = t.node(
        "GeometryNodePointsToVolume",
        x + 13,
        y - 22,
        {
            "Points": with_dummy.outputs[0],
            "Density": 1.5,
            "Resolution Mode": "Size",
            "Voxel Size": voxel,
            "Radius": t.math(
                "MULTIPLY",
                t.math(
                    "MAXIMUM",
                    t.math("MULTIPLY", size, 0.5, x=x + 12, y=y - 26),
                    voxel,
                    x=x + 13,
                    y=y - 26,
                ),
                t.math(
                    "GREATER_THAN",
                    t.attribute(".shatter_life", "FLOAT", x + 12, y - 27),
                    -0.5,
                    x=x + 13,
                    y=y - 27,
                ),
                x=x + 14,
                y=y - 26,
            ),
        },
    ).outputs[0]
    trails = t.node(
        "GeometryNodeGetNamedGrid",
        x + 14,
        y - 22,
        {"Volume": trails, "Name": "density"},
        data_type="FLOAT",
    ).outputs["Grid"]
    feed = t.math("MULTIPLY", dt, 4.0, x=x + 14, y=y - 18)
    density = t.math(
        "MULTIPLY_ADD",
        t.math(
            "ADD",
            sampled(source, "FLOAT", x + 15, y - 16),
            sampled(trails, "FLOAT", x + 15, y - 22),
            x=x + 16,
            y=y - 18,
        ),
        feed,
        t.math("MULTIPLY", sampled(carried, "FLOAT", x + 18, y - 13), fade, x=x + 19, y=y - 13),
        x=x + 20,
        y=y - 14,
    )
    density = t.math("MINIMUM", density, 1.0, x=x + 21, y=y - 14)
    # Not under the floor
    above = t.math(
        "GREATER_THAN",
        socket(t.node("ShaderNodeSeparateXYZ", x + 20, y - 16, {0: position}).outputs, "Z"),
        inputs["Floor"],
        x=x + 21,
        y=y - 16,
    )
    density = t.math("MULTIPLY", density, above, x=x + 21.5, y=y - 14)
    density = to_grid(density, "FLOAT", "Density", x + 22, y - 14)
    # Without the faded cells, not to grow the grid
    density = t.node(
        "GeometryNodeGridPrune",
        x + 23.5,
        y - 14,
        {"Grid": density, "Mode": "Threshold", "Threshold": 0.005},
        data_type="FLOAT",
    ).outputs[0]
    volume = t.node(
        "GeometryNodeVolumeCube",
        x + 23,
        y - 12,
        {"Resolution X": 2, "Resolution Y": 2, "Resolution Z": 2},
    ).outputs[0]
    volume = t.node(
        "GeometryNodeGetNamedGrid",
        x + 24,
        y - 12,
        {"Volume": volume, "Name": "density", "Remove": True},
        data_type="FLOAT",
    ).outputs["Volume"]
    return t.node(
        "GeometryNodeStoreNamedGrid",
        x + 25,
        y - 12,
        {"Volume": volume, "Name": "density", "Grid": density},
        data_type="FLOAT",
    ).outputs[0]


def rendered(t, dust, size, x, y):
    """Dust billowing by a noise slowly changing, blurred for soft edges, with the coordinates in
    Smoke Size for the details of the material"""
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
    coordinates = t.vmath("DIVIDE", position, size, x=x + 1, y=y - 4)
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
    grids = t.node("GeometryNodeFieldToGrid", x + 3.5, y - 3, {"Topology": grid["Grid"]})
    grids.grid_items.new("FLOAT", "Density")
    grids.grid_items.new("VECTOR", "Rest")
    t.connect(billows, grids.inputs["Density"])
    t.connect(coordinates, grids.inputs["Rest"])
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
    return t.node(
        "GeometryNodeStoreNamedGrid",
        x + 6,
        y,
        {"Volume": volume, "Name": "rest", "Grid": grids.outputs["Rest"]},
        data_type="VECTOR_FLOAT",
    ).outputs[0]


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.description = "Shatter the mesh into pieces where the Colliders or the floor hit it"
    add_output(ng, "Geometry", "NodeSocketGeometry")
    build_inputs(ng)

    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -12, 0).outputs
    self_object = t.node("GeometryNodeSelfObject", -12, -2).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -11, -2, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", -10, -2, {0: to_world}).outputs[0]
    index = t.node("GeometryNodeInputIndex", 40, -4).outputs[0]

    t.section("World Space", row=True)
    mesh = t.node(
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
    for name in (
        "Colliders",
        "Pieces",
        "Bodies",
        "Hull",
        "Planes",
        "Debris",
        "Smoke",
        "Dust",
        "Support",
    ):
        sim_out.state_items.new("GEOMETRY", name)
    sim_out.state_items.new("BOOLEAN", "Broken")
    t.connect(positions(t, mesh, -8, 0), sim_in.inputs["Geometry"])
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
    dt = t.math("MULTIPLY", dt, inputs["Time Scale"], x=-4, y=-4)
    mesh = velocity(t, mesh, sim_in.outputs["Geometry"], dt, -5, 2)
    colliders = velocity(t, colliders, sim_in.outputs["Colliders"], dt, -5, -6)
    t.connect(positions(t, colliders, -1, -6), sim_out.inputs["Colliders"])
    was_broken = sim_in.outputs["Broken"]

    t.section("Impact", row=True)
    # Only the Colliders that can reach the mesh
    bounds = t.node("GeometryNodeBoundBox", -2, -4, {"Geometry": mesh}).outputs
    speed = t.vmath("LENGTH", t.attribute(".shatter_velocity", "FLOAT_VECTOR", -3, -5), x=-2, y=-5)
    speed = statistic(t, mesh, speed, True, "FLOAT", -1, -5)["Max"]
    near = crop(t, colliders, bounds["Min"], bounds["Max"], speed, dt, inputs["Margin"], -1, -2)
    hit, impact, push = detect(t, mesh, near, inputs, dt, 0, 0)
    hit = t.math("MULTIPLY", hit, started, x=17, y=-1)
    # Only checked until the mesh breaks
    breaking = switch(t, was_broken, hit, False, "BOOLEAN", 17, 0)

    t.section("Fracture", row=True)
    each = fracture(t, mesh, impact, inputs, 0, 0)
    pieces, bodies, hull, planes = bodies_of(t, each, mesh, impact, push, inputs, 27, 0)
    bodies = anchored(t, bodies, hull, mesh, inputs, 45, 0)
    bodies_new = bodies

    t.section("State", row=True)
    state = {}
    for i, (name, new) in enumerate(
        (("Pieces", pieces), ("Bodies", bodies), ("Hull", hull), ("Planes", planes))
    ):
        state[name] = switch(t, breaking, sim_in.outputs[name], new, "GEOMETRY", 0, -i)
    broken = t.node(
        "FunctionNodeBooleanMath", 0, -4, {0: was_broken, 1: breaking}, operation="OR"
    ).outputs[0]
    t.connect(broken, sim_out.inputs["Broken"])
    # Not kept once broken
    t.connect(
        switch(t, broken, positions(t, mesh, -2, -6), None, "GEOMETRY", 0, -6),
        sim_out.inputs["Geometry"],
    )

    t.section("Physics", row=True)
    # Only the Colliders that can reach the pieces
    bodies = state["Bodies"]
    bounds = t.node("GeometryNodeBoundBox", -4, -4, {"Geometry": bodies}).outputs
    radius = statistic(
        t, bodies, t.attribute(".shatter_radius", "FLOAT", -4, -6), True, "FLOAT", -3, -6
    )["Max"]
    low = t.vmath("SUBTRACT", bounds["Min"], radius, x=-2, y=-4)
    high = t.vmath("ADD", bounds["Max"], radius, x=-2, y=-5)
    speed = t.vmath("LENGTH", t.attribute(".shatter_velocity", "FLOAT_VECTOR", -4, -7), x=-3, y=-7)
    speed = statistic(t, bodies, speed, True, "FLOAT", -2, -7)["Max"]
    near = crop(t, colliders, low, high, speed, dt, inputs["Margin"], -1, -2)
    # Broken again where a Collider hits the still pieces
    *hit_again, again = rehit(
        t, bodies, state["Pieces"], state["Hull"], state["Planes"], near, inputs, dt, 2, -40
    )
    again = t.node(
        "FunctionNodeBooleanMath", 92, -40, {0: again, 1: was_broken}, operation="AND"
    ).outputs[0]
    for name, broken_again in zip(("Bodies", "Pieces", "Hull", "Planes"), hit_again, strict=True):
        state[name] = switch(t, again, state[name], broken_again, "GEOMETRY", 93, -40)
    # The support between the pieces where they broke, at the break or again
    support = sim_in.outputs["Support"]
    for i, (now, new_pieces, new_bodies) in enumerate(
        (
            (again, state["Pieces"], state["Bodies"]),
            (breaking, pieces, bodies_new),
        )
    ):
        placed = cuts(t, new_pieces, new_bodies, 94, -44 - i * 4)[0]
        graph = support_graph(t, placed, new_bodies, 98, -44 - i * 4)
        support = switch(t, now, support, graph, "GEOMETRY", 114, -44 - i * 4)
    support = switch(t, inputs["Floor Support"], None, support, "GEOMETRY", 115, -44)
    t.connect(support, sim_out.inputs["Support"])
    bodies = step(t, state["Bodies"], state["Hull"], state["Planes"], near, inputs, dt, 0, 0)
    *broken_up, any_breaking = breakup(t, bodies, state["Pieces"], inputs, 42, -12)
    final = {}
    splitting = t.node(
        "FunctionNodeBooleanMath",
        79,
        -14,
        {0: inputs["Breakup"], 1: any_breaking},
        operation="AND",
    ).outputs[0]
    for i, (name, kept, split) in enumerate(
        zip(
            ("Bodies", "Pieces", "Hull", "Planes"),
            (bodies, state["Pieces"], state["Hull"], state["Planes"]),
            broken_up,
            strict=True,
        )
    ):
        geometry = switch(t, splitting, kept, split, "GEOMETRY", 80, -i)
        if name == "Bodies":
            # Falling where not held anymore
            holding = t.node(
                "FunctionNodeBooleanMath",
                81,
                -2,
                {0: inputs["Floor Support"], 1: broken},
                operation="AND",
            ).outputs[0]
            geometry = switch(
                t, holding, geometry, supported(t, geometry, support, 82, -4), "GEOMETRY", 85, 0
            )
            geometry = switch(t, broken, state["Bodies"], geometry, "GEOMETRY", 86, 0)
        final[name] = geometry

    t.section("Debris and Smoke", row=True)
    # Out of the pieces as they get loose, at the break, not held anymore or broken up
    placed, selection, area = cuts(t, final["Pieces"], final["Bodies"], -6, 0)
    any_shedding = statistic(t, final["Bodies"], shedding(t, -4, -8), True, "FLOAT", -2, -8)
    any_shedding = t.math("GREATER_THAN", any_shedding["Max"], 0.5, x=-1, y=-8)
    # The push of the Colliders only at the break
    push = t.vmath("SCALE", push, breaking, x=-1, y=-10)
    for i, (name, emitted) in enumerate(
        (
            ("Debris", emit_debris(t, placed, selection, area, push, inputs, 0, 0)),
            ("Smoke", emit_smoke(t, placed, selection, area, push, inputs, 0, -24)),
        )
    ):
        joined = t.node("GeometryNodeJoinGeometry", 18, -i * 24)
        t.connect(sim_in.outputs[name], joined.inputs[0])
        t.connect(switch(t, any_shedding, None, emitted, "GEOMETRY", 17, -i * 24), joined.inputs[0])
        final[name] = switch(t, inputs[name], None, joined.outputs[0], "GEOMETRY", 19, -i * 24)
    debris = debris_step(t, final["Debris"], near, inputs, dt, 20, 0)
    t.connect(debris, sim_out.inputs["Debris"])
    smoke = smoke_step(t, final["Smoke"], inputs, dt, 20, -24)
    t.connect(smoke, sim_out.inputs["Smoke"])
    dust = smoke_solver(t, sim_in.outputs["Dust"], smoke, debris, inputs, dt, 30, -24)
    # Only once broken
    smoking = t.node(
        "FunctionNodeBooleanMath", 59, -26, {0: inputs["Smoke"], 1: broken}, operation="AND"
    ).outputs[0]
    t.connect(switch(t, smoking, None, dust, "GEOMETRY", 60, -24), sim_out.inputs["Dust"])
    final["Bodies"] = t.store(
        final["Bodies"],
        ".shatter_shed",
        "FLOAT",
        t.attribute(".shatter_loose", "FLOAT", 60, -2),
        61,
        0,
    )
    for name in ("Bodies", "Pieces", "Hull", "Planes"):
        t.connect(final[name], sim_out.inputs[name])

    t.section("Output", row=True)
    rotation = t.attribute(".shatter_rotation", "QUATERNION", 41, -2)
    pieces = t.node(
        "GeometryNodeInstanceOnPoints",
        42,
        0,
        {
            "Points": sim_out.outputs["Bodies"],
            "Instance": sim_out.outputs["Pieces"],
            "Pick Instance": True,
            "Instance Index": index,
            "Rotation": rotation,
        },
    ).outputs[0]
    pieces = t.node("GeometryNodeRealizeInstances", 43, 0, {"Geometry": pieces}).outputs[0]
    # Chips as flat stones with the material of the faces they come from: after the pieces,
    # linked last, for the materials of the pieces to keep their indices
    stone = t.node("GeometryNodeMeshIcoSphere", 42, -4, {"Radius": 1.0, "Subdivisions": 1}).outputs[
        0
    ]
    stone = t.store(stone, ".shatter_chip", "BOOLEAN", True, 42.5, -4, domain="FACE")
    stone = t.node(
        "GeometryNodeSetShadeSmooth", 43, -4, {"Mesh": stone, "Shade Smooth": False}
    ).outputs[0]
    chips = t.node(
        "GeometryNodeInstanceOnPoints",
        43.5,
        -3,
        {
            "Points": sim_out.outputs["Debris"],
            "Instance": stone,
            "Rotation": t.attribute(".shatter_rotation", "QUATERNION", 43, -5),
            "Scale": t.attribute(".shatter_scale", "FLOAT_VECTOR", 43, -6),
        },
    ).outputs[0]
    chips = t.node("GeometryNodeRealizeInstances", 44, -3, {"Geometry": chips}).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 44.5, 0)
    t.connect(chips, joined.inputs[0])
    t.connect(pieces, joined.inputs[0])
    pieces = t.node(
        "GeometryNodeSetMaterialIndex",
        44.7,
        0,
        {
            "Geometry": joined.outputs[0],
            "Selection": t.attribute(".shatter_chip", "BOOLEAN", 44.5, -2),
            "Material Index": t.attribute(".shatter_material", "INT", 44.5, -3),
        },
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeTransform",
        44,
        0,
        {"Geometry": pieces, "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeRemoveAttribute",
        45,
        0,
        {"Geometry": pieces, "Pattern Mode": "Wildcard", "Name": ".shatter_*"},
    ).outputs[0]
    smoke = t.node(
        "GeometryNodeTransform",
        45,
        -8,
        {
            "Geometry": t.node(
                "GeometryNodeSetMaterial",
                44,
                -8,
                {
                    "Geometry": switch(
                        t,
                        inputs["Smoke"],
                        None,
                        rendered(t, sim_out.outputs["Dust"], inputs["Smoke Size"], 43, -10),
                        "GEOMETRY",
                        43.8,
                        -8,
                    ),
                    "Material": inputs["Smoke Material"],
                },
            ).outputs[0],
            "Mode": "Matrix",
            "Transform": to_local,
        },
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 45.5, 0)
    t.connect(smoke, joined.inputs[0])
    t.connect(pieces, joined.inputs[0])
    pieces = joined.outputs[0]
    output = switch(t, sim_out.outputs["Broken"], inputs["Geometry"], pieces, "GEOMETRY", 46, 0)
    t.node("NodeGroupOutput", 47, 0, {0: output})
    t.arrange()
    return ng


def build_dust_material():
    """Grey dust, its shape from the grid, finer wisps by a noise moving with it"""
    material = bpy.data.materials.new(DUST)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))
    density = t.node("ShaderNodeAttribute", -1000, 0, attribute_name="density").outputs["Fac"]
    # In Smoke Size, for the details to scale with the dust
    space = t.node("ShaderNodeAttribute", -1000, -200, attribute_name="rest").outputs["Vector"]
    noise = t.node(
        "ShaderNodeTexNoise",
        -800,
        -200,
        {"Vector": space, "Scale": 4.0, "Detail": 4.0, "Roughness": 0.6},
    ).outputs["Fac"]
    wisps = t.node("ShaderNodeMapRange", -550, -200, {0: noise, 1: 0.3, 2: 0.6}, clamp=True)
    density = t.math("MULTIPLY", density, wisps.outputs[0], x=-300, y=0)
    density = t.math("MULTIPLY", density, 5.0, x=-150, y=0)
    volume = t.node(
        "ShaderNodeVolumePrincipled",
        0,
        0,
        {
            "Color": (0.8, 0.77, 0.72, 1.0),
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
