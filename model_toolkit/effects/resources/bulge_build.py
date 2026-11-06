# Build bulge.blend: the Bulge node group
# Usage: Blender --background --factory-startup --python bulge_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "bulge.blend"
NODE_GROUP = "MustardUI Bulge"


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Bulge the mesh along its normals over the parts of the Colliders inside it, e.g. an "
        "object pushed under the skin, jiggling as they move"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects bulging the mesh where they are inside it",
    )
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        default_value=0.5,
        min_value=0.0,
        max_value=10.0,
        description="Height of the bulge right over the Colliders, as a fraction of the Width",
    )
    add_input(
        ng,
        "Width",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.1,
        min_value=0.0001,
        max_value=10.0,
        description="Distance from the Colliders the bulge spreads to",
    )
    add_input(
        ng,
        "Softness",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Rounded bulge, from a sharp outline of the Colliders to a smooth bump",
    )
    add_input(
        ng,
        "Reverse",
        "NodeSocketBool",
        default_value=False,
        description="Sink the mesh instead, e.g. sucked in",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the bulge, e.g. to the soft parts",
    )
    add_input(
        ng,
        "Entry Fade",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.02,
        min_value=0.0001,
        max_value=1.0,
        description="Depth the Colliders enter the mesh by before bulging it fully, not to pop",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        default_value=2,
        min_value=0,
        max_value=100,
        description="Iterations smoothing the bulge over the mesh",
    )
    add_input(
        ng,
        "Smooth Normals",
        "NodeSocketInt",
        default_value=20,
        min_value=0,
        max_value=200,
        description="Iterations smoothing the directions the mesh bulges in, not to fold small "
        "hollows over, e.g. the navel",
    )
    add_input(
        ng,
        "Jiggle",
        "NodeSocketBool",
        default_value=True,
        description="Bulge springing after the Colliders, simulated from the Start Frame",
    )
    add_input(
        ng,
        "Frequency",
        "NodeSocketFloat",
        default_value=3.0,
        min_value=0.1,
        max_value=30.0,
        description="Wobbles per second of the jiggle, higher for a stiffer bulge",
    )
    add_input(
        ng,
        "Damping",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="How fast the jiggle settles, from wobbling long to not overshooting",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    arrange_interface(
        ng,
        [
            (None, "Jiggle", False, "Jiggle", ["Frequency", "Damping", "Start Frame"]),
            (None, "Advanced", True, None, ["Entry Fade", "Smooth", "Smooth Normals"]),
        ],
    )

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -8, 0).outputs
    geometry = inputs["Geometry"]
    height, cover = build_height(t, inputs, geometry)

    t.section("Shape", row=True)
    sign = t.node(
        "GeometryNodeSwitch",
        0,
        -3,
        {"Switch": inputs["Reverse"], "False": 1.0, "True": -1.0},
        input_type="FLOAT",
    ).outputs[0]
    height = t.math("MULTIPLY", height, inputs["Strength"], x=0, y=-2)
    height = t.math("MULTIPLY", height, inputs["Width"], x=1, y=-2)
    height = t.math("MULTIPLY", height, inputs["Mask"], x=2, y=-2)
    height = t.math("MULTIPLY", height, sign, x=3, y=-2)
    # Covering the Colliders poking out of the mesh, smoothed with the bulge, not when sinking it
    cover = t.math("MULTIPLY", cover, inputs["Mask"], x=2, y=-4)
    cover = t.node(
        "GeometryNodeSwitch",
        3,
        -4,
        {"Switch": inputs["Reverse"], "False": cover, "True": 0.0},
        input_type="FLOAT",
    ).outputs[0]
    height = t.math("ADD", height, cover, x=3.5, y=-2)
    height = t.node(
        "GeometryNodeBlurAttribute",
        4,
        -2,
        {"Value": height, "Iterations": inputs["Smooth"]},
        data_type="FLOAT",
    ).outputs["Value"]
    captured = t.node("GeometryNodeCaptureAttribute", 5, 0, {"Geometry": geometry})
    captured.capture_items.new("FLOAT", "Height")
    t.connect(height, captured.inputs["Height"])
    height = build_jiggle(t, inputs, captured.outputs["Geometry"], captured.outputs["Height"])

    t.section("Bulge", row=True)
    # At least covering them after smoothing
    height = t.node(
        "GeometryNodeSwitch",
        2,
        -1,
        {
            "Switch": inputs["Reverse"],
            "False": t.math("MAXIMUM", height, cover, x=1, y=-1),
            "True": height,
        },
        input_type="FLOAT",
    ).outputs[0]
    # Smoothed for the vertices in hollows to move together, not across each other
    normal = t.node(
        "GeometryNodeBlurAttribute",
        1,
        -3,
        {
            "Value": t.node("GeometryNodeInputNormal", 0, -3).outputs[0],
            "Iterations": inputs["Smooth Normals"],
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    normal = t.vmath("NORMALIZE", normal, x=2, y=-3)
    offset = t.vmath("SCALE", normal, height, x=3, y=-2)
    bulge = t.node(
        "GeometryNodeSetPosition",
        4,
        0,
        {"Geometry": captured.outputs["Geometry"], "Offset": offset},
    )
    t.node("NodeGroupOutput", 5, 0, {0: bulge.outputs["Geometry"]})
    t.arrange()
    return ng


def build_height(t, inputs, geometry):
    """Bulge of the vertices by the parts of the Colliders inside the mesh, 1 right over them,
    and how far the vertices inside the Colliders move out to cover them"""
    t.section("Colliders", row=True)
    colliders = t.node(
        "GeometryNodeCollectionInfo",
        0,
        -2,
        {"Collection": inputs["Colliders"], "Separate Children": True},
        transform_space="RELATIVE",
    ).outputs[0]
    # Which Collider each point is of
    instance = t.node(
        "GeometryNodeCaptureAttribute", 1, -2, {"Geometry": colliders}, domain="INSTANCE"
    )
    instance.capture_items.new("INT", "Object")
    t.connect(t.node("GeometryNodeInputIndex", 0, -3).outputs[0], instance.inputs["Object"])
    colliders = t.node(
        "GeometryNodeRealizeInstances", 1.5, -2, {0: instance.outputs["Geometry"]}
    ).outputs[0]
    position = t.node("GeometryNodeInputPosition", 1, -3).outputs[0]
    normal = t.node("GeometryNodeInputNormal", 1, -4).outputs[0]
    # Nearest point of the Colliders, and how far they are
    nearest = t.node(
        "GeometryNodeProximity",
        2,
        -2,
        {"Geometry": colliders, "Sample Position": position},
        target_element="FACES",
    )

    t.section("Inside")

    def depth(point, y):
        """How deep the point is inside the mesh, along the normal of its nearest surface"""
        surface = t.node(
            "GeometryNodeProximity",
            0,
            y,
            {"Geometry": geometry, "Sample Position": point},
            target_element="FACES",
        ).outputs["Position"]
        surface_normal = t.node(
            "GeometryNodeSampleNearestSurface",
            0,
            y - 1,
            {"Mesh": geometry, "Value": normal, "Sample Position": point},
            data_type="FLOAT_VECTOR",
        ).outputs["Value"]
        return t.vmath(
            "DOT_PRODUCT",
            t.vmath("SUBTRACT", surface, point, x=1, y=y),
            surface_normal,
            x=2,
            y=y,
        )

    # Fading the Colliders crossing the mesh by how deep they entered it where nearest, not the
    # ones inside it, e.g. pushed close to the surface
    entry = t.node(
        "ShaderNodeMapRange",
        3,
        -2,
        {
            "Value": depth(nearest.outputs["Position"], -2),
            "From Min": 0.0,
            "From Max": inputs["Entry Fade"],
        },
        interpolation_type="SMOOTHSTEP",
        label="Entry",
    ).outputs[0]
    deepest_out = t.node(
        "GeometryNodeFieldMinAndMax",
        3,
        -5,
        {
            "Value": depth(t.node("GeometryNodeInputPosition", 0, -6).outputs[0], -5),
            "Group ID": instance.outputs["Object"],
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs["Min"]
    reach = t.math("MULTIPLY", inputs["Strength"], inputs["Width"], x=3, y=-7)
    # Also the ones poking out by less than the bulge height, which then covers them
    contained = t.math(
        "GREATER_THAN",
        t.math("ADD", deepest_out, reach, x=4, y=-6),
        -1e-4,
        x=4,
        y=-5,
    )
    contained = t.node(
        "GeometryNodeSampleNearestSurface",
        5,
        -5,
        {"Mesh": colliders, "Value": contained, "Sample Position": position},
        data_type="FLOAT",
    ).outputs["Value"]
    entry = t.math("MAXIMUM", entry, contained, x=6, y=-2)
    # None without Colliders
    entry = t.math("MULTIPLY", entry, nearest.outputs["Is Valid"], x=4, y=-2)

    t.section("Cover")
    # The vertices inside the Colliders poking out of the mesh by less than the bulge height,
    # covering them, not the ones out of it by more, e.g. a stub left out of the mesh
    over = t.node(
        "GeometryNodeRaycast",
        1,
        -5,
        {
            "Target Geometry": colliders,
            "Source Position": position,
            "Ray Direction": normal,
            "Ray Length": reach,
        },
    ).outputs
    leaving = t.math(
        "GREATER_THAN",
        t.vmath("DOT_PRODUCT", over["Hit Normal"], normal, x=2, y=-6),
        0.0,
        x=3,
        y=-6,
    )
    inside = t.math("MULTIPLY", over["Is Hit"], leaving, x=4, y=-5)

    t.section("Profile")

    def profile(distance, x, y):
        """1 at the Colliders, 0 at the Width, rounded by the Softness"""
        near = t.node(
            "ShaderNodeMapRange",
            x,
            y,
            {"Value": distance, "From Min": inputs["Width"], "From Max": 0.0},
            label="Near",
        ).outputs[0]
        rounded = t.node(
            "ShaderNodeMapRange",
            x + 1,
            y - 1,
            {"Value": near},
            interpolation_type="SMOOTHERSTEP",
            label="Rounded",
        ).outputs[0]
        return t.node(
            "ShaderNodeMix",
            x + 2,
            y,
            {"Factor": inputs["Softness"], "A": near, "B": rounded},
            data_type="FLOAT",
        ).outputs[0]

    lateral = t.math("MULTIPLY", profile(nearest.outputs["Distance"], 0, -2), entry, x=3, y=-2)
    height = t.math("MAXIMUM", lateral, inside, x=5, y=-2)
    cover = t.math("MULTIPLY", over["Hit Distance"], inside, x=5, y=-5)
    return height, cover


def build_jiggle(t, inputs, geometry, target):
    """Height of the vertices springing after the target height since the Start Frame, as a
    damped spring stepped implicitly not to blow up at any frame rate, the target without Jiggle"""
    t.section("Jiggle", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 12, 0)
    sim_in.pair_with_output(sim_out)
    state = t.node(
        "GeometryNodeSwitch",
        3,
        0,
        {"Switch": started, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    count = t.node("GeometryNodeAttributeDomainSize", 3, -2, {"Geometry": geometry}).outputs[
        "Point Count"
    ]
    kept = t.node(
        "GeometryNodeAttributeDomainSize",
        3,
        -3,
        {"Geometry": state},
        component="POINTCLOUD",
    ).outputs["Point Count"]
    # A point for each vertex, from the vertices again when they change
    same = t.node(
        "FunctionNodeCompare",
        4,
        -3,
        {"A": count, "B": kept},
        data_type="INT",
        operation="EQUAL",
    ).outputs[0]
    # None without Jiggle, not to simulate them
    points = t.node(
        "GeometryNodePoints",
        4,
        0,
        {"Count": t.math("MULTIPLY", count, inputs["Jiggle"], x=3.5, y=-1)},
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 4, -5).outputs[0]

    def sample(source, value, x, y):
        return t.node(
            "GeometryNodeSampleIndex",
            x,
            y,
            {"Geometry": source, "Value": value, "Index": index},
            data_type="FLOAT",
        ).outputs[0]

    goal = sample(geometry, target, 5, -4)

    def previous(name, fallback, y):
        return t.node(
            "GeometryNodeSwitch",
            6,
            y,
            {
                "Switch": same,
                "False": fallback,
                "True": sample(state, t.attribute(name, "FLOAT", 4.5, y - 1), 5.5, y),
            },
            input_type="FLOAT",
        ).outputs[0]

    height = previous(".bulge_height", goal, -6)
    speed = previous(".bulge_speed", 0.0, -8)
    dt = sim_in.outputs["Delta Time"]
    omega = t.math("MULTIPLY", inputs["Frequency"], 6.283185307, x=6, y=-10)
    stiffness = t.math("MULTIPLY", omega, omega, x=7, y=-10)
    damping = t.math(
        "MULTIPLY", t.math("MULTIPLY", inputs["Damping"], 2.0, x=6, y=-11), omega, x=7, y=-11
    )
    # v' = (v + dt k (goal - h)) / (1 + dt c + dt^2 k), h' = h + dt v'
    pull = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", dt, stiffness, x=8, y=-10),
        t.math("SUBTRACT", goal, height, x=7, y=-6),
        x=8,
        y=-6,
    )
    resist = t.math(
        "ADD",
        t.math("ADD", 1.0, t.math("MULTIPLY", dt, damping, x=8, y=-11), x=9, y=-11),
        t.math("MULTIPLY", t.math("MULTIPLY", dt, dt, x=8, y=-12), stiffness, x=9, y=-12),
        x=10,
        y=-11,
    )
    speed = t.math("DIVIDE", t.math("ADD", speed, pull, x=9, y=-8), resist, x=10, y=-8)
    height = t.math("ADD", height, t.math("MULTIPLY", speed, dt, x=10, y=-7), x=11, y=-6)
    stepped = t.store(points, ".bulge_height", "FLOAT", height, 11, 0)
    stepped = t.store(stepped, ".bulge_speed", "FLOAT", speed, 11.5, 0)
    t.connect(stepped, sim_out.inputs["Geometry"])

    # The simulated height of each vertex, while it has one
    result = sim_out.outputs["Geometry"]
    simulated = t.node(
        "GeometryNodeAttributeDomainSize",
        13,
        -3,
        {"Geometry": result},
        component="POINTCLOUD",
    ).outputs["Point Count"]
    jiggling = t.math(
        "MULTIPLY",
        t.node(
            "FunctionNodeCompare",
            14,
            -3,
            {"A": count, "B": simulated},
            data_type="INT",
            operation="EQUAL",
        ).outputs[0],
        t.math("MULTIPLY", inputs["Jiggle"], started, x=14, y=-4),
        x=15,
        y=-3,
    )
    return t.node(
        "GeometryNodeSwitch",
        16,
        -2,
        {
            "Switch": jiggling,
            "False": target,
            "True": sample(result, t.attribute(".bulge_height", "FLOAT", 14, -6), 15, -6),
        },
        input_type="FLOAT",
    ).outputs[0]


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(),), fake_user=True)
