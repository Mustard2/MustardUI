# Build billow_dust.blend: the Billow Dust node group, its dust and glass materials
# Usage: Blender --background --factory-startup --python billow_dust_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write
from dust_puff_build import (
    BOUNCE,
    CARRIED,
    FRICTION,
    REST_SPEED,
    SHRINK,
    along,
    contacts,
    grain_step,
    positions,
    sample,
    scattered,
    stored,
    surface,
    switch,
    thrown,
    velocity,
)

RESOURCE = "billow_dust.blend"
NODE_GROUP = "MustardUI Billow Dust"
DUST = "MustardUI Billow Dust Dust"
GLASS = "MustardUI Billow Dust Glass"
# Share of the direction of the puffs blown out off the mesh and spread along it
LIFT = 0.6
SPREAD = 0.7
# Slowing of the puffs by the air per second
AIR_DRAG = 2.5
# Most puffs and debris pieces, and the share of the room left for them blown out in a frame at
# most, at random over the hit, for a long hit to keep bursting
MAX_PUFFS = 300
MAX_DEBRIS = 3000
BUDGET = 0.15
# Size of the puffs when blown out, as a share of their grown Size
START = 0.15
# Share of their lifetime the puffs thin out in, at the end
FADE = 0.6
# Children of each puff on its outer side, and children of theirs, their distance and size as
# shares of the parent, pulled toward the way the parent goes
CHILDREN = 14
GRANDCHILDREN = 10
CHILD_DISTANCE = (0.8, 1.0)
CHILD_SIZE = (0.3, 0.5)
CHILD_PULL = 0.6
# Children leaning up, the billows boiling over the top
CHILD_LEAN = 0.6
# Detail of the billows per Size, and their speed of change
NOISE_SCALE = 1.8
NOISE_SPEED = 0.3
# Density of the dust per meter times the Size, as thick at any size
DENSITY = 30.0
# Steps toward the Sun the shade is summed over, their length as a share of the Size, the
# darkening per step through the dust and the light left in the deepest shade
SHADE_STEPS = 10
SHADE_STEP = 0.13
SHADE_DARKEN = 0.6
AMBIENT = 0.25
# Voxels of the fade grid per voxel of the dust
FADE_VOXELS = 4
# Most voxels of the dust, coarser for large clouds, and the volume of a puff with its children
# by its radius cubed
MAX_VOXELS = 1e7
PUFF_VOLUME = 22.4
# Turns of the debris per meter thrown per meter of their size
SPIN = 0.2


def build_inputs(ng):
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects bursting dust out of the mesh where they hit it, e.g. the body",
    )
    add_input(
        ng, "Start Frame", "NodeSocketInt", default_value=1, description="First simulated frame"
    )
    add_input(
        ng,
        "Amount",
        "NodeSocketFloat",
        default_value=300.0,
        min_value=0.0,
        description="Puffs of dust per square meter of the Colliders hitting the mesh at 1 m/s",
    )
    add_input(
        ng,
        "Min Speed",
        "NodeSocketFloat",
        default_value=0.3,
        min_value=0.0,
        description="Speed of the Colliders, in m/s, below which they burst nothing",
    )
    add_input(
        ng,
        "Scuff",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Share of the speed of the Colliders sliding on the mesh bursting dust",
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
        default_value=2.0,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the dust and the debris blown out, relative to the hit",
    )
    add_input(
        ng,
        "Floor",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0,
        description="Height of the floor stopping the dust and the debris, in world space",
    )
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the random puffs and debris")

    panel = ng.interface.new_panel("Dust")
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.1,
        min_value=0.001,
        description="Size of the puffs of dust when grown, with smaller billows on them",
    )
    add_input(
        ng,
        "Growth",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=0.16,
        min_value=0.01,
        description="Seconds the puffs take to grow to most of their Size",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=1.5,
        min_value=0.01,
        description="Seconds the dust lasts, in average, thinning out at the end",
    )
    add_input(
        ng,
        "Rise",
        "NodeSocketFloat",
        panel,
        default_value=0.09,
        description="Speed of the dust rising, in m/s, settling when negative",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        panel,
        default_value=24,
        min_value=4,
        max_value=100,
        description="Voxels of the dust along the Size, more for finer and slower dust",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        panel,
        default_value=(0.72, 0.7, 0.67, 1.0),
        description="Color of the dust",
    )
    add_input(
        ng,
        "Sun",
        "NodeSocketObject",
        panel,
        description="Light the dust is shaded away from, from right above without it",
    )
    add_input(
        ng,
        "Shade",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Darkening of the dust away from the Sun, for EEVEE. Cycles shades the dust "
        "itself, set it to 0 there",
    )
    add_input(
        ng,
        "Dust Material",
        "NodeSocketMaterial",
        panel,
        description="Volume material of the dust",
    ).default_value = bpy.data.materials.get(DUST)

    panel = ng.interface.new_panel("Debris", default_closed=True)
    add_input(
        ng,
        "Debris",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Glass shards and chips thrown out with the dust, the chips with the material "
        "of the mesh",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Debris Amount",
        "NodeSocketFloat",
        panel,
        default_value=4000.0,
        min_value=0.0,
        description="Pieces per square meter of the Colliders hitting the mesh at 1 m/s",
    )
    add_input(
        ng,
        "Debris Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.008,
        min_value=0.0001,
        description="Size of the pieces, in average",
    )
    add_input(
        ng,
        "Glass",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="Share of the pieces that are glass shards",
    )
    add_input(
        ng,
        "Debris Lifetime",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=4.0,
        min_value=0.01,
        description="Seconds the pieces stay, in average, shrinking away at the end",
    )
    add_input(
        ng,
        "Glass Material",
        "NodeSocketMaterial",
        panel,
        description="Material of the glass shards",
    ).default_value = bpy.data.materials.get(GLASS)


def identified(t, inputs, ident, salt, x, y):
    """Random values by the ident, the seed plus an offset of it and the salt"""

    def random(low, high, seed, yy, data_type="FLOAT_VECTOR"):
        seed = t.math(
            "ADD", t.math("ADD", inputs["Seed"], seed, x=x, y=y - yy), salt, x=x, y=y - yy
        )
        node = t.node(
            "FunctionNodeRandomValue",
            x + 1,
            y - yy,
            {"Min": low, "Max": high, "ID": ident, "Seed": seed},
            data_type=data_type,
        )
        return socket(node.outputs, "Value")

    return random


def emitting(t, x, y):
    """Random values different on each frame, by the index of the points"""
    index = t.node("GeometryNodeInputIndex", x, y).outputs[0]
    frame = t.node("GeometryNodeInputSceneTime", x, y - 1).outputs["Frame"]
    return index, t.math("MULTIPLY", frame, 101.0, x=x + 0.5, y=y - 1)


def limited(t, points, count, most, x, y):
    """The points within a share of the room left by those already there, at random"""
    room = t.math("SUBTRACT", most, count, x=x, y=y - 3)
    emitted = t.node("GeometryNodeAttributeDomainSize", x, y - 4, {"Geometry": points}).outputs[
        "Point Count"
    ]
    kept = t.node(
        "FunctionNodeRandomValue",
        x + 1,
        y - 3,
        {
            "Probability": t.math(
                "DIVIDE",
                t.math("MULTIPLY", room, BUDGET, x=x + 0.5, y=y - 3),
                t.math("MAXIMUM", emitted, 1.0, x=x + 0.5, y=y - 4),
                x=x + 1,
                y=y - 4,
            ),
            "Seed": t.node("GeometryNodeInputSceneTime", x, y - 5).outputs["Frame"],
        },
        data_type="BOOLEAN",
    )
    # Never past the most
    index = t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]
    past = t.math(
        "GREATER_THAN", index, t.math("SUBTRACT", room, 0.5, x=x + 1, y=y - 2), x=x + 1.5, y=y - 2
    )
    # Not kept or past it
    dropped = t.node(
        "FunctionNodeBooleanMath",
        x + 2,
        y - 2,
        {0: socket(kept.outputs, "Value"), 1: past},
        operation="IMPLY",
    ).outputs[0]
    return t.node(
        "GeometryNodeDeleteGeometry", x + 3, y, {"Geometry": points, "Selection": dropped}
    ).outputs[0]


def emit_puffs(t, near, count, inputs, x, y):
    """Puffs blown out of the mesh under the hitting patches, faster the harder they hit"""
    puffs = scattered(t, near, inputs["Amount"], 30, inputs, x, y)
    index, salt = emitting(t, x + 7, y - 20)
    random = identified(t, inputs, index, salt, x + 8, y - 8)
    direction = thrown(t, random, LIFT, SPREAD, 31, x + 8, y - 4)
    speed = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.attribute(".dust_hit", "FLOAT", x + 9, y - 11),
            inputs["Burst"],
            x=x + 10,
            y=y - 11,
        ),
        random(0.35, 1.0, 32, 2, "FLOAT"),
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
    size = random(0.7, 1.3, 33, 4, "FLOAT")
    # Off the mesh by their size when blown out
    lifted = t.vmath(
        "SCALE",
        t.attribute(".dust_normal", "FLOAT_VECTOR", x + 9, y - 16),
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", inputs["Size"], START, x=x + 9, y=y - 17),
            size,
            x=x + 10,
            y=y - 17,
        ),
        x=x + 11,
        y=y - 16,
    )
    puffs = t.node(
        "GeometryNodeSetPosition", x + 13, y, {"Geometry": puffs, "Offset": lifted}
    ).outputs[0]
    puffs = t.store(puffs, ".dust_velocity", "FLOAT_VECTOR", moving, x + 14, y)
    # Their children billowing out the way they go, and up
    axis = t.vmath(
        "NORMALIZE",
        t.vmath("ADD", direction, (0.0, 0.0, CHILD_LEAN), x=x + 13, y=y - 6),
        x=x + 14,
        y=y - 6,
    )
    puffs = t.store(puffs, ".dust_axis", "FLOAT_VECTOR", axis, x + 15, y)
    puffs = t.store(puffs, ".dust_size", "FLOAT", size, x + 16, y)
    puffs = t.store(puffs, ".dust_id", "INT", random(0, 1 << 30, 34, 6, "INT"), x + 17, y)
    life = t.math(
        "MULTIPLY", random(0.6, 1.4, 35, 8, "FLOAT"), inputs["Lifetime"], x=x + 16, y=y - 9
    )
    puffs = t.store(puffs, ".dust_life", "FLOAT", life, x + 18, y)
    puffs = t.store(puffs, ".dust_age", "FLOAT", 0.0, x + 19, y)
    return limited(t, puffs, count, MAX_PUFFS, x + 20, y)


def emit_debris(t, near, ground, count, inputs, x, y):
    """Glass shards and chips thrown out of the mesh under the hitting patches, the chips with the
    material of the mesh there"""
    debris = scattered(t, near, inputs["Debris Amount"], 40, inputs, x, y)
    index, salt = emitting(t, x + 7, y - 24)
    random = identified(t, inputs, index, salt, x + 8, y - 8)
    direction = thrown(
        t,
        random,
        t.math("ADD", 1.0, random(0.0, 1.0, 41, 6, "FLOAT"), x=x + 9, y=y - 3),
        0.5,
        42,
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
        random(0.3, 1.0, 43, 2, "FLOAT"),
        x=x + 11,
        y=y - 10,
    )
    debris = t.store(
        debris,
        ".dust_velocity",
        "FLOAT_VECTOR",
        t.vmath("SCALE", direction, speed, x=x + 12, y=y - 4),
        x + 13,
        y,
    )
    glass = t.math(
        "LESS_THAN", random(0.0, 1.0, 44, 4, "FLOAT"), inputs["Glass"], x=x + 10, y=y - 5
    )
    debris = t.store(debris, ".dust_glass", "BOOLEAN", glass, x + 14, y)
    # Flat shards and chunky chips, of random sizes and turns
    size = t.math(
        "MULTIPLY", random(0.5, 1.5, 45, 12, "FLOAT"), inputs["Debris Size"], x=x + 12, y=y - 12
    )
    shape = switch(
        t,
        glass,
        random((0.8, 0.8, 0.4), (1.2, 1.2, 0.8), 46, 14),
        random((0.6, 0.6, 0.05), (1.4, 1.4, 0.05), 47, 16),
        "VECTOR",
        x + 12,
        y - 14,
    )
    debris = t.store(
        debris,
        ".dust_scale",
        "FLOAT_VECTOR",
        t.vmath("SCALE", shape, size, x=x + 13, y=y - 12),
        x + 15,
        y,
    )
    debris = t.store(
        debris,
        ".dust_rotation",
        "QUATERNION",
        t.node(
            "FunctionNodeEulerToRotation",
            x + 14,
            y - 18,
            {0: random((0.0, 0.0, 0.0), (6.3, 6.3, 6.3), 48, 18)},
        ).outputs[0],
        x + 16,
        y,
    )
    # Smaller pieces turning faster
    spin = t.vmath(
        "SCALE",
        random((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), 49, 20),
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", speed, SPIN, x=x + 12, y=y - 21),
            size,
            x=x + 13,
            y=y - 21,
        ),
        x=x + 14,
        y=y - 20,
    )
    debris = t.store(debris, ".dust_spin", "FLOAT_VECTOR", spin, x + 17, y)
    material = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 16,
        y - 14,
        {
            "Mesh": ground,
            "Value": t.node("GeometryNodeInputMaterialIndex", x + 15, y - 15).outputs[0],
            "Sample Position": t.node("GeometryNodeInputPosition", x + 15, y - 16).outputs[0],
        },
        data_type="INT",
    ).outputs["Value"]
    debris = t.store(debris, ".dust_material", "INT", material, x + 18, y)
    life = t.math(
        "MULTIPLY", random(0.7, 1.3, 50, 22, "FLOAT"), inputs["Debris Lifetime"], x=x + 18, y=y - 12
    )
    debris = t.store(debris, ".dust_life", "FLOAT", life, x + 19, y)
    debris = t.store(debris, ".dust_age", "FLOAT", 0.0, x + 20, y)
    return limited(t, debris, count, MAX_DEBRIS, x + 21, y)


def rim(t, near, x, y):
    """The hitting faces on the border of their patches, where the dust gets out, not caught
    between the Colliders and the mesh pressed together"""
    border = t.node(
        "GeometryNodeFieldOnDomain",
        x + 1,
        y - 2,
        {
            0: t.math(
                "LESS_THAN",
                t.node("GeometryNodeInputMeshEdgeNeighbors", x, y - 2).outputs["Face Count"],
                1.5,
                x=x + 0.5,
                y=y - 2,
            )
        },
        domain="EDGE",
        data_type="FLOAT",
    ).outputs[0]
    # Of the faces, the share of their edges on the border
    return t.node(
        "GeometryNodeDeleteGeometry",
        x + 2,
        y,
        {"Geometry": near, "Selection": t.math("LESS_THAN", border, 0.01, x=x + 1.5, y=y - 2)},
        domain="FACE",
    ).outputs[0]


def outside(t, colliders, points, point, moving, margin, x, y):
    """The point and the speed moved out of the Colliders near the points"""
    box = t.node("GeometryNodeBoundBox", x, y - 2, {"Geometry": points}).outputs
    position = t.node("GeometryNodeInputPosition", x, y - 4).outputs[0]
    low = t.vmath(
        "SUBTRACT",
        position,
        t.vmath("SUBTRACT", box["Min"], margin, x=x + 1, y=y - 2),
        x=x + 2,
        y=y - 2,
    )
    high = t.vmath(
        "SUBTRACT", t.vmath("ADD", box["Max"], margin, x=x + 1, y=y - 3), position, x=x + 2, y=y - 3
    )
    xyz = t.node(
        "ShaderNodeSeparateXYZ", x + 3, y - 2, {0: t.vmath("MINIMUM", low, high, x=x + 3, y=y - 3)}
    ).outputs
    away = t.math(
        "LESS_THAN",
        t.math(
            "MINIMUM",
            t.math("MINIMUM", xyz["X"], xyz["Y"], x=x + 4, y=y - 2),
            xyz["Z"],
            x=x + 5,
            y=y - 2,
        ),
        0.0,
        x=x + 6,
        y=y - 2,
    )
    near = t.node(
        "GeometryNodeDeleteGeometry", x + 7, y, {"Geometry": colliders, "Selection": away}
    ).outputs[0]
    proximity = t.node(
        "GeometryNodeProximity",
        x + 8,
        y,
        {"Geometry": near, "Sample Position": point},
        target_element="FACES",
    ).outputs
    normal = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 8,
        y - 2,
        {
            "Mesh": near,
            "Value": t.node("GeometryNodeInputNormal", x + 7, y - 3).outputs["Normal"],
            "Sample Position": point,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    depth = t.vmath(
        "DOT_PRODUCT",
        t.vmath("SUBTRACT", point, proximity["Position"], x=x + 9, y=y - 1),
        normal,
        x=x + 10,
        y=y - 1,
    )
    inside = t.node(
        "FunctionNodeBooleanMath",
        x + 11,
        y - 1,
        {0: t.math("LESS_THAN", depth, 0.0, x=x + 10.5, y=y - 2), 1: proximity["Is Valid"]},
        operation="AND",
    ).outputs[0]
    point = switch(t, inside, point, proximity["Position"], "VECTOR", x + 12, y)
    into = t.math(
        "MULTIPLY",
        t.math(
            "MINIMUM",
            t.vmath("DOT_PRODUCT", moving, normal, x=x + 10, y=y - 4),
            0.0,
            x=x + 11,
            y=y - 4,
        ),
        inside,
        x=x + 12,
        y=y - 4,
    )
    moving = t.vmath(
        "SUBTRACT", moving, t.vmath("SCALE", normal, into, x=x + 13, y=y - 4), x=x + 14, y=y - 3
    )
    return point, moving


def floored(t, point, moving, floor, x, y):
    """The point over the floor, not moving down into it"""
    xyz = t.node("ShaderNodeSeparateXYZ", x, y, {0: point}).outputs
    under = t.math("LESS_THAN", xyz["Z"], floor, x=x + 1, y=y - 1)
    point = t.node(
        "ShaderNodeCombineXYZ",
        x + 2,
        y,
        {"X": xyz["X"], "Y": xyz["Y"], "Z": t.math("MAXIMUM", xyz["Z"], floor, x=x + 1, y=y)},
    ).outputs[0]
    speed = t.node("ShaderNodeSeparateXYZ", x, y - 2, {0: moving}).outputs
    down = t.math(
        "MULTIPLY",
        t.math("MINIMUM", speed["Z"], 0.0, x=x + 1, y=y - 3),
        under,
        x=x + 2,
        y=y - 3,
    )
    moving = t.node(
        "ShaderNodeCombineXYZ",
        x + 3,
        y - 2,
        {
            "X": speed["X"],
            "Y": speed["Y"],
            "Z": t.math("SUBTRACT", speed["Z"], down, x=x + 3, y=y - 3),
        },
    ).outputs[0]
    return point, moving, under


def puff_step(t, puffs, ground, colliders, inputs, dt, x, y):
    """Puffs slowed by the air and rising with it, kept out of the mesh, the Colliders and the
    floor"""
    position = t.node("GeometryNodeInputPosition", x, y - 6).outputs[0]
    moving = t.attribute(".dust_velocity", "FLOAT_VECTOR", x, y - 1)
    up = t.node("ShaderNodeCombineXYZ", x, y - 3, {"Z": inputs["Rise"]}).outputs[0]
    drag = t.math("MULTIPLY", dt, AIR_DRAG, x=x, y=y - 4, clamp=True)
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
    # Out of the mesh, where in front of its faces
    _, normal, offset, height = surface(t, ground, point, x + 5, y - 7)
    aside = t.vmath("LENGTH", along(t, offset, normal, x + 8, y - 9), x=x + 10, y=y - 9)
    inside = t.node(
        "FunctionNodeBooleanMath",
        x + 11,
        y - 7,
        {
            0: t.math("LESS_THAN", height, 0.0, x=x + 10, y=y - 7),
            1: t.math("LESS_THAN", aside, inputs["Contact"], x=x + 10.5, y=y - 9),
        },
        operation="AND",
    ).outputs[0]
    depth = t.math("MULTIPLY", height, inside, x=x + 12, y=y - 7)
    point = t.vmath(
        "SUBTRACT", point, t.vmath("SCALE", normal, depth, x=x + 13, y=y - 7), x=x + 14, y=y - 6
    )
    into = t.math(
        "MULTIPLY",
        t.math(
            "MINIMUM",
            t.vmath("DOT_PRODUCT", moving, normal, x=x + 11, y=y - 11),
            0.0,
            x=x + 12,
            y=y - 11,
        ),
        inside,
        x=x + 13,
        y=y - 11,
    )
    moving = t.vmath(
        "SUBTRACT", moving, t.vmath("SCALE", normal, into, x=x + 14, y=y - 11), x=x + 15, y=y - 10
    )
    margin = t.math("MULTIPLY", inputs["Size"], 2.6, x=x + 15, y=y - 14)
    point, moving = outside(t, colliders, puffs, point, moving, margin, x + 16, y - 6)
    point, moving, _ = floored(t, point, moving, inputs["Floor"], x + 31, y - 6)
    puffs = t.store(puffs, ".dust_velocity", "FLOAT_VECTOR", moving, x + 35, y)
    puffs = t.node(
        "GeometryNodeSetPosition", x + 36, y, {"Geometry": puffs, "Position": point}
    ).outputs[0]
    age = t.math("ADD", t.attribute(".dust_age", "FLOAT", x + 36, y - 2), dt, x=x + 37, y=y - 2)
    puffs = t.store(puffs, ".dust_age", "FLOAT", age, x + 37, y)
    old = t.math(
        "GREATER_THAN",
        t.attribute(".dust_age", "FLOAT", x + 37, y - 3),
        t.attribute(".dust_life", "FLOAT", x + 37, y - 4),
        x=x + 38,
        y=y - 3,
    )
    return t.node(
        "GeometryNodeDeleteGeometry", x + 39, y, {"Geometry": puffs, "Selection": old}
    ).outputs[0]


def debris_step(t, debris, ground, inputs, dt, x, y):
    """Pieces falling, bouncing on the mesh and the floor to rest, turning while they fly"""
    debris = grain_step(t, debris, ground, dt, x, y)
    x += 20
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    moving = t.attribute(".dust_velocity", "FLOAT_VECTOR", x, y - 3)
    # Reaching down by their turned extent, not their thickness
    up = t.node(
        "FunctionNodeRotateVector",
        x - 1,
        y - 6,
        {
            "Vector": (0.0, 0.0, 1.0),
            "Rotation": t.node(
                "FunctionNodeInvertRotation",
                x - 2,
                y - 6,
                {0: t.attribute(".dust_rotation", "QUATERNION", x - 3, y - 6)},
            ).outputs[0],
        },
    ).outputs[0]
    radius = t.vmath(
        "LENGTH",
        t.vmath(
            "MULTIPLY", t.attribute(".dust_scale", "FLOAT_VECTOR", x - 1, y - 5), up, x=x, y=y - 5
        ),
        x=x + 0.5,
        y=y - 5,
    )
    low = t.math("ADD", inputs["Floor"], radius, x=x + 1, y=y - 5)
    point, landed, under = floored(t, position, moving, low, x + 1, y - 2)
    # On the floor, bouncing a little and sliding to rest
    speed = t.node("ShaderNodeSeparateXYZ", x + 5, y - 6, {0: landed}).outputs
    sliding = 1.0 - FRICTION
    bounced = t.node(
        "ShaderNodeCombineXYZ",
        x + 6,
        y - 6,
        {
            "X": t.math("MULTIPLY", speed["X"], sliding, x=x + 5.5, y=y - 7),
            "Y": t.math("MULTIPLY", speed["Y"], sliding, x=x + 5.5, y=y - 8),
            "Z": t.math(
                "MULTIPLY",
                t.math(
                    "MINIMUM",
                    t.vmath("DOT_PRODUCT", moving, (0, 0, 1), x=x + 5, y=y - 9),
                    0.0,
                    x=x + 5.5,
                    y=y - 9,
                ),
                -BOUNCE,
                x=x + 6,
                y=y - 9,
            ),
        },
    ).outputs[0]
    resting = t.math(
        "LESS_THAN", t.vmath("LENGTH", bounced, x=x + 7, y=y - 7), REST_SPEED, x=x + 8, y=y - 7
    )
    bounced = switch(t, resting, bounced, (0.0, 0.0, 0.0), "VECTOR", x + 9, y - 6)
    moving = switch(t, under, moving, bounced, "VECTOR", x + 10, y - 3)
    debris = t.store(debris, ".dust_velocity", "FLOAT_VECTOR", moving, x + 11, y)
    debris = t.node(
        "GeometryNodeSetPosition", x + 12, y, {"Geometry": debris, "Position": point}
    ).outputs[0]
    # Turning only while flying
    spin = t.attribute(".dust_spin", "FLOAT_VECTOR", x + 10, y - 10)
    flying = t.math(
        "GREATER_THAN", t.vmath("LENGTH", moving, x=x + 11, y=y - 9), REST_SPEED, x=x + 12, y=y - 9
    )
    rotation = t.node(
        "FunctionNodeRotateRotation",
        x + 13,
        y - 8,
        {
            "Rotation": t.attribute(".dust_rotation", "QUATERNION", x + 12, y - 8),
            "Rotate By": t.node(
                "FunctionNodeAxisAngleToRotation",
                x + 12.5,
                y - 10,
                {
                    "Axis": t.vmath("NORMALIZE", spin, x=x + 11, y=y - 10),
                    "Angle": t.math(
                        "MULTIPLY",
                        t.math(
                            "MULTIPLY",
                            t.vmath("LENGTH", spin, x=x + 11, y=y - 11),
                            dt,
                            x=x + 12,
                            y=y - 11,
                        ),
                        flying,
                        x=x + 12.5,
                        y=y - 11,
                    ),
                },
            ).outputs[0],
        },
        rotation_space="GLOBAL",
    ).outputs[0]
    return t.store(debris, ".dust_rotation", "QUATERNION", rotation, x + 14, y)


def offspring(t, parents, per, inputs, seed, x, y):
    """Points on the outer side of each parent, leaning the way of its axis, with their radius,
    id and axis, the same around the parent on every frame"""
    count = t.node(
        "GeometryNodeAttributeDomainSize", x, y, {"Geometry": parents}, component="POINTCLOUD"
    ).outputs["Point Count"]
    index = t.node("GeometryNodeInputIndex", x, y - 2).outputs[0]
    parent = t.math("FLOOR", t.math("DIVIDE", index, per, x=x + 1, y=y - 2), x=x + 2, y=y - 2)
    nth = t.math("FLOORED_MODULO", index, per, x=x + 1, y=y - 3)
    ident = sample(
        t, parents, t.attribute(".dust_id", "INT", x + 2, y - 4), parent, "INT", x + 3, y - 4
    )
    random = identified(
        t, inputs, ident, t.math("MULTIPLY", nth, 101.0, x=x + 2, y=y - 5), x + 4, y - 6
    )
    center = sample(
        t,
        parents,
        t.node("GeometryNodeInputPosition", x + 2, y - 7).outputs[0],
        parent,
        "FLOAT_VECTOR",
        x + 3,
        y - 7,
    )
    radius = sample(
        t,
        parents,
        t.node("GeometryNodeInputRadius", x + 2, y - 8).outputs[0],
        parent,
        "FLOAT",
        x + 3,
        y - 8,
    )
    axis = sample(
        t,
        parents,
        t.attribute(".dust_axis", "FLOAT_VECTOR", x + 2, y - 9),
        parent,
        "FLOAT_VECTOR",
        x + 3,
        y - 9,
    )
    unit = t.vmath(
        "NORMALIZE", random((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), seed, 0), x=x + 6, y=y - 6
    )
    direction = t.vmath(
        "NORMALIZE",
        t.vmath(
            "ADD", unit, t.vmath("SCALE", axis, CHILD_PULL, x=x + 6, y=y - 9), x=x + 7, y=y - 7
        ),
        x=x + 8,
        y=y - 7,
    )
    distance = t.math(
        "MULTIPLY", random(*CHILD_DISTANCE, seed + 1, 2, "FLOAT"), radius, x=x + 8, y=y - 8
    )
    points = t.node(
        "GeometryNodePoints",
        x + 10,
        y,
        {
            "Count": t.math("MULTIPLY", count, per, x=x + 1, y=y),
            "Position": t.vmath(
                "ADD",
                center,
                t.vmath("SCALE", direction, distance, x=x + 9, y=y - 8),
                x=x + 9.5,
                y=y - 7,
            ),
            "Radius": t.math(
                "MULTIPLY", random(*CHILD_SIZE, seed + 2, 4, "FLOAT"), radius, x=x + 9, y=y - 10
            ),
        },
    ).outputs[0]
    points = t.store(points, ".dust_id", "INT", random(0, 1 << 30, seed + 3, 8, "INT"), x + 11, y)
    lean = t.vmath(
        "NORMALIZE",
        t.vmath("ADD", direction, (0.0, 0.0, CHILD_LEAN), x=x + 10, y=y - 12),
        x=x + 11,
        y=y - 12,
    )
    return t.store(points, ".dust_axis", "FLOAT_VECTOR", lean, x + 12, y)


def to_grid(t, topology, items, x, y):
    """Field to Grid outputs of the named (data type, value) items on the topology"""
    node = t.node("GeometryNodeFieldToGrid", x, y, {"Topology": topology})
    for name, (data_type, value) in items.items():
        node.grid_items.new(data_type, name)
        t.connect(value, node.inputs[name])
    return node.outputs


def sampled(t, grid, at, x, y):
    return t.node(
        "GeometryNodeSampleGrid", x, y, {"Grid": grid, "Position": at}, data_type="FLOAT"
    ).outputs[0]


def billows(t, puffs, inputs, x, y):
    """Dust of the growing puffs with their children and grandchildren, thinning out at the end of
    their life, its color shaded away from the Sun"""
    size = inputs["Size"]
    age = t.attribute(".dust_age", "FLOAT", x, y - 2)
    life = t.attribute(".dust_life", "FLOAT", x, y - 3)
    grown = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "EXPONENT",
            t.math(
                "DIVIDE",
                t.math("MULTIPLY", age, -1.0, x=x + 1, y=y - 2),
                inputs["Growth"],
                x=x + 2,
                y=y - 2,
            ),
            x=x + 3,
            y=y - 2,
        ),
        x=x + 4,
        y=y - 2,
    )
    grown = t.math("MULTIPLY_ADD", grown, 1.0 - START, START, x=x + 5, y=y - 2)
    radius = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", grown, size, x=x + 6, y=y - 2),
        t.attribute(".dust_size", "FLOAT", x + 5, y - 3),
        x=x + 7,
        y=y - 2,
    )
    puffs = t.node(
        "GeometryNodeSetPointRadius", x + 8, y, {"Points": puffs, "Radius": radius}
    ).outputs[0]
    # Coarser for a cloud past the most voxels
    total = t.node(
        "GeometryNodeAttributeStatistic",
        x + 9,
        y - 18,
        {
            "Geometry": puffs,
            "Attribute": t.math(
                "POWER",
                t.node("GeometryNodeInputRadius", x + 8, y - 19).outputs[0],
                3.0,
                x=x + 8.5,
                y=y - 19,
            ),
        },
    ).outputs["Sum"]
    voxel = t.math(
        "MAXIMUM",
        t.math("DIVIDE", size, inputs["Resolution"], x=x + 10, y=y - 20),
        t.math(
            "POWER",
            t.math("MULTIPLY", total, PUFF_VOLUME / MAX_VOXELS, x=x + 10, y=y - 18),
            1.0 / 3.0,
            x=x + 11,
            y=y - 18,
        ),
        x=x + 12,
        y=y - 19,
    )
    fade = t.math(
        "DIVIDE",
        t.math("SUBTRACT", life, age, x=x + 7, y=y - 4),
        t.math("MULTIPLY", life, FADE, x=x + 7, y=y - 5),
        x=x + 8,
        y=y - 4,
        clamp=True,
    )
    puffs = t.store(puffs, ".dust_fade", "FLOAT", fade, x + 9, y)

    children = offspring(t, puffs, CHILDREN, inputs, 60, x + 10, y - 4)
    grandchildren = offspring(t, children, GRANDCHILDREN, inputs, 70, x + 23, y - 4)
    spheres = t.node("GeometryNodeJoinGeometry", x + 36, y)
    for geometry in (grandchildren, children, puffs):
        t.connect(geometry, spheres.inputs[0])
    radius = t.node("GeometryNodeInputRadius", x + 36, y - 2).outputs[0]
    dust = t.node(
        "GeometryNodePointsToVolume",
        x + 37,
        y,
        {
            "Points": spheres.outputs[0],
            "Density": 1.0,
            "Resolution Mode": "Size",
            "Voxel Size": voxel,
            "Radius": radius,
        },
    ).outputs[0]
    dust = t.node(
        "GeometryNodeGetNamedGrid",
        x + 38,
        y,
        {"Volume": dust, "Name": "density"},
        data_type="FLOAT",
    ).outputs["Grid"]

    # Fade of the nearest puff, on a coarser grid around the puffs and their children
    around = t.node(
        "GeometryNodePointsToVolume",
        x + 37,
        y - 6,
        {
            "Points": puffs,
            "Density": 1.0,
            "Resolution Mode": "Size",
            "Voxel Size": t.math("MULTIPLY", voxel, FADE_VOXELS, x=x + 36, y=y - 8),
            "Radius": t.math("MULTIPLY", radius, 2.0, x=x + 36, y=y - 9),
        },
    ).outputs[0]
    around = t.node(
        "GeometryNodeGetNamedGrid",
        x + 38,
        y - 6,
        {"Volume": around, "Name": "density"},
        data_type="FLOAT",
    ).outputs["Grid"]
    position = t.node("GeometryNodeInputPosition", x + 38, y - 10).outputs[0]
    nearest = t.node(
        "GeometryNodeSampleNearest", x + 39, y - 9, {"Geometry": puffs, "Sample Position": position}
    ).outputs[0]
    fades = to_grid(
        t,
        around,
        {
            "Fade": (
                "FLOAT",
                sample(
                    t,
                    puffs,
                    t.attribute(".dust_fade", "FLOAT", x + 39, y - 11),
                    nearest,
                    "FLOAT",
                    x + 40,
                    y - 10,
                ),
            )
        },
        x + 41,
        y - 6,
    )["Fade"]

    # Billows: the puffs eaten away by a noise slowly changing, more and thinner as they fade
    fading = sampled(t, fades, position, x + 42, y - 7)
    time = t.node("GeometryNodeInputSceneTime", x + 39, y - 14).outputs["Seconds"]
    noise = t.node(
        "ShaderNodeTexNoise",
        x + 41,
        y - 13,
        {
            "Vector": t.vmath(
                "SCALE",
                position,
                t.math("DIVIDE", NOISE_SCALE, size, x=x + 39, y=y - 13),
                x=x + 40,
                y=y - 12,
            ),
            "W": t.math("MULTIPLY", time, NOISE_SPEED, x=x + 40, y=y - 14),
            "Scale": 1.0,
            "Detail": 4.0,
            "Roughness": 0.6,
        },
        noise_dimensions="4D",
    ).outputs["Fac"]
    worn = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            sampled(t, dust, position, x + 41, y - 2),
            t.math("MULTIPLY_ADD", fading, 0.5, 0.5, x=x + 43, y=y - 7),
            x=x + 43,
            y=y - 2,
        ),
        t.math("MULTIPLY_ADD", noise, 1.2, -0.1, x=x + 42, y=y - 12),
        x=x + 44,
        y=y - 2,
    )
    worn = t.node(
        "ShaderNodeMapRange",
        x + 45,
        y - 2,
        {0: worn, 1: 0.2, 2: 0.5},
        interpolation_type="SMOOTHSTEP",
        clamp=True,
    ).outputs[0]
    worn = t.math("MULTIPLY", worn, fading, x=x + 45.5, y=y - 3)
    worn = to_grid(t, dust, {"Billows": ("FLOAT", worn)}, x + 46, y)["Billows"]

    # Light from the Sun left after the dust on the way, as baked in EEVEE does not shade it
    sun = t.node(
        "GeometryNodeObjectInfo",
        x + 45,
        y - 8,
        {"Object": inputs["Sun"]},
        transform_space="ORIGINAL",
    ).outputs["Rotation"]
    toward = t.node(
        "FunctionNodeRotateVector", x + 46, y - 8, {"Vector": (0.0, 0.0, 1.0), "Rotation": sun}
    ).outputs[0]
    step = t.vmath(
        "SCALE", toward, t.math("MULTIPLY", size, SHADE_STEP, x=x + 46, y=y - 10), x=x + 47, y=y - 9
    )
    total = None
    for k in range(1, SHADE_STEPS + 1):
        at = t.vmath(
            "ADD",
            position,
            t.vmath("SCALE", step, float(k), x=x + 48, y=y - 8 - k),
            x=x + 49,
            y=y - 8 - k,
        )
        value = sampled(t, worn, at, x + 50, y - 8 - k)
        total = value if total is None else t.math("ADD", total, value, x=x + 51, y=y - 8 - k)
    lit = t.math(
        "EXPONENT", t.math("MULTIPLY", total, -SHADE_DARKEN, x=x + 52, y=y - 10), x=x + 53, y=y - 10
    )
    lit = t.math("MULTIPLY_ADD", lit, 1.0 - AMBIENT, AMBIENT, x=x + 54, y=y - 10)
    # Not shaded at no Shade
    shade = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "MULTIPLY",
            inputs["Shade"],
            t.math("SUBTRACT", 1.0, lit, x=x + 55, y=y - 10),
            x=x + 56,
            y=y - 10,
        ),
        x=x + 57,
        y=y - 10,
    )
    grids = to_grid(
        t,
        worn,
        {
            "Density": (
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    sampled(t, worn, position, x + 55, y - 2),
                    t.math("DIVIDE", DENSITY, size, x=x + 55, y=y - 4),
                    x=x + 56,
                    y=y - 2,
                ),
            ),
            "Color": ("VECTOR", t.vmath("SCALE", inputs["Color"], shade, x=x + 58, y=y - 9)),
        },
        x + 59,
        y,
    )
    volume = stored(t, grids["Density"], x + 60, y)
    return t.node(
        "GeometryNodeStoreNamedGrid",
        x + 63,
        y,
        {"Volume": volume, "Name": "color", "Grid": grids["Color"]},
        data_type="VECTOR_FLOAT",
    ).outputs[0]


def debris_meshes(t, debris, inputs, mesh, to_local, x, y):
    """Shards and chips of the debris, the chips with the material of the mesh they come from,
    as an instance not to be changed by the modifiers after"""
    left = t.math(
        "DIVIDE",
        t.math(
            "SUBTRACT",
            t.attribute(".dust_life", "FLOAT", x, y - 8),
            t.attribute(".dust_age", "FLOAT", x, y - 9),
            x=x + 1,
            y=y - 8,
        ),
        t.math(
            "MULTIPLY", t.attribute(".dust_life", "FLOAT", x, y - 10), SHRINK, x=x + 1, y=y - 10
        ),
        x=x + 2,
        y=y - 8,
        clamp=True,
    )
    scale = t.vmath(
        "SCALE", t.attribute(".dust_scale", "FLOAT_VECTOR", x + 2, y - 7), left, x=x + 3, y=y - 7
    )
    rotation = t.attribute(".dust_rotation", "QUATERNION", x + 2, y - 6)
    glass = t.attribute(".dust_glass", "BOOLEAN", x + 2, y - 5)
    chip = t.node("GeometryNodeMeshIcoSphere", x, y - 2, {"Radius": 1.0, "Subdivisions": 1})
    shard = t.node(
        "GeometryNodeMeshCircle", x, y - 4, {"Vertices": 3, "Radius": 1.0}, fill_type="NGON"
    )
    pieces = t.node("GeometryNodeJoinGeometry", x + 4, y)
    for selection, piece in (
        (glass, shard.outputs[0]),
        (
            t.node("FunctionNodeBooleanMath", x + 2, y - 3, {0: glass}, operation="NOT").outputs[0],
            chip.outputs[0],
        ),
    ):
        flat = t.node(
            "GeometryNodeSetShadeSmooth",
            x + 2,
            y - 2,
            {
                "Mesh": t.store(piece, ".dust_piece", "BOOLEAN", True, x + 1, y - 2),
                "Shade Smooth": False,
            },
        ).outputs[0]
        t.connect(
            t.node(
                "GeometryNodeInstanceOnPoints",
                x + 3,
                y,
                {
                    "Points": debris,
                    "Selection": selection,
                    "Instance": flat,
                    "Rotation": rotation,
                    "Scale": scale,
                },
            ).outputs[0],
            pieces.inputs[0],
        )
    pieces = t.node("GeometryNodeRealizeInstances", x + 5, y, {"Geometry": pieces.outputs[0]})
    pieces = t.node(
        "GeometryNodeTransform",
        x + 6,
        y,
        {"Geometry": pieces.outputs[0], "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    # The mesh materials from its loose points, linked last, without its attributes
    materials = t.node(
        "GeometryNodeDeleteGeometry",
        x + 6,
        y - 3,
        {"Geometry": mesh, "Selection": True},
        domain="FACE",
        mode="ONLY_FACE",
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", x + 7, y)
    t.connect(pieces, joined.inputs[0])
    t.connect(t.strip(materials, x + 7, y - 3), joined.inputs[0])
    pieces = t.node(
        "GeometryNodeSetMaterialIndex",
        x + 13,
        y,
        {
            "Geometry": joined.outputs[0],
            "Material Index": t.attribute(".dust_material", "INT", x + 12, y - 1),
        },
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeDeleteGeometry",
        x + 14,
        y,
        {
            "Geometry": pieces,
            "Selection": t.node(
                "FunctionNodeBooleanMath",
                x + 13,
                y - 2,
                {0: t.attribute(".dust_piece", "BOOLEAN", x + 12, y - 2)},
                operation="NOT",
            ).outputs[0],
        },
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeSetMaterial",
        x + 15,
        y,
        {
            "Geometry": pieces,
            "Selection": t.attribute(".dust_glass", "BOOLEAN", x + 14, y - 2),
            "Material": inputs["Glass Material"],
        },
    ).outputs[0]
    pieces = t.node(
        "GeometryNodeRemoveAttribute",
        x + 16,
        y,
        {"Geometry": pieces, "Pattern Mode": "Wildcard", "Name": ".dust_*"},
    ).outputs[0]
    return t.node("GeometryNodeGeometryToInstance", x + 17, y, {0: pieces}).outputs[0]


def count_of(t, points, x, y):
    return t.node(
        "GeometryNodeAttributeDomainSize", x, y, {"Geometry": points}, component="POINTCLOUD"
    ).outputs["Point Count"]


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Burst thick billowing dust and debris out of the mesh where the Colliders hit it, as a "
        "building crushed"
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
    sim_out.state_items[0].name = "Colliders"
    for name in ("Puffs", "Debris"):
        sim_out.state_items.new("GEOMETRY", name)
    t.connect(positions(t, colliders, -8, -3), sim_in.inputs["Colliders"])
    dt = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=-5, y=-4)
    colliders = velocity(t, colliders, sim_in.outputs["Colliders"], dt, -5, -6)
    t.connect(positions(t, colliders, -1, -6), sim_out.inputs["Colliders"])

    t.section("Contact", row=True)
    near = rim(t, contacts(t, colliders, mesh, inputs, 0, 0), 25, 0)
    hitting = t.node("GeometryNodeAttributeDomainSize", 25, -2, {"Geometry": near}).outputs[
        "Face Count"
    ]
    hitting = t.math("GREATER_THAN", hitting, 0, x=26, y=-2)

    t.section("Puffs and Debris", row=True)
    states = {}
    for i, (name, emit, enabled) in enumerate(
        (
            ("Puffs", lambda n: emit_puffs(t, near, n, inputs, 0, 0), True),
            ("Debris", lambda n: emit_debris(t, near, mesh, n, inputs, 0, -28), inputs["Debris"]),
        )
    ):
        emitted = emit(count_of(t, sim_in.outputs[name], 19, -i * 28 - 3))
        joined = t.node("GeometryNodeJoinGeometry", 23, -i * 28)
        t.connect(sim_in.outputs[name], joined.inputs[0])
        # Only computed when hitting
        t.connect(switch(t, hitting, None, emitted, "GEOMETRY", 22, -i * 28), joined.inputs[0])
        states[name] = switch(t, enabled, None, joined.outputs[0], "GEOMETRY", 24, -i * 28)
    puffs = puff_step(t, states["Puffs"], mesh, colliders, inputs, dt, 25, 0)
    t.connect(puffs, sim_out.inputs["Puffs"])
    t.connect(debris_step(t, states["Debris"], mesh, inputs, dt, 25, -28), sim_out.inputs["Debris"])

    t.section("Output", row=True)
    debris = sim_out.outputs["Debris"]
    pieces = switch(
        t,
        t.math("GREATER_THAN", count_of(t, debris, 17, -6), 0, x=18, y=-6),
        None,
        debris_meshes(t, debris, inputs, inputs["Geometry"], to_local, 0, -3),
        "GEOMETRY",
        19,
        -3,
    )
    # The dust while there are puffs, after the attributes, as they warn on volumes
    puffs = sim_out.outputs["Puffs"]
    dust = switch(
        t,
        t.math("GREATER_THAN", count_of(t, puffs, 0, -14), 0, x=1, y=-14),
        None,
        billows(t, puffs, inputs, 0, -18),
        "GEOMETRY",
        65,
        -16,
    )
    dust = t.node(
        "GeometryNodeSetMaterial", 66, -16, {"Geometry": dust, "Material": inputs["Dust Material"]}
    ).outputs[0]
    dust = t.node(
        "GeometryNodeTransform",
        67,
        -16,
        {"Geometry": dust, "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 68, 0)
    for geometry in (dust, pieces, inputs["Geometry"]):
        t.connect(geometry, joined.inputs[0])
    t.node("NodeGroupOutput", 69, 0, {0: joined.outputs[0]})
    t.arrange()
    return ng


def build_dust_material():
    """Dust of the density and the shaded color of the grids"""
    material = bpy.data.materials.new(DUST)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))
    density = t.node("ShaderNodeAttribute", -300, 0, attribute_name="density").outputs["Fac"]
    color = t.node("ShaderNodeAttribute", -300, 200, attribute_name="color").outputs["Color"]
    volume = t.node(
        "ShaderNodeVolumePrincipled",
        0,
        0,
        {
            "Color": color,
            "Density": density,
            "Anisotropy": 0.2,
            # Read above, not to square it
            "Density Attribute": "",
        },
    )
    t.node("ShaderNodeOutputMaterial", 300, 0, {"Volume": volume.outputs[0]})
    return material


def build_glass_material():
    """Clear glass glinting in the light"""
    material = bpy.data.materials.new(GLASS)
    shader = material.node_tree.nodes["Principled BSDF"]
    shader.inputs["Base Color"].default_value = (0.8, 0.88, 0.92, 1.0)
    shader.inputs["Metallic"].default_value = 0.5
    shader.inputs["Roughness"].default_value = 0.05
    shader.inputs["Transmission Weight"].default_value = 0.5
    return material


if __name__ == "__main__":
    materials = (build_dust_material(), build_glass_material())
    write(RESOURCE, (build_node_group(), *materials))
