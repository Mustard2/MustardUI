# Build cloth_rip.blend: the Cloth Rip node group, on the Cloth Dynamics of Blender 5.2
# Usage: Blender --background --factory-startup --python cloth_rip_build.py [-- out.blend]
# With CLOTH_RIP_DEBUG set, the simulation attributes are kept in the output, to inspect them
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, socket, write

RESOURCE = "cloth_rip.blend"
NODE_GROUP = "MustardUI Cloth Rip"
# Prefix of the Cloth Dynamics node groups bundled with Blender, copied in the resource not to
# depend on the asset library, hidden
PREFIX = f".{NODE_GROUP} - "
CLOTH_DYNAMICS = "Cloth Dynamics (Experimental)"
ASSETS = os.path.join("assets", "nodes", "geometry_nodes_dynamics_assets.blend")
# Attributes of the simulation, kept between its frames
ATTRIBUTES = (
    "rip_pin",
    "rip_hold",
    "rip_near",
    "rip_anchor",
    "rip_held",
    "rip_state",
    "rip_grip",
    "rip_start",
    "rip_axis",
    "rip_tear",
    "rip_target",
    "rip_cut",
    "rip_boundary",
    "rip_noise",
)
# Distance of the cloth from the Colliders and the floor
COLLISION = 0.002
# Exponent averaging the stretch of the edges of a face into about their maximum
MAX_POWER = 64.0
# Edges shorter than this fraction of the mean edge stretch relative to it, not to their length
TINY_EDGE = 0.5
# Softness of the pin to the mesh at Shape 0, the compliance being its fifth power
SHAPE_SOFTNESS = 0.3


def load_cloth_dynamics():
    """The Cloth Dynamics node groups of Blender, copied with the prefix"""
    path = os.path.join(bpy.utils.system_resource("DATAFILES"), ASSETS)
    before = set(bpy.data.node_groups)
    with bpy.data.libraries.load(path) as (_, target):
        target.node_groups = [CLOTH_DYNAMICS, "Collider"]
    for group in [g for g in bpy.data.node_groups if g.library]:
        group.make_local()
    groups = [g for g in bpy.data.node_groups if g not in before]
    for group in groups:
        group.name = PREFIX + group.name
        group.asset_clear()
        group.use_fake_user = False
    for library in list(bpy.data.libraries):
        bpy.data.libraries.remove(library)
    return groups


def build_node_group():
    groups = load_cloth_dynamics()
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Rip the cloth grabbed by the Pulls, simulated as a whole from the Start Frame, tearing "
        "along ragged lines near them as they pull, the torn pieces held or let go"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Pulls",
        "NodeSocketCollection",
        description="Collection of the Empties grabbing the cloth around their spheres from the "
        "Start Frame, pulling it as they move until it rips. A sphere scaled to 0 lets go",
    )
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Collection of the meshes the cloth collides with, e.g. the body",
    )
    add_input(
        ng,
        "Start Frame",
        "NodeSocketInt",
        default_value=1,
        description="Frame the Pulls start grabbing the cloth",
    )
    add_input(
        ng,
        "Anchor",
        "NodeSocketFloat",
        hide_value=True,
        description="Vertex Group of the cloth pinned to the mesh, e.g. a collar, the rest "
        "simulated from the Start Frame, held on the mesh by the Shape",
    )
    add_input(
        ng,
        "Shape",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.0,
        min_value=0.0,
        max_value=1.0,
        description="Hold of the cloth on the shape of the mesh, for an outfit without an Anchor "
        "not to sag or slide off, none near the Pulls and the tears and on the torn out pieces",
    )
    add_input(
        ng,
        "Hang",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.1,
        min_value=0.0,
        max_value=10.0,
        description="Distance from the tears the cloth hangs free within, not held on the shape "
        "of the mesh, less and less farther",
    )

    panel = ng.interface.new_panel("Tear")
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        panel,
        default_value=1.4,
        min_value=1.0,
        max_value=10.0,
        description="Stretch of the cloth tearing it near a grab, along the lines between its "
        "patches, over the stretch of the cloth around",
    )
    add_input(
        ng,
        "Propagation",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="How much less stretch a tear needs to run on from its ends. At 0 as much "
        "as to start, at 1 any",
    )
    add_input(
        ng,
        "Tear Speed",
        "NodeSocketInt",
        panel,
        default_value=3,
        min_value=1,
        max_value=20,
        description="Edges a tear can run on from each of its ends per frame",
    )
    add_input(
        ng,
        "Tear Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.12,
        min_value=0.0,
        max_value=10.0,
        description="Distance from a Pull the cloth tears within, following it as it moves",
    )
    add_input(
        ng,
        "Piece Size",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.06,
        min_value=0.001,
        max_value=10.0,
        description="Size of the patches of the cloth, torn along the lines between them",
    )
    add_input(
        ng,
        "Randomness",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.6,
        min_value=0.0,
        max_value=1.0,
        description="Irregularity of the patch sizes",
    )
    add_input(
        ng,
        "Edge Noise",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.5,
        min_value=0.0,
        max_value=1.0,
        description="Raggedness of the tear lines, and variation of the Strength along them",
    )
    add_input(
        ng,
        "Fray",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.3,
        min_value=0.0,
        max_value=1.0,
        description="Share of the faces along the tears coming off as crumbs, fraying the edges",
    )
    add_input(
        ng,
        "Snap",
        "NodeSocketFloat",
        panel,
        default_value=4.0,
        min_value=1.0,
        max_value=100.0,
        description="Stretch of the free cloth snapping it, where it is pulled thin",
    )
    add_input(
        ng,
        "Pull Before Tear",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.02,
        min_value=0.0,
        max_value=10.0,
        description="Distance a Pull moves from where it grabbed before the cloth can tear",
    )

    panel = ng.interface.new_panel("Grip")
    add_input(
        ng,
        "Grab",
        "NodeSocketFloat",
        panel,
        default_value=2.0,
        min_value=1.0,
        max_value=10.0,
        description="How far out of its sphere a Pull grabs the cloth, in radii of the sphere, "
        "the cloth around it held in hand, and the cloth it runs into gathered as it drags along",
    )
    add_input(
        ng,
        "Grip",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.1,
        min_value=0.0,
        max_value=1.0,
        description="Softness of the grip of the Pulls on the cloth, a little for the Colliders "
        "to win over it",
    )
    add_input(
        ng,
        "Release",
        "NodeSocketBool",
        panel,
        default_value=False,
        description="Let go of the torn out pieces as soon as they detach from the cloth, "
        "instead of holding them until the Pull is scaled to 0",
    )

    panel = ng.interface.new_panel("Cloth")
    add_input(
        ng,
        "Stretchiness",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.05,
        min_value=0.0,
        max_value=1.0,
        description="Elasticity of the cloth",
    )
    add_input(
        ng,
        "Bendiness",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=0.05,
        min_value=0.0,
        max_value=1.0,
        description="How much the cloth bends, also stretching it in this version of Blender, "
        "sagging if high",
    )
    add_input(
        ng,
        "Damping",
        "NodeSocketFloat",
        panel,
        default_value=1.0,
        min_value=0.0,
        max_value=100.0,
        description="Slowing of the cloth, for stability",
    )
    add_input(
        ng,
        "Friction",
        "NodeSocketFloat",
        panel,
        default_value=0.5,
        min_value=0.0,
        max_value=10.0,
        description="Friction of the cloth on the Colliders and the floor",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.003,
        min_value=0.0,
        max_value=1.0,
        description="Distance the cloth is pushed to from the Colliders and itself, inflating the "
        "outfit if large, letting the body through if small",
    )
    add_input(
        ng,
        "Substeps",
        "NodeSocketInt",
        panel,
        default_value=5,
        min_value=1,
        max_value=100,
        description="Simulation steps per frame",
    )
    add_input(
        ng,
        "Constraint Steps",
        "NodeSocketInt",
        panel,
        default_value=15,
        min_value=1,
        max_value=100,
        description="Solver iterations per substep",
    )

    panel = ng.interface.new_panel("Floor")
    add_input(
        ng,
        "Floor",
        "NodeSocketBool",
        panel,
        default_value=True,
        description="The fallen pieces land on a floor",
    )
    add_input(
        ng,
        "Floor Height",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0,
        min_value=-1000.0,
        max_value=1000.0,
        description="Height of the floor",
    )
    toggle = next(
        x for x in ng.interface.items_tree if x.name == "Floor" and x.item_type == "SOCKET"
    )
    toggle.is_panel_toggle = True

    t = Tree(ng)
    t.section("Inputs", row=True)
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    rest_attribute = t.node(
        "GeometryNodeInputNamedAttribute",
        0,
        -2,
        {"Name": "rest_position"},
        data_type="FLOAT_VECTOR",
    ).outputs
    # The rest position when it exists, e.g. from an Armature, as the cloth does not move
    rest = t.node(
        "GeometryNodeSwitch",
        1,
        -2,
        {
            "Switch": rest_attribute["Exists"],
            "False": t.node("GeometryNodeInputPosition", 0, -3).outputs[0],
            "True": rest_attribute["Attribute"],
        },
        input_type="VECTOR",
    ).outputs[0]
    started = t.math(
        "GREATER_THAN",
        t.node("GeometryNodeInputSceneTime", 0, -4).outputs["Frame"],
        t.math("SUBTRACT", inputs["Start Frame"], 0.5, x=1, y=-5),
        x=2,
        y=-4,
    )
    # The simulation is in world space, the Pulls and the Colliders relative to the mesh
    to_world = t.node(
        "GeometryNodeObjectInfo",
        1,
        -6,
        {"Object": t.node("GeometryNodeSelfObject", 0, -6).outputs[0]},
        transform_space="ORIGINAL",
    ).outputs["Transform"]
    pulls = t.node(
        "GeometryNodeTransform",
        2,
        -7,
        {
            "Geometry": t.node(
                "GeometryNodeCollectionInfo",
                1,
                -7,
                {"Collection": inputs["Pulls"], "Separate Children": True},
                transform_space="RELATIVE",
            ).outputs[0],
            "Mode": "Matrix",
            "Transform": to_world,
        },
    ).outputs[0]
    pull_count = t.node(
        "GeometryNodeAttributeDomainSize", 3, -7, {"Geometry": pulls}, component="INSTANCES"
    ).outputs["Instance Count"]
    cells = t.math("DIVIDE", 1.0, inputs["Piece Size"], x=0, y=-9)
    # The Colliders relative to the mesh, for the stock Collider, and in world space for the
    # Pulls, not grabbing inside them nor pulling the cloth into them
    colliders = t.node(
        "GeometryNodeRealizeInstances",
        1,
        -11,
        {
            "Geometry": t.node(
                "GeometryNodeCollectionInfo",
                0,
                -11,
                {"Collection": inputs["Colliders"]},
                transform_space="RELATIVE",
            ).outputs[0]
        },
    ).outputs[0]
    inside_colliders = t.node(
        "GeometryNodeTransform",
        2,
        -11,
        {"Geometry": colliders, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]

    t.section("Setup", row=True)
    # The cloth pinned to the mesh until grabbed, with its rest position for the patches
    geometry = t.store(inputs["Geometry"], "rip_rest", "FLOAT_VECTOR", rest, 0, 0)
    geometry = t.store(geometry, "rip_pin", "FLOAT", 1.0, 1, 0)
    geometry = t.store(
        geometry,
        "rip_anchor",
        "FLOAT",
        t.math("GREATER_THAN", inputs["Anchor"], 0.5, x=1, y=-2),
        2,
        0,
    )
    geometry = t.store(geometry, "rip_cut", "FLOAT", 0.0, 3, 0, domain="EDGE")
    # The lines between the patches, and the noise of the Strength along them, from the rest
    # position once, the split edges keeping them
    boundary = t.node(
        "GeometryNodeMeshFaceSetBoundaries",
        3,
        -3,
        {"Face Group ID": on_domain(t, patch(t, inputs, rest, cells, 0, -3), "FACE", "INT", 2, -3)},
    ).outputs["Boundary Edges"]
    geometry = t.store(geometry, "rip_boundary", "FLOAT", boundary, 4, 0, domain="EDGE")
    noise = t.math(
        "ADD",
        1.0,
        t.math(
            "MULTIPLY",
            inputs["Edge Noise"],
            t.math(
                "SUBTRACT",
                socket(
                    t.node(
                        "ShaderNodeTexNoise",
                        1,
                        -6,
                        {
                            "Vector": rest,
                            "Scale": t.math("MULTIPLY", cells, 1.5, x=0, y=-6),
                            "Detail": 2.0,
                        },
                    ).outputs,
                    "Fac",
                ),
                0.5,
                x=2,
                y=-6,
            ),
            x=3,
            y=-6,
        ),
        x=4,
        y=-6,
    )
    geometry = t.store(geometry, "rip_noise", "FLOAT", noise, 5, 0, domain="EDGE")

    grab = build_grab(t, inputs, pulls, pull_count, started, inside_colliders)
    tear = build_tear(t, inputs)

    t.section("Effectors", row=True)
    # The held points pinned to their target in the Pull
    state = t.attribute("rip_state", "FLOAT", 0, 0)
    held = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", state, 0.5, x=1, y=0),
        t.math("LESS_THAN", state, 1.5, x=1, y=-1),
        x=2,
        y=0,
    )
    compliance = t.node(
        "GeometryNodeGroup",
        1,
        -2,
        {"Softness": inputs["Grip"]},
        node_tree=bpy.data.node_groups[PREFIX + "Softness to Compliance"],
    ).outputs["Compliance"]
    pull = t.node(
        "GeometryNodeGroup",
        3,
        0,
        {
            "Selection": held,
            "Position": t.attribute("rip_target", "FLOAT_VECTOR", 2, -2),
            "Compliance": compliance,
        },
        node_tree=bpy.data.node_groups[PREFIX + "Pin Positions"],
    ).outputs["Constraint"]
    body = collider(t, inputs, colliders, True, 3, -4)
    ground = t.node(
        "GeometryNodeTransform",
        2,
        -7,
        {
            "Geometry": t.node(
                "GeometryNodeTransform",
                1,
                -7,
                {
                    "Geometry": t.node(
                        "GeometryNodeMeshGrid",
                        0,
                        -7,
                        {"Size X": 1000.0, "Size Y": 1000.0, "Vertices X": 2, "Vertices Y": 2},
                    ).outputs["Mesh"],
                    "Translation": t.node(
                        "ShaderNodeCombineXYZ", 0, -8, {"Z": inputs["Floor Height"]}
                    ).outputs[0],
                },
            ).outputs[0],
            "Mode": "Matrix",
            "Transform": t.node("FunctionNodeInvertMatrix", 1, -9, {0: to_world}).outputs[0],
        },
    ).outputs[0]
    floor = collider(t, inputs, ground, False, 3, -7)
    effectors = t.node(
        "GeometryNodeSwitch",
        6,
        0,
        {
            "Switch": inputs["Floor"],
            "False": bundle(
                t,
                5,
                0,
                (
                    ("Grab", "BUNDLE", grab),
                    ("Tear", "BUNDLE", tear),
                    ("Pull", "BUNDLE", pull),
                    ("Body", "BUNDLE", body),
                ),
            ),
            "True": bundle(
                t,
                5,
                -3,
                (
                    ("Grab", "BUNDLE", grab),
                    ("Tear", "BUNDLE", tear),
                    ("Pull", "BUNDLE", pull),
                    ("Body", "BUNDLE", body),
                    ("Floor", "BUNDLE", floor),
                ),
            ),
        },
        input_type="BUNDLE",
    ).outputs[0]

    t.section("Cloth", row=True)
    # Still before the Start Frame, with the least steps. The tearing on, with no edges of its
    # own, for the simulation to follow the topology changes of the Tear
    steps = {
        name: t.node(
            "GeometryNodeSwitch",
            0,
            -i - 2,
            {"Switch": started, "False": 1, "True": inputs[name]},
            input_type="INT",
        ).outputs[0]
        for i, name in enumerate(("Substeps", "Constraint Steps"))
    }
    cloth = t.node(
        "GeometryNodeGroup",
        1,
        0,
        {
            "Geometry": geometry,
            "Pin Group": t.attribute("rip_hold", "FLOAT", 0, 0),
            "Stretchiness": inputs["Stretchiness"],
            "Bendiness": inputs["Bendiness"],
            "Substeps": steps["Substeps"],
            "Constraint Steps": steps["Constraint Steps"],
            "Friction": inputs["Friction"],
            "Collision Radius": inputs["Thickness"],
            "Linear Damping": inputs["Damping"],
            "Tearing": True,
            "Tearing Mode": "Custom",
            "Tearing Edge Group": False,
            "Extra Sim Attributes": ",".join(ATTRIBUTES),
            "Effectors": effectors,
        },
        node_tree=bpy.data.node_groups[PREFIX + CLOTH_DYNAMICS],
    ).outputs["Geometry"]
    # With CLOTH_RIP_DEBUG set, the attributes of the simulation are kept in the output
    if not os.environ.get("CLOTH_RIP_DEBUG"):
        cloth = t.node(
            "GeometryNodeRemoveAttribute",
            2,
            0,
            {"Geometry": cloth, "Pattern Mode": "Wildcard", "Name": "rip_*"},
        ).outputs[0]
    t.node("NodeGroupOutput", 3, 0, {"Geometry": cloth})

    t.arrange()
    return ng, groups


def build_grab(t, inputs, pulls, pull_count, started, colliders):
    """Effector before the solver: each Pull grabs the points around its sphere once, gathering the
    ones reaching it while it holds, holding them in its space and marking the cloth near it as
    tearable, and lets go of the torn out pieces,
    once detached with Release or when scaled to 0. The cloth is pinned to the mesh until the
    Start Frame, then by the Anchor, and held on its shape by the Shape away from the Pulls"""
    t.section("Grab", row=True)
    cin, cout = closure(t, 0, 0)
    position = t.node("GeometryNodeInputPosition", 0, -2).outputs[0]
    state = t.attribute("rip_state", "FLOAT", 0, -4)
    free = t.math("LESS_THAN", state, 0.5, x=1, y=-4)
    held = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", state, 0.5, x=1, y=-5),
        t.math("LESS_THAN", state, 1.5, x=1, y=-6),
        x=2,
        y=-5,
    )
    detached = t.math("SUBTRACT", 1.0, attached(t, cin.outputs["Geometry"], 0, -7), x=4, y=-7)

    geometry = t.store(cin.outputs["Geometry"], "rip_tear", "FLOAT", 0.0, 1, 0, domain="FACE")
    geometry = t.store(geometry, "rip_near", "FLOAT", 0.0, 1, -1)
    pull_in = t.node("GeometryNodeRepeatInput", 2, 0, {"Iterations": pull_count})
    pull_out = t.node("GeometryNodeRepeatOutput", 20, 0)
    pull_in.pair_with_output(pull_out)
    t.connect(geometry, pull_in.inputs["Geometry"])
    geometry = pull_in.outputs["Geometry"]
    pull = pull_in.outputs["Iteration"]
    index = t.math("ADD", pull, 1.0, x=3, y=-1)
    transform = t.node(
        "GeometryNodeSampleIndex",
        4,
        -2,
        {
            "Geometry": pulls,
            "Value": t.node("GeometryNodeInstanceTransform", 3, -2).outputs[0],
            "Index": pull,
        },
        data_type="FLOAT4X4",
        domain="INSTANCE",
    ).outputs[0]
    parts = t.node("FunctionNodeSeparateTransform", 5, -2, {0: transform}).outputs
    radius = t.node("ShaderNodeSeparateXYZ", 6, -3, {0: parts["Scale"]}).outputs["X"]
    grab_radius = t.math("MULTIPLY", radius, inputs["Grab"], x=6, y=-9)
    # The Pull inside a Collider, its nearest surface facing away, grabs nothing and drops the
    # cloth, not to pull it through
    nearest = t.node(
        "GeometryNodeProximity",
        6,
        -39,
        {"Geometry": colliders, "Sample Position": parts["Translation"]},
        target_element="FACES",
    ).outputs
    inside = t.math(
        "MULTIPLY",
        nearest["Is Valid"],
        t.math(
            "GREATER_THAN",
            t.vmath(
                "DOT_PRODUCT",
                t.vmath("SUBTRACT", nearest["Position"], parts["Translation"], x=7, y=-39),
                t.node(
                    "GeometryNodeSampleNearestSurface",
                    7,
                    -41,
                    {
                        "Mesh": colliders,
                        "Value": t.node("GeometryNodeInputNormal", 6, -41).outputs[0],
                        "Sample Position": parts["Translation"],
                    },
                    data_type="FLOAT_VECTOR",
                ).outputs["Value"],
                x=8,
                y=-39,
            ),
            0.0,
            x=9,
            y=-39,
        ),
        x=10,
        y=-39,
    )
    scaled = t.math("GREATER_THAN", radius, 1e-6, x=7, y=-3)
    gripping = t.math("MULTIPLY", scaled, t.math("SUBTRACT", 1.0, inside, x=7, y=-4), x=8, y=-4)
    # The space of the Pull without its scale, the sphere radius
    space = t.node(
        "FunctionNodeCombineTransform",
        6,
        -2,
        {"Translation": parts["Translation"], "Rotation": parts["Rotation"]},
    ).outputs[0]
    by_this = t.math(
        "LESS_THAN",
        t.math(
            "ABSOLUTE",
            t.math("SUBTRACT", t.attribute("rip_held", "FLOAT", 3, -5), index, x=4, y=-5),
            x=5,
            y=-5,
        ),
        0.5,
        x=6,
        y=-5,
    )
    # Holding cloth still on the mesh, neither let go of nor torn out, to grab again otherwise
    holding = t.math(
        "GREATER_THAN",
        t.node(
            "GeometryNodeAttributeStatistic",
            7,
            -5,
            {
                "Geometry": geometry,
                "Selection": t.math(
                    "MULTIPLY",
                    t.math("MULTIPLY", by_this, held, x=5, y=-6),
                    attached(t, geometry, 0, -10),
                    x=6,
                    y=-6,
                ),
                "Attribute": 1.0,
            },
        ).outputs["Sum"],
        0.5,
        x=8,
        y=-5,
    )
    distance = t.vmath("DISTANCE", position, parts["Translation"], x=6, y=-8)
    # Grabbing the free points around the sphere, once, when holding nothing yet
    grabbing = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("SUBTRACT", 1.0, holding, x=9, y=-5),
            t.math("MULTIPLY", started, gripping, x=8, y=-3),
            x=10,
            y=-4,
        ),
        t.math(
            "MULTIPLY",
            t.math("LESS_THAN", distance, grab_radius, x=7, y=-8),
            free,
            x=8,
            y=-8,
        ),
        x=11,
        y=-5,
    )
    grabs = t.math(
        "GREATER_THAN",
        t.node(
            "GeometryNodeAttributeStatistic",
            12,
            -5,
            {"Geometry": geometry, "Selection": grabbing, "Attribute": 1.0},
        ).outputs["Sum"],
        0.5,
        x=13,
        y=-5,
    )
    # The Pull where it grabbed, kept
    start = t.node(
        "GeometryNodeSwitch",
        13,
        -11,
        {
            "Switch": grabs,
            "False": t.node(
                "GeometryNodeAttributeStatistic",
                12,
                -11,
                {
                    "Geometry": geometry,
                    "Selection": by_this,
                    "Attribute": t.attribute("rip_start", "FLOAT_VECTOR", 11, -11),
                },
                data_type="FLOAT_VECTOR",
            ).outputs["Mean"],
            "True": parts["Translation"],
        },
        input_type="VECTOR",
    ).outputs[0]
    # The normal of the cloth where it grabbed, kept
    axis = t.node(
        "GeometryNodeSwitch",
        13,
        -31,
        {
            "Switch": grabs,
            "False": t.node(
                "GeometryNodeAttributeStatistic",
                12,
                -31,
                {
                    "Geometry": geometry,
                    "Selection": by_this,
                    "Attribute": t.attribute("rip_axis", "FLOAT_VECTOR", 11, -31),
                },
                data_type="FLOAT_VECTOR",
            ).outputs["Mean"],
            "True": t.vmath(
                "NORMALIZE",
                t.node(
                    "GeometryNodeAttributeStatistic",
                    12,
                    -33,
                    {
                        "Geometry": geometry,
                        "Selection": grabbing,
                        "Attribute": t.node("GeometryNodeInputNormal", 11, -33).outputs[0],
                    },
                    data_type="FLOAT_VECTOR",
                ).outputs["Mean"],
                x=13,
                y=-33,
            ),
        },
        input_type="VECTOR",
    ).outputs[0]
    # The Pull pushed into the mesh drops the cloth, free to grab again, not to push it through
    pushed = t.math(
        "LESS_THAN",
        t.vmath(
            "DOT_PRODUCT",
            t.vmath("SUBTRACT", parts["Translation"], start, x=14, y=-35),
            axis,
            x=15,
            y=-35,
        ),
        t.math("MULTIPLY", inputs["Pull Before Tear"], -1.0, x=15, y=-36),
        x=16,
        y=-35,
    )
    dropping = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", held, by_this, x=16, y=-37),
        t.math("MAXIMUM", pushed, inside, x=16, y=-38),
        x=17,
        y=-36,
    )
    # Gathering the free points reaching the sphere while holding, not pushed
    gathering = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", holding, t.math("SUBTRACT", 1.0, pushed, x=15, y=-18), x=16, y=-18),
            t.math("MULTIPLY", started, gripping, x=8, y=-3),
            x=17,
            y=-19,
        ),
        t.math(
            "MULTIPLY",
            t.math("LESS_THAN", distance, grab_radius, x=7, y=-9),
            free,
            x=8,
            y=-9,
        ),
        x=18,
        y=-19,
    )
    taking = t.math("MAXIMUM", grabbing, gathering, x=19, y=-19)
    # The cloth pinned to the mesh until the Start Frame, then by the Anchor only
    pin = t.node(
        "GeometryNodeSwitch",
        15,
        -13,
        {"Switch": started, "False": 1.0, "True": t.attribute("rip_anchor", "FLOAT", 14, -13)},
        input_type="FLOAT",
    ).outputs[0]
    # The cloth that can tear: within the Tear Radius of the Pull, once it moved
    moved = t.vmath("DISTANCE", parts["Translation"], start, x=14, y=-17)
    pulled = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", moved, inputs["Pull Before Tear"], x=15, y=-17),
        t.math("MULTIPLY", holding, t.math("SUBTRACT", 1.0, pushed, x=15, y=-18), x=16, y=-18),
        x=16,
        y=-17,
    )
    near = t.math("LESS_THAN", distance, inputs["Tear Radius"], x=17, y=-23)
    tearable = t.math(
        "MAXIMUM",
        t.attribute("rip_tear", "FLOAT", 17, -25),
        t.math("MULTIPLY", pulled, near, x=18, y=-23),
        x=19,
        y=-25,
    )
    # Let go of the held points of the detached pieces with Release, or when scaled to 0
    releasing = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", held, by_this, x=7, y=-10),
        t.math(
            "MAXIMUM",
            t.math("MULTIPLY", detached, inputs["Release"], x=7, y=-11),
            t.math("SUBTRACT", 1.0, scaled, x=8, y=-12),
            x=9,
            y=-11,
        ),
        x=10,
        y=-10,
    )
    # The grabbed and gathered points in the Pull space, held by it from now on
    local = t.node(
        "FunctionNodeTransformPoint",
        8,
        -14,
        {
            "Vector": position,
            "Transform": t.node("FunctionNodeInvertMatrix", 7, -14, {0: space}).outputs[0],
        },
    ).outputs[0]
    for i, (name, data_type, value) in enumerate(
        (
            ("rip_grip", "FLOAT_VECTOR", local),
            ("rip_held", "FLOAT", index),
            ("rip_start", "FLOAT_VECTOR", start),
            ("rip_axis", "FLOAT_VECTOR", axis),
        )
    ):
        geometry = t.store(geometry, name, data_type, value, 14 + i, 0, selection=taking)
    geometry = t.store(
        geometry,
        "rip_state",
        "FLOAT",
        t.math(
            "MULTIPLY",
            t.math(
                "ADD",
                t.attribute("rip_state", "FLOAT", 16, -2),
                t.math("ADD", taking, releasing, x=16, y=-3),
                x=17,
                y=-2,
            ),
            t.math("SUBTRACT", 1.0, dropping, x=17, y=-4),
            x=18,
            y=-2,
        ),
        18,
        0,
    )
    geometry = t.store(geometry, "rip_held", "FLOAT", 0.0, 18, 1, selection=dropping)
    geometry = t.store(geometry, "rip_pin", "FLOAT", pin, 19, 0)
    geometry = t.store(geometry, "rip_tear", "FLOAT", tearable, 20, 0, domain="FACE")
    # How near the Pull, the Shape not holding the cloth it grabs around, fully from the Tear Radius
    geometry = t.store(
        geometry,
        "rip_near",
        "FLOAT",
        t.math(
            "MAXIMUM",
            t.attribute("rip_near", "FLOAT", 18, -27),
            t.math(
                "SUBTRACT",
                1.0,
                t.node(
                    "ShaderNodeMapRange",
                    18,
                    -28,
                    {
                        "Value": distance,
                        "From Min": grab_radius,
                        "From Max": t.math(
                            "MAXIMUM",
                            inputs["Tear Radius"],
                            t.math("MULTIPLY", grab_radius, 1.5, x=16, y=-29),
                            x=17,
                            y=-29,
                        ),
                    },
                ).outputs[0],
                x=19,
                y=-28,
            ),
            x=19,
            y=-27,
        ),
        20,
        -1,
    )
    # The target of the held points, moving with the Pull, clamped to the Colliders
    geometry = t.store(
        geometry,
        "rip_target",
        "FLOAT_VECTOR",
        clamp_to_colliders(
            t,
            colliders,
            inputs,
            t.node(
                "FunctionNodeTransformPoint",
                19,
                -3,
                {"Vector": t.attribute("rip_grip", "FLOAT_VECTOR", 18, -3), "Transform": space},
            ).outputs[0],
            19,
            -40,
        ),
        21,
        0,
        selection=t.math(
            "MULTIPLY",
            by_this,
            t.math("GREATER_THAN", t.attribute("rip_state", "FLOAT", 19, -5), 0.5, x=20, y=-5),
            x=21,
            y=-5,
        ),
    )
    t.connect(geometry, pull_out.inputs["Geometry"])
    pull_out.parent = t.frame
    # The cloth held by a Pull gone from the collection freed, not to hang in the air
    stale = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", t.attribute("rip_state", "FLOAT", 20, -14), 0.5, x=21, y=-14),
        t.math(
            "GREATER_THAN",
            t.attribute("rip_held", "FLOAT", 20, -15),
            t.math("ADD", pull_count, 0.5, x=20, y=-16),
            x=21,
            y=-15,
        ),
        x=22,
        y=-14,
    )
    geometry = t.store(
        pull_out.outputs["Geometry"], "rip_state", "FLOAT", 0.0, 23, -14, selection=stale
    )
    geometry = t.store(geometry, "rip_held", "FLOAT", 0.0, 24, -14, selection=stale)
    # The hold of the cloth: pinned to the mesh by the Anchor, else by the Shape away from the
    # Pulls and the tears, but the held points and the detached pieces, free
    loose = t.math(
        "MAXIMUM",
        t.math("GREATER_THAN", t.attribute("rip_state", "FLOAT", 21, -3), 0.5, x=22, y=-3),
        t.math("SUBTRACT", 1.0, attached(t, pull_out.outputs["Geometry"], 20, -5), x=23, y=-5),
        x=23,
        y=-3,
    )
    # The cloth near the tears hanging free of the Shape, within the Hang of the cut edges
    cut_points = t.node(
        "GeometryNodeSeparateGeometry",
        21,
        -11,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "GREATER_THAN",
                on_domain(t, t.attribute("rip_cut", "FLOAT", 19, -11), "POINT", "FLOAT", 20, -11),
                0.001,
                x=20,
                y=-12,
            ),
        },
        domain="POINT",
    ).outputs["Selection"]
    proximity = t.node(
        "GeometryNodeProximity",
        22,
        -11,
        {
            "Geometry": cut_points,
            "Sample Position": t.node("GeometryNodeInputPosition", 21, -12).outputs[0],
        },
        target_element="POINTS",
    ).outputs
    hanging = t.math(
        "MULTIPLY",
        proximity["Is Valid"],
        t.math(
            "SUBTRACT",
            1.0,
            t.node(
                "ShaderNodeMapRange",
                23,
                -11,
                {"Value": proximity["Distance"], "From Min": 0.0, "From Max": inputs["Hang"]},
            ).outputs[0],
            x=24,
            y=-11,
        ),
        x=25,
        y=-11,
    )
    hold = t.math(
        "MULTIPLY",
        t.math(
            "MAXIMUM",
            t.attribute("rip_pin", "FLOAT", 21, -7),
            t.math(
                "MULTIPLY",
                shape_pin(t, inputs, 21, -9),
                t.math(
                    "SUBTRACT",
                    1.0,
                    t.math(
                        "MAXIMUM", t.attribute("rip_near", "FLOAT", 21, -8), hanging, x=22, y=-9
                    ),
                    x=22,
                    y=-8,
                ),
                x=23,
                y=-8,
            ),
            x=24,
            y=-7,
        ),
        t.math("SUBTRACT", 1.0, loose, x=24, y=-3),
        x=25,
        y=-7,
    )
    geometry = t.store(geometry, "rip_hold", "FLOAT", hold, 25, 0)
    t.connect(geometry, cout.inputs["Geometry"])
    return effector(t, cout, "Pre-Solve", 27, 0)


def clamp_to_colliders(t, colliders, inputs, target, x, y):
    """The target, clamped to the surface of the Colliders, the Thickness out, when inside one:
    the cloth pressed on the body by a Pull, not pulled through it"""
    nearest = t.node(
        "GeometryNodeProximity",
        x,
        y,
        {"Geometry": colliders, "Sample Position": target},
        target_element="FACES",
    ).outputs
    normal = t.node(
        "GeometryNodeSampleNearestSurface",
        x,
        y - 2,
        {
            "Mesh": colliders,
            "Value": t.node("GeometryNodeInputNormal", x - 1, y - 2).outputs[0],
            "Sample Position": target,
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    inside = t.math(
        "MULTIPLY",
        nearest["Is Valid"],
        t.math(
            "GREATER_THAN",
            t.vmath(
                "DOT_PRODUCT",
                t.vmath("SUBTRACT", nearest["Position"], target, x=x + 1, y=y),
                normal,
                x=x + 2,
                y=y,
            ),
            0.0,
            x=x + 3,
            y=y,
        ),
        x=x + 4,
        y=y,
    )
    return t.node(
        "GeometryNodeSwitch",
        x + 5,
        y,
        {
            "Switch": inside,
            "False": target,
            "True": t.vmath(
                "ADD",
                nearest["Position"],
                t.vmath("SCALE", normal, inputs["Thickness"], x=x + 3, y=y - 2),
                x=x + 4,
                y=y - 2,
            ),
        },
        input_type="VECTOR",
    ).outputs[0]


def attached(t, geometry, x, y):
    """Whether each point is on the cloth rather than on a piece torn out of it: on an island
    with points pinned to the mesh, or on the largest island when none is pinned"""
    island = t.node("GeometryNodeInputMeshIsland", x, y - 1).outputs["Island Index"]
    pinned = t.math("GREATER_THAN", t.attribute("rip_pin", "FLOAT", x, y), 0.9, x=x + 1, y=y)
    island_pinned = t.node(
        "GeometryNodeAccumulateField", x + 2, y, {"Value": pinned, "Group ID": island}
    ).outputs["Total"]
    island_size = t.node(
        "GeometryNodeAccumulateField", x + 2, y - 2, {"Value": 1.0, "Group ID": island}
    ).outputs["Total"]
    largest = t.math(
        "GREATER_THAN",
        island_size,
        t.math(
            "SUBTRACT",
            t.node(
                "GeometryNodeAttributeStatistic",
                x + 2,
                y - 3,
                {"Geometry": geometry, "Attribute": island_size},
            ).outputs["Max"],
            0.5,
            x=x + 3,
            y=y - 3,
        ),
        x=x + 4,
        y=y - 2,
    )
    none_pinned = t.math(
        "LESS_THAN",
        t.node(
            "GeometryNodeAttributeStatistic",
            x + 2,
            y - 4,
            {"Geometry": geometry, "Attribute": pinned},
        ).outputs["Sum"],
        0.5,
        x=x + 3,
        y=y - 4,
    )
    return t.math(
        "MAXIMUM",
        t.math("GREATER_THAN", island_pinned, 0.5, x=x + 3, y=y),
        t.math("MULTIPLY", largest, none_pinned, x=x + 5, y=y - 2),
        x=x + 6,
        y=y,
    )


def shape_pin(t, inputs, x, y):
    """Pin of the cloth to the mesh from the Shape: none at 0, a spring over it, rigid at 1, as
    the compliance of a pin is the fifth power of 1 - pin"""
    return t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", inputs["Shape"], 0.0, x=x, y=y),
        t.math(
            "SUBTRACT",
            1.0,
            t.math(
                "MULTIPLY",
                SHAPE_SOFTNESS,
                t.math(
                    "POWER",
                    t.math("SUBTRACT", 1.0, inputs["Shape"], x=x, y=y - 1),
                    2.0,
                    x=x + 1,
                    y=y - 1,
                ),
                x=x + 2,
                y=y - 1,
            ),
            x=x + 3,
            y=y - 1,
        ),
        x=x + 4,
        y=y,
    )


def build_tear(t, inputs):
    """Effector after the solver: the stretched edges between the patches split, starting near a
    grab and running on from the ends of the tears, within reach of the grab, the cloth pulled thin
    snapping"""
    t.section("Tear", row=True)
    cin, cout = closure(t, 0, 0)
    rest = t.attribute("rip_rest", "FLOAT_VECTOR", 0, -2)
    ends = t.node("GeometryNodeInputMeshEdgeVertices", 0, -4).outputs
    rest_length = t.attribute("rest_length", "FLOAT", 0, -5)
    # Stretch of the edges, by their rest length floored at half the mean one, not to tear on the
    # jitter of tiny edges, about the largest of each face, around each edge
    floor = t.math(
        "MULTIPLY",
        t.node(
            "GeometryNodeAttributeStatistic",
            1,
            -6,
            {"Geometry": cin.outputs["Geometry"], "Attribute": rest_length},
            domain="EDGE",
        ).outputs["Mean"],
        TINY_EDGE,
        x=2,
        y=-6,
    )
    strain = t.math(
        "MULTIPLY_ADD",
        t.math(
            "SUBTRACT",
            t.vmath("DISTANCE", ends["Position 1"], ends["Position 2"], x=1, y=-4),
            rest_length,
            x=2,
            y=-4,
        ),
        t.math("DIVIDE", 1.0, t.math("MAXIMUM", rest_length, floor, x=2, y=-5), x=3, y=-5),
        1.0,
        x=3,
        y=-4,
    )
    stretch = t.math(
        "POWER",
        on_domain(
            t,
            t.math(
                "POWER",
                t.math("MAXIMUM", on_domain(t, strain, "EDGE", "FLOAT", 3, -4), 1.0, x=4, y=-4),
                MAX_POWER,
                x=5,
                y=-4,
            ),
            "FACE",
            "FLOAT",
            6,
            -4,
        ),
        1.0 / MAX_POWER,
        x=7,
        y=-4,
    )
    # The Strength varying along the tear lines, from the Setup
    noise = t.attribute("rip_noise", "FLOAT", 4, -7)
    # Over the stretch of the free cloth around, as it is stretched by the solver anyway
    baseline = t.math(
        "MAXIMUM",
        t.node(
            "GeometryNodeAttributeStatistic",
            3,
            -8,
            {
                "Geometry": cin.outputs["Geometry"],
                "Selection": t.math(
                    "LESS_THAN",
                    on_domain(t, t.attribute("rip_pin", "FLOAT", 0, -8), "FACE", "FLOAT", 1, -8),
                    0.5,
                    x=2,
                    y=-8,
                ),
                "Attribute": stretch,
            },
            domain="FACE",
        ).outputs["Median"],
        1.0,
        x=4,
        y=-8,
    )
    excess = t.math("SUBTRACT", inputs["Strength"], 1.0, x=3, y=-9)
    threshold = t.math("MULTIPLY_ADD", excess, noise, baseline, x=5, y=-8)
    running = t.math(
        "MULTIPLY_ADD",
        t.math(
            "MULTIPLY",
            excess,
            t.math("SUBTRACT", 1.0, inputs["Propagation"], x=3, y=-10),
            x=4,
            y=-10,
        ),
        noise,
        baseline,
        x=5,
        y=-10,
    )
    # The lines between the patches from the Setup, between two faces still
    boundary = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", t.attribute("rip_boundary", "FLOAT", 0, -12), 0.5, x=1, y=-12),
        t.math(
            "GREATER_THAN",
            t.node("GeometryNodeInputMeshEdgeNeighbors", 0, -13).outputs["Face Count"],
            1.5,
            x=1,
            y=-13,
        ),
        x=2,
        y=-12,
    )
    region = t.math("GREATER_THAN", t.attribute("rip_tear", "FLOAT", 3, -14), 0.25, x=4, y=-14)
    # The edges tearing, each pass running the tears on by one edge
    # Nothing to tear, snap or fray before a Pull grabbed the cloth
    active = t.math(
        "GREATER_THAN",
        t.node(
            "GeometryNodeAttributeStatistic",
            0,
            2,
            {
                "Geometry": cin.outputs["Geometry"],
                "Attribute": t.attribute("rip_state", "FLOAT", -1, 2),
            },
        ).outputs["Max"],
        0.5,
        x=1,
        y=2,
    )
    pass_in = t.node(
        "GeometryNodeRepeatInput",
        1,
        0,
        {
            "Iterations": t.node(
                "GeometryNodeSwitch",
                0,
                1,
                {"Switch": active, "False": 0, "True": inputs["Tear Speed"]},
                input_type="INT",
            ).outputs[0]
        },
    )
    pass_out = t.node("GeometryNodeRepeatOutput", 12, 0)
    pass_in.pair_with_output(pass_out)
    t.connect(cin.outputs["Geometry"], pass_in.inputs["Geometry"])
    cut = t.attribute("rip_cut", "FLOAT", 7, -1)
    tip = t.math(
        "GREATER_THAN",
        on_domain(t, on_domain(t, cut, "POINT", "FLOAT", 8, -1), "EDGE", "FLOAT", 9, -1),
        0.001,
        x=10,
        y=-1,
    )
    tearing = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", boundary, t.math("LESS_THAN", cut, 0.5, x=8, y=-3), x=9, y=-3),
        t.math(
            "MAXIMUM",
            t.math(
                "MULTIPLY", region, t.math("GREATER_THAN", stretch, threshold, x=8, y=-5), x=9, y=-5
            ),
            t.math(
                "MULTIPLY",
                t.math("MULTIPLY", tip, region, x=8, y=-8),
                t.math("GREATER_THAN", stretch, running, x=8, y=-7),
                x=9,
                y=-7,
            ),
            x=10,
            y=-5,
        ),
        x=11,
        y=-3,
    )
    geometry = pass_in.outputs["Geometry"]
    if os.environ.get("CLOTH_RIP_DEBUG"):
        geometry = t.store(geometry, "dbg_stretch", "FLOAT", stretch, 9, 2, domain="FACE")
        geometry = t.store(geometry, "dbg_strain", "FLOAT", strain, 9, 3, domain="EDGE")
    geometry = t.store(
        geometry,
        "rip_cut",
        "FLOAT",
        t.math("MAXIMUM", cut, tearing, x=11, y=-1),
        10,
        0,
        domain="EDGE",
    )
    geometry = t.node(
        "GeometryNodeSplitEdges",
        11,
        0,
        {"Mesh": geometry, "Selection": t.attribute("rip_cut", "FLOAT", 10, -9)},
    ).outputs[0]
    t.connect(geometry, pass_out.inputs["Geometry"])
    pass_out.parent = t.frame
    # The free cloth pulled thin snapped, as the threads left between the torn pieces: by the
    # stretch over the faces around, not to punch a hole at a spike of the solver
    around = on_domain(t, on_domain(t, stretch, "EDGE", "FLOAT", 10, -3), "FACE", "FLOAT", 11, -3)
    snapping = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", around, inputs["Snap"], x=12, y=-3),
        t.math(
            "LESS_THAN",
            on_domain(t, t.attribute("rip_pin", "FLOAT", 10, -12), "FACE", "FLOAT", 11, -12),
            0.5,
            x=12,
            y=-12,
        ),
        x=13,
        y=-3,
    )
    # The faces along the tears split off as crumbs by the Fray, picked by their rest position
    crumb = t.math(
        "MULTIPLY",
        t.math(
            "GREATER_THAN",
            on_domain(t, t.attribute("rip_cut", "FLOAT", 10, -15), "FACE", "FLOAT", 11, -15),
            0.01,
            x=12,
            y=-15,
        ),
        t.math(
            "LESS_THAN",
            t.node(
                "FunctionNodeRandomValue",
                12,
                -17,
                {
                    "Min": 0.0,
                    "Max": 1.0,
                    "ID": t.node(
                        "FunctionNodeHashValue",
                        11,
                        -17,
                        {"Value": on_domain(t, rest, "FACE", "FLOAT_VECTOR", 10, -17), "Seed": 7},
                        data_type="VECTOR",
                    ).outputs[0],
                },
                data_type="FLOAT",
            ).outputs[0],
            inputs["Fray"],
            x=13,
            y=-17,
        ),
        x=13,
        y=-15,
    )
    fraying = t.math(
        "GREATER_THAN", on_domain(t, crumb, "EDGE", "FLOAT", 14, -15), 0.01, x=15, y=-15
    )
    geometry = t.store(
        pass_out.outputs["Geometry"],
        "rip_cut",
        "FLOAT",
        t.math("MAXIMUM", t.attribute("rip_cut", "FLOAT", 13, -13), fraying, x=14, y=-13),
        13,
        0,
        domain="EDGE",
    )
    geometry = t.node(
        "GeometryNodeSplitEdges",
        14,
        0,
        {"Mesh": geometry, "Selection": t.attribute("rip_cut", "FLOAT", 13, -11)},
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeDeleteGeometry",
        15,
        0,
        {"Geometry": geometry, "Selection": snapping},
        domain="FACE",
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSwitch",
        16,
        0,
        {"Switch": active, "False": cin.outputs["Geometry"], "True": geometry},
        input_type="GEOMETRY",
    ).outputs[0]
    t.connect(geometry, cout.inputs["Geometry"])
    return effector(t, cout, "Post-Solve", 17, 0)


def patch(t, inputs, rest, cells, x, y):
    """Index of the patch of the cloth at the rest position, of random sizes, with ragged edges"""
    noise = t.node(
        "ShaderNodeTexNoise", x, y, {"Vector": rest, "Scale": cells, "Detail": 1.0}
    ).outputs["Color"]
    ragged = t.vmath(
        "ADD",
        rest,
        t.vmath(
            "SCALE",
            t.vmath("SUBTRACT", noise, (0.5, 0.5, 0.5), x=x + 1, y=y),
            t.math(
                "MULTIPLY",
                t.math("MULTIPLY", inputs["Edge Noise"], 0.4, x=x, y=y - 2),
                inputs["Piece Size"],
                x=x + 1,
                y=y - 2,
            ),
            x=x + 2,
            y=y,
        ),
        x=x + 3,
        y=y,
    )
    voronoi = t.node(
        "ShaderNodeTexVoronoi",
        x + 4,
        y,
        {"Vector": ragged, "Scale": cells, "Randomness": inputs["Randomness"]},
    ).outputs["Position"]
    return t.node(
        "FunctionNodeHashValue", x + 5, y, {"Value": voronoi}, data_type="VECTOR"
    ).outputs[0]


def on_domain(t, value, domain, data_type, x, y):
    return t.node(
        "GeometryNodeFieldOnDomain", x, y, {"Value": value}, domain=domain, data_type=data_type
    ).outputs[0]


def closure(t, x, y):
    """Closure of a geometry effector, paired"""
    cin = t.node("NodeClosureInput", x, y)
    cout = t.node("NodeClosureOutput", x + 20, y)
    cin.pair_with_output(cout)
    cout.input_items.new("GEOMETRY", "Geometry")
    cout.input_items.new("MATRIX", "To World Transform")
    cout.output_items.new("GEOMETRY", "Geometry")
    return cin, cout


def effector(t, cout, stage, x, y):
    """Custom geometry effector of the closure, at the stage of the simulation"""
    return t.node(
        "GeometryNodeGroup",
        x,
        y,
        {"Type": "Geometry", "Stage": stage, "Geometry Effector": cout.outputs["Closure"]},
        node_tree=bpy.data.node_groups[PREFIX + "Custom Effector"],
    ).outputs["Effector"]


def collider(t, inputs, geometry, deforming, x, y):
    """Collider of the geometry, with the Friction"""
    return t.node(
        "GeometryNodeGroup",
        x,
        y,
        {
            "Geometry": geometry,
            "Deforming": deforming,
            "Margin": COLLISION,
            "Friction": inputs["Friction"],
        },
        node_tree=bpy.data.node_groups[PREFIX + "Collider"],
    ).outputs["Collider"]


def bundle(t, x, y, items):
    """Bundle of the items, (name, socket type, value or socket)"""
    node = t.node("NodeCombineBundle", x, y)
    for name, socket_type, value in items:
        node.bundle_items.new(socket_type, name)
        t.connect(value, node.inputs[name])
    return node.outputs[0]


if __name__ == "__main__":
    ng, groups = build_node_group()
    write(RESOURCE, (ng, *groups))
