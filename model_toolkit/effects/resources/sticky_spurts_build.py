# Build sticky_spurts.blend: the Sticky Spurts node group, ropes of thick liquid shot in
# spurts that stick where they land, and its material
# Usage: Blender --background --factory-startup --python sticky_spurts_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write

RESOURCE = "sticky_spurts.blend"
NODE_GROUP = "MustardUI Sticky Spurts"
MATERIAL = "MustardUI Sticky Spurts"
# Milk of the liquid: where thinnest, at its full where as high as MILK times the Thickness, and
# its patches, their size per meter and their contrast, and the size of the ripples per meter
HAZE = 0.2
MILK = 2.0
PATCHES = 50.0
PATCHINESS = 0.5
RIPPLES = 200.0
# Rope nodes per Thickness travelled at the Speed
NODES = 1.0
# Sways per second of the Wobble, and beads per second along the ropes
WOBBLE_RATE = 20.0
BEAD_RATE = 150.0
# Height of the landed ropes per half width
HEIGHT = 0.25
# Distance between the nodes of a rope, per Thickness, breaking it
BREAK = 8.0
# Iterations evening out the cross-section along the ropes, and spheres across the landed ones
BLUR = 6
ROW = 7
# Seconds before the nodes still falling are removed
FALL = 3.0
# Radius of the trails of the running drops per Thickness, facing down of the surfaces where they
# hang, and seconds from landing before they run
TRAIL = 0.45
HANG = 0.35
SETTLE = 0.5
# Liquid of the running drops, of their start, when they stop
STOP = 0.3
# Ids of the running drops, after the ones of the spurts
RUNS = 1000000


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Ropes of thick liquid shot in spurts from the Control along its Z axis, sticking where "
        "they land on the Targets"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Control", "NodeSocketObject", description="Empty shooting along its Z axis")
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
        default_value=(0.93, 0.93, 0.9, 0.6),
        description="Color of the liquid, its alpha the opacity where thick",
    )
    add_input(ng, "Material", "NodeSocketMaterial", description="Material of the liquid")
    add_input(ng, "Seed", "NodeSocketInt", description="Seed of the aim of the spurts")

    panel = ng.interface.new_panel("Spurts")
    add_input(
        ng,
        "Start Frame",
        "NodeSocketInt",
        panel,
        default_value=1,
        description="Frame of the first spurt",
    )
    add_input(
        ng,
        "Spurts",
        "NodeSocketInt",
        panel,
        default_value=5,
        min_value=0,
        max_value=100,
        description="Number of spurts",
    )
    add_input(
        ng,
        "Interval",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=0.9,
        min_value=0.01,
        max_value=100.0,
        description="Seconds from a spurt to the next",
    )
    add_input(
        ng,
        "Duration",
        "NodeSocketFloat",
        panel,
        subtype="TIME_ABSOLUTE",
        default_value=0.18,
        min_value=0.01,
        max_value=100.0,
        description="Seconds of each spurt",
    )
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        panel,
        default_value=4.0,
        min_value=0.0,
        max_value=100.0,
        description="Speed of the liquid at the start of the first spurt, in meters per second",
    )
    add_input(
        ng,
        "End Speed",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.35,
        min_value=0.0,
        max_value=1.0,
        description="Speed at the end of each spurt, of its start, landing lower as it weakens",
    )
    add_input(
        ng,
        "Fade",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.12,
        min_value=0.0,
        max_value=1.0,
        description="Weakening of each spurt from the one before, slower and thinner",
    )
    add_input(
        ng,
        "Aim",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Random turn of each spurt, landing apart",
    )
    add_input(
        ng,
        "Wobble",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.02,
        min_value=0.0,
        max_value=1.0,
        description="Smooth swaying of the shooting direction, waving the ropes",
    )

    panel = ng.interface.new_panel("Rope")
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0011,
        min_value=0.0001,
        max_value=1.0,
        description="Radius of the ropes leaving the Control, thicker where they pile up",
    )
    add_input(
        ng,
        "Beads",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.15,
        min_value=0.0,
        max_value=1.0,
        description="Thickness changing along the ropes, in beads",
    )

    panel = ng.interface.new_panel("Runs")
    add_input(
        ng,
        "Runs",
        "NodeSocketFloat",
        panel,
        default_value=0.4,
        min_value=0.0,
        max_value=100.0,
        description="Drops starting to run down the slopes per second, gathering the liquid around",
    )
    add_input(
        ng,
        "Run Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0018,
        min_value=0.0,
        max_value=1.0,
        description="Radius of the running drops",
    )
    add_input(
        ng,
        "Run Speed",
        "NodeSocketFloat",
        panel,
        default_value=0.004,
        min_value=0.0,
        max_value=10.0,
        description="Speed of the running drops down a wall, in meters per second",
    )
    add_input(
        ng,
        "Drip Length",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.012,
        min_value=0.0,
        max_value=10.0,
        description="Length the drops hang from the surfaces facing down before dripping",
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
        default_value=0.3,
        min_value=0.0,
        max_value=100.0,
        description="Slowdown of the flying liquid per second",
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
        default_value=2,
        min_value=1,
        max_value=100,
        description="Simulation steps per frame",
    )

    panel = ng.interface.new_panel("Surface")
    add_input(
        ng,
        "Mesh",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="Mesh of the liquid, off to show the ropes as points, faster",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketFloat",
        panel,
        default_value=2.5,
        min_value=0.5,
        max_value=20.0,
        description="Voxels per Thickness of the mesh",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        panel,
        default_value=8,
        min_value=0,
        max_value=20,
        description="Iterations smoothing the mesh, merging the beads",
    )

    t = Tree(ng, spacing=(200, 160))
    cursor = [0, 0]

    def at():
        cursor[1] -= 1
        return {"x": cursor[0], "y": cursor[1]}

    def section(label, row=False):
        t.section(label, row)
        cursor[0] += 10
        cursor[1] = 0

    def node(idname, inputs=None, **props):
        return t.node(idname, inputs=inputs, **at(), **props)

    def m(operation, *values, clamp=False):
        return t.math(operation, *values, clamp=clamp, **at())

    def vm(operation, *values):
        return t.vmath(operation, *values, **at())

    def attribute(name, data_type):
        return t.attribute("rope_" + name, data_type, **at())

    def store(geometry, name, data_type, value, selection=None):
        return t.store(geometry, "rope_" + name, data_type, value, selection=selection, **at())

    def logic(operation, *values):
        return node(
            "FunctionNodeBooleanMath", dict(enumerate(values)), operation=operation
        ).outputs[0]

    def switch(condition, false, true, input_type):
        return node(
            "GeometryNodeSwitch",
            {"Switch": condition, "False": false, "True": true},
            input_type=input_type,
        ).outputs[0]

    section("Spaces", row=True)
    # Simulated in the space of the object, which is locked
    inputs = node("NodeGroupInput").outputs
    position = node("GeometryNodeInputPosition").outputs[0]
    index = node("GeometryNodeInputIndex").outputs[0]
    self_object = node("GeometryNodeSelfObject").outputs[0]
    to_local = node(
        "FunctionNodeInvertMatrix",
        {
            "Matrix": node(
                "GeometryNodeObjectInfo", {"Object": self_object}, transform_space="ORIGINAL"
            ).outputs["Transform"]
        },
    ).outputs[0]
    gravity = node(
        "FunctionNodeTransformDirection", {"Transform": to_local, "Direction": inputs["Gravity"]}
    ).outputs[0]
    thickness = inputs["Thickness"]
    down = vm("NORMALIZE", gravity)

    section("Targets")
    # Each Target with a key of its points staying the same as it deforms, its rest position or
    # its position in its object, and its index
    each_in = node(
        "GeometryNodeForeachGeometryElementInput",
        {
            "Geometry": node(
                "GeometryNodeCollectionInfo",
                {"Collection": inputs["Targets"], "Separate Children": True},
                transform_space="RELATIVE",
            ).outputs[0]
        },
    )
    each_out = node("GeometryNodeForeachGeometryElementOutput", domain="INSTANCE")
    each_in.pair_with_output(each_out)
    each_out.input_items.new("MATRIX", "Transform")
    t.connect(node("GeometryNodeInstanceTransform").outputs[0], each_in.inputs["Transform"])
    target = node("GeometryNodeRealizeInstances", {0: each_in.outputs["Element"]}).outputs[0]
    rest = node(
        "GeometryNodeInputNamedAttribute", {"Name": "rest_position"}, data_type="FLOAT_VECTOR"
    ).outputs
    in_object = node(
        "FunctionNodeTransformPoint",
        {
            "Vector": position,
            "Transform": node(
                "FunctionNodeInvertMatrix", {"Matrix": each_in.outputs["Transform"]}
            ).outputs[0],
        },
    ).outputs[0]
    key = switch(rest["Exists"], in_object, rest["Attribute"], "VECTOR")
    target = store(target, "key", "FLOAT_VECTOR", key)
    target = store(target, "index", "INT", each_in.outputs["Index"])
    target = store(target, "world", "FLOAT_VECTOR", position)
    target = store(
        target, "world_normal", "FLOAT_VECTOR", node("GeometryNodeInputNormal").outputs[0]
    )
    t.connect(target, socket(each_out.inputs, "Generation_0"))
    surfaces = socket(each_out.outputs, "Generation_0")
    keyed = node(
        "GeometryNodeSetPosition",
        {"Geometry": surfaces, "Position": attribute("key", "FLOAT_VECTOR")},
    ).outputs[0]

    def on_targets(value):
        """Value of the Targets as they are now where the nodes landed"""
        return node(
            "GeometryNodeSampleNearestSurface",
            {
                "Mesh": keyed,
                "Value": attribute(value, "FLOAT_VECTOR"),
                "Group ID": attribute("index", "INT"),
                "Sample Position": attribute("rest", "FLOAT_VECTOR"),
                "Sample Group ID": attribute("target", "INT"),
            },
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]

    section("Simulation", row=True)
    sim_in = node("GeometryNodeSimulationInput")
    sim_out = node("GeometryNodeSimulationOutput")
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("FLOAT", "Time")
    sim_out.state_items.new("FLOAT", "Start")
    sim_in.inputs["Start"].default_value = -1.0
    dt = m("MULTIPLY", sim_in.outputs["Delta Time"], inputs["Time Scale"])
    time = sim_in.outputs["Time"]
    stuck = attribute("stuck", "BOOLEAN")
    # Started at the Start Frame
    frame = node("GeometryNodeInputSceneTime").outputs["Frame"]
    start = switch(
        logic(
            "AND",
            m("LESS_THAN", sim_in.outputs["Start"], 0.0),
            m("GREATER_THAN", frame, m("SUBTRACT", inputs["Start Frame"], 0.5)),
        ),
        sim_in.outputs["Start"],
        time,
        "FLOAT",
    )
    started = m("GREATER_THAN", start, -0.5)
    # The landed nodes on the Targets as they are now
    state = node(
        "GeometryNodeSetPosition",
        {
            "Geometry": sim_in.outputs["Geometry"],
            "Selection": stuck,
            "Position": on_targets("world"),
        },
    ).outputs[0]
    state = store(
        state, "normal", "FLOAT_VECTOR", vm("NORMALIZE", on_targets("world_normal")), stuck
    )

    section("Runs")
    # Hanging under where they hang from
    hang = attribute("hang", "FLOAT")
    runner = attribute("runner", "BOOLEAN")
    normal = attribute("normal", "FLOAT_VECTOR")
    state = node(
        "GeometryNodeSetPosition",
        {"Geometry": state, "Selection": stuck, "Offset": vm("SCALE", down, hang)},
    ).outputs[0]
    elapsed = m("SUBTRACT", time, start)
    # Captured, not to change as the attributes they are made of change
    flags = node("GeometryNodeCaptureAttribute", {"Geometry": state})
    hanging = logic("AND", stuck, m("GREATER_THAN", hang, 0.0))
    for name, data_type, value in (
        ("Hanging", "BOOLEAN", hanging),
        ("Running", "BOOLEAN", logic("AND", runner, logic("NOT", hanging))),
        (
            "Downhill",
            "VECTOR",
            vm("SUBTRACT", down, vm("SCALE", normal, vm("DOT_PRODUCT", down, normal))),
        ),
        ("Longer", "FLOAT", m("ADD", hang, m("MULTIPLY", inputs["Run Speed"], dt))),
    ):
        flags.capture_items.new(data_type, name)
        t.connect(value, flags.inputs[name])
    state = flags.outputs["Geometry"]
    hanging, running, downhill, longer = (
        flags.outputs[name] for name in ("Hanging", "Running", "Downhill", "Longer")
    )
    # Running down the slopes, leaving a trail of their liquid where they were
    travel = m("MULTIPLY", m("MULTIPLY", inputs["Run Speed"], dt), vm("LENGTH", downhill))
    trail_volume = m(
        "MULTIPLY", travel, m("MULTIPLY", m("MULTIPLY", thickness, thickness), 3.14159 * TRAIL**2)
    )
    trail = node(
        "GeometryNodeDuplicateElements",
        {"Geometry": state, "Selection": running},
        domain="POINT",
    ).outputs["Geometry"]
    trail = store(trail, "volume", "FLOAT", trail_volume)
    trail = store(trail, "runner", "BOOLEAN", False)
    trail = store(trail, "birth", "FLOAT", elapsed)
    state = store(
        state, "volume", "FLOAT", m("SUBTRACT", attribute("volume", "FLOAT"), trail_volume), running
    )
    state = store(state, "birth", "FLOAT", m("ADD", elapsed, 1e-4), running)
    # On the Targets as they are now, where they ran to
    goal = vm("ADD", position, vm("SCALE", downhill, m("MULTIPLY", inputs["Run Speed"], dt)))
    snap = node("GeometryNodeCaptureAttribute", {"Geometry": state})
    for name, data_type, value in (
        ("Position", "VECTOR", position),
        ("Normal", "VECTOR", node("GeometryNodeInputNormal").outputs[0]),
        ("Key", "VECTOR", attribute("key", "FLOAT_VECTOR")),
        ("Index", "INT", attribute("index", "INT")),
    ):
        snap.capture_items.new(data_type, name)
        t.connect(
            node(
                "GeometryNodeSampleNearestSurface",
                {"Mesh": surfaces, "Value": value, "Sample Position": goal},
                data_type="INT" if data_type == "INT" else "FLOAT_VECTOR",
            ).outputs["Value"],
            snap.inputs[name],
        )
    state = node(
        "GeometryNodeSetPosition",
        {
            "Geometry": snap.outputs["Geometry"],
            "Selection": running,
            "Position": snap.outputs["Position"],
        },
    ).outputs[0]
    state = store(state, "normal", "FLOAT_VECTOR", vm("NORMALIZE", snap.outputs["Normal"]), running)
    state = store(state, "rest", "FLOAT_VECTOR", snap.outputs["Key"], running)
    state = store(state, "target", "INT", snap.outputs["Index"], running)
    # Stopping with too little liquid left, and hanging from the surfaces facing down
    drop = m("MULTIPLY", m("POWER", inputs["Run Size"], 3.0), 4.18879)
    state = store(
        state,
        "runner",
        "BOOLEAN",
        m("GREATER_THAN", attribute("volume", "FLOAT"), m("MULTIPLY", drop, STOP)),
        running,
    )
    state = store(
        state,
        "hang",
        "FLOAT",
        1e-5,
        logic("AND", running, m("GREATER_THAN", vm("DOT_PRODUCT", normal, down), HANG)),
    )
    # Hanging longer, dripping when as long as the Drip Length
    state = store(state, "hang", "FLOAT", longer, hanging)
    dripping = logic("AND", hanging, m("GREATER_THAN", longer, inputs["Drip Length"]))
    for name, data_type, value in (
        ("stuck", "BOOLEAN", False),
        ("runner", "BOOLEAN", False),
        ("hang", "FLOAT", 0.0),
        ("velocity", "FLOAT_VECTOR", (0.0, 0.0, 0.0)),
    ):
        state = store(state, name, data_type, value, dripping)
    # New drops on the slopes, a while after landing, at the rate of the Runs, taking the liquid
    # around them
    ready = logic(
        "AND",
        logic(
            "AND",
            logic("AND", stuck, logic("NOT", runner)),
            m("LESS_THAN", attribute("id", "INT"), RUNS - 0.5),
        ),
        logic(
            "AND",
            m("GREATER_THAN", m("SUBTRACT", elapsed, attribute("landed", "FLOAT")), SETTLE),
            m("GREATER_THAN", vm("LENGTH", downhill), 0.5),
        ),
    )
    ready_count = node(
        "GeometryNodeAttributeStatistic", {"Geometry": state, "Attribute": ready}, domain="POINT"
    ).outputs["Sum"]
    chance = m("DIVIDE", m("MULTIPLY", inputs["Runs"], dt), m("MAXIMUM", ready_count, 1.0))
    starting = logic(
        "AND",
        ready,
        m(
            "LESS_THAN",
            node(
                "FunctionNodeRandomValue",
                {"ID": index, "Seed": m("MULTIPLY_ADD", frame, 13.0, inputs["Seed"])},
                data_type="FLOAT",
            ).outputs[0],
            chance,
        ),
    )
    runs = node(
        "GeometryNodeDuplicateElements", {"Geometry": state, "Selection": starting}, domain="POINT"
    ).outputs["Geometry"]
    runs = store(runs, "runner", "BOOLEAN", True)
    runs = store(runs, "volume", "FLOAT", drop)
    runs = store(runs, "birth", "FLOAT", m("ADD", elapsed, 1e-4))
    runs = store(
        runs,
        "id",
        "INT",
        m("ADD", m("MULTIPLY_ADD", m("FLOORED_MODULO", frame, 10000.0), 1000.0, RUNS), index),
    )
    near = node("GeometryNodeProximity", {"Geometry": runs}, target_element="POINTS").outputs
    gathered = logic(
        "AND",
        m("LESS_THAN", attribute("id", "INT"), RUNS - 0.5),
        logic(
            "AND",
            near["Is Valid"],
            m("LESS_THAN", near["Distance"], m("MULTIPLY", inputs["Run Size"], 2.0)),
        ),
    )
    state = store(
        state, "volume", "FLOAT", m("MULTIPLY", attribute("volume", "FLOAT"), 0.4), gathered
    )
    runs_join = node("GeometryNodeJoinGeometry")
    for geometry in (state, trail, runs):
        t.connect(geometry, runs_join.inputs[0])
    state = runs_join.outputs[0]

    section("Spurts")
    # The nodes of the time of the frame, kept in the spurts
    rate = m("DIVIDE", m("MULTIPLY", inputs["Speed"], NODES), thickness)
    before = m("FLOOR", m("MULTIPLY", m("SUBTRACT", time, start), rate))
    count = m(
        "SUBTRACT",
        m("FLOOR", m("MULTIPLY", m("SUBTRACT", m("ADD", time, dt), start), rate)),
        before,
    )
    points = node(
        "GeometryNodePoints", {"Count": m("MULTIPLY", m("MAXIMUM", count, 0.0), started)}
    ).outputs[0]
    # When emitted, stored as the points out of the spurts are removed
    points = store(
        points, "birth", "FLOAT", m("DIVIDE", m("ADD", before, m("ADD", index, 1.0)), rate)
    )
    emitted = attribute("birth", "FLOAT")
    spurt = m("FLOOR", m("DIVIDE", emitted, inputs["Interval"]))
    along = m(
        "DIVIDE",
        m("SUBTRACT", emitted, m("MULTIPLY", spurt, inputs["Interval"])),
        inputs["Duration"],
    )
    outside = logic(
        "OR",
        m("GREATER_THAN", spurt, m("SUBTRACT", inputs["Spurts"], 0.5)),
        m("GREATER_THAN", along, 1.0),
    )
    points = node(
        "GeometryNodeDeleteGeometry", {"Geometry": points, "Selection": outside}, domain="POINT"
    ).outputs[0]
    strength = m("POWER", m("SUBTRACT", 1.0, inputs["Fade"]), spurt)
    speed = m(
        "MULTIPLY",
        m("MULTIPLY", inputs["Speed"], strength),
        m("MULTIPLY_ADD", along, m("SUBTRACT", inputs["End Speed"], 1.0), 1.0),
    )
    # Beads along the ropes, thin at their ends
    beads = node(
        "ShaderNodeTexNoise",
        {"W": m("MULTIPLY_ADD", emitted, BEAD_RATE, m("MULTIPLY", spurt, 7.3)), "Detail": 0.0},
        noise_dimensions="1D",
    ).outputs["Factor"]
    beads = m("MULTIPLY_ADD", m("SUBTRACT", beads, 0.5), m("MULTIPLY", inputs["Beads"], 4.0), 1.0)
    ends = m(
        "POWER",
        m(
            "MINIMUM",
            m("MULTIPLY", along, 6.0),
            m("MULTIPLY", m("SUBTRACT", 1.0, along), 4.0),
            clamp=True,
        ),
        0.5,
    )
    radius = m(
        "MAXIMUM",
        m("MULTIPLY", m("MULTIPLY", thickness, m("SQRT", strength)), m("MULTIPLY", beads, ends)),
        m("MULTIPLY", thickness, 0.2),
    )
    # Along the Control, turned for each spurt and swaying
    control = node(
        "GeometryNodeObjectInfo", {"Object": inputs["Control"]}, transform_space="RELATIVE"
    ).outputs
    axis = vm(
        "NORMALIZE",
        node(
            "FunctionNodeTransformDirection",
            {"Transform": control["Transform"], "Direction": (0.0, 0.0, 1.0)},
        ).outputs[0],
    )
    turn = node(
        "FunctionNodeRandomValue",
        {"Min": (-1.0, -1.0, -1.0), "ID": spurt, "Seed": inputs["Seed"]},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    # Across the axis, landing apart
    turn = vm("SUBTRACT", turn, vm("SCALE", axis, vm("DOT_PRODUCT", turn, axis)))
    sway = node(
        "ShaderNodeTexNoise",
        {
            "W": m("MULTIPLY_ADD", inputs["Seed"], 3.1, m("MULTIPLY", emitted, WOBBLE_RATE)),
            "Detail": 0.0,
        },
        noise_dimensions="1D",
    ).outputs["Color"]
    sway = vm(
        "MULTIPLY", vm("SUBTRACT", sway, (0.5, 0.5, 0.5)), m("MULTIPLY", inputs["Wobble"], 2.0)
    )
    direction = vm("NORMALIZE", vm("ADD", vm("ADD", axis, vm("SCALE", turn, inputs["Aim"])), sway))
    velocity = vm("SCALE", direction, speed)
    # Back from the Control as long before the frame as they were emitted, flying in it
    points = node(
        "GeometryNodeSetPosition",
        {
            "Geometry": points,
            "Position": vm(
                "ADD",
                control["Location"],
                vm("SCALE", velocity, m("SUBTRACT", m("SUBTRACT", time, start), emitted)),
            ),
        },
    ).outputs[0]
    points = store(points, "velocity", "FLOAT_VECTOR", velocity)
    # Liquid of each node, as long as the distance to the next emitted
    points = store(
        points,
        "volume",
        "FLOAT",
        m(
            "MULTIPLY",
            m("MULTIPLY", m("MULTIPLY", radius, radius), 3.14159),
            m("DIVIDE", speed, rate),
        ),
    )
    points = store(points, "id", "INT", spurt)
    join = node("GeometryNodeJoinGeometry")
    for geometry in (state, points):
        t.connect(geometry, join.inputs[0])

    section("Flight")
    steps_in = node("GeometryNodeRepeatInput", {"Iterations": inputs["Substeps"]})
    steps_out = node("GeometryNodeRepeatOutput")
    steps_in.pair_with_output(steps_out)
    t.connect(join.outputs[0], steps_in.inputs["Geometry"])
    step = m("DIVIDE", dt, inputs["Substeps"])
    flying = logic("NOT", stuck)
    # Falling, slowed by the drag, and landing where they hit the Targets
    moved = vm(
        "SCALE",
        vm("ADD", attribute("velocity", "FLOAT_VECTOR"), vm("SCALE", gravity, step)),
        m("DIVIDE", 1.0, m("MULTIPLY_ADD", inputs["Drag"], step, 1.0)),
    )
    hit = node("GeometryNodeCaptureAttribute", {"Geometry": steps_in.outputs["Geometry"]})
    rays = [
        node(
            "GeometryNodeRaycast",
            {
                "Target Geometry": surfaces,
                "Attribute": attribute(name, data_type),
                "Source Position": position,
                "Ray Direction": moved,
                "Ray Length": m("MULTIPLY", vm("LENGTH", moved), step),
            },
            data_type=data_type,
        ).outputs
        for name, data_type in (("key", "FLOAT_VECTOR"), ("index", "INT"))
    ]
    for name, data_type, value in (
        ("Hit", "BOOLEAN", logic("AND", rays[0]["Is Hit"], flying)),
        ("Position", "VECTOR", rays[0]["Hit Position"]),
        ("Normal", "VECTOR", rays[0]["Hit Normal"]),
        ("Key", "VECTOR", rays[0]["Attribute"]),
        ("Target", "INT", rays[1]["Attribute"]),
        ("Velocity", "VECTOR", moved),
    ):
        hit.capture_items.new(data_type, name)
        t.connect(value, hit.inputs[name])
    hits = hit.outputs["Hit"]
    geometry = node(
        "GeometryNodeSetPosition",
        {
            "Geometry": hit.outputs["Geometry"],
            "Selection": flying,
            "Position": switch(
                hits,
                vm("ADD", position, vm("SCALE", hit.outputs["Velocity"], step)),
                hit.outputs["Position"],
                "VECTOR",
            ),
        },
    ).outputs[0]
    geometry = store(geometry, "velocity", "FLOAT_VECTOR", hit.outputs["Velocity"], flying)
    geometry = store(geometry, "normal", "FLOAT_VECTOR", hit.outputs["Normal"], hits)
    geometry = store(geometry, "rest", "FLOAT_VECTOR", hit.outputs["Key"], hits)
    geometry = store(geometry, "target", "INT", hit.outputs["Target"], hits)
    geometry = store(geometry, "stuck", "BOOLEAN", True, hits)
    geometry = store(geometry, "landed", "FLOAT", m("SUBTRACT", m("ADD", time, dt), start), hits)
    t.connect(geometry, steps_out.inputs["Geometry"])
    # Without the nodes falling past the Targets
    state = node(
        "GeometryNodeDeleteGeometry",
        {
            "Geometry": steps_out.outputs["Geometry"],
            "Selection": logic(
                "AND",
                flying,
                m(
                    "GREATER_THAN",
                    m(
                        "SUBTRACT",
                        m("SUBTRACT", m("ADD", time, dt), start),
                        attribute("birth", "FLOAT"),
                    ),
                    FALL,
                ),
            ),
        },
        domain="POINT",
    ).outputs[0]
    t.connect(state, sim_out.inputs["Geometry"])
    t.connect(m("ADD", time, dt), sim_out.inputs["Time"])
    t.connect(start, sim_out.inputs["Start"])

    section("Ropes", row=True)
    # The nodes of each spurt in order, broken where apart
    ropes = node(
        "GeometryNodeSortElements",
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Group ID": attribute("id", "INT"),
            "Sort Weight": attribute("birth", "FLOAT"),
        },
        domain="POINT",
    ).outputs[0]

    def following(value, data_type):
        return node(
            "GeometryNodeSampleIndex",
            {"Geometry": ropes, "Value": value, "Index": m("ADD", index, 1.0)},
            data_type=data_type,
            domain="POINT",
            clamp=True,
        ).outputs[0]

    # Landed apart from flying, their shapes not to blend into bulges, but the hanging drops
    lying = logic("AND", stuck, logic("NOT", m("GREATER_THAN", attribute("hang", "FLOAT"), 0.0)))
    hanger = following(attribute("runner", "BOOLEAN"), "BOOLEAN")
    joined = logic(
        "AND",
        node(
            "FunctionNodeCompare",
            {"A": attribute("id", "INT"), "B": following(attribute("id", "INT"), "INT")},
            data_type="INT",
            operation="EQUAL",
        ).outputs[0],
        logic(
            "OR",
            hanger,
            logic(
                "AND",
                m(
                    "LESS_THAN",
                    vm("DISTANCE", position, following(position, "FLOAT_VECTOR")),
                    m("MULTIPLY", thickness, BREAK),
                ),
                logic("XNOR", lying, following(lying, "BOOLEAN")),
            ),
        ),
    )
    ropes = store(
        ropes,
        "rope",
        "INT",
        node(
            "GeometryNodeAccumulateField", {"Value": logic("NOT", joined)}, data_type="INT"
        ).outputs["Trailing"],
    )

    curves = node(
        "GeometryNodePointsToCurves",
        {
            "Points": ropes,
            "Curve Group ID": attribute("rope", "INT"),
            "Weight": attribute("birth", "FLOAT"),
        },
    ).outputs[0]

    # Cross-section of the liquid of the nodes along the length of rope they hold, half the way to
    # the nodes before and after, thinning as it stretches and thickening as it piles up, evened
    # out along the rope
    def neighbor(offset):
        """Distance to the node before or after in the rope, 0 at its ends"""
        other = node("GeometryNodeOffsetPointInCurve", {"Offset": offset}).outputs
        return m(
            "MULTIPLY",
            vm(
                "DISTANCE",
                position,
                node(
                    "GeometryNodeSampleIndex",
                    {"Geometry": curves, "Value": position, "Index": other["Point Index"]},
                    data_type="FLOAT_VECTOR",
                    domain="POINT",
                ).outputs[0],
            ),
            other["Is Valid Offset"],
        )

    sides = m(
        "ADD",
        node("GeometryNodeOffsetPointInCurve", {"Offset": 1}).outputs["Is Valid Offset"],
        node("GeometryNodeOffsetPointInCurve", {"Offset": -1}).outputs["Is Valid Offset"],
    )
    length = switch(
        m("GREATER_THAN", sides, 0.5),
        thickness,
        m("DIVIDE", m("ADD", neighbor(1), neighbor(-1)), m("MAXIMUM", sides, 1.0)),
        "FLOAT",
    )
    # The running drops as long as wide
    length = switch(
        attribute("runner", "BOOLEAN"),
        length,
        m("POWER", attribute("volume", "FLOAT"), 1 / 3),
        "FLOAT",
    )
    area = m(
        "DIVIDE",
        attribute("volume", "FLOAT"),
        m("MAXIMUM", length, m("MULTIPLY", thickness, 0.25)),
    )
    curves = store(
        curves,
        "area",
        "FLOAT",
        node(
            "GeometryNodeBlurAttribute", {"Value": area, "Iterations": BLUR}, data_type="FLOAT"
        ).outputs[0],
    )
    area = attribute("area", "FLOAT")
    # Flying round, not thinner than the voxels, and landed as wide and as high as the HEIGHT of
    # its half width
    curves = node(
        "GeometryNodeSetCurveRadius",
        {
            "Curve": curves,
            "Radius": m(
                "MAXIMUM", m("SQRT", m("DIVIDE", area, 3.14159)), m("MULTIPLY", thickness, 0.35)
            ),
        },
    ).outputs[0]
    width = m("SQRT", m("DIVIDE", m("MULTIPLY", area, 2.0), 3.14159 * HEIGHT))
    curves = store(curves, "width", "FLOAT", width)
    curves = store(curves, "lying", "FLOAT", lying)
    curves = node(
        "GeometryNodeCurveSplineType", {"Curve": curves}, spline_type="CATMULL_ROM"
    ).outputs[0]
    curves = node(
        "GeometryNodeResampleCurve",
        {"Curve": curves, "Mode": "Length", "Length": m("MULTIPLY", thickness, 0.5)},
    ).outputs[0]
    samples = node("GeometryNodeCurveToPoints", {"Curve": curves}, mode="EVALUATED").outputs
    tangent = samples["Tangent"]
    samples = samples["Points"]
    samples = store(
        samples,
        "across",
        "FLOAT_VECTOR",
        vm("NORMALIZE", vm("CROSS_PRODUCT", tangent, attribute("normal", "FLOAT_VECTOR"))),
    )
    flat = m("GREATER_THAN", attribute("lying", "FLOAT"), 0.5)
    # Landed, as a row of spheres across the rope on the surface, as high as an ellipse, hugging
    # the surface however curved
    row = node(
        "GeometryNodeDuplicateElements",
        {
            "Geometry": node(
                "GeometryNodeDeleteGeometry",
                {"Geometry": samples, "Selection": logic("NOT", flat)},
                domain="POINT",
            ).outputs[0],
            "Amount": ROW,
        },
        domain="POINT",
    ).outputs
    side = m("MULTIPLY", m("MULTIPLY_ADD", row["Duplicate Index"], 2.0 / (ROW - 1), -1.0), 0.85)
    width = attribute("width", "FLOAT")
    row = node(
        "GeometryNodeSetPosition",
        {
            "Geometry": row["Geometry"],
            "Position": node(
                "GeometryNodeSampleNearestSurface",
                {
                    "Mesh": surfaces,
                    "Value": position,
                    "Sample Position": vm(
                        "ADD",
                        position,
                        vm(
                            "SCALE", attribute("across", "FLOAT_VECTOR"), m("MULTIPLY", side, width)
                        ),
                    ),
                },
                data_type="FLOAT_VECTOR",
            ).outputs["Value"],
        },
    ).outputs[0]
    row = node(
        "GeometryNodeSetPointRadius",
        {
            "Points": row,
            "Radius": m(
                "MULTIPLY",
                m("MULTIPLY", width, HEIGHT),
                m("SQRT", m("SUBTRACT", 1.0, m("MULTIPLY", side, side))),
            ),
        },
    ).outputs[0]
    round_points = node(
        "GeometryNodeDeleteGeometry", {"Geometry": samples, "Selection": flat}, domain="POINT"
    ).outputs[0]
    samples = node("GeometryNodeJoinGeometry")
    for geometry in (round_points, row):
        t.connect(geometry, samples.inputs[0])
    samples = samples.outputs[0]

    section("Mesh")
    voxel = m("DIVIDE", thickness, inputs["Resolution"])
    sdf = node(
        "GeometryNodePointsToSDFGrid",
        {
            "Points": samples,
            "Radius": node("GeometryNodeInputRadius").outputs[0],
            "Voxel Size": voxel,
        },
    ).outputs[0]
    sdf = node(
        "GeometryNodeSDFGridMean", {"Grid": sdf, "Width": 1, "Iterations": inputs["Smooth"]}
    ).outputs[0]
    mesh = node("GeometryNodeGridToMesh", {"Grid": sdf}).outputs[0]
    # Above the Targets only, with the height over them for the shader
    near = [
        node(
            "GeometryNodeSampleNearestSurface",
            {"Mesh": surfaces, "Value": value},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        for value in (
            position,
            node("GeometryNodeInputNormal").outputs[0],
            attribute("key", "FLOAT_VECTOR"),
        )
    ]
    above = vm("DOT_PRODUCT", vm("SUBTRACT", position, near[0]), vm("NORMALIZE", near[1]))
    mesh = t.store(mesh, "liquid_height", "FLOAT", m("DIVIDE", above, thickness), **at())
    # Where on the Targets, for the shader patterns to stay on them as they move
    mesh = t.store(mesh, "liquid_coordinate", "FLOAT_VECTOR", near[2], **at())
    mesh = node(
        "GeometryNodeDeleteGeometry",
        {
            "Geometry": mesh,
            "Selection": m("LESS_THAN", t.attribute("liquid_height", "FLOAT", **at()), -0.3),
        },
        domain="POINT",
    ).outputs[0]
    mesh = node("GeometryNodeSetShadeSmooth", {"Mesh": mesh}).outputs[0]
    # Nothing without liquid, the grid empty
    has_liquid = m(
        "GREATER_THAN",
        node(
            "GeometryNodeAttributeDomainSize", {"Geometry": samples}, component="POINTCLOUD"
        ).outputs["Point Count"],
        0.0,
    )
    mesh = switch(has_liquid, None, mesh, "GEOMETRY")
    liquid = switch(inputs["Mesh"], samples, mesh, "GEOMETRY")
    liquid = t.store(liquid, "liquid_color", "FLOAT_COLOR", inputs["Color"], **at())
    liquid = node(
        "GeometryNodeSetMaterial", {"Geometry": liquid, "Material": inputs["Material"]}
    ).outputs[0]
    # Bakeable with the simulation, for the playback not to mesh every frame again
    bake = node("GeometryNodeBake")
    bake.bake_items.new("GEOMETRY", "Geometry")
    t.connect(liquid, bake.inputs["Geometry"])
    node("NodeGroupOutput", {0: bake.outputs["Geometry"]})
    t.arrange()
    return ng


def build_material():
    """Milky by the height of the liquid, in patches, a haze where thin, under a wet coat,
    colored by liquid_color"""
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    material.use_transparent_shadow = True
    material.surface_render_method = "BLENDED"
    material.use_backface_culling = True
    material.use_transparency_overlap = False
    t = Tree(material.node_tree)
    color = t.node("ShaderNodeAttribute", -6, 2, attribute_name="liquid_color").outputs
    height = t.node(
        "ShaderNodeAttribute", -6, -1, attribute_type="GEOMETRY", attribute_name="liquid_height"
    ).outputs["Fac"]
    where = t.node(
        "ShaderNodeAttribute", -6, -3, attribute_type="GEOMETRY", attribute_name="liquid_coordinate"
    ).outputs["Vector"]
    # Milkier where higher, from a haze, in patches, opaque as the alpha of the color
    milk = t.node(
        "ShaderNodeMapRange",
        -4,
        -1,
        {"Value": t.math("DIVIDE", height, MILK, x=-5, y=-1, clamp=True), "To Min": HAZE},
    ).outputs[0]
    patches = t.node(
        "ShaderNodeTexNoise", -5, -3, {"Vector": where, "Scale": PATCHES, "Detail": 0.0}
    ).outputs["Factor"]
    patches = t.node(
        "ShaderNodeMapRange",
        -4,
        -3,
        {
            "Value": patches,
            "From Min": 0.35,
            "From Max": 0.65,
            "To Min": 1.0 - PATCHINESS,
            "To Max": 1.0 + PATCHINESS,
        },
    ).outputs[0]
    milk = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", milk, patches, x=-3, y=-2),
        color["Alpha"],
        x=-2,
        y=-2,
        clamp=True,
    )
    # Small ripples catching the light
    ripples = t.node(
        "ShaderNodeBump",
        -3,
        -5,
        {
            "Strength": 0.1,
            "Distance": 0.0005,
            "Height": t.node(
                "ShaderNodeTexNoise", -4, -5, {"Vector": where, "Scale": RIPPLES, "Detail": 0.0}
            ).outputs["Factor"],
        },
    ).outputs["Normal"]
    milky = t.node(
        "ShaderNodeBsdfPrincipled",
        -1,
        1,
        {
            "Base Color": color["Color"],
            "Roughness": 0.35,
            "Specular IOR Level": 0.0,
            "Subsurface Weight": 0.6,
            "Subsurface Radius": (1.0, 0.9, 0.8),
            "Subsurface Scale": 0.003,
            "Normal": ripples,
        },
    ).outputs[0]
    under = t.node(
        "ShaderNodeMixShader",
        0,
        0,
        {0: milk, 1: t.node("ShaderNodeBsdfTransparent", -1, -1).outputs[0], 2: milky},
    ).outputs[0]
    # Wet coat over all, reflecting more at grazing angles, stronger than water for its highlights
    surface = t.node(
        "ShaderNodeMixShader",
        1,
        0,
        {
            0: t.node("ShaderNodeFresnel", 0, -2, {"IOR": 1.8, "Normal": ripples}).outputs[0],
            1: under,
            2: t.node(
                "ShaderNodeBsdfGlossy", 0, -3, {"Roughness": 0.02, "Normal": ripples}
            ).outputs[0],
        },
    )
    t.node("ShaderNodeOutputMaterial", 3, 0, {"Surface": surface.outputs[0]})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material()))
