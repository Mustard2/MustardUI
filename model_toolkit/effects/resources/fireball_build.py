# Build fireball.blend: the Fireball node group and material
# Usage: Blender --background --factory-startup --python fireball_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "fireball.blend"
NODE_GROUP = "MustardUI Fireball"
MATERIAL = "MustardUI Fireball"


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = "Fireball on the Control, emitting particles that trail behind it as it moves"

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Control", "NodeSocketObject", description="Empty whose sphere is the fireball")
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(1.0, 0.22, 0.02, 1.0),
        description="Color of the flames, stored in the fireball_color attribute",
    )
    add_input(
        ng,
        "Brightness",
        "NodeSocketFloat",
        default_value=1.0,
        min_value=0.0,
        max_value=100.0,
        description="Multiplier of the emission strength, stored in the fireball_brightness attribute",  # noqa: E501
    )
    add_input(
        ng, "Material", "NodeSocketMaterial", description="Material of the core and the particles"
    )

    panel = ng.interface.new_panel("Core")
    add_input(
        ng,
        "Core Noise",
        "NodeSocketFloat",
        panel,
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Irregularity of the core surface",
    )
    add_input(
        ng,
        "Flicker",
        "NodeSocketFloat",
        panel,
        default_value=3.0,
        min_value=0.0,
        max_value=100.0,
        description="Speed of the core surface changes",
    )

    panel = ng.interface.new_panel("Particles")
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        panel,
        default_value=5000.0,
        min_value=0.0,
        max_value=1e6,
        description="Particles emitted each frame per square meter of core",
    )
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        panel,
        default_value=0.0035,
        min_value=0.0,
        max_value=1.0,
        subtype="DISTANCE",
        description="Radius of the particles",
    )
    add_input(
        ng,
        "Lifetime",
        "NodeSocketFloat",
        panel,
        default_value=7.0,
        min_value=0.01,
        max_value=1000.0,
        subtype="TIME_ABSOLUTE",
        description="Seconds before the particles disappear",
    )
    add_input(
        ng,
        "Randomness",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Variation of size, lifetime and speed between particles",
    )

    panel = ng.interface.new_panel("Motion")
    add_input(
        ng,
        "Speed",
        "NodeSocketFloat",
        panel,
        default_value=0.05,
        min_value=0.0,
        max_value=100.0,
        description="Initial speed of the particles, away from the core",
    )
    add_input(
        ng,
        "Force",
        "NodeSocketVector",
        panel,
        default_value=(0.0, 0.0, 0.3),
        subtype="ACCELERATION",
        description="Acceleration of the particles, in world space",
    )
    add_input(
        ng,
        "Turbulence",
        "NodeSocketFloat",
        panel,
        default_value=1.5,
        min_value=0.0,
        max_value=100.0,
        description="Strength of the random motion",
    )
    add_input(
        ng,
        "Turbulence Scale",
        "NodeSocketFloat",
        panel,
        default_value=5.0,
        min_value=0.0,
        max_value=1000.0,
        description="Size of the random motion",
    )
    add_input(
        ng,
        "Drag",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.0,
        max_value=100.0,
        description="Slowdown of the particles per second",
    )

    t = Tree(ng)
    inputs = t.node("NodeGroupInput", -14, 0).outputs
    time = t.node("GeometryNodeInputSceneTime", -14, -3).outputs
    info = t.node(
        "GeometryNodeObjectInfo",
        -12,
        2,
        {"Object": inputs["Control"]},
        transform_space="RELATIVE",
    )
    location = info.outputs["Location"]

    # Core: a unit sphere with a flickering surface, on the Control
    ico = t.node("GeometryNodeMeshIcoSphere", -12, 6, {"Subdivisions": 4})
    flicker = t.math("MULTIPLY", time["Seconds"], inputs["Flicker"], x=-12, y=8)
    noise = t.node(
        "ShaderNodeTexNoise", -11, 8, {"Scale": 1.5, "W": flicker}, noise_dimensions="4D"
    )
    bump = t.math("SUBTRACT", noise.outputs["Fac"], 0.5, x=-10, y=8)
    bump = t.math("MULTIPLY", bump, inputs["Core Noise"], x=-9, y=8)
    bump = t.math("MULTIPLY", bump, 2.0, x=-8, y=8)
    normal = t.node("GeometryNodeInputNormal", -8, 9).outputs[0]
    surface = t.node(
        "GeometryNodeSetPosition",
        -7,
        6,
        {"Geometry": ico.outputs["Mesh"], "Offset": t.vmath("SCALE", normal, bump, x=-7, y=8)},
    )
    core = t.node(
        "GeometryNodeTransform",
        -6,
        6,
        {
            "Geometry": surface.outputs["Geometry"],
            "Translation": location,
            "Rotation": info.outputs["Rotation"],
            "Scale": info.outputs["Scale"],
        },
    ).outputs["Geometry"]

    # Emission from the surface, spread along the motion of the Control since the previous frame
    sim_in = t.node("GeometryNodeSimulationInput", -6, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 12, 0)
    sim_in.pair_with_output(sim_out)
    sim_out.state_items.new("VECTOR", "Previous")
    t.connect(location, sim_in.inputs["Previous"])
    dt = sim_in.outputs["Delta Time"]

    distribute = t.node(
        "GeometryNodeDistributePointsOnFaces",
        -10,
        0,
        {"Mesh": core, "Density": inputs["Density"], "Seed": time["Frame"]},
        distribute_method="RANDOM",
    )
    random = t.node(
        "FunctionNodeRandomValue", -9, -3, {"Seed": time["Frame"]}, data_type="FLOAT_VECTOR"
    )
    spread = t.vmath("SCALE", random.outputs[0], inputs["Randomness"], x=-8, y=-3)
    variation = t.node(
        "ShaderNodeSeparateXYZ",
        -7,
        -3,
        {0: t.vmath("SUBTRACT", (1.0, 1.0, 1.0), spread, x=-7.5, y=-3)},
    ).outputs
    speed = t.math("MULTIPLY", inputs["Speed"], variation[0], x=-8, y=-6)
    emitted = distribute.outputs["Points"]
    for i, (name, data_type, value) in enumerate(
        (
            (
                "velocity",
                "FLOAT_VECTOR",
                t.vmath("SCALE", distribute.outputs["Normal"], speed, x=-7, y=-5),
            ),
            ("size", "FLOAT", t.math("MULTIPLY", inputs["Size"], variation[1], x=-6, y=-7)),
            ("lifetime", "FLOAT", t.math("MULTIPLY", inputs["Lifetime"], variation[2], x=-6, y=-8)),
        )
    ):
        emitted = t.store(emitted, name, data_type, value, -6 + i * 0.7, -1)

    seed = t.math("ADD", time["Frame"], 0.5, x=-6, y=-4)
    spread = t.node("FunctionNodeRandomValue", -5, -4, {"Seed": seed}, data_type="FLOAT")
    motion = t.vmath("SUBTRACT", sim_in.outputs["Previous"], location, x=-5, y=-3)
    trail = t.node(
        "GeometryNodeSetPosition",
        -4,
        -1,
        {"Geometry": emitted, "Offset": t.vmath("SCALE", motion, spread.outputs[0], x=-4, y=-3)},
    )
    join = t.node("GeometryNodeJoinGeometry", -3, 0)
    t.connect(trail.outputs["Geometry"], join.inputs[0])
    t.connect(sim_in.outputs["Geometry"], join.inputs[0])

    # Force from world to object space, and turbulence
    self_object = t.node("GeometryNodeSelfObject", -5, -9).outputs[0]
    self_info = t.node(
        "GeometryNodeObjectInfo", -4, -9, {"Object": self_object}, transform_space="ORIGINAL"
    )
    invert = t.node("FunctionNodeInvertMatrix", -3, -9, {0: self_info.outputs["Transform"]})
    force = t.node(
        "FunctionNodeTransformDirection",
        -2,
        -9,
        {"Transform": invert.outputs[0], "Direction": inputs["Force"]},
    )

    turbulence = t.node(
        "ShaderNodeTexNoise",
        -3,
        -12,
        {"W": time["Seconds"], "Scale": inputs["Turbulence Scale"]},
        noise_dimensions="4D",
    )
    turbulence = t.vmath("SUBTRACT", turbulence.outputs["Color"], (0.5, 0.5, 0.5), x=-2, y=-12)
    strength = t.math("MULTIPLY", inputs["Turbulence"], 2.0, x=-2, y=-13)
    turbulence = t.vmath("SCALE", turbulence, strength, x=-1, y=-12)

    acceleration = t.vmath("ADD", force.outputs[0], turbulence, x=0, y=-10)
    velocity = t.vmath(
        "ADD",
        t.attribute("velocity", "FLOAT_VECTOR", 0, -7),
        t.vmath("SCALE", acceleration, dt, x=1, y=-10),
        x=1,
        y=-7,
    )
    damping = t.math("MULTIPLY", inputs["Drag"], dt, x=0, y=-12)
    damping = t.math("SUBTRACT", 1.0, damping, x=1, y=-12)
    damping = t.math("MAXIMUM", damping, 0.0, x=2, y=-12)
    velocity = t.vmath("SCALE", velocity, damping, x=2, y=-7)
    particles = t.store(join.outputs[0], "velocity", "FLOAT_VECTOR", velocity, 3, 0)

    offset = t.vmath("SCALE", t.attribute("velocity", "FLOAT_VECTOR", 3, -3), dt, x=4, y=-3)
    move = t.node("GeometryNodeSetPosition", 4, 0, {"Geometry": particles, "Offset": offset})
    age = t.math("ADD", t.attribute("age", "FLOAT", 4, -5), dt, x=5, y=-5)
    particles = t.store(move.outputs[0], "age", "FLOAT", age, 5, 0)

    expired = t.math(
        "GREATER_THAN",
        t.attribute("age", "FLOAT", 5, -6),
        t.attribute("lifetime", "FLOAT", 5, -7),
        x=6,
        y=-6,
    )
    alive = t.node(
        "GeometryNodeDeleteGeometry",
        6,
        0,
        {"Geometry": particles, "Selection": expired},
        domain="POINT",
    )
    t.connect(alive.outputs[0], sim_out.inputs["Geometry"])
    t.connect(location, sim_out.inputs["Previous"])

    # Shrink the particles with age, and store the age for the material
    age = t.math(
        "DIVIDE",
        t.attribute("age", "FLOAT", 12, -3),
        t.attribute("lifetime", "FLOAT", 12, -4),
        x=12.5,
        y=-3,
    )
    progress = t.node("ShaderNodeClamp", 13, -3, {"Value": age}).outputs[0]
    flames = t.store(sim_out.outputs["Geometry"], "fireball_age", "FLOAT", progress, 14, 0)
    radius = t.math(
        "MULTIPLY",
        t.attribute("size", "FLOAT", 14, -3),
        t.math("SUBTRACT", 1.0, progress, x=14, y=-4),
        x=15,
        y=-3,
    )
    flames = t.node(
        "GeometryNodeSetPointRadius", 15, 0, {"Points": flames, "Radius": radius}
    ).outputs[0]

    output = t.node("GeometryNodeJoinGeometry", 16, 0)
    t.connect(flames, output.inputs[0])
    t.connect(core, output.inputs[0])
    output = t.store(output.outputs[0], "fireball_color", "FLOAT_COLOR", inputs["Color"], 17, 0)
    output = t.store(output, "fireball_brightness", "FLOAT", inputs["Brightness"], 17.5, 0)
    output = t.node(
        "GeometryNodeSetMaterial", 18, 0, {"Geometry": output, "Material": inputs["Material"]}
    )
    t.node("NodeGroupOutput", 20, 0, {0: output.outputs[0]})
    return ng


def build_material():
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree)

    age = t.node("ShaderNodeAttribute", -6, 1, attribute_name="fireball_age").outputs["Fac"]
    color = t.node("ShaderNodeAttribute", -6, -1, attribute_name="fireball_color")

    # Hotter in the middle of the core and of each particle
    rim = t.node("ShaderNodeLayerWeight", -6, 3, {"Blend": 0.3})
    heat = t.node(
        "ShaderNodeMath",
        -4,
        2,
        {0: rim.outputs["Facing"], 1: 0.35, 2: age},
        operation="MULTIPLY_ADD",
    ).outputs[0]

    # White hot, then the flame color, then dark smoke
    to_flame = t.node("ShaderNodeMapRange", -3, 3, {"Value": heat, "From Max": 0.35}, clamp=True)
    hot = t.node(
        "ShaderNodeMix",
        -2,
        2,
        {"Factor": to_flame.outputs[0], "A": (1.0, 0.8, 0.45, 1.0), "B": color.outputs["Color"]},
        data_type="RGBA",
    )
    to_smoke = t.node("ShaderNodeMapRange", -1, 3, {"Value": heat, "From Min": 0.35}, clamp=True)
    smoke = t.node(
        "ShaderNodeMix",
        0,
        2,
        {"Factor": to_smoke.outputs[0], "A": hot.outputs[2], "B": (0.02, 0.01, 0.005, 1.0)},
        data_type="RGBA",
    )

    strength = t.node(
        "ShaderNodeMapRange",
        0,
        0,
        {"Value": heat, "To Min": 20.0, "To Max": 0.0},
        clamp=True,
    )
    brightness = t.node("ShaderNodeAttribute", 0, -2, attribute_name="fireball_brightness")
    strength = t.node(
        "ShaderNodeMath",
        1,
        0,
        {0: strength.outputs[0], 1: brightness.outputs["Fac"]},
        operation="MULTIPLY",
    )
    emission = t.node(
        "ShaderNodeEmission",
        2,
        1,
        {"Color": smoke.outputs[2], "Strength": strength.outputs[0]},
    )
    t.node("ShaderNodeOutputMaterial", 4, 0, {"Surface": emission.outputs[0]})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material()))
