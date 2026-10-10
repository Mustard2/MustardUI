# Build disintegration.blend: the Disintegration node group and the particles material
# Usage: Blender --background --factory-startup --python disintegration_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "disintegration.blend"
NODE_GROUP = "MustardUI Disintegration"
MATERIAL = "MustardUI Disintegration Particles"


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.description = "Disintegrate the mesh inside the Control sphere into particles"

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng, "Control", "NodeSocketObject", description="Empty whose sphere disintegrates the mesh"
    )

    panel = ng.interface.new_panel("Edge")
    add_input(
        ng,
        "Edge Width",
        "NodeSocketFloat",
        panel,
        default_value=0.03,
        min_value=0.0,
        max_value=10.0,
        subtype="DISTANCE",
        description="Width of the edge emitting particles, stored in the disintegration_edge attribute",  # noqa: E501
    )
    add_input(
        ng,
        "Edge Noise",
        "NodeSocketFloat",
        panel,
        default_value=0.15,
        min_value=0.0,
        max_value=1.0,
        subtype="FACTOR",
        description="Irregularity of the edge, relative to the sphere radius",
    )
    add_input(
        ng,
        "Noise Scale",
        "NodeSocketFloat",
        panel,
        default_value=2.0,
        min_value=0.0,
        max_value=100.0,
        description="Scale of the edge irregularity",
    )

    panel = ng.interface.new_panel("Particles")
    add_input(ng, "Material", "NodeSocketMaterial", panel, description="Material of the particles")
    add_input(
        ng,
        "Density",
        "NodeSocketFloat",
        panel,
        default_value=10000.0,
        min_value=0.0,
        max_value=1e6,
        description="Particles emitted each frame per square meter of edge",
    )
    add_input(
        ng,
        "Size",
        "NodeSocketFloat",
        panel,
        default_value=0.001,
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
        default_value=2.0,
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
        default_value=0.15,
        min_value=0.0,
        max_value=100.0,
        description="Initial speed of the particles, away from the surface",
    )
    add_input(
        ng,
        "Force",
        "NodeSocketVector",
        panel,
        default_value=(0.0, 0.0, 0.1),
        subtype="ACCELERATION",
        description="Acceleration of the particles, in world space",
    )
    add_input(
        ng,
        "Turbulence",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
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
    inputs = t.node("NodeGroupInput", -12, 0).outputs
    time = t.node("GeometryNodeInputSceneTime", -3, -2).outputs

    # Cutter: an irregular sphere following the Control
    ico = t.node("GeometryNodeMeshIcoSphere", -10, 3, {"Subdivisions": 4})
    noise = t.node(
        "ShaderNodeTexNoise", -10, 5, {"Scale": inputs["Noise Scale"]}, noise_dimensions="3D"
    )
    bump = t.math("SUBTRACT", noise.outputs["Fac"], 0.5, x=-9, y=5)
    bump = t.math("MULTIPLY", bump, inputs["Edge Noise"], x=-8, y=5)
    bump = t.math("MULTIPLY", bump, 2.0, x=-7, y=5)
    position = t.node("GeometryNodeInputPosition", -7, 6).outputs[0]
    irregular = t.node(
        "GeometryNodeSetPosition",
        -6,
        3,
        {"Geometry": ico.outputs["Mesh"], "Offset": t.vmath("SCALE", position, bump, x=-6, y=5)},
    )
    info = t.node(
        "GeometryNodeObjectInfo",
        -10,
        1,
        {"Object": inputs["Control"]},
        transform_space="RELATIVE",
    )
    cutter = t.node(
        "GeometryNodeTransform",
        -5,
        3,
        {
            "Geometry": irregular.outputs["Geometry"],
            "Translation": info.outputs["Location"],
            "Rotation": info.outputs["Rotation"],
            "Scale": info.outputs["Scale"],
        },
    ).outputs["Geometry"]

    # The boolean keeps parts of the cutter on open meshes: tag the faces of the mesh to keep them
    tagged = t.store(
        inputs["Geometry"], ".disintegration_source", "BOOLEAN", True, -4, 0, domain="FACE"
    )
    boolean = t.node(
        "GeometryNodeMeshBoolean",
        -3,
        1,
        {"Mesh 1": tagged, "Mesh 2": cutter},
        operation="DIFFERENCE",
        solver="FLOAT",
    )
    source = t.attribute(".disintegration_source", "BOOLEAN", -3, -0.5)
    cutter_faces = t.node(
        "GeometryNodeDeleteGeometry",
        -2,
        0,
        {
            "Geometry": boolean.outputs["Mesh"],
            "Selection": t.math("SUBTRACT", 1.0, source, x=-2.5, y=-0.5),
        },
        domain="FACE",
    )
    untag = t.node(
        "GeometryNodeRemoveAttribute",
        -1,
        0,
        {"Geometry": cutter_faces.outputs[0], "Name": ".disintegration_source"},
    )
    cut = untag.outputs[0]

    # Edge: distance from the cutter
    proximity = t.node("GeometryNodeProximity", -3, 3, {0: cutter}, target_element="FACES")
    distance = proximity.outputs["Distance"]
    edge = t.node(
        "ShaderNodeMapRange",
        -2,
        3,
        {0: distance, 2: inputs["Edge Width"], 3: 1.0, 4: 0.0},
    )
    with_edge = t.store(cut, "disintegration_edge", "FLOAT", edge.outputs[0], 0, 1)

    # Emission from the edge, with per-particle random size, lifetime and speed
    distribute = t.node(
        "GeometryNodeDistributePointsOnFaces",
        -1,
        -1,
        {
            "Mesh": cut,
            "Selection": t.math("LESS_THAN", distance, inputs["Edge Width"], x=-2, y=-1),
            "Density": inputs["Density"],
            "Seed": time["Frame"],
        },
        distribute_method="RANDOM",
    )
    random = t.node(
        "FunctionNodeRandomValue", -1, -3, {"Seed": time["Frame"]}, data_type="FLOAT_VECTOR"
    )
    spread = t.vmath("SCALE", random.outputs[0], inputs["Randomness"], x=0, y=-3)
    variation = t.node(
        "ShaderNodeSeparateXYZ", 2, -3, {0: t.vmath("SUBTRACT", (1.0, 1.0, 1.0), spread, x=1, y=-3)}
    ).outputs
    speed = t.math("MULTIPLY", inputs["Speed"], variation[0], x=3, y=-4)
    emitted = distribute.outputs["Points"]
    for i, (name, data_type, value) in enumerate(
        (
            (
                "velocity",
                "FLOAT_VECTOR",
                t.vmath("SCALE", distribute.outputs["Normal"], speed, x=4, y=-3),
            ),
            ("size", "FLOAT", t.math("MULTIPLY", inputs["Size"], variation[1], x=3, y=-5)),
            ("lifetime", "FLOAT", t.math("MULTIPLY", inputs["Lifetime"], variation[2], x=3, y=-6)),
        )
    ):
        emitted = t.store(emitted, name, data_type, value, 5 + i, -1)

    # Simulation: move, age and remove the particles
    sim_in = t.node("GeometryNodeSimulationInput", 7, -6)
    sim_out = t.node("GeometryNodeSimulationOutput", 12, -6)
    sim_in.pair_with_output(sim_out)
    dt = sim_in.outputs["Delta Time"]
    join = t.node("GeometryNodeJoinGeometry", 8, -6)
    t.connect(emitted, join.inputs[0])
    t.connect(sim_in.outputs["Geometry"], join.inputs[0])

    # Force from world to object space
    self_object = t.node("GeometryNodeSelfObject", 3, -9).outputs[0]
    self_info = t.node(
        "GeometryNodeObjectInfo", 4, -9, {"Object": self_object}, transform_space="ORIGINAL"
    )
    invert = t.node("FunctionNodeInvertMatrix", 5, -9, {0: self_info.outputs["Transform"]})
    force = t.node(
        "FunctionNodeTransformDirection",
        6,
        -9,
        {"Transform": invert.outputs[0], "Direction": inputs["Force"]},
    )

    turbulence = t.node(
        "ShaderNodeTexNoise",
        4,
        -11,
        {"W": time["Seconds"], "Scale": inputs["Turbulence Scale"]},
        noise_dimensions="4D",
    )
    turbulence = t.vmath("SUBTRACT", turbulence.outputs["Color"], (0.5, 0.5, 0.5), x=5, y=-11)
    strength = t.math("MULTIPLY", inputs["Turbulence"], 2.0, x=5, y=-12)
    turbulence = t.vmath("SCALE", turbulence, strength, x=6, y=-11)

    acceleration = t.vmath("ADD", force.outputs[0], turbulence, x=7, y=-10)
    velocity = t.vmath(
        "ADD",
        t.attribute("velocity", "FLOAT_VECTOR", 7, -8),
        t.vmath("SCALE", acceleration, dt, x=8, y=-10),
        x=8,
        y=-8,
    )
    damping = t.math("MULTIPLY", inputs["Drag"], dt, x=7, y=-12)
    damping = t.math("SUBTRACT", 1.0, damping, x=8, y=-12)
    damping = t.math("MAXIMUM", damping, 0.0, x=9, y=-12)
    velocity = t.vmath("SCALE", velocity, damping, x=9, y=-8)
    particles = t.store(join.outputs[0], "velocity", "FLOAT_VECTOR", velocity, 9, -6)

    offset = t.vmath("SCALE", t.attribute("velocity", "FLOAT_VECTOR", 9, -9), dt, x=10, y=-9)
    move = t.node("GeometryNodeSetPosition", 10, -6, {"Geometry": particles, "Offset": offset})
    age = t.math("ADD", t.attribute("age", "FLOAT", 10, -10), dt, x=11, y=-10)
    particles = t.store(move.outputs[0], "age", "FLOAT", age, 11, -6)

    expired = t.math(
        "GREATER_THAN",
        t.attribute("age", "FLOAT", 10, -12),
        t.attribute("lifetime", "FLOAT", 10, -13),
        x=11,
        y=-12,
    )
    alive = t.node(
        "GeometryNodeDeleteGeometry",
        11.5,
        -7,
        {"Geometry": particles, "Selection": expired},
        domain="POINT",
    )
    t.connect(alive.outputs[0], sim_out.inputs["Geometry"])

    # Shrink the particles with age, and store the age for the material
    age = t.math(
        "DIVIDE",
        t.attribute("age", "FLOAT", 11, -11),
        t.attribute("lifetime", "FLOAT", 11, -12),
        x=12,
        y=-10,
    )
    progress = t.node("ShaderNodeClamp", 12, -9, {"Value": age}).outputs[0]
    particles = t.store(
        sim_out.outputs["Geometry"], "disintegration_age", "FLOAT", progress, 13, -6
    )
    radius = t.math(
        "MULTIPLY",
        t.attribute("size", "FLOAT", 13, -9),
        t.math("SUBTRACT", 1.0, progress, x=13, y=-10),
        x=14,
        y=-9,
    )
    particles = t.node(
        "GeometryNodeSetPointRadius", 14, -6, {"Points": particles, "Radius": radius}
    ).outputs[0]
    particles = t.node(
        "GeometryNodeSetMaterial",
        15,
        -6,
        {"Geometry": particles, "Material": inputs["Material"]},
    ).outputs[0]

    output = t.node("GeometryNodeJoinGeometry", 16, 0)
    t.connect(particles, output.inputs[0])
    t.connect(with_edge, output.inputs[0])
    t.node("NodeGroupOutput", 17, 0, {0: output.outputs[0]})
    return ng


def build_material():
    material = bpy.data.materials.new(MATERIAL)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree, spacing=(1, 1))

    age = t.node("ShaderNodeAttribute", -600, 0, attribute_name="disintegration_age")
    ramp = t.node("ShaderNodeValToRGB", -350, 100, {"Fac": age.outputs["Fac"]})
    elements = ramp.color_ramp.elements
    elements[0].color = (1.0, 0.8, 0.45, 1.0)
    elements[1].position = 0.35
    elements[1].color = (1.0, 0.25, 0.02, 1.0)
    elements.new(1.0).color = (0.02, 0.01, 0.005, 1.0)
    strength = t.node("ShaderNodeMapRange", -350, -150, {0: age.outputs["Fac"], 3: 20.0, 4: 0.0})
    emission = t.node(
        "ShaderNodeEmission",
        -50,
        0,
        {"Color": ramp.outputs["Color"], "Strength": strength.outputs[0]},
    )
    t.node("ShaderNodeOutputMaterial", 200, 0, {"Surface": emission.outputs[0]})
    return material


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_material()))
