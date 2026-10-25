# Build foam.blend: the Foam node group, the foam and the bubbles materials
# Usage: Blender --background --factory-startup --python foam_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write

RESOURCE = "foam.blend"
NODE_GROUP = "MustardUI Foam"
MATERIAL = "MustardUI Foam"
BUBBLES = "MustardUI Foam Bubbles"
# Height of the foam over the mesh where it ends, not to flicker with it
LIFT = 0.0003
# At least as high as the subdivided mesh sinks under the faces, relative to their edges
LIFT_EDGE = 0.04
# Height of the single layer of bubbles at the lacy border, relative to Bubble Size
LAYER = 1.0
# Rounds smoothing the height and the normal of the foam, on the mesh before subdividing it
SMOOTH = 3
# Raggedness of the border, relative to the Control radius, and its features per Clump Scale
RAGGED = 0.5
RAGGED_SCALE = 0.6
# Fade of the smoothing to the border of the faces reached, past the foam, relative to the
# Controls radius
INNER = 0.4
# Faces reached, relative to the Controls radius, past the ragged border and the fade above
REACH = 1.0 + RAGGED + INNER
# Lumps on the clumps per Clump Scale, their radius relative to their cell and their share of the
# height at full Clumps
LUMP_SCALE = 3.0
LUMP_RADIUS = 0.8
LUMPS = 0.6
# Points across each lump the foam is subdivided to, at most MAX_LEVEL times and MAX_FACES faces
LUMP_STEPS = 3.0
# Sliding features per Clump Scale, and the share of the Speed varying between them
SLIDE_SCALE = 0.3
SLIDE_VARIATION = 0.5
# Rounds smoothing the sliding over the mesh
SLIDE_SMOOTH = 20
# Shares of the slide sampled for the trail, from where it started, the most foam left there at
# full Trail, and how much less where it slid from earlier
TRAIL_STEPS = (0.0, 0.25, 0.5, 0.75)
TRAIL = 0.6
TRAIL_FADE = 0.6
# Amount of the foam passing that leaves the whole trail
TRAIL_LEFT = 0.15
# Streaks of the trail per Clump Scale
STREAKS = 2.0
# Most rounds smoothing the mesh under the thick foam
MAX_SPREAD = 200.0
# Edges in the denser parts of the mesh, relative to the mean edge
DENSE = 0.5
# Share of the Thickness over which the mesh under the foam is fully smoothed
FULL_SMOOTH = 0.3
# Least height of the foam over the mesh under it, relative to its height
COVER = 0.25
MAX_LEVEL = 3.0
MAX_FACES = 200000.0
# Amount of foam over which the bubbles are as many as Density
FULL = 0.3
# Distance from the foam at rest over which the bubbles are dropped, relative to the mesh edges
OFF = 0.25
# Height of the bubble centers over the foam, and their part kept below it, relative to them
RAISE = 0.3
CUT = 0.6
# Height of the white meniscus of the bubbles over the foam, relative to them, and the white of
# their film above it
MENISCUS = 0.2
MILK = 0.06
# Thickness of the soap film of the bubbles, in nanometers at full Iridescence
FILM = (250.0, 750.0)
SOAP_IOR = 1.33
# Reflection of the soap film, its two faces and their interference brighter than water, and the
# most of the light it takes from what is seen through it at grazing angles, the foam around it
# reflected there rather than the surroundings
SHINE = 3.0
EDGE = 0.4
# Layers of bubbles drawn on the foam, each smaller by DECAY, and the share of their cells used at
# Coverage 0.5
LAYERS = 6
DECAY = 0.6
PRESENCE = (0.45, 0.55, 0.55, 0.5, 0.45, 0.4)
# Share of each layer seen through, the smaller bubbles white as they scatter the light
SEE = (1.0, 0.8, 0.5, 0.2, 0.0, 0.0)
# Radius of the drawn bubbles relative to their cell, and the height of their caps
RADIUS = (0.22, 0.45)
CAP = 0.6
# Foam seen through the drawn bubbles a little darker, their rim white as the walls between them,
# and the share of the surface under the foam seen through them where it is thick
DEPTH = 0.15
THICK_SEE = 0.6
# Light let through the foam to the surface under it, scattered by its bubbles
FOAM_LIGHT = 0.6
RIM = 0.8
# At the lacy border: the start of the rim of the bubbles, thin walls between them, and the share
# of the foam seen through between the bubbles
LACE_RIM = 0.92
LACE_GAP = 0.8
# Share of the Lace over which the foam fades out at its border
FADE = 1.0
ROUGHNESS = (0.4, 0.08)
# Light scattering in the foam, relative to Bubble Size
SCATTER = 1.5
# Shade variation of the foam per meter
SHADE = 30.0


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Cover the mesh inside the spheres of the Controls with soap foam, puffy clumps thinning "
        "to a lacy layer of bubbles at the border, with soap bubbles on it"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Controls",
        "NodeSocketCollection",
        description="Empties whose spheres define the foam area",
    )
    add_input(
        ng,
        "Amount",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Amount of foam, animate it to wash the foam away from its border",
    )
    add_input(
        ng,
        "Start Frame",
        "NodeSocketInt",
        description="Frame the bubbles start popping and the foam sliding",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.012,
        min_value=0.0,
        description="Height of the thickest clumps of foam",
    )
    add_input(
        ng,
        "Falloff",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="Width of the ragged border of the foam, relative to the Controls radius",
    )
    add_input(
        ng,
        "Clumps",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.7,
        min_value=0.0,
        max_value=1.0,
        description="Foam gathered in puffy clumps, with gaps between them",
    )
    add_input(
        ng,
        "Clump Scale",
        "NodeSocketFloat",
        default_value=30.0,
        min_value=0.0,
        description="Number of clumps per meter",
    )
    add_input(
        ng,
        "Lace",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Width of the border where the foam is a single lacy layer of bubbles, "
        "showing the surface through them",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the foam",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(0.95, 0.95, 0.95, 1.0),
        description="Color of the foam",
    )
    add_input(ng, "Material", "NodeSocketMaterial", description="Material of the foam")
    panel = ng.interface.new_panel("Bubbles")
    add_input(
        ng,
        "Bubble Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0012,
        min_value=0.0,
        description="Radius of the largest bubbles drawn on the foam, smaller ones filling the "
        "gaps between them",
    )
    add_input(
        ng,
        "Coverage",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Share of the foam covered by the bubbles drawn on it, packed at 1",
    )
    add_input(
        ng,
        "Iridescence",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Rainbow colors of the soap film of the bubbles",
    )
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        panel,
        default_value=6000.0,
        min_value=0.0,
        max_value=200000.0,
        description="Soap bubbles on the foam per square meter",
    )
    add_input(
        ng,
        "Min Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0006,
        min_value=0.0,
        description="Radius of the smallest soap bubbles",
    )
    add_input(
        ng,
        "Max Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.003,
        min_value=0.0,
        description="Radius of the largest soap bubbles, fewer than the small ones",
    )
    add_input(
        ng,
        "Pop Rate",
        "NodeSocketFloat",
        panel,
        default_value=0.0,
        min_value=0.0,
        description="Chance per second of each soap bubble to pop, from the Start Frame",
    )
    add_input(ng, "Seed", "NodeSocketInt", panel, description="Seed of the bubbles placement")
    add_input(
        ng, "Bubble Material", "NodeSocketMaterial", panel, description="Material of the bubbles"
    )
    panel = ng.interface.new_panel("Sliding", default_closed=True)
    # In the panel header
    add_input(
        ng,
        "Sliding",
        "NodeSocketBool",
        panel,
        default_value=False,
        description="The foam sliding down the mesh with gravity, simulated from the Start Frame",
    ).is_panel_toggle = True
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        panel,
        default_value=0.002,
        min_value=0.0,
        description="Speed of the foam on a vertical surface, in meters per second, some parts "
        "faster than others",
    )
    add_input(
        ng,
        "Trail",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Thin trail of foam left where it slid, fading where it slid from earlier",
    )

    t = Tree(ng, spacing=(200, 160))
    t.section("Rest")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
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

    # The foam sliding, its rest position moved up the mesh to show it lower
    components = t.node("GeometryNodeSeparateComponents", 0, 1, {0: inputs["Geometry"]}).outputs
    mesh, offset, shift = build_slide(t, inputs, components["Mesh"], rest)

    t.section("Reach", row=True)
    # Distance from the closest sphere of the Controls, in its space, slid and not
    controls = t.node(
        "GeometryNodeCollectionInfo",
        0,
        2,
        {"Collection": inputs["Controls"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    mesh = t.store(mesh, ".foam_distance", "FLOAT", 1e9, 1, 0)
    mesh = t.store(mesh, ".foam_still", "FLOAT", 1e9, 2, 0)
    repeat_in = t.node("GeometryNodeRepeatInput", 3, 0)
    repeat_out = t.node("GeometryNodeRepeatOutput", 9, 0)
    repeat_in.pair_with_output(repeat_out)
    count = t.node(
        "GeometryNodeAttributeDomainSize", 2, 2, {"Geometry": controls}, component="INSTANCES"
    ).outputs["Instance Count"]
    t.connect(count, repeat_in.inputs["Iterations"])
    t.connect(mesh, repeat_in.inputs["Geometry"])
    inverse = t.node(
        "FunctionNodeInvertMatrix",
        5,
        -2,
        {
            0: t.node(
                "GeometryNodeSampleIndex",
                4,
                -2,
                {
                    "Geometry": controls,
                    "Value": t.node("GeometryNodeInstanceTransform", 3, -2).outputs[0],
                    "Index": repeat_in.outputs["Iteration"],
                },
                data_type="FLOAT4X4",
                domain="INSTANCE",
            ).outputs[0]
        },
    ).outputs[0]
    mesh = repeat_in.outputs["Geometry"]
    for i, (name, point) in enumerate(
        ((".foam_distance", t.vmath("ADD", position, shift, x=5, y=-4)), (".foam_still", position))
    ):
        local = t.node(
            "FunctionNodeTransformPoint", 6, -3 - 2 * i, {"Vector": point, "Transform": inverse}
        ).outputs[0]
        closest = t.math(
            "MINIMUM",
            t.attribute(name, "FLOAT", 6, -4 - 2 * i),
            t.vmath("LENGTH", local, x=7, y=-3 - 2 * i),
            x=8,
            y=-3 - 2 * i,
        )
        mesh = t.store(mesh, name, "FLOAT", closest, 7 + i * 0.5, 0)
    t.connect(mesh, repeat_out.inputs["Geometry"])
    mesh = repeat_out.outputs["Geometry"]

    # The faces the foam can reach, without the attributes of the mesh
    source = t.node("GeometryNodeCaptureAttribute", 10, 0, {"Geometry": mesh})
    for data_type, name, value in (
        ("VECTOR", "Rest", t.vmath("ADD", rest, offset, x=9, y=-2)),
        ("VECTOR", "Still Rest", rest),
        ("VECTOR", "Offset", offset),
        ("FLOAT", "Distance", t.attribute(".foam_distance", "FLOAT", 9, -3)),
        ("FLOAT", "Still Distance", t.attribute(".foam_still", "FLOAT", 9, -3.5)),
        # As floats, any point of a face reached
        (
            "FLOAT",
            "Near",
            t.math("LESS_THAN", t.attribute(".foam_distance", "FLOAT", 8, -4), REACH, x=9, y=-4),
        ),
        (
            "FLOAT",
            "Still Near",
            t.math("LESS_THAN", t.attribute(".foam_still", "FLOAT", 8, -5), REACH, x=9, y=-5),
        ),
    ):
        source.capture_items.new(data_type, name)
        t.connect(value, source.inputs[name])
    source = source.outputs
    rest = source["Rest"]
    patch = t.node(
        "GeometryNodeDeleteGeometry",
        11,
        0,
        {
            "Geometry": source["Geometry"],
            # Where the foam is and where it slid from, leaving its trail
            "Selection": t.math(
                "LESS_THAN",
                t.math("MAXIMUM", source["Near"], source["Still Near"], x=10, y=-1),
                0.01,
                x=11,
                y=-1,
            ),
        },
        domain="FACE",
    ).outputs[0]
    patch = t.strip(patch, 12, 0)

    ends = t.node("GeometryNodeInputMeshEdgeVertices", 10, -1).outputs
    edges = t.node(
        "GeometryNodeAttributeStatistic",
        11,
        -1,
        {
            "Geometry": patch,
            "Attribute": t.vmath("DISTANCE", ends["Position 1"], ends["Position 2"], x=11, y=-2),
        },
        domain="EDGE",
    ).outputs
    edge = edges["Mean"]
    step = t.math(
        "DIVIDE",
        1.0,
        t.math("MULTIPLY", inputs["Clump Scale"], LUMP_SCALE * LUMP_STEPS, x=11, y=-3),
        x=12,
        y=-3,
    )
    # By the size of the faces covering most of the area, in meshes denser in parts
    area = t.node("GeometryNodeInputMeshFaceArea", 10, -8).outputs[0]
    sums = [
        t.node(
            "GeometryNodeAttributeStatistic",
            11,
            -8 - i,
            {"Geometry": patch, "Attribute": value},
            domain="FACE",
        ).outputs["Sum"]
        for i, value in enumerate((t.math("MULTIPLY", area, area, x=10, y=-9), area))
    ]
    size = t.math("SQRT", t.math("DIVIDE", sums[0], sums[1], x=12, y=-8), x=13, y=-8)
    level = t.math("LOGARITHM", t.math("DIVIDE", size, step, x=12, y=-1), 2.0, x=13, y=-1)
    faces = t.node(
        "GeometryNodeAttributeDomainSize", 11, -4, {"Geometry": patch}, component="MESH"
    ).outputs["Face Count"]
    most = t.math("LOGARITHM", t.math("DIVIDE", MAX_FACES, faces, x=12, y=-4), 4.0, x=13, y=-4)
    # At least once, on the smooth surface of the mesh subdivided by the next modifiers
    level = t.math(
        "MINIMUM",
        t.math("MAXIMUM", t.math("ROUND", level, x=14, y=-1), 1.0, x=15, y=-1),
        MAX_LEVEL,
        x=16,
        y=-1,
    )
    level = t.math(
        "MAXIMUM",
        t.math("MINIMUM", level, t.math("FLOOR", most, x=14, y=-4), x=17, y=-2),
        0.0,
        x=18,
        y=-2,
    )
    # As far on the subdivided mesh
    rounds = t.math("MULTIPLY", t.math("POWER", 2.0, level, x=18, y=-3), SMOOTH, x=19, y=-3)
    # Rounds smoothing the mesh before subdividing it, more in its denser parts
    spread = t.math(
        "POWER",
        t.math(
            "DIVIDE", inputs["Thickness"], t.math("MULTIPLY", edge, DENSE, x=9, y=-6), x=10, y=-6
        ),
        2.0,
        x=11,
        y=-6,
    )
    spread = t.math("MINIMUM", t.math("MAXIMUM", spread, 1.0, x=12, y=-6), MAX_SPREAD, x=13, y=-6)

    t.section("Foam", row=True)
    amount = foam_amount(t, inputs, rest, source["Distance"], 0, 0)
    # A thin trail where the foam slid, in streaks along the way, thinner where it slid from earlier
    way = t.vmath("NORMALIZE", source["Offset"], x=0, y=-8)
    across = t.vmath(
        "SUBTRACT",
        source["Still Rest"],
        t.vmath(
            "SCALE",
            way,
            t.vmath("DOT_PRODUCT", source["Still Rest"], way, x=1, y=-9),
            x=2,
            y=-9,
        ),
        x=3,
        y=-8,
    )
    streaks = t.node(
        "ShaderNodeMapRange",
        5,
        -8,
        {
            "Value": t.node(
                "ShaderNodeTexNoise",
                4,
                -8,
                {
                    "Vector": across,
                    "Scale": t.math("MULTIPLY", inputs["Clump Scale"], STREAKS, x=3, y=-10),
                    "Detail": 2.0,
                },
            ).outputs["Fac"],
            "From Min": 0.4,
            "From Max": 0.65,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    trail = None
    for i, share in enumerate(TRAIL_STEPS):
        y = -12 - 4 * i
        coord = t.vmath(
            "MULTIPLY_ADD",
            source["Offset"],
            t.node("ShaderNodeCombineXYZ", 0, y, {"X": share, "Y": share, "Z": share}).outputs[0],
            source["Still Rest"],
            x=1,
            y=y,
        )
        distance = t.math(
            "MULTIPLY_ADD",
            t.math("SUBTRACT", source["Distance"], source["Still Distance"], x=0, y=y - 1),
            share,
            source["Still Distance"],
            x=1,
            y=y - 1,
        )
        left = t.math(
            "MULTIPLY",
            # Any foam passing leaving it
            t.node(
                "ShaderNodeMapRange",
                7,
                y,
                {
                    "Value": foam_amount(t, inputs, coord, distance, 2, y),
                    "From Max": TRAIL_LEFT,
                },
                interpolation_type="SMOOTHSTEP",
            ).outputs[0],
            t.math(
                "MULTIPLY",
                inputs["Trail"],
                TRAIL * (1.0 - TRAIL_FADE * (1.0 - share)),
                x=8,
                y=y - 1,
            ),
            x=9,
            y=y,
        )
        trail = left if trail is None else t.math("MAXIMUM", trail, left, x=10, y=y)
    trail = t.node(
        "GeometryNodeSwitch",
        11,
        -12,
        {
            "Switch": inputs["Sliding"],
            "False": 0.0,
            "True": t.math("MULTIPLY", trail, streaks, x=10.5, y=-12),
        },
        input_type="FLOAT",
    ).outputs[0]
    amount = t.math("MAXIMUM", amount, trail, x=12, y=-5)
    # Rounded lumps on them, as packed blobs
    lump = t.node(
        "ShaderNodeTexVoronoi",
        1,
        -9,
        {
            "Vector": rest,
            "Scale": t.math("MULTIPLY", inputs["Clump Scale"], LUMP_SCALE, x=0, y=-10),
        },
        voronoi_dimensions="3D",
    ).outputs["Distance"]
    lump = t.math(
        "SUBTRACT",
        1.0,
        t.math("POWER", t.math("DIVIDE", lump, LUMP_RADIUS, x=2, y=-9), 2.0, x=3, y=-9),
        x=4,
        y=-9,
    )
    lump = t.math("SQRT", t.math("MAXIMUM", lump, 0.0, x=5, y=-9), x=6, y=-9)
    lumps = t.math("MULTIPLY", inputs["Clumps"], LUMPS, x=5, y=-10)
    lump = t.math("MULTIPLY_ADD", t.math("SUBTRACT", lump, 1.0, x=7, y=-9), lumps, 1.0, x=8, y=-9)

    # A layer of bubbles at the lacy border, rising steeply to the clumps
    lace = t.node(
        "ShaderNodeMapRange",
        9,
        -7,
        {
            "Value": amount,
            "From Max": t.math("MAXIMUM", inputs["Lace"], 0.0001, x=8, y=-8),
            "To Min": 1.0,
            "To Max": 0.0,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    body = t.node(
        "ShaderNodeMapRange", 9, -5, {"Value": amount, "From Min": inputs["Lace"]}
    ).outputs[0]
    body = t.math("MULTIPLY", t.math("SQRT", body, x=10, y=-5), lump, x=10, y=-6)
    layer = t.math("MULTIPLY", inputs["Bubble Size"], LAYER, x=9, y=-9)
    layer = t.math(
        "MULTIPLY", layer, t.math("MULTIPLY", amount, 50.0, x=9, y=-10, clamp=True), x=10, y=-9
    )
    height = t.math("MULTIPLY_ADD", body, inputs["Thickness"], layer, x=11, y=-6)
    lift = t.math("MAXIMUM", t.math("MULTIPLY", edge, LIFT_EDGE, x=11, y=-8), LIFT, x=12, y=-8)
    height = t.math("ADD", height, lift, x=12, y=-6)

    t.section("Shape", row=True)
    # On the mesh before subdividing it, smoothed as much as the foam is thick, bridging the small
    # bumps and pits, at least COVER of the height over the mesh where that sank it
    coarse = t.node("GeometryNodeCaptureAttribute", 1, 0, {"Geometry": patch})
    thick = t.math(
        "DIVIDE",
        height,
        t.math(
            "MAXIMUM",
            t.math("MULTIPLY", inputs["Thickness"], FULL_SMOOTH, x=-1, y=-4),
            0.0001,
            x=0,
            y=-4,
        ),
        x=0,
        y=-3,
        clamp=True,
    )
    for data_type, name, value in (
        ("VECTOR", "Posed", position),
        ("FLOAT", "Height", height),
        ("FLOAT", "Weight", thick),
    ):
        coarse.capture_items.new(data_type, name)
        t.connect(value, coarse.inputs[name])
    coarse = coarse.outputs
    # Not reaching the border of the faces, not to change as faces there come and go
    inner = t.node(
        "ShaderNodeMapRange",
        1,
        -6,
        {
            "Value": source["Distance"],
            "From Min": REACH,
            "From Max": REACH - INNER,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]

    def smoothed(value, x, y):
        """Twice the blur minus the blur of it: small features gone, large curves hardly shrunk"""
        blur = [value]
        for i in range(2):
            blur.append(
                t.node(
                    "GeometryNodeBlurAttribute",
                    x + i * 0.5,
                    y - i,
                    {"Value": blur[-1], "Iterations": spread, "Weight": inner},
                    data_type="FLOAT_VECTOR",
                ).outputs[0]
            )
        blurred = t.vmath(
            "SUBTRACT", t.vmath("SCALE", blur[1], 2.0, x=x + 1, y=y - 2), blur[2], x=x + 1, y=y - 1
        )
        return socket(
            t.node(
                "ShaderNodeMix",
                x + 1,
                y,
                {"Factor": coarse["Weight"], "A": value, "B": blurred},
                data_type="VECTOR",
            ).outputs,
            "Result",
        )

    base = t.node(
        "GeometryNodeSetPosition",
        4,
        0,
        {"Geometry": coarse["Geometry"], "Position": smoothed(position, 2, -2)},
    ).outputs[0]
    up = smooth_normal(t, SMOOTH, 4, -6)
    below = t.vmath(
        "DOT_PRODUCT",
        t.vmath(
            "SUBTRACT",
            coarse["Posed"],
            t.vmath(
                "MULTIPLY_ADD",
                up,
                t.node(
                    "ShaderNodeCombineXYZ",
                    4,
                    -8,
                    {"X": coarse["Height"], "Y": coarse["Height"], "Z": coarse["Height"]},
                ).outputs[0],
                t.node("GeometryNodeInputPosition", 4, -9).outputs[0],
                x=5,
                y=-8,
            ),
            x=6,
            y=-7,
        ),
        up,
        x=7,
        y=-7,
    )
    push = t.math(
        "MAXIMUM", t.math("MULTIPLY_ADD", coarse["Height"], COVER, below, x=8, y=-7), 0.0, x=9, y=-7
    )
    # The smoothing sinking it into large curves made up, by its average around, the small bumps
    # showing through
    sink = t.vmath(
        "DOT_PRODUCT",
        t.vmath(
            "SUBTRACT",
            coarse["Posed"],
            t.node("GeometryNodeInputPosition", 6, -11).outputs[0],
            x=7,
            y=-11,
        ),
        up,
        x=8,
        y=-11,
    )

    # Over about the Thickness around, by the mean edge
    reach = t.math(
        "MINIMUM",
        t.math("POWER", t.math("DIVIDE", inputs["Thickness"], edge, x=8, y=-13), 2.0, x=9, y=-13),
        MAX_SPREAD,
        x=9.5,
        y=-13,
    )

    def around(value, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            10,
            y,
            {"Value": value, "Iterations": reach, "Weight": inner},
            data_type="FLOAT",
        ).outputs[0]

    shaped = t.node("GeometryNodeCaptureAttribute", 10, 0, {"Geometry": base})
    for data_type, name, value in (
        ("FLOAT", "Push", t.math("MAXIMUM", around(push, -7), around(sink, -11), x=11, y=-9)),
        ("VECTOR", "Texture Base", smoothed(rest, 8, -10)),
    ):
        shaped.capture_items.new(data_type, name)
        t.connect(value, shaped.inputs[name])
    shaped = shaped.outputs
    patch = t.node(
        "GeometryNodeSubdivisionSurface",
        11,
        0,
        {"Mesh": shaped["Geometry"], "Level": level},
    ).outputs[0]

    # Only the faces with foam
    captured = t.node("GeometryNodeCaptureAttribute", 13, 0, {"Geometry": patch})
    for data_type, name, value in (
        ("FLOAT", "Amount", amount),
        ("FLOAT", "Height", height),
        ("FLOAT", "Lace", lace),
    ):
        captured.capture_items.new(data_type, name)
        t.connect(value, captured.inputs[name])
    captured = captured.outputs
    patch = t.node(
        "GeometryNodeDeleteGeometry",
        14,
        0,
        {
            "Geometry": captured["Geometry"],
            "Selection": t.math("LESS_THAN", captured["Amount"], 0.000001, x=13, y=-2),
        },
        domain="FACE",
    ).outputs[0]
    # Smoothed but at the border, staying on the mesh
    smooth = t.node(
        "GeometryNodeBlurAttribute",
        20,
        -2,
        {"Value": captured["Height"], "Iterations": rounds},
        data_type="FLOAT",
    ).outputs[0]
    smooth = t.node(
        "GeometryNodeSwitch",
        21,
        -2,
        {
            "Switch": t.math("GREATER_THAN", captured["Amount"], 0.0, x=20, y=-4),
            "False": captured["Height"],
            "True": smooth,
        },
        input_type="FLOAT",
    ).outputs[0]
    patch = t.store(patch, ".foam_height", "FLOAT", smooth, 22, 0)

    t.section("Shell", row=True)
    height = t.math("ADD", t.attribute(".foam_height", "FLOAT", 0, -3), shaped["Push"], x=1, y=-3)

    def raised(geometry, x, y):
        """The geometry raised by the foam along its normal, smoothed not to cross itself"""
        offset = t.vmath("SCALE", smooth_normal(t, rounds, x, y - 2), height, x=x + 1, y=y - 2)
        return t.node(
            "GeometryNodeSetPosition", x + 1, y, {"Geometry": geometry, "Offset": offset}
        ).outputs[0]

    shell = raised(patch, 1, 0)
    top = t.node("GeometryNodeCaptureAttribute", 3, 0, {"Geometry": shell})
    for name, value in (
        ("Top", t.node("GeometryNodeInputPosition", 2, -3).outputs[0]),
        ("Up", t.node("GeometryNodeInputNormal", 2, -4).outputs[0]),
    ):
        top.capture_items.new("VECTOR", name)
        t.connect(value, top.inputs[name])
    top = top.outputs
    # The texture coordinates on the foam shaped the same at rest, following its surface
    texture = t.node(
        "GeometryNodeSetPosition",
        4,
        3,
        {"Geometry": top["Geometry"], "Position": shaped["Texture Base"]},
    ).outputs[0]
    texture = t.node("GeometryNodeCaptureAttribute", 7, 3, {"Geometry": raised(texture, 5, 3)})
    texture.capture_items.new("VECTOR", "Texture")
    t.connect(t.node("GeometryNodeInputPosition", 6, 2).outputs[0], texture.inputs["Texture"])
    texture = texture.outputs
    shell = t.node(
        "GeometryNodeSetPosition",
        8,
        0,
        {"Geometry": texture["Geometry"], "Position": top["Top"]},
    ).outputs[0]
    foam_shell = shell
    shell = t.node("GeometryNodeSetShadeSmooth", 2, 0, {"Geometry": shell}).outputs[0]
    # For the shader: rest position and lace, color and iridescence, bubble size
    rest_xyz = t.node("ShaderNodeSeparateXYZ", 8, -2, {0: texture["Texture"]}).outputs
    packed = t.node(
        "FunctionNodeCombineColor",
        3,
        -2,
        {
            "Red": rest_xyz["X"],
            "Green": rest_xyz["Y"],
            "Blue": rest_xyz["Z"],
            "Alpha": captured["Lace"],
        },
    ).outputs[0]
    shell = t.store(shell, "foam", "FLOAT_COLOR", packed, 4, 0)
    rgb = t.node("FunctionNodeSeparateColor", 3, -4, {0: inputs["Color"]}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        4,
        -4,
        {
            "Red": rgb["Red"],
            "Green": rgb["Green"],
            "Blue": rgb["Blue"],
            "Alpha": inputs["Iridescence"],
        },
    ).outputs[0]
    shell = t.store(shell, "foam_color", "FLOAT_COLOR", color, 5, 0)
    # Fading out at the border
    fade = t.node(
        "ShaderNodeMapRange",
        8,
        -8,
        {
            "Value": captured["Amount"],
            "From Max": t.math(
                "MAXIMUM", t.math("MULTIPLY", inputs["Lace"], FADE, x=7, y=-9), 0.02, x=8, y=-9
            ),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    bubbles = t.node(
        "ShaderNodeCombineXYZ",
        9,
        -6,
        {"X": inputs["Bubble Size"], "Y": inputs["Coverage"], "Z": fade},
    ).outputs[0]
    shell = t.store(shell, "foam_bubbles", "FLOAT_VECTOR", bubbles, 6, 0)
    # Without the hidden attributes
    shell = t.node(
        "GeometryNodeRemoveAttribute",
        6.5,
        0,
        {"Geometry": shell, "Pattern Mode": "Wildcard", "Name": ".foam_*"},
    ).outputs[0]
    shell = t.node(
        "GeometryNodeSetMaterial", 7, 0, {"Geometry": shell, "Material": inputs["Material"]}
    ).outputs[0]
    # As an instance, not to be subdivided by the next modifiers
    shell = t.node("GeometryNodeGeometryToInstance", 8, 0, {0: shell}).outputs[0]

    t.section("Bubbles", row=True)
    # Placed on the whole rest mesh where the foam started, not to move on the deformed one nor as
    # the foam changes
    still = t.node(
        "GeometryNodeSetPosition",
        0,
        0,
        {"Geometry": source["Geometry"], "Position": source["Still Rest"]},
    ).outputs[0]
    bubbles = t.node(
        "GeometryNodeDistributePointsOnFaces",
        1,
        0,
        {
            "Mesh": still,
            "Selection": t.math("GREATER_THAN", source["Still Near"], 0.01, x=0, y=-2),
            "Density": inputs["Density"],
            "Seed": inputs["Seed"],
        },
        distribute_method="RANDOM",
    ).outputs["Points"]
    bubbles = t.strip(bubbles, 2, 0)
    # On the foam closest to them at rest, slid with it, none where there is no foam
    foam_rest = t.node(
        "GeometryNodeSetPosition",
        2,
        3,
        {"Geometry": foam_shell, "Position": source["Still Rest"]},
    ).outputs[0]
    point = t.node("GeometryNodeInputPosition", 3, -3).outputs[0]
    # Where they show slid, back on the surface the offset left along a straight line
    slid = t.vmath(
        "SUBTRACT",
        point,
        t.node(
            "GeometryNodeSampleNearestSurface",
            4,
            -5,
            {"Mesh": still, "Value": source["Offset"], "Sample Position": point},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"],
        x=5,
        y=-5,
    )
    slid = t.node(
        "GeometryNodeSampleNearestSurface",
        6,
        -5,
        {
            "Mesh": still,
            "Value": t.node("GeometryNodeInputPosition", 5, -6).outputs[0],
            "Sample Position": slid,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    where = t.node(
        "GeometryNodeSwitch",
        7,
        -4,
        {"Switch": inputs["Sliding"], "False": point, "True": slid},
        input_type="VECTOR",
    ).outputs[0]
    sampled = t.node("GeometryNodeCaptureAttribute", 8, 0, {"Geometry": bubbles})
    for i, (data_type, name, value) in enumerate(
        (
            ("FLOAT", "Amount", captured["Amount"]),
            ("VECTOR", "Top", top["Top"]),
            ("VECTOR", "Up", top["Up"]),
            ("VECTOR", "Rest", source["Still Rest"]),
        )
    ):
        sample = t.node(
            "GeometryNodeSampleNearestSurface",
            7,
            -2 - 2 * i,
            {"Mesh": foam_rest, "Value": value, "Sample Position": where},
            data_type="FLOAT" if data_type == "FLOAT" else "FLOAT_VECTOR",
        ).outputs["Value"]
        sampled.capture_items.new(data_type, name)
        t.connect(sample, sampled.inputs[name])
    # Random values from where they are at rest, before moving them
    random = t.node(
        "ShaderNodeTexWhiteNoise", 7, -12, {"Vector": point}, noise_dimensions="3D"
    ).outputs
    for data_type, name, value in (
        ("FLOAT", "Chance", random["Value"]),
        ("VECTOR", "Random", random["Color"]),
        ("VECTOR", "Where", where),
    ):
        sampled.capture_items.new(data_type, name)
        t.connect(value, sampled.inputs[name])
    sampled = sampled.outputs
    bubbles = sampled["Geometry"]
    off = t.math(
        "GREATER_THAN",
        t.vmath("DISTANCE", sampled["Rest"], sampled["Where"], x=9, y=-3),
        t.math("MULTIPLY", edge, OFF, x=9, y=-4),
        x=10,
        y=-3,
    )
    values = t.node("ShaderNodeSeparateXYZ", 3, -3, {0: sampled["Random"]}).outputs
    # Fewer where the foam is thin, popping at random from the Start Frame
    sparse = t.math(
        "GREATER_THAN",
        sampled["Chance"],
        t.math("DIVIDE", sampled["Amount"], FULL, x=3, y=-2),
        x=4,
        y=-2,
    )
    time = t.node("GeometryNodeInputSceneTime", 2, -6).outputs
    age = t.math(
        "MULTIPLY",
        t.math("SUBTRACT", time["Frame"], inputs["Start Frame"], x=3, y=-6),
        t.math("DIVIDE", time["Seconds"], time["Frame"], x=3, y=-7),
        x=4,
        y=-6,
    )
    life = t.math(
        "DIVIDE",
        t.math(
            "MULTIPLY",
            t.math(
                "LOGARITHM", t.math("SUBTRACT", 1.0, values["Y"], x=3, y=-8), 2.718281828, x=4, y=-8
            ),
            -1.0,
            x=5,
            y=-8,
        ),
        inputs["Pop Rate"],
        x=6,
        y=-8,
    )
    popped = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", age, life, x=7, y=-7),
        t.math("GREATER_THAN", inputs["Pop Rate"], 0.0, x=7, y=-8),
        x=8,
        y=-7,
    )
    bubbles = t.node(
        "GeometryNodeDeleteGeometry",
        9,
        0,
        {
            "Geometry": bubbles,
            "Selection": t.math(
                "MAXIMUM", t.math("MAXIMUM", sparse, popped, x=9, y=-2), off, x=10, y=-2
            ),
        },
    ).outputs[0]

    # Mostly small, half sunk in the foam
    radius = t.node(
        "ShaderNodeMapRange",
        5,
        -4,
        {
            "Value": t.math("POWER", values["X"], 2.0, x=4, y=-4),
            "To Min": inputs["Min Radius"],
            "To Max": inputs["Max Radius"],
        },
    ).outputs[0]
    normal = t.vmath("NORMALIZE", sampled["Up"], x=8, y=-4)
    bubbles = t.node(
        "GeometryNodeSetPosition",
        10,
        0,
        {
            "Geometry": bubbles,
            "Position": t.vmath(
                "ADD",
                sampled["Top"],
                t.vmath("SCALE", normal, t.math("MULTIPLY", radius, RAISE, x=9, y=-6), x=9, y=-5),
                x=10,
                y=-4,
            ),
        },
    ).outputs[0]
    film = t.math(
        "MULTIPLY",
        t.math("MULTIPLY_ADD", values["Z"], FILM[1] - FILM[0], FILM[0], x=10, y=-7),
        inputs["Iridescence"],
        x=11,
        y=-7,
    )
    bubbles = t.store(bubbles, "foam_film", "FLOAT", film, 11, 0)
    sphere = t.node(
        "GeometryNodeMeshUVSphere", 10, -10, {"Segments": 16, "Rings": 8, "Radius": 1.0}
    )
    sphere_z = t.node(
        "ShaderNodeSeparateXYZ",
        10,
        -12,
        {0: t.node("GeometryNodeInputPosition", 9, -12).outputs[0]},
    ).outputs["Z"]
    sphere = t.node(
        "GeometryNodeDeleteGeometry",
        11,
        -10,
        {
            "Geometry": sphere.outputs["Mesh"],
            "Selection": t.math("LESS_THAN", sphere_z, -CUT, x=11, y=-12),
        },
    ).outputs[0]
    sphere = t.node("GeometryNodeSetShadeSmooth", 12, -10, {"Geometry": sphere}).outputs[0]
    sphere = t.node(
        "GeometryNodeSetMaterial",
        13,
        -10,
        {"Geometry": sphere, "Material": inputs["Bubble Material"]},
    ).outputs[0]
    rotation = t.node(
        "FunctionNodeAlignRotationToVector", 12, -4, {"Vector": normal}, axis="Z"
    ).outputs[0]
    bubbles = t.node(
        "GeometryNodeInstanceOnPoints",
        14,
        0,
        {"Points": bubbles, "Instance": sphere, "Rotation": rotation, "Scale": radius},
    ).outputs[0]

    # The mesh first, the foam and the bubbles as instances
    output = t.node("GeometryNodeJoinGeometry", 15, 2)
    for name in ("Instances", "Volume", "Point Cloud", "Grease Pencil", "Curve"):
        t.connect(components[name], output.inputs[0])
    t.connect(bubbles, output.inputs[0])
    t.connect(shell, output.inputs[0])
    t.connect(components["Mesh"], output.inputs[0])
    t.node("NodeGroupOutput", 16, 2, {0: output.outputs[0]})
    t.arrange()
    return ng


def foam_amount(t, inputs, coord, distance, x, y):
    """Amount of foam at the rest coordinates, by the distance from the Controls"""
    ragged = t.node(
        "ShaderNodeTexNoise",
        x,
        y,
        {
            "Vector": coord,
            "Scale": t.math("MULTIPLY", inputs["Clump Scale"], RAGGED_SCALE, x=x - 1, y=y - 1),
            "Detail": 3.0,
        },
    ).outputs["Fac"]
    falloff = t.math("MAXIMUM", inputs["Falloff"], 0.001, x=x + 1, y=y - 1)
    distance = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", ragged, 0.5, x=x + 1, y=y),
        RAGGED,
        distance,
        x=x + 2,
        y=y,
    )
    sphere = t.node(
        "ShaderNodeMapRange",
        x + 3,
        y,
        {
            "Value": distance,
            "From Min": 1.0,
            "From Max": t.math("SUBTRACT", 1.0, falloff, x=x + 2, y=y - 1),
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    # Puffy clumps
    clump = t.node(
        "ShaderNodeTexNoise",
        x,
        y - 2,
        {"Vector": coord, "Scale": inputs["Clump Scale"], "Detail": 2.0},
    ).outputs["Fac"]
    clump = t.node(
        "ShaderNodeMapRange",
        x + 1,
        y - 2,
        {"Value": clump, "From Min": 0.4, "From Max": 0.6},
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    clump = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", clump, 1.0, x=x + 2, y=y - 2),
        inputs["Clumps"],
        1.0,
        x=x + 3,
        y=y - 2,
    )
    amount = t.math("MULTIPLY", sphere, clump, x=x + 4, y=y)
    amount = t.math("MULTIPLY", amount, inputs["Mask"], x=x + 5, y=y)
    # Washed away from the thin foam first, leaving the clumps
    return t.math(
        "DIVIDE",
        t.math(
            "SUBTRACT",
            amount,
            t.math("SUBTRACT", 1.0, inputs["Amount"], x=x + 5, y=y - 1),
            x=x + 6,
            y=y,
        ),
        t.math("MAXIMUM", inputs["Amount"], 0.0001, x=x + 6, y=y - 1),
        x=x + 7,
        y=y,
        clamp=True,
    )


def smooth_normal(t, rounds, x, y):
    """Normal blurred over the rounds, not to cross itself in the folds"""
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        x,
        y,
        {"Value": t.node("GeometryNodeInputNormal", x - 1, y).outputs[0], "Iterations": rounds},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    return t.vmath("NORMALIZE", blurred, x=x + 0.5, y=y)


def build_slide(t, inputs, mesh, rest):
    """The mesh with the offsets of the foam sliding down it, in the rest space and deformed"""
    t.section("Sliding", row=True)
    posed = t.node("GeometryNodeCaptureAttribute", 1, 0, {"Geometry": mesh})
    for name, value in (
        ("Posed", t.node("GeometryNodeInputPosition", 0, -1).outputs[0]),
        ("Normal", t.node("GeometryNodeInputNormal", 0, -2).outputs[0]),
    ):
        posed.capture_items.new("VECTOR", name)
        t.connect(value, posed.inputs[name])
    posed = posed.outputs
    at_rest = t.node(
        "GeometryNodeSetPosition", 2, 0, {"Geometry": posed["Geometry"], "Position": rest}
    ).outputs[0]
    # Turning the deformed surface onto the rest one
    rest_normal = t.node("GeometryNodeInputNormal", 1, -4).outputs[0]
    turn = t.node(
        "FunctionNodeAxisAngleToRotation",
        4,
        -4,
        {
            "Axis": t.vmath(
                "NORMALIZE",
                t.vmath("CROSS_PRODUCT", posed["Normal"], rest_normal, x=2, y=-4),
                x=3,
                y=-4,
            ),
            "Angle": t.math(
                "ARCCOSINE",
                t.math(
                    "MINIMUM",
                    t.vmath("DOT_PRODUCT", posed["Normal"], rest_normal, x=2, y=-5),
                    1.0,
                    x=3,
                    y=-5,
                ),
                x=3.5,
                y=-5,
            ),
        },
    ).outputs[0]
    # Gravity along the deformed surface, in the space of the mesh
    transform = t.node(
        "GeometryNodeObjectInfo",
        1,
        -7,
        {"Object": t.node("GeometryNodeSelfObject", 0, -7).outputs[0]},
        transform_space="ORIGINAL",
    ).outputs["Transform"]
    down = t.node(
        "FunctionNodeTransformDirection",
        3,
        -7,
        {
            "Transform": t.node("FunctionNodeInvertMatrix", 2, -7, {0: transform}).outputs[0],
            "Direction": (0.0, 0.0, -1.0),
        },
    ).outputs[0]
    along = t.vmath(
        "SUBTRACT",
        down,
        t.vmath("PROJECT", down, posed["Normal"], x=4, y=-8),
        x=5,
        y=-7,
    )
    along = t.node("FunctionNodeRotateVector", 6, -6, {"Vector": along, "Rotation": turn}).outputs[
        0
    ]
    # Some parts faster than others, the rest position moving up to show the foam lower
    variation = t.node(
        "ShaderNodeMapRange",
        6,
        -9,
        {
            "Value": t.node(
                "ShaderNodeTexNoise",
                5,
                -9,
                {
                    "Vector": rest,
                    "Scale": t.math("MULTIPLY", inputs["Clump Scale"], SLIDE_SCALE, x=4, y=-10),
                },
            ).outputs["Fac"],
            "From Min": 0.3,
            "From Max": 0.7,
            "To Min": 1.0 - SLIDE_VARIATION,
            "To Max": 1.0 + SLIDE_VARIATION,
        },
    ).outputs[0]
    rate = t.vmath(
        "SCALE",
        along,
        t.math(
            "MULTIPLY", inputs["Speed"], t.math("MULTIPLY", variation, -1.0, x=7, y=-9), x=8, y=-9
        ),
        x=9,
        y=-7,
    )

    # The offsets on points, none without sliding not to cache them
    count = t.node(
        "GeometryNodeSwitch",
        3,
        3,
        {
            "Switch": inputs["Sliding"],
            "False": 0,
            "True": t.node(
                "GeometryNodeAttributeDomainSize", 2, 4, {"Geometry": mesh}, component="MESH"
            ).outputs["Point Count"],
        },
        input_type="INT",
    ).outputs[0]
    points = t.node("GeometryNodePoints", 4, 3, {"Count": count}).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 5, 3)
    sim_out = t.node("GeometryNodeSimulationOutput", 12, 3)
    sim_in.pair_with_output(sim_out)
    t.connect(points, sim_in.inputs["Geometry"])
    # Started again when Sliding is turned on or off later
    state = t.node(
        "GeometryNodeSwitch",
        7,
        3,
        {
            "Switch": t.node(
                "FunctionNodeCompare",
                6,
                4,
                {
                    "A": t.node(
                        "GeometryNodeAttributeDomainSize",
                        5,
                        4,
                        {"Geometry": sim_in.outputs["Geometry"]},
                        component="POINTCLOUD",
                    ).outputs["Point Count"],
                    "B": count,
                },
                data_type="INT",
                operation="EQUAL",
            ).outputs[0],
            "False": points,
            "True": sim_in.outputs["Geometry"],
        },
        input_type="GEOMETRY",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 6, 1).outputs[0]
    velocity = t.node(
        "GeometryNodeSampleIndex",
        7,
        1,
        {
            "Geometry": at_rest,
            # As one mass, not turned around by the small bumps and pits
            "Value": t.node(
                "GeometryNodeBlurAttribute",
                6,
                0,
                {"Value": rate, "Iterations": SLIDE_SMOOTH},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
            "Index": index,
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    started = t.node(
        "FunctionNodeCompare",
        8,
        5,
        {
            "A": t.node("GeometryNodeInputSceneTime", 7, 5).outputs["Frame"],
            "B": inputs["Start Frame"],
        },
        data_type="FLOAT",
        operation="GREATER_EQUAL",
    ).outputs[0]
    step = t.math("MULTIPLY", sim_in.outputs["Delta Time"], started, x=9, y=5)
    moved = t.vmath(
        "MULTIPLY_ADD",
        velocity,
        t.node("ShaderNodeCombineXYZ", 9, 4, {"X": step, "Y": step, "Z": step}).outputs[0],
        t.attribute(".foam_offset", "FLOAT_VECTOR", 9, 2),
        x=10,
        y=2,
    )
    state = t.store(state, ".foam_offset", "FLOAT_VECTOR", moved, 11, 3)
    t.connect(state, sim_out.inputs["Geometry"])
    offset = t.node(
        "GeometryNodeSampleIndex",
        13,
        1,
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Value": t.attribute(".foam_offset", "FLOAT_VECTOR", 12, 0),
            "Index": index,
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]
    slid = t.node("GeometryNodeCaptureAttribute", 15, 0, {"Geometry": at_rest})
    for name, value in (
        ("Offset", offset),
        (
            "Shift",
            t.node(
                "FunctionNodeRotateVector",
                14,
                -2,
                {
                    "Vector": offset,
                    "Rotation": t.node("FunctionNodeInvertRotation", 13, -2, {0: turn}).outputs[0],
                },
            ).outputs[0],
        ),
    ):
        slid.capture_items.new("VECTOR", name)
        t.connect(value, slid.inputs[name])
    slid = slid.outputs
    slid_mesh = t.node(
        "GeometryNodeSetPosition", 16, 0, {"Geometry": slid["Geometry"], "Position": posed["Posed"]}
    ).outputs[0]

    # Not computed without sliding
    def pick(still, moved, input_type, y):
        return t.node(
            "GeometryNodeSwitch",
            17,
            y,
            {"Switch": inputs["Sliding"], "False": still, "True": moved},
            input_type=input_type,
        ).outputs[0]

    return (
        pick(mesh, slid_mesh, "GEOMETRY", 0),
        pick((0.0, 0.0, 0.0), slid["Offset"], "VECTOR", -1),
        pick((0.0, 0.0, 0.0), slid["Shift"], "VECTOR", -2),
    )


def soap_film(t, thickness, normal, x, y):
    """Soap film reflecting by Fresnel, rainbow colored by its thickness in nm"""
    fresnel = t.node("ShaderNodeFresnel", x, y - 2, {"IOR": SOAP_IOR, "Normal": normal}).outputs[0]
    # Letting through the light not reflected
    through = t.node(
        "ShaderNodeBsdfTransparent",
        x + 1,
        y - 2,
        {
            "Color": t.math(
                "SUBTRACT",
                1.0,
                t.math("MINIMUM", fresnel, EDGE, x=x + 0.5, y=y - 3),
                x=x + 0.5,
                y=y - 2,
            )
        },
    )
    reflect = t.node(
        "ShaderNodeBsdfPrincipled",
        x + 1,
        y,
        {
            "Base Color": (0.0, 0.0, 0.0, 1.0),
            "Roughness": 0.0,
            "IOR": SOAP_IOR,
            "Specular IOR Level": 0.5 * SHINE,
            "Thin Film Thickness": thickness,
            "Thin Film IOR": SOAP_IOR,
            "Normal": normal,
        },
    ).outputs[0]
    return t.node("ShaderNodeAddShader", x + 2, y, {0: through.outputs[0], 1: reflect}).outputs[0]


def build_material():
    """White foam with layers of bubbles drawn on it, see-through at the lacy border"""
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    material.use_transparent_shadow = True
    t = Tree(material.node_tree, spacing=(200, 180))
    foam = t.node(
        "ShaderNodeAttribute", 0, 0, attribute_type="GEOMETRY", attribute_name="foam"
    ).outputs
    look = t.node(
        "ShaderNodeAttribute", 0, -2, attribute_type="GEOMETRY", attribute_name="foam_color"
    ).outputs
    bubbles = t.node(
        "ShaderNodeAttribute", 0, -4, attribute_type="GEOMETRY", attribute_name="foam_bubbles"
    ).outputs["Vector"]
    bubbles = t.node("ShaderNodeSeparateXYZ", 1, -4, {0: bubbles}).outputs
    size, fade = bubbles["X"], bubbles["Z"]
    coverage = t.math("MULTIPLY", bubbles["Y"], 2.0, x=1, y=-5)
    p = foam["Vector"]

    # Domes of the bubbles of each layer, the highest one showing with its cell values
    height = shape = film = see = None
    for i in range(LAYERS):
        y = -6 - 3 * i
        cell = t.math("MULTIPLY", size, 2.0 * DECAY**i, x=1, y=y)
        voronoi = t.node(
            "ShaderNodeTexVoronoi",
            2,
            y,
            {"Vector": p, "Scale": t.math("DIVIDE", 1.0, cell, x=1, y=y - 1)},
            voronoi_dimensions="3D",
        ).outputs
        random = t.node(
            "ShaderNodeTexWhiteNoise",
            3,
            y,
            {"Vector": voronoi["Position"], "W": float(i)},
            noise_dimensions="4D",
        ).outputs["Color"]
        values = t.node("ShaderNodeSeparateXYZ", 4, y, {0: random}).outputs
        radius = t.math("MULTIPLY_ADD", values["X"], RADIUS[1] - RADIUS[0], RADIUS[0], x=5, y=y)
        dome = t.math(
            "SUBTRACT",
            t.math("MULTIPLY", radius, radius, x=6, y=y),
            t.math("MULTIPLY", voronoi["Distance"], voronoi["Distance"], x=6, y=y - 1),
            x=7,
            y=y,
        )
        dome = t.math("SQRT", t.math("MAXIMUM", dome, 0.0, x=8, y=y), x=9, y=y)
        dome = t.math("MULTIPLY", dome, t.math("MULTIPLY", cell, CAP, x=9, y=y - 2), x=10, y=y)
        dome = t.math(
            "MULTIPLY",
            dome,
            t.math(
                "LESS_THAN",
                values["Y"],
                t.math("MULTIPLY", coverage, PRESENCE[i], x=8, y=y - 2),
                x=9,
                y=y - 1,
            ),
            x=11,
            y=y,
        )
        # Center 0 to rim 1
        place = t.math("DIVIDE", voronoi["Distance"], radius, x=10, y=y - 1)
        if height is None:
            height, shape, film, see = dome, place, values["Z"], SEE[i]
            continue
        higher = t.math("GREATER_THAN", dome, height, x=12, y=y)
        shape = socket(
            t.node("ShaderNodeMix", 13, y, {"Factor": higher, "A": shape, "B": place}).outputs,
            "Result",
        )
        film = socket(
            t.node(
                "ShaderNodeMix", 13, y - 1, {"Factor": higher, "A": film, "B": values["Z"]}
            ).outputs,
            "Result",
        )
        see = socket(
            t.node("ShaderNodeMix", 13, y - 2, {"Factor": higher, "A": see, "B": SEE[i]}).outputs,
            "Result",
        )
        height = t.math("MAXIMUM", height, dome, x=13, y=y + 1)

    # The caps of the bubbles see-through and glossy, the walls between them white
    cap = t.node(
        "ShaderNodeMapRange",
        15,
        -4,
        {
            "Value": shape,
            "From Min": t.math("MULTIPLY_ADD", foam["Alpha"], LACE_RIM - RIM, RIM, x=14, y=-5),
            "From Max": 1.0,
            "To Min": 1.0,
            "To Max": 0.0,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    cap = t.math("MULTIPLY", cap, t.math("GREATER_THAN", height, 0.0, x=15, y=-6), x=16, y=-5)
    dark = t.math(
        "MULTIPLY",
        t.math("MULTIPLY_ADD", t.math("MULTIPLY", shape, shape, x=15, y=-8), -0.6, 1.0, x=16, y=-8),
        DEPTH,
        x=17,
        y=-8,
    )
    clear = t.math("MULTIPLY", cap, see, x=17, y=-6)
    dark = t.math("MULTIPLY", dark, clear, x=18, y=-7)
    shade = t.node(
        "ShaderNodeTexNoise", 15, -10, {"Vector": p, "Scale": SHADE, "Detail": 3.0}
    ).outputs["Fac"]
    shade = t.math("MULTIPLY_ADD", shade, 0.1, 0.95, x=16, y=-10)
    shade = t.math("MULTIPLY", shade, t.math("SUBTRACT", 1.0, dark, x=18, y=-9), x=19, y=-9)
    base = t.node(
        "ShaderNodeMix",
        20,
        -2,
        {"Factor": 1.0, "A": look["Color"], "B": shade},
        data_type="RGBA",
        blend_type="MULTIPLY",
    )
    base = next(s for s in base.outputs if s.type == "RGBA")
    film = t.math(
        "MULTIPLY",
        t.math("MULTIPLY_ADD", film, FILM[1] - FILM[0], FILM[0], x=16, y=-12),
        t.math("MULTIPLY", look["Alpha"], cap, x=16, y=-13),
        x=17,
        y=-12,
    )
    # The height in meters, not scaled down by the default Distance
    normal = t.node("ShaderNodeBump", 16, -14, {"Distance": 1.0, "Height": height}).outputs[
        "Normal"
    ]
    principled = t.node(
        "ShaderNodeBsdfPrincipled",
        21,
        0,
        {
            "Base Color": base,
            "Roughness": t.node(
                "ShaderNodeMapRange",
                20,
                -5,
                {"Value": cap, "To Min": ROUGHNESS[0], "To Max": ROUGHNESS[1]},
            ).outputs[0],
            "IOR": SOAP_IOR,
            "Specular IOR Level": t.math("MULTIPLY_ADD", cap, 0.5 * (SHINE - 1.0), 0.5, x=20, y=-6),
            "Subsurface Weight": 1.0,
            "Subsurface Radius": (1.0, 1.0, 1.0),
            "Subsurface Scale": t.math("MULTIPLY", size, SCATTER, x=20, y=-7),
            "Thin Film Thickness": film,
            "Thin Film IOR": SOAP_IOR,
            "Normal": normal,
        },
        subsurface_method="BURLEY",
    ).outputs[0]
    # The surface under the foam seen through the larger bubbles, and at the lacy border through
    # the whole bubbles and the gaps between them, walls only on their rims
    inside = t.math("GREATER_THAN", height, 0.0, x=19, y=-11)
    gap = t.math("MULTIPLY", t.math("SUBTRACT", 1.0, inside, x=20, y=-11), LACE_GAP, x=21, y=-11)
    through = socket(
        t.node(
            "ShaderNodeMix",
            22,
            -6,
            {
                "Factor": foam["Alpha"],
                "A": t.math("MULTIPLY", clear, THICK_SEE, x=21, y=-9),
                "B": t.math("ADD", cap, gap, x=21, y=-10, clamp=True),
            },
        ).outputs,
        "Result",
    )
    soap = soap_film(t, film, normal, 20, -16)
    surface = t.node("ShaderNodeMixShader", 23, 0, {0: through, 1: principled, 2: soap}).outputs[0]
    # Fading out at the border
    gone = t.node("ShaderNodeBsdfTransparent", 23, 1).outputs[0]
    surface = t.node("ShaderNodeMixShader", 23.5, 0, {0: fade, 1: gone, 2: surface}).outputs[0]
    # Shadows let through in part, the surface under the foam lit
    shadow = t.math(
        "MULTIPLY",
        t.node("ShaderNodeLightPath", 22, 2).outputs["Is Shadow Ray"],
        FOAM_LIGHT,
        x=23,
        y=2,
    )
    surface = t.node(
        "ShaderNodeMixShader",
        24,
        0,
        {0: shadow, 1: surface, 2: gone},
    ).outputs[0]
    t.node("ShaderNodeOutputMaterial", 25, 0, {"Surface": surface})
    return material


def build_bubbles():
    """Soap bubbles, clear with rainbow swirls in their film"""
    material = bpy.data.materials.new(BUBBLES)
    material.node_tree.nodes.clear()
    material.use_transparent_shadow = True
    t = Tree(material.node_tree)
    film = t.node(
        "ShaderNodeAttribute", 0, 0, attribute_type="INSTANCER", attribute_name="foam_film"
    ).outputs["Fac"]
    coords = t.node("ShaderNodeTexCoord", 0, -2).outputs["Object"]
    swirl = t.node(
        "ShaderNodeTexNoise", 1, -2, {"Vector": coords, "Scale": 1.5, "Detail": 3.0}
    ).outputs["Fac"]
    swirl = t.math("MULTIPLY_ADD", swirl, 1.2, 0.4, x=2, y=-2)
    # Thicker at the bottom, the soap draining down
    drain = t.math(
        "MULTIPLY_ADD",
        t.node("ShaderNodeSeparateXYZ", 1, -4, {0: coords}).outputs["Z"],
        -0.3,
        1.15,
        x=2,
        y=-4,
    )
    film = t.math("MULTIPLY", film, t.math("MULTIPLY", swirl, drain, x=3, y=-3), x=4, y=0)
    # White where it meets the foam, a little milky above
    meniscus = t.node(
        "ShaderNodeMapRange",
        5,
        -4,
        {
            "Value": t.node("ShaderNodeSeparateXYZ", 4, -4, {0: coords}).outputs["Z"],
            "From Min": -RAISE,
            "From Max": MENISCUS - RAISE,
            "To Min": 1.0,
            "To Max": MILK,
        },
        interpolation_type="SMOOTHSTEP",
    ).outputs[0]
    foam = t.node(
        "ShaderNodeBsdfPrincipled",
        6,
        -3,
        {"Base Color": (0.9, 0.9, 0.9, 1.0), "Roughness": ROUGHNESS[0], "IOR": SOAP_IOR},
    ).outputs[0]
    surface = t.node(
        "ShaderNodeMixShader", 7, 0, {0: meniscus, 1: soap_film(t, film, None, 5, 0), 2: foam}
    ).outputs[0]
    t.node("ShaderNodeOutputMaterial", 8, 0, {"Surface": surface})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material(), build_bubbles()), fake_user=True)
