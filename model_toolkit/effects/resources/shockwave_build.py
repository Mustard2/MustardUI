# Build shockwave.blend: the Shockwave node group, its air and dust materials
# Usage: Blender --background --factory-startup --python shockwave_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "shockwave.blend"
NODE_GROUP = "MustardUI Shockwave"
MATERIAL = "MustardUI Shockwave Air"
DUST = "MustardUI Shockwave Dust"
# Faces of the front, its ring on the ground in the middle
SEGMENTS = 64
RINGS = 32
# Half height of the band of the front on the ground it starts on, touching it for the dust
BAND = 0.004
# Height of the front showing over the ground, relative to its radius, fading to it
SKIRT = 0.4
# Refraction of the air squeezed in the front, seen at its rim, and its glint in EEVEE
REFRACTION = 0.02
RIM = 3.0
GLINT = 0.25
# Voxels of the dust over the Radius, its height at the front relative to the Height, the seconds
# it rises most of the way in, its soft edge at the front relative to the Radius and the size of
# its billows relative to the Height
VOXELS = 50
# Voxels over the half width of the dust at most, as it spreads far
MAX_VOXELS = 100
LOW = 0.3
RISE = 0.35
EDGE = 0.04
BILLOWS = 0.5
# Width of the dense ring of dust at its edge, relative to the Radius, and the share of the haze
# left behind it
RING = 0.1
HAZE = 0.02
# How much denser the ring gets gathering the dust as it slows, and wider as it drifts; the share
# of its rise it starts rising at, of the whole life of the dust it starts fading at, and how high
# off the ground it lifts relative to the Height
PILE = 0.5
WIDEN = 0.5
RISE_START = 0.25
FADE_START = 0.4
LIFT = 0.35
# Bumps of the top of the rising dust relative to its height, their size relative to the Height,
# and how far past its edge the drifting ring spreads, relative to its width
BUMPS = 0.5
BUMP_SIZE = 1.5
SPREAD = 2.0
# Speed of the dust drifting on once the blast settles, relative to the front's starting speed;
# the share of the Duration the blast settles in, and the Durations the drift settles in, the dust
# rising in that and the Duration
DRIFT = 0.08
BLAST = 0.6
SETTLE = 3.3
# Smoke from the center: its radius relative to the Radius and half height relative to the
# Height, growing as the ring drifts; how high it rises by the end relative to the Height, and its
# density relative to the ring's
CORE = 0.12
CORE_WIDEN = 1.5
PUFF = 0.35
PUFF_GROW = 0.6
PUFF_RISE = 2.0
CENTER = 1.2
# Soft edge of the smoke dissolving from the bottom, and how ragged along its billows, relative to
# its half height
DISSOLVE = 0.4
RAGGED = 0.6
# Density of the thickest dust, more in EEVEE thinning it in its coarse grid, and the scale of its
# detail per meter
DUST_DENSITY = 16.0
EEVEE_DENSITY = 2.0
DETAIL = 6.0


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Front of a blast wave growing from the object, fast then slowing down, hitting the "
        "effects with it among their Colliders, and the dust it kicks up from the ground"
    )
    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Radius",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=5.0,
        min_value=0.01,
        description="Radius the wave stops at",
    )
    add_input(
        ng,
        "Duration",
        "NodeSocketFloat",
        default_value=0.6,
        min_value=0.01,
        description="Seconds the wave takes to reach the Radius, starting at twice its average "
        "speed and slowing down to a stop",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="Frame the wave starts at")
    add_input(
        ng,
        "Distortion",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Air bent by the front near the ground, 0 for a front not seen",
    )
    add_input(ng, "Material", "NodeSocketMaterial", description="Material of the front")
    add_input(
        ng,
        "Dust",
        "NodeSocketBool",
        default_value=True,
        description="Dust kicked up from the ground where the front passed, rising and thinning",
    )
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        description="Density of the dust",
    )
    add_input(
        ng,
        "Height",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=1.0,
        min_value=0.01,
        description="Height the dust rises to",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        default_value=3.1,
        min_value=0.01,
        description="Seconds the dust lasts after the front stops, drifting, rising and thinning",
    )
    add_input(
        ng,
        "Center",
        "NodeSocketBool",
        default_value=False,
        description="Smoke also rising from the center, where the wave starts",
    )
    add_input(ng, "Dust Material", "NodeSocketMaterial", description="Material of the dust")
    arrange_interface(
        ng,
        [
            (
                None,
                "Dust",
                False,
                "Dust",
                ["Density", "Height", "Lifetime", "Center", "Dust Material"],
            )
        ],
    )

    t = Tree(ng)
    t.section("Front")
    inputs = t.node("NodeGroupInput", -1, 0).outputs
    time = t.node("GeometryNodeInputSceneTime", -1, -3).outputs
    # Seconds since the start, the frame rate from the scene time
    seconds = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", time["Frame"], inputs["Start Frame"], x=0, y=-3),
        t.math("DIVIDE", time["Seconds"], time["Frame"], x=0, y=-4),
        x=1,
        y=-3,
    )
    progress = t.math("DIVIDE", seconds, inputs["Duration"], x=2, y=-3, clamp=True)
    left = t.math("SUBTRACT", 1.0, progress, x=3, y=-3)
    radius = t.math(
        "MULTIPLY",
        inputs["Radius"],
        t.math("SUBTRACT", 1.0, t.math("MULTIPLY", left, left, x=4, y=-4), x=5, y=-4),
        x=6,
        y=-3,
    )
    radius = t.math("MAXIMUM", radius, 1e-4, x=7, y=-3)
    sphere = t.node(
        "GeometryNodeMeshUVSphere", 7, 0, {"Segments": SEGMENTS, "Rings": RINGS, "Radius": radius}
    ).outputs["Mesh"]
    # A thin band around its middle, on the ground it starts on, its faces touching it
    band = t.node(
        "GeometryNodeMeshCircle", 7, -5, {"Vertices": SEGMENTS, "Radius": radius}
    ).outputs[0]
    band = t.node(
        "GeometryNodeSetPosition", 7.5, -5, {"Geometry": band, "Offset": (0.0, 0.0, -BAND)}
    ).outputs[0]
    band = t.node(
        "GeometryNodeExtrudeMesh",
        8,
        -5,
        {"Mesh": band, "Offset": (0.0, 0.0, 1.0), "Offset Scale": 2.0 * BAND},
        mode="EDGES",
    ).outputs["Mesh"]
    joined = t.node("GeometryNodeJoinGeometry", 8.5, 0)
    for part in (band, sphere):
        t.connect(part, joined.inputs[0])
    sphere = joined.outputs[0]
    sphere = t.node("GeometryNodeSetShadeSmooth", 9, 0, {"Geometry": sphere}).outputs[0]
    sphere = t.node(
        "GeometryNodeSetMaterial", 10, 0, {"Geometry": sphere, "Material": inputs["Material"]}
    ).outputs[0]
    # On all of it while growing, for the effects it hits
    sphere = t.store(sphere, "shockwave", "FLOAT", left, 11, 0)
    # Seen near the ground only, fading
    height = t.node(
        "ShaderNodeSeparateXYZ",
        10,
        -6,
        {0: t.node("GeometryNodeInputPosition", 9.5, -6).outputs[0]},
    ).outputs["Z"]
    skirt = t.node(
        "ShaderNodeMapRange",
        11,
        -6,
        {
            "Value": t.math("DIVIDE", height, radius, x=10.5, y=-7),
            "From Min": 0.0,
            "From Max": SKIRT,
            "To Min": 1.0,
            "To Max": 0.0,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    air = t.math(
        "MULTIPLY", t.math("MULTIPLY", skirt, left, x=11.5, y=-6), inputs["Distortion"], x=12, y=-6
    )
    sphere = t.store(sphere, "shockwave_air", "FLOAT", air, 12, 0)
    # Only while growing
    growing = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", seconds, 0.0, x=9, y=-3),
        t.math("LESS_THAN", progress, 1.0, x=9, y=-4),
        x=10,
        y=-3,
    )
    front = t.node(
        "GeometryNodeSwitch",
        13,
        0,
        {"Switch": growing, "True": sphere},
        input_type="GEOMETRY",
    ).outputs[0]

    t.section("Dust", row=True)
    dust = build_dust(t, inputs, seconds, 0, 0)
    output = t.node("GeometryNodeJoinGeometry", 30, 0)
    for part in (dust, front):
        t.connect(part, output.inputs[0])
    t.node("NodeGroupOutput", 31, 0, {"Geometry": output.outputs[0]})
    t.arrange()
    return ng


def layer(t, z, bottom, top, height, x, y):
    """Density of a layer of dust from the bottom to the top, soft at both, denser low"""
    lower = t.node(
        "ShaderNodeMapRange",
        x,
        y,
        {
            "Value": z,
            "From Min": t.math(
                "SUBTRACT",
                bottom,
                t.math("MULTIPLY", height, 0.3, x=x - 1, y=y - 1),
                x=x - 0.5,
                y=y - 1,
            ),
            "From Max": bottom,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    upper = t.node(
        "ShaderNodeMapRange",
        x,
        y - 2,
        {
            "Value": z,
            "From Min": t.math(
                "MULTIPLY_ADD",
                t.math("SUBTRACT", top, bottom, x=x - 1, y=y - 3),
                0.4,
                bottom,
                x=x - 0.5,
                y=y - 3,
            ),
            "From Max": top,
            "To Min": 1.0,
            "To Max": 0.0,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    return t.math("MULTIPLY", lower, upper, x=x + 1, y=y)


def build_dust(t, inputs, seconds, x, y):
    """Dust kicked up from the ground by the front, carried on past its Radius slowing down,
    gathering in a ring that lifts off the ground and rises, with a haze left behind it"""
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    xyz = t.node("ShaderNodeSeparateXYZ", x + 1, y - 2, {0: position}).outputs
    across = t.vmath(
        "LENGTH",
        t.node("ShaderNodeCombineXYZ", x + 2, y - 2, {"X": xyz["X"], "Y": xyz["Y"]}).outputs[0],
        x=x + 3,
        y=y - 2,
    )

    # Edge of the dust slowing down smoothly from the front's speed to a slow drift that keeps
    # going: a blast part settling in BLAST x Duration, scaled to be at the Radius as the front
    # stops, and a drift settling in the Lifetime
    def settled(time, scale, yy):
        """1 - e ^ (-time / scale)"""
        return t.math(
            "SUBTRACT",
            1.0,
            t.math(
                "EXPONENT",
                t.math(
                    "DIVIDE",
                    time,
                    t.math("MULTIPLY", scale, -1.0, x=x + 3, y=yy - 1),
                    x=x + 4,
                    y=yy,
                ),
                x=x + 5,
                y=yy,
            ),
            x=x + 6,
            y=yy,
        )

    elapsed = t.math("MAXIMUM", seconds, 0.0, x=x + 2, y=y - 12)
    slowed = settled(
        elapsed, t.math("MULTIPLY", inputs["Duration"], BLAST, x=x + 2, y=y - 11), y - 10
    )
    calm = settled(
        elapsed, t.math("MULTIPLY", inputs["Duration"], SETTLE, x=x + 2, y=y - 13), y - 12
    )
    # Drift distance relative to the Radius, as its speed by the time it settles in, with the blast
    # part reaching the rest of the Radius as the front stops
    drifting = 2.0 * DRIFT * SETTLE
    blast = (1.0 - drifting * (1.0 - math.exp(-1.0 / SETTLE))) / (1.0 - math.exp(-1.0 / BLAST))
    reach = t.math(
        "MULTIPLY",
        inputs["Radius"],
        t.math(
            "MULTIPLY_ADD",
            slowed,
            blast,
            t.math("MULTIPLY", calm, drifting, x=x + 7, y=y - 12),
            x=x + 8,
            y=y - 10,
        ),
        x=x + 9,
        y=y - 9,
    )
    # Seconds since the front passed there, and how fast it was there kicking up the dust
    fast = t.math(
        "SQRT",
        t.math(
            "MAXIMUM",
            t.math(
                "SUBTRACT",
                1.0,
                t.math("DIVIDE", across, inputs["Radius"], x=x + 4, y=y - 3),
                x=x + 5,
                y=y - 3,
            ),
            0.0,
            x=x + 6,
            y=y - 3,
        ),
        x=x + 7,
        y=y - 3,
    )
    passed = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", 1.0, fast, x=x + 7.5, y=y - 4),
        inputs["Duration"],
        x=x + 8,
        y=y - 3,
    )
    age = t.math(
        "MAXIMUM", t.math("SUBTRACT", seconds, passed, x=x + 9, y=y - 4), 0.0, x=x + 10, y=y - 4
    )
    edge = t.math("MULTIPLY", inputs["Radius"], EDGE, x=x + 4, y=y - 6)
    # Share of the whole life of the dust fading at its end, and of its rise
    life = t.math(
        "DIVIDE",
        seconds,
        t.math("ADD", inputs["Duration"], inputs["Lifetime"], x=x + 9, y=y - 13),
        x=x + 10,
        y=y - 13,
    )
    grown = t.math(
        "DIVIDE",
        seconds,
        t.math("MULTIPLY", inputs["Duration"], 1.0 + SETTLE, x=x + 9, y=y - 12),
        x=x + 10,
        y=y - 12,
    )

    def ramp(value, low, high, yy):
        return t.node(
            "ShaderNodeMapRange",
            x + 11,
            yy,
            {"Value": value, "From Min": low, "From Max": high},
            interpolation_type="SMOOTHSTEP",
        ).outputs[0]

    rise = ramp(grown, RISE_START, 1.0, y - 12)
    fading = ramp(life, FADE_START, 1.0, y - 13)
    fade = t.math("SUBTRACT", 1.0, fading, x=x + 12, y=y - 13)
    width = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Radius"], RING, x=x + 11, y=y - 8),
        t.math("MULTIPLY_ADD", calm, WIDEN, 1.0, x=x + 12, y=y - 9),
        x=x + 12.5,
        y=y - 8,
    )
    # Sharp at the front, spreading past its edge as it drifts
    spread = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", width, SPREAD, x=x + 12, y=y - 7),
        calm,
        x=x + 12.5,
        y=y - 7,
    )
    reached = t.node(
        "ShaderNodeMapRange",
        x + 13,
        y - 6,
        {
            "Value": across,
            "From Min": t.math("ADD", reach, spread, x=x + 13, y=y - 7),
            "From Max": t.math("SUBTRACT", reach, edge, x=x + 13, y=y - 8),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Bumps of its top, larger noise drifting in time
    bumps = t.node(
        "ShaderNodeTexNoise",
        x + 13,
        y - 16,
        {
            "Vector": position,
            "W": t.math("MULTIPLY", seconds, 0.3, x=x + 12, y=y - 17),
            "Scale": t.math(
                "DIVIDE",
                1.0,
                t.math("MULTIPLY", inputs["Height"], BUMP_SIZE, x=x + 11, y=y - 17),
                x=x + 12,
                y=y - 16,
            ),
            "Detail": 2.0,
        },
        noise_dimensions="4D",
    ).outputs["Fac"]
    # Heights read lower under the higher bumps
    bumped = t.math(
        "DIVIDE",
        xyz["Z"],
        t.math(
            "MULTIPLY_ADD",
            t.math("SUBTRACT", bumps, 0.5, x=x + 14, y=y - 16),
            2.0 * BUMPS,
            1.0,
            x=x + 14.5,
            y=y - 16,
        ),
        x=x + 15,
        y=y - 16,
    )

    # The ring gathering the dust it carries as it slows, widening, lifting off the ground and
    # rising up to the Height
    ring = t.math(
        "DIVIDE", t.math("SUBTRACT", reach, across, x=x + 11, y=y - 5), width, x=x + 12, y=y - 5
    )
    ring = t.math(
        "EXPONENT",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", ring, ring, x=x + 12.25, y=y - 6),
            -1.0,
            x=x + 12.5,
            y=y - 5,
        ),
        x=x + 13,
        y=y - 5,
    )
    gathered = t.math("MULTIPLY_ADD", slowed, PILE, 1.0, x=x + 13, y=y - 6)
    ring = t.math(
        "MULTIPLY", t.math("MULTIPLY", ring, gathered, x=x + 13.5, y=y - 5), fade, x=x + 14, y=y - 5
    )
    top = t.math(
        "MULTIPLY",
        inputs["Height"],
        t.math("MULTIPLY_ADD", rise, 1.0 - LOW, LOW, x=x + 13, y=y - 14),
        x=x + 14,
        y=y - 14,
    )
    bottom = t.math(
        "MULTIPLY",
        inputs["Height"],
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", rise, rise, x=x + 13, y=y - 15),
            LIFT,
            x=x + 13.5,
            y=y - 15,
        ),
        x=x + 14,
        y=y - 15,
    )
    ring = t.math(
        "MULTIPLY",
        ring,
        layer(t, bumped, bottom, top, inputs["Height"], x + 15, y - 14),
        x=x + 16,
        y=y - 5,
    )

    # The haze kicked up behind it, as much as the edge was fast there, rising and thinning
    risen = t.math(
        "SUBTRACT",
        1.0,
        t.math("EXPONENT", t.math("DIVIDE", age, -RISE, x=x + 12, y=y - 17), x=x + 13, y=y - 17),
        x=x + 14,
        y=y - 17,
    )
    haze_top = t.math(
        "MULTIPLY",
        inputs["Height"],
        t.math("MULTIPLY_ADD", risen, 1.0 - LOW, LOW, x=x + 15, y=y - 17),
        x=x + 16,
        y=y - 17,
    )
    haze = t.math(
        "MULTIPLY",
        t.math(
            "EXPONENT",
            t.math(
                "MULTIPLY",
                t.math("DIVIDE", age, inputs["Lifetime"], x=x + 12, y=y - 19),
                -3.0,
                x=x + 13,
                y=y - 19,
            ),
            x=x + 14,
            y=y - 19,
        ),
        t.math("MULTIPLY", fast, HAZE, x=x + 15, y=y - 20),
        x=x + 16,
        y=y - 19,
    )
    haze = t.math(
        "MULTIPLY",
        haze,
        layer(t, xyz["Z"], 0.0, haze_top, inputs["Height"], x + 17, y - 17),
        x=x + 18,
        y=y - 19,
    )

    def billowing(lift, yy):
        """Billows of the dust churning in time, carried up by lift"""
        noise = t.node(
            "ShaderNodeTexNoise",
            x + 16,
            yy,
            {
                "Vector": t.vmath(
                    "SUBTRACT",
                    position,
                    t.node("ShaderNodeCombineXYZ", x + 14, yy - 1, {"Z": lift}).outputs[0],
                    x=x + 15,
                    y=yy - 1,
                ),
                "W": t.math("MULTIPLY", seconds, 0.6, x=x + 15, y=yy - 2),
                "Scale": t.math(
                    "DIVIDE",
                    1.0,
                    t.math("MULTIPLY", inputs["Height"], BILLOWS, x=x + 14, y=yy - 2),
                    x=x + 15,
                    y=yy,
                ),
                "Detail": 3.0,
            },
            noise_dimensions="4D",
        ).outputs["Fac"]
        return t.node(
            "ShaderNodeMapRange",
            x + 17,
            yy,
            {"Value": noise, "From Min": 0.35, "From Max": 0.65},
            interpolation_type="SMOOTHSTEP",
        ).outputs[0]

    # Billowing, rising with it
    billows = billowing(t.math("MULTIPLY", inputs["Height"], rise, x=x + 13, y=y - 12), y - 11)

    # A cloud of smoke from the center with the Center option, rising off the ground the whole
    # time slower than the ring and spreading, its billows carried up with it
    lift = t.math(
        "MULTIPLY",
        inputs["Height"],
        t.math("MULTIPLY", life, PUFF_RISE, x=x + 12, y=y - 23),
        x=x + 13,
        y=y - 23,
    )
    middle = t.math("MULTIPLY_ADD", inputs["Height"], PUFF, lift, x=x + 14, y=y - 24)
    widening = t.math("MULTIPLY_ADD", calm, CORE_WIDEN, 1.0, x=x + 12, y=y - 25)
    wide = t.math(
        "DIVIDE",
        across,
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", inputs["Radius"], CORE, x=x + 12, y=y - 26),
            widening,
            x=x + 13,
            y=y - 26,
        ),
        x=x + 14,
        y=y - 26,
    )
    tall = t.math(
        "DIVIDE",
        t.math("SUBTRACT", xyz["Z"], middle, x=x + 15, y=y - 24),
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", inputs["Height"], PUFF, x=x + 13, y=y - 28),
            t.math("MULTIPLY_ADD", calm, PUFF_GROW, 1.0, x=x + 13, y=y - 27),
            x=x + 14,
            y=y - 27,
        ),
        x=x + 16,
        y=y - 24,
    )
    puff = t.math(
        "EXPONENT",
        t.math(
            "MULTIPLY",
            t.math(
                "ADD",
                t.math("MULTIPLY", wide, wide, x=x + 15, y=y - 26),
                t.math("MULTIPLY", tall, tall, x=x + 16.5, y=y - 25),
                x=x + 17,
                y=y - 24,
            ),
            -1.0,
            x=x + 17.5,
            y=y - 24,
        ),
        x=x + 18,
        y=y - 24,
    )
    # Dissolving from the bottom up as it fades, along its billows, from 2 half heights below its
    # middle to 1.7 above
    puff_billows = billowing(lift, y - 29)
    dissolving = t.math("MULTIPLY_ADD", fading, 3.7, -2.0, x=x + 16, y=y - 31)
    kept = t.node(
        "ShaderNodeMapRange",
        x + 18,
        y - 30,
        {
            "Value": t.math(
                "MULTIPLY_ADD",
                t.math("SUBTRACT", puff_billows, 0.5, x=x + 16, y=y - 32),
                RAGGED,
                tall,
                x=x + 17,
                y=y - 32,
            ),
            "From Min": t.math("SUBTRACT", dissolving, DISSOLVE, x=x + 17, y=y - 30),
            "From Max": t.math("ADD", dissolving, DISSOLVE, x=x + 17, y=y - 31),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Puffing up with the blast
    for i, factor in enumerate((slowed, kept, puff_billows)):
        puff = t.math("MULTIPLY", puff, factor, x=x + 18.5 + i * 0.5, y=y - 24)
    # Not worked out without Center
    puff = t.node(
        "GeometryNodeSwitch",
        x + 19.5,
        y - 24,
        {
            "Switch": inputs["Center"],
            "True": t.math("MULTIPLY", puff, CENTER, x=x + 19.5, y=y - 25),
        },
        input_type="FLOAT",
    ).outputs[0]
    density = t.math("ADD", ring, haze, x=x + 18.5, y=y - 5)
    for i, factor in enumerate((reached, billows)):
        density = t.math("MULTIPLY", density, factor, x=x + 19 + i * 0.5, y=y - 5)
    density = t.math(
        "MULTIPLY",
        t.math("ADD", density, puff, x=x + 20, y=y - 5),
        inputs["Density"],
        x=x + 20.5,
        y=y - 5,
    )

    # Over the ring and as high as the dust rises, as many voxels however large, coarser as it
    # spreads far
    half = t.math(
        "ADD", reach, t.math("MULTIPLY", width, SPREAD, x=x + 18, y=y - 15), x=x + 19, y=y - 15
    )
    voxel = t.math(
        "MAXIMUM",
        t.math("DIVIDE", inputs["Radius"], VOXELS, x=x + 18, y=y - 14),
        t.math("DIVIDE", half, MAX_VOXELS, x=x + 18, y=y - 13),
        x=x + 19,
        y=y - 14,
    )
    high = t.math(
        "MULTIPLY",
        inputs["Height"],
        t.math(
            "MULTIPLY_ADD",
            inputs["Center"],
            PUFF_RISE + PUFF * (2.5 + 1.5 * PUFF_GROW) - 1.1,
            1.1,
            x=x + 18,
            y=y - 16,
        ),
        x=x + 19,
        y=y - 16,
    )

    def count(length, yy):
        return t.math(
            "MAXIMUM",
            t.math("CEIL", t.math("DIVIDE", length, voxel, x=x + 20, y=yy), x=x + 21, y=yy),
            2.0,
            x=x + 22,
            y=yy,
        )

    volume = t.node(
        "GeometryNodeVolumeCube",
        x + 24,
        y,
        {
            "Density": density,
            "Background": 0.0,
            "Min": t.node(
                "ShaderNodeCombineXYZ",
                x + 23,
                y - 14,
                {
                    "X": t.math("MULTIPLY", half, -1.0, x=x + 22, y=y - 14),
                    "Y": t.math("MULTIPLY", half, -1.0, x=x + 22, y=y - 13),
                    "Z": t.math("MULTIPLY", voxel, -1.0, x=x + 22, y=y - 12),
                },
            ).outputs[0],
            "Max": t.node(
                "ShaderNodeCombineXYZ", x + 23, y - 16, {"X": half, "Y": half, "Z": high}
            ).outputs[0],
            "Resolution X": count(t.math("MULTIPLY", half, 2.0, x=x + 19.5, y=y - 17), y - 17),
            "Resolution Y": count(t.math("MULTIPLY", half, 2.0, x=x + 19.5, y=y - 18), y - 18),
            "Resolution Z": count(t.math("ADD", high, voxel, x=x + 19.5, y=y - 19), y - 19),
        },
    ).outputs[0]
    volume = t.node(
        "GeometryNodeSetMaterial",
        x + 25,
        y,
        {"Geometry": volume, "Material": inputs["Dust Material"]},
    ).outputs[0]
    # While the dust lasts
    dusty = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", seconds, 0.0, x=x + 24, y=y - 3),
        t.math(
            "LESS_THAN",
            seconds,
            t.math("ADD", inputs["Duration"], inputs["Lifetime"], x=x + 23, y=y - 4),
            x=x + 24,
            y=y - 4,
        ),
        x=x + 25,
        y=y - 3,
    )
    dusty = t.math("MULTIPLY", dusty, inputs["Dust"], x=x + 25.5, y=y - 3)
    return t.node(
        "GeometryNodeSwitch", x + 26, y, {"Switch": dusty, "True": volume}, input_type="GEOMETRY"
    ).outputs[0]


def build_material():
    """Clear air bent by the front at its rim near the ground, refracting in Cycles and glinting
    in EEVEE"""
    material = bpy.data.materials.new(MATERIAL)
    material.use_backface_culling = False
    material.use_transparent_shadow = True
    tree = material.node_tree
    tree.nodes.clear()
    t = Tree(tree, spacing=(200, 180))
    air = t.node(
        "ShaderNodeAttribute", 0, 0, attribute_type="GEOMETRY", attribute_name="shockwave_air"
    ).outputs["Fac"]
    facing = t.node("ShaderNodeLayerWeight", 0, -2, {"Blend": 0.5}).outputs["Facing"]
    rim = t.math("MULTIPLY", t.math("POWER", facing, RIM, x=1, y=-2), air, x=2, y=-2, clamp=True)
    # Casting no shadow
    shadow = t.node("ShaderNodeLightPath", 1, -6).outputs["Is Shadow Ray"]
    rim = t.math("MULTIPLY", rim, t.math("SUBTRACT", 1.0, shadow, x=2, y=-6), x=2.5, y=-2)
    transparent = t.node("ShaderNodeBsdfTransparent", 2, 1).outputs[0]
    refraction = t.node(
        "ShaderNodeBsdfRefraction",
        2,
        -4,
        {"IOR": t.math("MULTIPLY_ADD", air, REFRACTION, 1.0, x=1, y=-4), "Roughness": 0.0},
    ).outputs[0]
    cycles = t.node("ShaderNodeMixShader", 3, 0, {0: rim, 1: transparent, 2: refraction})
    glossy = t.node("ShaderNodeBsdfGlossy", 2, -6, {"Roughness": 0.05}).outputs[0]
    eevee = t.node(
        "ShaderNodeMixShader",
        3,
        -4,
        {0: t.math("MULTIPLY", rim, GLINT, x=2.5, y=-3), 1: transparent, 2: glossy},
    )
    t.node("ShaderNodeOutputMaterial", 4, 0, {"Surface": cycles.outputs[0]}, target="CYCLES")
    t.node("ShaderNodeOutputMaterial", 4, -4, {"Surface": eevee.outputs[0]}, target="EEVEE")
    return material


def build_dust_material():
    """Grey brown dust with a finer billowing detail"""
    material = bpy.data.materials.new(DUST)
    tree = material.node_tree
    tree.nodes.clear()
    t = Tree(tree, spacing=(200, 180))
    density = t.node(
        "ShaderNodeAttribute", 0, 0, attribute_type="GEOMETRY", attribute_name="density"
    ).outputs["Fac"]
    detail = t.node(
        "ShaderNodeTexNoise",
        0,
        -2,
        {
            "Vector": t.node("ShaderNodeTexCoord", -1, -2).outputs["Object"],
            "Scale": DETAIL,
            "Detail": 4.0,
        },
    ).outputs["Fac"]
    detail = t.node(
        "ShaderNodeMapRange",
        1,
        -2,
        {"Value": detail, "From Min": 0.3, "From Max": 0.7, "To Min": 0.3, "To Max": 1.0},
    ).outputs[0]
    density = t.math(
        "MULTIPLY", t.math("MULTIPLY", density, detail, x=2, y=0), DUST_DENSITY, x=3, y=0
    )
    for i, (target, boost) in enumerate((("CYCLES", 1.0), ("EEVEE", EEVEE_DENSITY))):
        volume = t.node(
            "ShaderNodeVolumePrincipled",
            4,
            -i * 3,
            {
                "Color": (0.68, 0.62, 0.54, 1.0),
                "Density": t.math("MULTIPLY", density, boost, x=3.5, y=-i * 3),
                "Anisotropy": 0.3,
            },
        )
        # The density read here only, not squared by the default attribute
        volume.inputs["Density Attribute"].default_value = ""
        t.node("ShaderNodeOutputMaterial", 5, -i * 3, {"Volume": volume.outputs[0]}, target=target)
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material(), build_dust_material()), fake_user=True)
