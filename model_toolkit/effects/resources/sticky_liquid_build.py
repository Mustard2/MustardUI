# Build sticky_liquid.blend: the Sticky Liquid node group and the liquid material
# Usage: Blender --background --factory-startup --python sticky_liquid_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write

RESOURCE = "sticky_liquid.blend"
NODE_GROUP = "MustardUI Sticky Liquid"
MATERIAL = "MustardUI Sticky Liquid"
# Height of the stuck particles over the surface, and size of the neighbor cells, per size
FILM = 0.5
CELL = 4.0
# Distance kept between the particles, relative to their size
SPACING = 1.6
# Offsets of the grids of the neighbor cells, in cells
GRIDS = ((0.0, 0.0, 0.0), (0.5, 0.5, 0.5), (0.25, 0.75, 0.5), (0.75, 0.25, 0.0))
# Seconds for the landed drops to spread into the film, at full viscosity
SETTLE = 0.5
# Speed in meters per second under which the stuck liquid rests
YIELD = 0.002
# Share of the liquid of the drops held by their strings
VOLUME = 0.5
# Longest motion stretching the falling particles, a frame
SWEEP = 1 / 24
# Radius of the spheres of the stuck particles, their height over the surface, and its growth per
# stuck particle around, per particle radius
FILM_RADIUS = 2.5
FILM_HEIGHT = 0.3
BULGE = 0.06


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Viscous liquid emitted from the Control along its Z axis, sticking to the Targets "
        "where it slides and drips"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng, "Control", "NodeSocketObject", description="Empty emitting the liquid along its Z axis"
    )
    add_input(
        ng,
        "Targets",
        "NodeSocketCollection",
        description="Meshes the liquid sticks to, following them as they move and deform",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(0.9, 0.88, 0.82, 1.0),
        description="Color of the liquid, stored in the liquid_color attribute",
    )
    add_input(ng, "Material", "NodeSocketMaterial", description="Material of the liquid")
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the random emission")

    panel = ng.interface.new_panel("Emission")
    add_input(
        ng,
        "Rate",
        "NodeSocketFloat",
        panel,
        default_value=500.0,
        min_value=0.0,
        max_value=1e5,
        description="Particles emitted per second",
    )
    add_input(
        ng,
        "Duration",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=1.0,
        min_value=0.0,
        max_value=1e4,
        description="Seconds of emission from the start of the simulation, 0 to never stop",
    )
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.0,
        max_value=100.0,
        description="Initial speed of the particles, in meters per second",
    )
    add_input(
        ng,
        "Spread",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.03,
        min_value=0.0,
        max_value=1.0,
        description="Randomness of the emission direction",
    )
    add_input(
        ng,
        "Nozzle",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.001,
        min_value=0.0,
        max_value=10.0,
        description="Radius of the emitting disc, scaled with the Control",
    )

    panel = ng.interface.new_panel("Liquid")
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.002,
        min_value=0.0001,
        max_value=1.0,
        description="Radius of the particles",
    )
    add_input(
        ng,
        "Viscosity",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Thickness of the liquid: moving as one, sliding slowly, stretching strings",
    )
    add_input(
        ng,
        "Stickiness",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Amount of liquid hanging under the Targets before dripping",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=30.0,
        min_value=0.01,
        max_value=1e4,
        description="Seconds before the particles disappear",
    )

    panel = ng.interface.new_panel("Strings")
    add_input(
        ng,
        "String Length",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.04,
        min_value=0.0,
        max_value=10.0,
        description="Distance of the drops from where they dripped breaking their strings, "
        "0 for no strings",
    )
    add_input(
        ng,
        "String Thickness",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0008,
        min_value=0.0,
        max_value=1.0,
        description="Radius of the strings at their ends, thinning as they stretch",
    )

    panel = ng.interface.new_panel("Physics")
    add_input(
        ng,
        "Gravity",
        "NodeSocketVector",
        panel,
        subtype="ACCELERATION",
        default_value=(0.0, 0.0, -9.81),
        description="Acceleration of the liquid, in world space",
    )
    add_input(
        ng,
        "Drag",
        "NodeSocketFloat",
        panel,
        default_value=0.2,
        min_value=0.0,
        max_value=100.0,
        description="Slowdown of the falling liquid per second",
    )
    add_input(
        ng,
        "Substeps",
        "NodeSocketInt",
        panel,
        default_value=2,
        min_value=1,
        max_value=100,
        description="Simulation steps per frame, higher for fast liquid not to pass through",
    )

    panel = ng.interface.new_panel("Surface")
    add_input(
        ng,
        "Mesh",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Mesh of the liquid, off to show the particles and the strings, faster",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketFloat",
        panel,
        default_value=2.0,
        min_value=0.5,
        max_value=20.0,
        description="Voxels per particle radius of the mesh",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        panel,
        default_value=25,
        min_value=0,
        max_value=100,
        description="Iterations smoothing the mesh, rounder and glossier, thinning small drops",
    )

    t = Tree(ng, spacing=(200, 160))
    t.section("Spaces")
    inputs = t.node("NodeGroupInput", -30, 0).outputs
    position = t.node("GeometryNodeInputPosition", -30, -8).outputs[0]
    index = t.node("GeometryNodeInputIndex", -30, -9).outputs[0]

    # Simulated in the space of the object, which is locked
    self_object = t.node("GeometryNodeSelfObject", -30, -3).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -29, -3, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", -28, -3, {"Matrix": to_world}).outputs[0]
    gravity = t.node(
        "FunctionNodeTransformDirection",
        -27,
        -3,
        {"Transform": to_local, "Direction": inputs["Gravity"]},
    ).outputs[0]
    down = t.vmath("NORMALIZE", gravity, x=-26, y=-3)
    size = inputs["Size"]
    film = t.math("MULTIPLY", size, FILM, x=-26, y=-5)

    t.section("Targets")
    # Each Target with its rest position, or its position without, and its index
    targets = t.node(
        "GeometryNodeCollectionInfo",
        -29,
        4,
        {"Collection": inputs["Targets"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    each_in = t.node("GeometryNodeForeachGeometryElementInput", -28, 4, {"Geometry": targets})
    each_out = t.node("GeometryNodeForeachGeometryElementOutput", -22, 4, domain="INSTANCE")
    each_in.pair_with_output(each_out)
    each_out.input_items.new("MATRIX", "Transform")
    t.connect(
        t.node("GeometryNodeInstanceTransform", -29, 2).outputs[0], each_in.inputs["Transform"]
    )
    target = t.node("GeometryNodeRealizeInstances", -27, 4, {0: each_in.outputs["Element"]})
    rest = t.node(
        "GeometryNodeInputNamedAttribute",
        -27,
        2,
        {"Name": "rest_position"},
        data_type="FLOAT_VECTOR",
    ).outputs
    local = t.node(
        "FunctionNodeTransformPoint",
        -26,
        1,
        {
            "Vector": position,
            "Transform": t.node(
                "FunctionNodeInvertMatrix", -27, 1, {"Matrix": each_in.outputs["Transform"]}
            ).outputs[0],
        },
    ).outputs[0]
    rest = t.node(
        "GeometryNodeSwitch",
        -25,
        2,
        {"Switch": rest["Exists"], "False": local, "True": socket(rest, "Attribute")},
        input_type="VECTOR",
    ).outputs[0]
    target = t.store(target.outputs[0], "liquid_rest", "FLOAT_VECTOR", rest, -24, 4)
    target = t.store(target, "liquid_target", "INT", each_in.outputs["Index"], -23, 4)
    t.connect(target, socket(each_out.inputs, "Geometry"))
    surfaces = each_out.outputs[2]

    t.section("Surfaces")
    # Current position and normal on the meshes moved to rest, to follow them as they deform
    world = t.node("GeometryNodeCaptureAttribute", -21, 4, {"Geometry": surfaces})
    for name, value in (
        ("Position", position),
        ("Normal", t.node("GeometryNodeInputNormal", -22, 2).outputs[0]),
    ):
        world.capture_items.new("VECTOR", name)
        t.connect(value, world.inputs[name])
    surfaces = world.outputs["Geometry"]
    at_rest = t.node(
        "GeometryNodeSetPosition",
        -20,
        6,
        {"Geometry": surfaces, "Position": t.attribute("liquid_rest", "FLOAT_VECTOR", -21, 6)},
    ).outputs[0]

    def attribute(name, data_type, x, y):
        return t.attribute("liquid_" + name, data_type, x, y)

    def tangent(vector, normal, x, y):
        """Vector without its component along the normal"""
        along = t.vmath("DOT_PRODUCT", vector, normal, x=x, y=y - 1)
        return t.vmath(
            "SUBTRACT", vector, t.vmath("SCALE", normal, along, x=x + 1, y=y - 1), x=x + 2, y=y
        )

    def project(geometry, x, y):
        """Stuck particles moved on the nearest surface, storing their rest position and Target"""
        nearest = t.node("GeometryNodeCaptureAttribute", x, y, {"Geometry": geometry})
        for i, (data_type, name, value) in enumerate(
            (
                ("VECTOR", "Position", world.outputs["Position"]),
                ("VECTOR", "Normal", world.outputs["Normal"]),
                ("VECTOR", "Rest", attribute("rest", "FLOAT_VECTOR", x - 2, y - 6)),
                ("INT", "Target", attribute("target", "INT", x - 2, y - 7)),
            )
        ):
            sample = t.node(
                "GeometryNodeSampleNearestSurface",
                x - 1,
                y - 2 - i,
                {"Mesh": surfaces, "Value": value},
                data_type="INT" if data_type == "INT" else "FLOAT_VECTOR",
            ).outputs
            nearest.capture_items.new(data_type, name)
            t.connect(sample["Value"], nearest.inputs[name])
        nearest.capture_items.new("BOOLEAN", "Valid")
        t.connect(sample["Is Valid"], nearest.inputs["Valid"])
        fields = dict(nearest.outputs.items())
        fields["Normal"] = t.vmath("NORMALIZE", fields["Normal"], x=x + 1, y=y - 2)
        stuck = t.node(
            "FunctionNodeBooleanMath",
            x + 1,
            y - 3,
            {0: attribute("stuck", "BOOLEAN", x, y - 3), 1: fields["Valid"]},
            operation="AND",
        ).outputs[0]
        on_surface = t.vmath(
            "ADD",
            fields["Position"],
            t.vmath("SCALE", fields["Normal"], film, x=x + 2, y=y - 2),
            x=x + 3,
            y=y - 2,
        )
        geometry = t.node(
            "GeometryNodeSetPosition",
            x + 2,
            y,
            {"Geometry": fields["Geometry"], "Selection": stuck, "Position": on_surface},
        ).outputs[0]
        for i, (name, data_type) in enumerate(
            (("Rest", "FLOAT_VECTOR"), ("Target", "INT"), ("Normal", "FLOAT_VECTOR"))
        ):
            node = t.node(
                "GeometryNodeStoreNamedAttribute",
                x + 3 + i,
                y,
                {
                    "Geometry": geometry,
                    "Selection": stuck,
                    "Name": "liquid_" + name.lower(),
                    "Value": fields[name],
                },
                data_type=data_type,
            )
            geometry = node.outputs[0]
        return geometry, fields

    t.section("Simulation", row=True)
    sim_in = t.node("GeometryNodeSimulationInput", -18, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 40, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("FLOAT", "Time")
    dt = sim_in.outputs["Delta Time"]
    stuck = attribute("stuck", "BOOLEAN", -18, -3)

    def from_rest(prefix, value, x, y):
        """Value of the Targets at the stored rest position, as they are now"""
        return t.node(
            "GeometryNodeSampleNearestSurface",
            x,
            y,
            {
                "Mesh": at_rest,
                "Value": value,
                "Group ID": attribute("target", "INT", x - 1, y - 1),
                "Sample Position": attribute(prefix + "rest", "FLOAT_VECTOR", x - 1, y - 2),
                "Sample Group ID": attribute(prefix + "target", "INT", x - 1, y - 3),
            },
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]

    # Stuck particles back on their rest position, and the strings on where they dripped, on the
    # Targets as they are now
    anchor = [
        from_rest("", value, -17, -4 - 4 * i)
        for i, value in enumerate((world.outputs["Position"], world.outputs["Normal"]))
    ]
    anchor = t.vmath(
        "ADD",
        anchor[0],
        t.vmath("SCALE", t.vmath("NORMALIZE", anchor[1], x=-16, y=-5), film, x=-15, y=-5),
        x=-14,
        y=-4,
    )
    state = t.node(
        "GeometryNodeSetPosition",
        -15,
        0,
        {"Geometry": sim_in.outputs["Geometry"], "Selection": stuck, "Position": anchor},
    ).outputs[0]
    state = t.node(
        "GeometryNodeStoreNamedAttribute",
        -14,
        0,
        {
            "Geometry": state,
            "Selection": attribute("string", "BOOLEAN", -15, -13),
            "Name": "liquid_anchor",
            "Value": from_rest("string_", world.outputs["Position"], -15, -14),
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]

    t.section("Emission")
    # The particles of the elapsed time, over the Duration
    time = sim_in.outputs["Time"]
    end = t.node(
        "GeometryNodeSwitch",
        -16,
        12,
        {
            "Switch": t.math("GREATER_THAN", inputs["Duration"], 0.0, x=-17, y=12),
            "False": 1e9,
            "True": inputs["Duration"],
        },
        input_type="FLOAT",
    ).outputs[0]
    emitted = [
        t.math(
            "FLOOR",
            t.math(
                "MULTIPLY",
                t.math("MINIMUM", value, end, x=-15, y=12 - i),
                inputs["Rate"],
                x=-14,
                y=12 - i,
            ),
            x=-13,
            y=12 - i,
        )
        for i, value in enumerate((t.math("ADD", time, dt, x=-16, y=11), time))
    ]
    count = t.math("SUBTRACT", emitted[0], emitted[1], x=-12, y=12)
    frame = t.node("GeometryNodeInputSceneTime", -14, 9).outputs["Frame"]
    seed = t.math("MULTIPLY_ADD", frame, 7.0, inputs["Seed"], x=-13, y=9)
    random = t.node(
        "FunctionNodeRandomValue",
        -12,
        9,
        {"ID": index, "Seed": seed},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    random = t.node("ShaderNodeSeparateXYZ", -11, 9, {0: random}).outputs
    jitter = t.node(
        "FunctionNodeRandomValue",
        -12,
        7,
        {"Min": (-1.0, -1.0, -1.0), "ID": index, "Seed": t.math("ADD", seed, 3.0, x=-13, y=7)},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    control = t.node(
        "GeometryNodeObjectInfo",
        -13,
        5,
        {"Object": inputs["Control"]},
        transform_space="RELATIVE",
    ).outputs
    axis = t.node(
        "FunctionNodeTransformDirection",
        -12,
        5,
        {"Transform": control["Transform"], "Direction": (0.0, 0.0, 1.0)},
    ).outputs[0]
    axis = t.vmath("NORMALIZE", axis, x=-11, y=5)
    # On a disc across the axis, and along it as emitted during the frame
    angle = t.math("MULTIPLY", random["X"], 2 * math.pi, x=-10, y=10)
    radius = t.math(
        "MULTIPLY", t.math("SQRT", random["Y"], x=-10, y=9), inputs["Nozzle"], x=-9, y=9
    )
    disc = t.node(
        "ShaderNodeCombineXYZ",
        -8,
        10,
        {
            "X": t.math("MULTIPLY", t.math("COSINE", angle, x=-9, y=11), radius, x=-8, y=11),
            "Y": t.math("MULTIPLY", t.math("SINE", angle, x=-9, y=12), radius, x=-8, y=12),
        },
    ).outputs[0]
    disc = t.node(
        "FunctionNodeTransformPoint", -7, 10, {"Vector": disc, "Transform": control["Transform"]}
    ).outputs[0]
    direction = t.vmath(
        "NORMALIZE",
        t.vmath("ADD", axis, t.vmath("SCALE", jitter, inputs["Spread"], x=-10, y=7), x=-9, y=7),
        x=-8,
        y=7,
    )
    speed = t.math(
        "MULTIPLY",
        inputs["Speed"],
        t.math("MULTIPLY_ADD", random["Z"], 0.2, 0.9, x=-9, y=6),
        x=-8,
        y=6,
    )
    velocity = t.vmath("SCALE", direction, speed, x=-7, y=7)
    ahead = t.math("MULTIPLY", t.math("MULTIPLY", dt, random["Z"], x=-7, y=8), speed, x=-6, y=8)
    points = t.node(
        "GeometryNodePoints",
        -5,
        9,
        {
            "Count": count,
            "Position": t.vmath(
                "ADD", disc, t.vmath("SCALE", direction, ahead, x=-6, y=9), x=-5, y=10
            ),
            "Radius": t.math(
                "MULTIPLY",
                size,
                t.math("MULTIPLY_ADD", random["X"], 0.4, 0.8, x=-6, y=11),
                x=-5,
                y=11,
            ),
        },
    ).outputs[0]
    points = t.store(points, "velocity", "FLOAT_VECTOR", velocity, -4, 9)
    join = t.node("GeometryNodeJoinGeometry", -3, 0)
    for geometry in (points, state):
        t.connect(geometry, join.inputs[0])
    state = join.outputs[0]

    t.section("Substeps")
    steps_in = t.node("GeometryNodeRepeatInput", -2, 0, {"Iterations": inputs["Substeps"]})
    steps_out = t.node("GeometryNodeRepeatOutput", 30, 0)
    steps_in.pair_with_output(steps_out)
    t.connect(state, steps_in.inputs["Geometry"])
    step = t.math("DIVIDE", dt, inputs["Substeps"], x=-2, y=-3)
    state, surface = project(steps_in.outputs["Geometry"], 0, 0)
    normal = surface["Normal"]

    # Neighbors: in the cells of offset grids, for the same liquid to always be pulled the same way
    # and smoothly, and the nearest particle
    cell = t.math("MULTIPLY", size, CELL, x=2, y=-12)
    in_cells = t.vmath("SCALE", position, t.math("DIVIDE", 1.0, cell, x=3, y=-14), x=4, y=-12)
    keys = [
        # The stuck and the falling liquid apart, the strings holding the drops instead
        t.node(
            "FunctionNodeHashValue",
            6,
            -12 - i,
            {
                "Value": t.vmath(
                    "FLOOR", t.vmath("ADD", in_cells, offset, x=4, y=-13 - i), x=5, y=-13 - i
                ),
                "Seed": attribute("stuck", "BOOLEAN", 5, -15),
            },
            data_type="VECTOR",
        ).outputs[0]
        for i, offset in enumerate(GRIDS)
    ]

    def around(value, x, y, total=False):
        """Mean, or total, of the value in the cells of the particle, over the grids"""
        nodes = [
            t.node(
                "GeometryNodeAccumulateField" if total else "GeometryNodeFieldAverage",
                x,
                y - i,
                {"Value": value, "Group ID": key},
                data_type="FLOAT" if total else "FLOAT_VECTOR",
            ).outputs["Total" if total else "Mean"]
            for i, key in enumerate(keys)
        ]
        add = (
            (lambda a, b: t.math("ADD", a, b, x=x + 1, y=y))
            if total
            else (lambda a, b: t.vmath("ADD", a, b, x=x + 1, y=y))
        )
        result = nodes[0]
        for node in nodes[1:]:
            result = add(result, node)
        if total:
            return t.math("DIVIDE", result, len(nodes), x=x + 2, y=y)
        return t.vmath("SCALE", result, 1 / len(nodes), x=x + 2, y=y)

    velocity = t.attribute("velocity", "FLOAT_VECTOR", 4, -15)
    mean_velocity = around(velocity, 7, -12)
    mean_position = around(position, 7, -14)
    count = around(1.0, 7, -16, total=True)
    nearest = t.node(
        "GeometryNodeSampleIndex",
        7,
        -16,
        {
            "Geometry": state,
            "Value": position,
            "Index": t.node("GeometryNodeIndexOfNearest", 6, -16).outputs["Index"],
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]

    t.section("Forces")
    # Velocities evened out by the viscosity, and the stuck liquid pulled together
    viscosity = inputs["Viscosity"]
    blend = t.math("MULTIPLY", t.math("MULTIPLY", viscosity, 100.0, x=8, y=-18), step, x=9, y=-18)
    blend = t.math("DIVIDE", blend, t.math("ADD", blend, 1.0, x=10, y=-19), x=11, y=-18)
    velocity = t.vmath(
        "ADD",
        velocity,
        t.vmath(
            "SCALE", t.vmath("SUBTRACT", mean_velocity, velocity, x=10, y=-17), blend, x=11, y=-17
        ),
        x=12,
        y=-16,
    )
    # The same for any particle size
    cohesion = t.math(
        "MULTIPLY",
        t.math("DIVIDE", t.math("MULTIPLY", viscosity, 1.2, x=10, y=-20), size, x=11, y=-20),
        step,
        x=12,
        y=-20,
    )
    gathered = t.vmath(
        "ADD",
        velocity,
        t.vmath(
            "SCALE",
            t.vmath("SUBTRACT", mean_position, position, x=12, y=-19),
            cohesion,
            x=13,
            y=-19,
        ),
        x=14,
        y=-18,
    )
    # Falling, slowed by the drag
    falling = t.vmath("ADD", velocity, t.vmath("SCALE", gravity, step, x=14, y=-22), x=15, y=-22)
    falling = t.vmath(
        "SCALE",
        falling,
        t.math(
            "DIVIDE",
            1.0,
            t.math("MULTIPLY_ADD", inputs["Drag"], step, 1.0, x=15, y=-24),
            x=16,
            y=-24,
        ),
        x=17,
        y=-22,
    )
    # Sliding faster with more liquid, leaving a thin trail, slower the more viscous
    mass = t.math("MAXIMUM", t.math("SUBTRACT", count, 2.0, x=13, y=-25), 0.0, x=14, y=-25)
    mass = t.math("DIVIDE", mass, t.math("ADD", count, 3.0, x=14, y=-26), x=15, y=-26)
    slope = t.vmath("SCALE", tangent(gravity, normal, 14, -28), mass, x=17, y=-28)
    sliding = t.vmath(
        "ADD",
        tangent(gathered, normal, 15, -30),
        t.vmath("SCALE", slope, step, x=18, y=-28),
        x=19,
        y=-29,
    )
    friction = t.math("POWER", 100.0, viscosity, x=17, y=-32)
    friction = t.math("MULTIPLY", t.math("MULTIPLY", friction, 4.0, x=18, y=-32), step, x=19, y=-32)
    sliding = t.vmath(
        "SCALE",
        sliding,
        t.math("DIVIDE", 1.0, t.math("ADD", friction, 1.0, x=20, y=-32), x=21, y=-32),
        x=21,
        y=-29,
    )
    # Resting below the yield speed, not to creep and flicker
    speed = t.vmath("LENGTH", sliding, x=21, y=-34)
    sliding = t.vmath(
        "SCALE",
        sliding,
        t.math(
            "DIVIDE",
            t.math("MAXIMUM", t.math("SUBTRACT", speed, YIELD, x=22, y=-34), 0.0, x=23, y=-34),
            t.math("MAXIMUM", speed, 1e-6, x=22, y=-35),
            x=24,
            y=-34,
        ),
        x=25,
        y=-29,
    )
    stuck = t.node(
        "FunctionNodeBooleanMath",
        16,
        -34,
        {0: attribute("stuck", "BOOLEAN", 15, -34), 1: surface["Valid"]},
        operation="AND",
    ).outputs[0]
    velocity = t.node(
        "GeometryNodeSwitch",
        22,
        -22,
        {"Switch": stuck, "False": falling, "True": sliding},
        input_type="VECTOR",
    ).outputs[0]
    # Drops held back by their strings, stretching them, with the viscosity, less as they thin
    string = attribute("string", "BOOLEAN", 20, -26)
    stretch = t.vmath(
        "SUBTRACT", position, attribute("anchor", "FLOAT_VECTOR", 20, -27), x=21, y=-27
    )
    along = t.vmath("NORMALIZE", stretch, x=22, y=-27)
    resistance = t.math(
        "MULTIPLY", t.math("MULTIPLY", viscosity, 600.0, x=21, y=-29), step, x=22, y=-29
    )
    thinning = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "DIVIDE",
            t.vmath("LENGTH", stretch, x=22, y=-31),
            inputs["String Length"],
            x=23,
            y=-31,
            clamp=True,
        ),
        x=24,
        y=-31,
    )
    resistance = t.math(
        "MULTIPLY", resistance, t.math("SQRT", thinning, x=24.5, y=-30), x=25, y=-30
    )
    resistance = t.math(
        "DIVIDE", resistance, t.math("ADD", resistance, 1.0, x=25, y=-31), x=26, y=-30
    )
    resistance = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", resistance, string, x=25, y=-29),
        t.math("MAXIMUM", t.vmath("DOT_PRODUCT", velocity, along, x=23, y=-28), 0.0, x=24, y=-28),
        x=26,
        y=-28,
    )
    velocity = t.vmath(
        "SUBTRACT", velocity, t.vmath("SCALE", along, resistance, x=27, y=-28), x=28, y=-24
    )
    broken = t.math(
        "GREATER_THAN",
        t.vmath("LENGTH", stretch, x=22, y=-31),
        inputs["String Length"],
        x=23,
        y=-31,
    )

    t.section("Contacts")
    # Dripping from the surfaces facing down, with enough liquid hanging, as separate drops
    pull = t.vmath("DOT_PRODUCT", down, normal, x=16, y=-36)
    amount = around(stuck, 16, -38, total=True)
    hanging = t.math(
        "GREATER_THAN",
        t.math("MULTIPLY", pull, amount, x=17, y=-37),
        t.math("MULTIPLY_ADD", inputs["Stickiness"], 10.0, 1.0, x=17, y=-38),
        x=18,
        y=-37,
    )
    drips = t.node(
        "FunctionNodeBooleanMath",
        20,
        -36,
        {
            0: stuck,
            1: t.node(
                "FunctionNodeBooleanMath",
                19,
                -37,
                {0: t.math("GREATER_THAN", pull, 0.5, x=18, y=-36), 1: hanging},
                operation="AND",
            ).outputs[0],
        },
        operation="AND",
    ).outputs[0]
    # Sticking where the falling particles hit the surfaces, or are just under them
    ray = t.node(
        "GeometryNodeRaycast",
        23,
        -40,
        {
            "Target Geometry": surfaces,
            "Ray Direction": velocity,
            "Ray Length": t.math(
                "MULTIPLY_ADD",
                t.vmath("LENGTH", velocity, x=22, y=-42),
                step,
                film,
                x=23,
                y=-42,
            ),
        },
    ).outputs
    below = t.vmath(
        "DOT_PRODUCT",
        t.vmath("SUBTRACT", position, surface["Position"], x=21, y=-44),
        normal,
        x=22,
        y=-44,
    )
    close = t.math(
        "LESS_THAN",
        t.vmath("DISTANCE", position, surface["Position"], x=22, y=-45),
        t.math("MULTIPLY", size, 2.0, x=22, y=-46),
        x=23,
        y=-45,
    )
    under = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", below, 0.0, x=23, y=-44),
        t.math("MULTIPLY", close, surface["Valid"], x=24, y=-45),
        x=24,
        y=-44,
    )
    hits = t.node(
        "FunctionNodeBooleanMath",
        25,
        -40,
        {
            0: t.node(
                "FunctionNodeBooleanMath",
                24,
                -40,
                {0: ray["Is Hit"], 1: under},
                operation="OR",
            ).outputs[0],
            1: stuck,
        },
        operation="NIMPLY",
    ).outputs[0]
    contact = [
        t.node(
            "GeometryNodeSwitch",
            25,
            -42 - i,
            {"Switch": ray["Is Hit"], "False": value, "True": ray[name]},
            input_type="VECTOR",
        ).outputs[0]
        for i, (name, value) in enumerate(
            (("Hit Position", surface["Position"]), ("Hit Normal", normal))
        )
    ]
    contact_normal = t.vmath("NORMALIZE", contact[1], x=26, y=-43)
    contact_position = t.vmath(
        "ADD",
        contact[0],
        t.vmath("SCALE", contact_normal, film, x=27, y=-43),
        x=28,
        y=-42,
    )

    # Moving, the stuck liquid kept apart from the nearest particle to spread, and off the surface
    # when dripping
    away = t.vmath("SUBTRACT", position, nearest, x=22, y=-48)
    push = t.math(
        "MAXIMUM",
        t.math(
            "SUBTRACT",
            t.math("MULTIPLY", size, SPACING, x=23, y=-49),
            t.vmath("LENGTH", away, x=23, y=-50),
            x=24,
            y=-49,
        ),
        0.0,
        x=25,
        y=-49,
    )
    push = t.math("MULTIPLY", push, stuck, x=25.5, y=-49)
    # Not moving into it either, for the liquid to come to rest
    apart = t.vmath("NORMALIZE", away, x=24, y=-48)
    closing = t.math(
        "MINIMUM", t.vmath("DOT_PRODUCT", velocity, apart, x=25, y=-52), 0.0, x=26, y=-52
    )
    closing = t.math(
        "MULTIPLY", closing, t.math("GREATER_THAN", push, 0.0, x=26, y=-53), x=27, y=-52
    )
    velocity = t.vmath(
        "SUBTRACT", velocity, t.vmath("SCALE", apart, closing, x=28, y=-52), x=29, y=-51
    )
    moved = t.vmath("ADD", position, t.vmath("SCALE", velocity, step, x=23, y=-47), x=24, y=-47)
    moved = t.vmath(
        "ADD",
        moved,
        t.vmath("SCALE", apart, t.math("MULTIPLY", push, 0.3, x=26, y=-49), x=25, y=-48),
        x=26,
        y=-47,
    )
    moved = t.vmath(
        "ADD",
        moved,
        t.vmath("SCALE", normal, t.math("MULTIPLY", drips, film, x=26, y=-51), x=27, y=-50),
        x=28,
        y=-47,
    )
    new_stuck = t.node(
        "FunctionNodeBooleanMath",
        29,
        -48,
        {
            0: t.node(
                "FunctionNodeBooleanMath", 28, -48, {0: stuck, 1: drips}, operation="NIMPLY"
            ).outputs[0],
            1: hits,
        },
        operation="OR",
    ).outputs[0]
    new = t.node("GeometryNodeCaptureAttribute", 29, 0, {"Geometry": state})
    for data_type, name, value in (
        (
            "VECTOR",
            "Position",
            t.node(
                "GeometryNodeSwitch",
                29,
                -42,
                {"Switch": hits, "False": moved, "True": contact_position},
                input_type="VECTOR",
            ).outputs[0],
        ),
        (
            "VECTOR",
            "Velocity",
            t.node(
                "GeometryNodeSwitch",
                29,
                -44,
                {
                    "Switch": hits,
                    # Dripping straight off the surface, not along it to stick again
                    "False": t.node(
                        "GeometryNodeSwitch",
                        28,
                        -43,
                        {
                            "Switch": drips,
                            "False": velocity,
                            "True": t.vmath("SCALE", normal, 0.02, x=27, y=-43),
                        },
                        input_type="VECTOR",
                    ).outputs[0],
                    "True": t.vmath(
                        "SCALE",
                        tangent(velocity, contact_normal, 26, -46),
                        t.math("SUBTRACT", 1.0, inputs["Stickiness"], x=28, y=-46),
                        x=29,
                        y=-46,
                    ),
                },
                input_type="VECTOR",
            ).outputs[0],
        ),
        (
            "BOOLEAN",
            "Stuck",
            new_stuck,
        ),
    ):
        new.capture_items.new(data_type, name)
        t.connect(value, new.inputs[name])

    # Strings from where the drops dripped, until they break or the drops land, all the particles
    # of a drop with the same anchor at once, for them to land as one drop
    landed = t.node(
        "GeometryNodeAccumulateField",
        25,
        -54,
        {
            "Value": t.math("MULTIPLY", hits, string, x=24, y=-54),
            "Group ID": t.node(
                "FunctionNodeHashValue",
                24,
                -55,
                {"Value": attribute("anchor", "FLOAT_VECTOR", 23, -55)},
                data_type="VECTOR",
            ).outputs[0],
        },
        data_type="INT",
    ).outputs["Total"]
    held = t.node(
        "FunctionNodeBooleanMath",
        27,
        -52,
        {
            0: t.node(
                "FunctionNodeBooleanMath", 26, -52, {0: string, 1: broken}, operation="NIMPLY"
            ).outputs[0],
            1: t.math("GREATER_THAN", landed, 0.0, x=26, y=-54),
        },
        operation="NIMPLY",
    ).outputs[0]
    # For all the particles of the drops, from where each drop dripped, for them to stay together
    # in one neck
    strings = t.node(
        "FunctionNodeBooleanMath",
        29,
        -52,
        {
            0: held,
            1: t.node(
                "FunctionNodeBooleanMath",
                28,
                -56,
                {
                    0: drips,
                    1: t.math("GREATER_THAN", inputs["String Length"], 0.0, x=26, y=-56),
                },
                operation="AND",
            ).outputs[0],
        },
        operation="OR",
    ).outputs[0]
    drop = t.node(
        "GeometryNodeSwitch",
        26,
        -58,
        {"Switch": drips, "False": -1, "True": keys[0]},
        input_type="INT",
    ).outputs[0]

    def from_drop(value, y):
        """Mean of the value over the particles of the drop"""
        return t.node(
            "GeometryNodeFieldAverage",
            27,
            y,
            {"Value": value, "Group ID": drop},
            data_type="FLOAT_VECTOR",
        ).outputs["Mean"]

    new.capture_items.new("BOOLEAN", "String")
    t.connect(strings, new.inputs["String"])
    # Set when dripping, kept while held
    for i, (data_type, attribute_type, name, dripped) in enumerate(
        (
            ("VECTOR", "FLOAT_VECTOR", "Anchor", from_drop(surface["Position"], -60)),
            ("VECTOR", "FLOAT_VECTOR", "String Rest", from_drop(surface["Rest"], -61)),
            ("INT", "INT", "String Target", surface["Target"]),
        )
    ):
        kept = attribute(name.lower().replace(" ", "_"), attribute_type, 28, -58 - i)
        new.capture_items.new(data_type, name)
        t.connect(
            t.node(
                "GeometryNodeSwitch",
                29,
                -58 - i,
                {"Switch": drips, "False": kept, "True": dripped},
                input_type=data_type,
            ).outputs[0],
            new.inputs[name],
        )
    # Time since landing, for the drops to spread on the surface
    new.capture_items.new("FLOAT", "Settle")
    t.connect(
        t.math(
            "MULTIPLY",
            new_stuck,
            t.math("MULTIPLY_ADD", attribute("settle", "FLOAT", 28, -64), stuck, step, x=29, y=-64),
            x=30,
            y=-64,
        ),
        new.inputs["Settle"],
    )
    # Stuck liquid around, bulging the surface
    new.capture_items.new("FLOAT", "Amount")
    t.connect(amount, new.inputs["Amount"])
    state = t.node(
        "GeometryNodeSetPosition",
        30,
        0,
        {"Geometry": new.outputs["Geometry"], "Position": new.outputs["Position"]},
    ).outputs[0]
    for name, attribute_name, data_type in (
        ("Velocity", "velocity", "FLOAT_VECTOR"),
        ("Stuck", "liquid_stuck", "BOOLEAN"),
        ("String", "liquid_string", "BOOLEAN"),
        ("Anchor", "liquid_anchor", "FLOAT_VECTOR"),
        ("String Rest", "liquid_string_rest", "FLOAT_VECTOR"),
        ("String Target", "liquid_string_target", "INT"),
        ("Amount", "liquid_amount", "FLOAT"),
        ("Settle", "liquid_settle", "FLOAT"),
    ):
        state = t.store(state, attribute_name, data_type, new.outputs[name], 31, 0)
    t.connect(state, steps_out.inputs["Geometry"])

    t.section("Aging")
    # On the surfaces for the next frame, and removed past their lifetime
    state, _ = project(steps_out.outputs["Geometry"], 34, 0)
    age = t.math("ADD", attribute("age", "FLOAT", 38, -3), dt, x=39, y=-3)
    state = t.store(state, "liquid_age", "FLOAT", age, 39, 0)
    state = t.node(
        "GeometryNodeDeleteGeometry",
        40,
        0,
        {
            "Geometry": state,
            "Selection": t.math(
                "GREATER_THAN", attribute("age", "FLOAT", 39, -5), inputs["Lifetime"], x=40, y=-5
            ),
        },
        domain="POINT",
    ).outputs[0]
    t.connect(state, sim_out.inputs["Geometry"])
    t.connect(t.math("ADD", time, dt, x=40, y=-7), sim_out.inputs["Time"])

    t.section("Particles", row=True)
    # Shrinking at the end of their lifetime, not to pop
    particles = sim_out.outputs["Geometry"]
    fade = t.math(
        "DIVIDE",
        t.math("SUBTRACT", inputs["Lifetime"], attribute("age", "FLOAT", 41, -3), x=42, y=-3),
        0.5,
        x=43,
        y=-3,
        clamp=True,
    )
    particles = t.node(
        "GeometryNodeSetPointRadius",
        44,
        0,
        {
            "Points": particles,
            "Radius": t.math(
                "MULTIPLY", t.node("GeometryNodeInputRadius", 43, -4).outputs[0], fade, x=44, y=-4
            ),
        },
    ).outputs[0]
    radius = t.node("GeometryNodeInputRadius", 45, -6).outputs[0]
    stuck = attribute("stuck", "BOOLEAN", 45, -7)
    voxel = t.math("DIVIDE", size, inputs["Resolution"], x=45, y=-8)

    def resample(selection, count, place, sample_radius, x, y):
        """Particles selected, duplicated by the count, placed and sized by the duplicate index,
        sampling the surface"""
        points = t.node(
            "GeometryNodeDeleteGeometry",
            x,
            y,
            {
                "Geometry": particles,
                "Selection": t.node(
                    "FunctionNodeBooleanMath", x - 1, y - 2, {0: selection}, operation="NOT"
                ).outputs[0],
            },
            domain="POINT",
        ).outputs[0]
        duplicate = t.node(
            "GeometryNodeDuplicateElements",
            x + 1,
            y,
            {"Geometry": points, "Amount": count},
            domain="POINT",
        ).outputs
        i = duplicate["Duplicate Index"]
        points = t.node(
            "GeometryNodeSetPosition",
            x + 2,
            y,
            {"Geometry": duplicate["Geometry"], "Position": place(i)},
        ).outputs[0]
        return t.node(
            "GeometryNodeSetPointRadius", x + 3, y, {"Points": points, "Radius": sample_radius(i)}
        ).outputs[0]

    # Falling liquid stretched along its motion up to the next particles emitted, for a stream to
    # be continuous and drops round
    sweep = t.vmath(
        "SCALE",
        t.attribute("velocity", "FLOAT_VECTOR", 45, 2),
        t.math("MINIMUM", t.math("DIVIDE", 2.0, inputs["Rate"], x=44, y=3), SWEEP, x=45, y=3),
        x=46,
        y=2,
    )
    sweeps = t.math(
        "CEIL",
        t.math(
            "DIVIDE",
            t.vmath("LENGTH", sweep, x=47, y=2),
            t.math("MULTIPLY", radius, 0.5, x=47, y=3),
            x=48,
            y=2,
        ),
        x=49,
        y=2,
    )
    sweeps = t.node("ShaderNodeClamp", 50, 2, {"Value": sweeps, "Min": 1.0, "Max": 48.0}).outputs[0]

    def along_sweep(i):
        return t.vmath(
            "SUBTRACT",
            position,
            t.vmath(
                "SCALE",
                sweep,
                t.math(
                    "DIVIDE",
                    i,
                    t.math("MAXIMUM", t.math("SUBTRACT", sweeps, 1.0, x=50, y=4), 1.0, x=51, y=4),
                    x=52,
                    y=4,
                ),
                x=53,
                y=3,
            ),
            x=54,
            y=3,
        )

    falling = resample(
        t.node("FunctionNodeBooleanMath", 45, 0, {0: stuck}, operation="NOT").outputs[0],
        sweeps,
        along_sweep,
        lambda i: radius,
        46,
        0,
    )

    # Stuck liquid as large spheres sunk in the surface, their flat caps making a thin film tapering
    # at its edges, higher with more liquid around
    normal = t.vmath("NORMALIZE", attribute("normal", "FLOAT_VECTOR", 45, -12), x=46, y=-12)
    cap = t.math(
        "MULTIPLY",
        radius,
        t.math(
            "MULTIPLY_ADD",
            t.math("MINIMUM", attribute("amount", "FLOAT", 45, -14), 10.0, x=46, y=-14),
            BULGE,
            FILM_HEIGHT,
            x=47,
            y=-14,
        ),
        x=48,
        y=-14,
    )
    sphere = t.math("MULTIPLY", radius, FILM_RADIUS, x=48, y=-15)
    sunk = t.math("ADD", t.math("SUBTRACT", sphere, cap, x=49, y=-15), film, x=50, y=-15)
    # Round drops when landing, spreading over a time longer the more viscous
    spread = t.math(
        "DIVIDE",
        attribute("settle", "FLOAT", 46, -17),
        t.math("MULTIPLY_ADD", inputs["Viscosity"], SETTLE, 0.2, x=46, y=-18),
        x=47,
        y=-17,
        clamp=True,
    )
    # A little larger, for the drops to merge
    bead = t.math("MULTIPLY", radius, 1.3, x=48, y=-17)
    sphere = t.node("ShaderNodeMix", 49, -16, {"Factor": spread, "A": bead, "B": sphere}).outputs[0]
    sunk = t.math("MULTIPLY", sunk, spread, x=51, y=-16)
    film_points = resample(
        stuck,
        1,
        lambda i: t.vmath(
            "SUBTRACT", position, t.vmath("SCALE", normal, sunk, x=51, y=-15), x=52, y=-15
        ),
        lambda i: sphere,
        46,
        -10,
    )
    t.section("Strings")
    # From where the drops dripped to their middle, thin in the middle, sagging, and thinning as
    # they stretch, merging in the surface
    threads = t.node(
        "GeometryNodeDeleteGeometry",
        44,
        -24,
        {
            "Geometry": particles,
            "Selection": t.node(
                "FunctionNodeBooleanMath",
                43,
                -26,
                {0: attribute("string", "BOOLEAN", 42, -26)},
                operation="NOT",
            ).outputs[0],
        },
        domain="POINT",
    ).outputs[0]
    anchor = attribute("anchor", "FLOAT_VECTOR", 45, -30)
    # The particles of a drop, sharing the place where it dripped, and the first of them
    drop = t.node(
        "GeometryNodeAccumulateField",
        44,
        -28,
        {
            "Value": 1,
            "Group ID": t.node(
                "FunctionNodeHashValue", 43, -28, {"Value": anchor}, data_type="VECTOR"
            ).outputs[0],
        },
        data_type="INT",
        domain="POINT",
    ).outputs
    threads = t.store(threads, "liquid_bundle", "FLOAT", drop["Total"], 44.2, -24)
    threads = t.store(
        threads,
        "liquid_lead",
        "BOOLEAN",
        t.math("LESS_THAN", drop["Leading"], 1.5, x=44, y=-29),
        44.4,
        -24,
    )
    threads = t.store(threads, "liquid_strand", "INT", index, 44.6, -24)
    stretch = t.vmath("SUBTRACT", position, anchor, x=46, y=-30)
    length = t.vmath("LENGTH", stretch, x=47, y=-30)
    # Dense enough for a smooth surface
    samples = t.math(
        "CEIL",
        t.math("DIVIDE", length, t.math("MULTIPLY", voxel, 0.7, x=47, y=-31), x=48, y=-31),
        x=49,
        y=-31,
    )
    samples = t.node(
        "ShaderNodeClamp", 50, -31, {"Value": samples, "Min": 2.0, "Max": 400.0}
    ).outputs[0]
    duplicate = t.node(
        "GeometryNodeDuplicateElements",
        51,
        -24,
        {"Geometry": threads, "Amount": samples},
        domain="POINT",
    ).outputs
    u = t.math(
        "DIVIDE",
        duplicate["Duplicate Index"],
        t.math("SUBTRACT", samples, 1.0, x=51, y=-33),
        x=52,
        y=-33,
    )
    hanging = t.vmath("DOT_PRODUCT", t.vmath("NORMALIZE", stretch, x=47, y=-32), down, x=48, y=-32)
    sag = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", length, 0.3, x=48, y=-34),
        t.math("SUBTRACT", 1.0, t.math("ABSOLUTE", hanging, x=49, y=-32), x=50, y=-32),
        x=51,
        y=-34,
    )
    bow = t.math("MULTIPLY", u, t.math("SUBTRACT", 1.0, u, x=53, y=-35), x=54, y=-35)
    bow = t.math("MULTIPLY", t.math("MULTIPLY", bow, 4.0, x=55, y=-35), sag, x=56, y=-35)
    along = t.vmath("ADD", anchor, t.vmath("SCALE", stretch, u, x=53, y=-33), x=54, y=-33)
    along = t.vmath("ADD", along, t.vmath("SCALE", down, bow, x=57, y=-35), x=58, y=-33)
    # Wavy, the same along the string as it stretches, still at the ends
    wave = t.node(
        "ShaderNodeTexNoise",
        56,
        -36,
        {
            "Vector": t.vmath(
                "ADD",
                t.vmath("SCALE", anchor, 50.0, x=53, y=-36),
                t.vmath(
                    "SCALE", (0.0, 0.0, 1.0), t.math("MULTIPLY", u, 3.0, x=53, y=-37), x=54, y=-37
                ),
                x=55,
                y=-36,
            ),
            "Scale": 1.0,
        },
    ).outputs["Color"]
    wave = t.vmath("SUBTRACT", wave, (0.5, 0.5, 0.5), x=57, y=-36)
    wave = t.vmath(
        "SCALE",
        wave,
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", u, t.math("SUBTRACT", 1.0, u, x=56, y=-38), x=57, y=-38),
            t.math("MULTIPLY", length, 0.2, x=57, y=-39),
            x=58,
            y=-38,
        ),
        x=59,
        y=-36,
    )
    along = t.vmath("ADD", along, wave, x=60, y=-33)
    # As thick as the drop where it leaves the liquid and at the drop, tapering to a neck in the
    # middle holding a share of the liquid of the drop, thinning as it stretches
    ends = t.math(
        "ADD",
        t.math("POWER", t.math("SUBTRACT", 1.0, u, x=53, y=-40), 3.0, x=54, y=-40),
        t.math("POWER", u, 4.0, x=54, y=-41),
        x=55,
        y=-40,
    )
    held = t.math(
        "MULTIPLY",
        t.math("POWER", radius, 3.0, x=53, y=-38),
        t.math("MULTIPLY", attribute("bundle", "FLOAT", 52, -39), VOLUME * 4 / 3, x=53, y=-39),
        x=54,
        y=-38,
    )
    neck = t.math(
        "SQRT",
        t.math("DIVIDE", held, t.math("MAXIMUM", length, 1e-6, x=54, y=-39), x=55, y=-38),
        x=56,
        y=-38,
    )
    neck = t.math("MINIMUM", neck, inputs["String Thickness"], x=57, y=-38)
    threads = t.node(
        "GeometryNodeSetPointRadius",
        60,
        -24,
        {
            "Points": duplicate["Geometry"],
            "Radius": t.math(
                "MAXIMUM", neck, t.math("MULTIPLY", radius, ends, x=57, y=-40), x=58, y=-38
            ),
        },
    ).outputs[0]
    threads = t.store(threads, "liquid_neck", "FLOAT", neck, 60.5, -24)
    threads = t.store(threads, "liquid_along", "FLOAT", u, 60.7, -24)
    # Placed after, the shape following the particle and its anchor
    threads = t.node(
        "GeometryNodeSetPosition", 61, -24, {"Geometry": threads, "Position": along}
    ).outputs[0]
    # And one tube for each drop, the string thinner than the voxels can be
    tubes = t.node(
        "GeometryNodeDeleteGeometry",
        62,
        -30,
        {
            "Geometry": threads,
            "Selection": t.node(
                "FunctionNodeBooleanMath",
                61,
                -31,
                {0: attribute("lead", "BOOLEAN", 60, -31)},
                operation="NOT",
            ).outputs[0],
        },
        domain="POINT",
    ).outputs[0]
    tubes = t.node(
        "GeometryNodePointsToCurves",
        63,
        -30,
        {
            "Points": tubes,
            "Curve Group ID": attribute("strand", "INT", 62, -32),
            "Weight": attribute("along", "FLOAT", 62, -33),
        },
    ).outputs[0]
    tubes = t.node(
        "GeometryNodeCurveToMesh",
        64,
        -30,
        {
            "Curve": tubes,
            "Profile Curve": t.node(
                "GeometryNodeCurvePrimitiveCircle", 63, -32, {"Resolution": 8, "Radius": 1.0}
            ).outputs["Curve"],
            "Scale": attribute("neck", "FLOAT", 63, -33),
            "Fill Caps": True,
        },
    ).outputs[0]
    tubes = t.node("GeometryNodeSetShadeSmooth", 65, -30, {"Mesh": tubes}).outputs[0]

    t.section("Mesh", row=True)
    # One surface around the falling liquid and the film, grown, smoothed and shrunk back
    samples = t.node("GeometryNodeJoinGeometry", 62, 0)
    for geometry in (falling, film_points):
        t.connect(geometry, samples.inputs[0])
    samples = samples.outputs[0]
    sdf = t.node(
        "GeometryNodePointsToSDFGrid",
        63,
        0,
        {"Points": samples, "Radius": radius, "Voxel Size": voxel},
    ).outputs[0]
    # By about a particle, whatever the resolution, for the particles not to show
    closing = t.math("MULTIPLY", size, 0.5, x=63, y=2)
    sdf = t.node("GeometryNodeSDFGridOffset", 64, 0, {"Grid": sdf, "Distance": closing}).outputs[0]
    sdf = t.node(
        "GeometryNodeSDFGridMean",
        65,
        0,
        {
            "Grid": sdf,
            "Width": t.math("CEIL", inputs["Resolution"], x=64, y=2),
            "Iterations": 3,
        },
    ).outputs[0]
    sdf = t.node(
        "GeometryNodeSDFGridOffset",
        66,
        0,
        {"Grid": sdf, "Distance": t.math("MULTIPLY", closing, -1.0, x=65, y=2)},
    ).outputs[0]
    # With the strings and the falling drops, too small for that smoothing, blended in lightly,
    # the same with or without them for the surface not to change as they come and go
    details = t.node("GeometryNodeJoinGeometry", 64.5, -3)
    for geometry in (threads, falling):
        t.connect(geometry, details.inputs[0])
    details = details.outputs[0]
    union = t.node("GeometryNodeSDFGridBoolean", 66.5, 0, operation="UNION")
    for grid in (
        sdf,
        t.node(
            "GeometryNodePointsToSDFGrid",
            65,
            -3,
            {"Points": details, "Radius": radius, "Voxel Size": voxel},
        ).outputs[0],
    ):
        t.connect(grid, socket(union.inputs, "Grid 2"))
    # Without them, their empty grid would resample the surface
    has_details = t.math(
        "GREATER_THAN",
        t.node(
            "GeometryNodeAttributeDomainSize", 66, 2, {"Geometry": details}, component="POINTCLOUD"
        ).outputs["Point Count"],
        0.0,
        x=66.5,
        y=2,
    )
    sdf = t.node(
        "GeometryNodeSwitch",
        67,
        0,
        {"Switch": has_details, "False": sdf, "True": union.outputs[0]},
        input_type="FLOAT",
    ).outputs[0]
    sdf = t.node("GeometryNodeSDFGridMean", 67.5, 0, {"Grid": sdf}).outputs[0]
    mesh = t.node("GeometryNodeGridToMesh", 68, 0, {"Grid": sdf}).outputs[0]
    # Nothing without liquid, for the grids not to be made empty
    mesh = t.node(
        "GeometryNodeSwitch",
        68.2,
        0,
        {
            "Switch": t.math(
                "GREATER_THAN",
                t.node(
                    "GeometryNodeAttributeDomainSize",
                    67.5,
                    3,
                    {"Geometry": samples},
                    component="POINTCLOUD",
                ).outputs["Point Count"],
                0.0,
                x=68,
                y=3,
            ),
            "True": mesh,
        },
        input_type="GEOMETRY",
    ).outputs[0]
    # Smoothed, without the grain of the voxels changing every frame
    mesh = t.node(
        "GeometryNodeSetPosition",
        67.5,
        0,
        {
            "Geometry": mesh,
            "Position": t.node(
                "GeometryNodeBlurAttribute",
                67,
                -2,
                {"Value": position, "Iterations": inputs["Smooth"]},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
        },
    ).outputs[0]
    # Without the part hidden under the surfaces, most of the sunk film
    under = [
        t.node(
            "GeometryNodeSampleNearestSurface",
            67.5,
            -4 - i,
            {"Mesh": surfaces, "Value": world.outputs[name]},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for i, name in enumerate(("Position", "Normal"))
    ]
    under = t.vmath(
        "DOT_PRODUCT",
        t.vmath("SUBTRACT", position, under[0], x=68, y=-4),
        t.vmath("NORMALIZE", under[1], x=68, y=-5),
        x=69,
        y=-4,
    )
    mesh = t.node(
        "GeometryNodeDeleteGeometry",
        68,
        0,
        {
            "Geometry": mesh,
            "Selection": t.math(
                "LESS_THAN", under, t.math("MULTIPLY", size, -0.5, x=69, y=-5), x=70, y=-4
            ),
        },
        domain="POINT",
    ).outputs[0]
    mesh = t.node("GeometryNodeSetShadeSmooth", 68.5, 0, {"Mesh": mesh}).outputs[0]
    join = t.node("GeometryNodeJoinGeometry", 68.7, 0)
    for geometry in (mesh, tubes):
        t.connect(geometry, join.inputs[0])
    mesh = join.outputs[0]
    # Without mesh, the particles and the strings
    preview = t.node("GeometryNodeJoinGeometry", 68, -2)
    for geometry in (particles, threads):
        t.connect(geometry, preview.inputs[0])
    preview = preview.outputs[0]
    liquid = t.node(
        "GeometryNodeSwitch",
        69,
        0,
        {"Switch": inputs["Mesh"], "False": preview, "True": mesh},
        input_type="GEOMETRY",
    ).outputs[0]
    liquid = t.node(
        "GeometryNodeRemoveAttribute",
        70,
        0,
        {"Geometry": liquid, "Pattern Mode": "Wildcard", "Name": "liquid_*"},
    ).outputs[0]
    liquid = t.store(liquid, "liquid_color", "FLOAT_COLOR", inputs["Color"], 71, 0)
    # For the shader, 1 on the surfaces, clear, to 0 a particle diameter off them, milky
    near = t.node("GeometryNodeProximity", 71, -3, {0: surfaces}, target_element="FACES").outputs
    thin = t.math(
        "SUBTRACT",
        1.0,
        t.math("DIVIDE", near["Distance"], t.math("MULTIPLY", size, 2.0, x=70, y=-5), x=71, y=-5),
        x=72,
        y=-4,
        clamp=True,
    )
    thin = t.math("MULTIPLY", thin, near["Is Valid"], x=72, y=-3)
    liquid = t.store(liquid, "liquid_thin", "FLOAT", thin, 72, 0)
    liquid = t.node(
        "GeometryNodeSetMaterial", 73, 0, {"Geometry": liquid, "Material": inputs["Material"]}
    ).outputs[0]
    # Bakeable with the simulation, for the playback not to mesh every frame again
    bake = t.node("GeometryNodeBake", 74, 0)
    bake.bake_items.new("GEOMETRY", "Geometry")
    t.connect(liquid, bake.inputs["Geometry"])
    t.node("NodeGroupOutput", 75, 0, {0: bake.outputs["Geometry"]})
    t.arrange()
    return ng


def build_material():
    """Milky liquid with a wet coat, clear where thin on the skin, colored by liquid_color"""
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    material.use_transparent_shadow = True
    # Smooth transparency in EEVEE, the dithered one noisy on the thin film, its front only
    material.surface_render_method = "BLENDED"
    material.use_backface_culling = True
    material.use_transparency_overlap = False
    t = Tree(material.node_tree)
    color = t.node("ShaderNodeAttribute", -4, 2, attribute_name="liquid_color").outputs["Color"]
    thin = t.node(
        "ShaderNodeAttribute", -4, -2, attribute_type="GEOMETRY", attribute_name="liquid_thin"
    ).outputs["Fac"]
    # Light scattering in the liquid, milky and glowing, under a sharp wet coat
    milky = t.node(
        "ShaderNodeBsdfPrincipled",
        0,
        1,
        {
            "Base Color": color,
            "Roughness": 0.3,
            "IOR": 1.4,
            "Subsurface Weight": 1.0,
            "Subsurface Radius": (1.0, 0.85, 0.7),
            "Subsurface Scale": 0.008,
            "Coat Weight": 1.0,
            "Coat Roughness": 0.03,
        },
    ).outputs[0]
    # Transparent where thin, for the skin and its light to show through, keeping the wet coat
    surface = t.node(
        "ShaderNodeMixShader",
        2,
        0,
        {
            0: t.math("MULTIPLY", thin, 0.9, x=-2, y=-2),
            1: milky,
            2: t.node("ShaderNodeBsdfTransparent", 0, -2).outputs[0],
        },
    )
    t.node("ShaderNodeOutputMaterial", 4, 0, {"Surface": surface.outputs[0]})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material()))
