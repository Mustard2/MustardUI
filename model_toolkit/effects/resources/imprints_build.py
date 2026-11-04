# Build imprints.blend: the Imprints node group and the Imprints Tint shader group
# Usage: Blender --background --factory-startup --python imprints_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, arrange_interface, write

RESOURCE = "imprints.blend"
NODE_GROUP = "MustardUI Imprints"
TINT = "MustardUI Imprints Tint"
# Depths below the surface the Colliders are looked for, not to imprint parts far under it
REACH = 3.0
# Distance out of the surface a Collider covering a point is looked for
OUTSIDE = 10.0
# Start of the rays through the mesh, inside it not to hit the faces of the point
SELF_OFFSET = 0.001
# Blur iterations of the rim, at most
RIM_ITERATIONS = 200
# Rounds of the soft imprints spreading them keeping the pressed points as deep, on a copy of
# the mesh merged to a fraction of the Softness, then pushing out of the Colliders the points
# moved into them
SOFT_ROUNDS = 128
COARSE = 12.0
# Blur iterations of the soft imprints back on the mesh, at most
SMOOTH_ITERATIONS = 64
# Fading of the soft imprints away from the pressed points, by round
FADE = 2.0
PUSH_ROUNDS = 2
# Depth of the imprints tinted fully, relative to the Depth
TINT_DEPTH = 0.4
# Depth of the imprints the rim fades out to, relative to the Depth, not to rise inside them
RIM_DEPTH = 0.1
# Spread of the rim around the imprints relative to its width, subdivided that far
RIM_SPREAD = 2.0
# Distance of the same points at each frame, in the simulated state, and welded
MATCH = 1e-5
# Speed along the ground of the debris dropping off the Colliders, unbounded
FAR = 1000.0
# Octaves and contrast of the uneven color of the imprints
DETAIL_OCTAVES = 4.0
DETAIL_CONTRAST = 2.5
# Debris shapes, their dents and flattening
DEBRIS_SHAPES = 4
DEBRIS_DENT = 0.3
DEBRIS_FLAT = ((0.5, 1.0), (0.3, 0.6))
# Seconds the debris sticks to the Colliders at most, mostly less, how far up it follows them
# relative to the Depth, its spin (radians per second) and the speed kept bouncing, resting below a
# bounce of its size
DEBRIS_STICK = 0.8
DEBRIS_REACH = 10.0
DEBRIS_SPIN = 12.0
BOUNCE = 0.25
GRAVITY = 9.81


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Imprint the Colliders in the mesh, as in snow, sand or a cushion, storing the "
        "imprint attribute read by the Imprints Tint shader"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Colliders",
        "NodeSocketCollection",
        description="Objects pressing into the mesh, e.g. the body and the shoes",
    )
    add_input(
        ng,
        "Depth",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.05,
        min_value=0.0,
        description="Deepest imprint, as thick as the soft layer",
    )
    add_input(
        ng,
        "Subdivisions",
        "NodeSocketInt",
        default_value=0,
        min_value=0,
        max_value=16,
        description="Subdivisions of the mesh near the Colliders and the imprints",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        default_value=1,
        min_value=0,
        max_value=50,
        description="Iterations smoothing the imprints over the mesh",
    )
    add_input(
        ng,
        "Rim",
        "NodeSocketFloat",
        default_value=0.5,
        min_value=-2.0,
        max_value=2.0,
        description="Height of the rim pushed up around the imprints, or of the bulge around "
        "the soft ones, relative to their depth, negative to sink the surface around them",
    )
    add_input(
        ng,
        "Rim Width",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.03,
        min_value=0.0,
        description="Width of the rim around the imprints",
    )
    add_input(
        ng,
        "Noise",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.2,
        min_value=0.0,
        max_value=1.0,
        description="Uneven depth of the imprints and the rim",
    )
    add_input(
        ng,
        "Noise Scale",
        "NodeSocketFloat",
        default_value=40.0,
        min_value=0.0,
        description="Number of bumps of the Noise per meter",
    )
    add_input(
        ng,
        "Color",
        "NodeSocketColor",
        default_value=(0.8, 0.8, 0.8, 1.0),
        description="Color multiplying the base color of the materials in the imprints",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the imprints, e.g. to the soft parts",
    )
    add_input(
        ng,
        "Lasting",
        "NodeSocketBool",
        default_value=True,
        description="Keep the imprints where the Colliders were, simulated from the Start Frame",
    )
    add_input(ng, "Start Frame", "NodeSocketInt", description="First simulated frame")
    add_input(
        ng,
        "Recovery",
        "NodeSocketFloat",
        default_value=0.0,
        min_value=0.0,
        description="Seconds for the deepest imprints to fill back, 0 to keep them",
    )
    softness = add_input(
        ng,
        "Softness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.0,
        min_value=0.0,
        description="Distance the imprints spread over, the soft surface wrapping around the "
        "Colliders as a cushion, 0 for crisp imprints as footprints",
    )
    add_input(
        ng,
        "Debris",
        "NodeSocketBool",
        default_value=False,
        description="Chunks sticking to the Colliders and falling off them as they leave the "
        "imprints, simulated from the Start Frame",
    )
    add_input(
        ng,
        "Debris Amount",
        "NodeSocketFloat",
        default_value=6000.0,
        min_value=0.0,
        description="Chunks per square meter of the imprints",
    )
    add_input(
        ng,
        "Debris Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.008,
        min_value=0.0,
        description="Size of the largest chunks",
    )
    add_input(
        ng,
        "Tint",
        "NodeSocketBool",
        default_value=True,
        description="Color the imprints, in the materials with the Imprints Tint shader",
    )
    add_input(
        ng,
        "Detail",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=0.4,
        min_value=0.0,
        max_value=1.0,
        description="Uneven color of the imprints",
    )
    add_input(
        ng,
        "Detail Scale",
        "NodeSocketFloat",
        default_value=150.0,
        min_value=0.0,
        description="Number of spots of the Detail per meter",
    )
    strength = add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=10.0,
        description="Overall strength of the imprints, multiplying how deep they are pressed, also "
        "past the Depth, and so their rim",
    )
    # After Smooth and Depth, added last to keep the identifiers of the inputs before them
    for item, after in ((softness, "Smooth"), (strength, "Depth")):
        ng.interface.move(
            item, list(ng.interface.items_tree).index(ng.interface.items_tree[after]) + 1
        )
    arrange_interface(
        ng,
        [
            (None, "Tint", True, "Tint", ["Color", "Detail", "Detail Scale"]),
            (None, "Debris", True, "Debris", ["Debris Amount", "Debris Size"]),
            (None, "Lasting", False, "Lasting", ["Start Frame", "Recovery"]),
        ],
    )

    t = Tree(ng)
    t.section("Colliders")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    # Only the mesh, not the drops of a Wet before, the other components joined back as they are
    components = t.node("GeometryNodeSeparateComponents", -1, 1, {0: inputs["Geometry"]}).outputs
    self_object = t.node("GeometryNodeSelfObject", -2, -2).outputs[0]
    to_world = t.node(
        "GeometryNodeObjectInfo", -1, -2, {"Object": self_object}, transform_space="ORIGINAL"
    ).outputs["Transform"]
    to_local = t.node("FunctionNodeInvertMatrix", 0, -2, {0: to_world}).outputs[0]
    position = t.node("GeometryNodeInputPosition", 0, -3).outputs[0]
    world = t.node(
        "FunctionNodeTransformPoint", 1, -3, {"Vector": position, "Transform": to_world}
    ).outputs[0]
    # Normals by the inverse transpose, the mesh being scaled unevenly
    normal = t.node(
        "FunctionNodeTransformDirection",
        2,
        -4,
        {
            "Direction": t.node("GeometryNodeInputNormal", 1, -4).outputs["Normal"],
            "Transform": t.node("FunctionNodeTransposeMatrix", 1, -5, {0: to_local}).outputs[0],
        },
    ).outputs[0]
    normal = t.vmath("NORMALIZE", normal, x=3, y=-4)

    colliders = t.node(
        "GeometryNodeCollectionInfo",
        0,
        -7,
        {"Collection": inputs["Colliders"]},
        transform_space="RELATIVE",
    ).outputs[0]
    colliders = t.node("GeometryNodeRealizeInstances", 1, -7, {"Geometry": colliders}).outputs[0]
    colliders = t.node(
        "GeometryNodeTransform",
        2,
        -7,
        {"Geometry": colliders, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    box = t.node("GeometryNodeBoundBox", 3, -8, {"Geometry": colliders}).outputs
    mesh = t.node(
        "GeometryNodeTransform",
        2,
        -11,
        {"Geometry": components["Mesh"], "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]

    t.section("Imprint", row=True)
    reach = t.math("MULTIPLY", inputs["Depth"], REACH, x=3, y=-6)
    # Subdivided where the Colliders may press it, the same at each frame
    geometry = refine(
        t, components["Mesh"], inputs["Subdivisions"], to_world, box, reach, None, None, 0, 0
    )
    # Within half the thickness of the mesh, pressed at most to its middle from either side
    through = t.node(
        "GeometryNodeRaycast",
        3,
        -11,
        {
            "Target Geometry": mesh,
            "Source Position": t.vmath(
                "SUBTRACT", world, t.vmath("SCALE", normal, SELF_OFFSET, x=2, y=-12), x=2.5, y=-12
            ),
            "Ray Direction": t.vmath("SCALE", normal, -1.0, x=2, y=-13),
            "Ray Length": t.math("MULTIPLY", reach, 2.0, x=2, y=-14),
        },
    ).outputs
    half = t.math(
        "MULTIPLY",
        t.math("ADD", through["Hit Distance"], SELF_OFFSET, x=4, y=-11),
        0.5,
        x=4.5,
        y=-11,
    )
    thickness = t.node(
        "GeometryNodeSwitch",
        5,
        -10,
        {
            "Switch": through["Is Hit"],
            "False": reach,
            "True": t.math("MINIMUM", reach, half, x=5, y=-11),
        },
        input_type="FLOAT",
    ).outputs[0]
    geometry = t.store(geometry, ".imprint_reach", "FLOAT", thickness, 5.5, 0)
    limited = t.attribute(".imprint_reach", "FLOAT", 6, -10)
    # Only the points near the Colliders cast a ray
    near = in_box(t, box, world, limited, 4, -9)
    depth = pressed_depth(t, colliders, world, normal, limited, inputs["Depth"], 4, -5, reach)
    depth = t.math("MULTIPLY", depth, inputs["Mask"], x=9, y=-5)
    depth = t.math("MULTIPLY", depth, inputs["Strength"], x=9.5, y=-5)
    store = t.node(
        "GeometryNodeStoreNamedAttribute",
        10,
        0,
        {"Geometry": geometry, "Name": ".imprint_live", "Value": depth, "Selection": near},
        data_type="FLOAT",
        domain="POINT",
    )
    live = t.attribute(".imprint_live", "FLOAT", 11, -2)

    t.section("Lasting", row=True)
    state = build_lasting(t, inputs, store.outputs["Geometry"], live)

    t.section("Subdivision", row=True)
    # Subdivided where the Colliders may press it and around the imprints, as far as their rim
    # spreads
    spread = t.math(
        "ADD",
        t.math("MULTIPLY", inputs["Rim Width"], RIM_SPREAD, x=0, y=-4),
        inputs["Softness"],
        x=1,
        y=-4,
    )
    around = t.node(
        "GeometryNodeTransform",
        1,
        -2,
        {"Geometry": state, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    # Around the Colliders as far as the soft imprints spread too
    geometry = refine(
        t,
        components["Mesh"],
        inputs["Subdivisions"],
        to_world,
        box,
        t.math("ADD", reach, inputs["Softness"], x=2, y=-8),
        around,
        spread,
        3,
        0,
    )
    geometry = t.store(geometry, ".imprint_reach", "FLOAT", thickness, 8, 0)
    reach = t.attribute(".imprint_reach", "FLOAT", 8, -2)
    # The state at the same positions, without Lasting the depth now
    index = t.node(
        "GeometryNodeSampleNearest",
        8,
        -4,
        {"Geometry": state, "Sample Position": position},
        domain="POINT",
    ).outputs[0]

    def at(name, data_type, y):
        return t.node(
            "GeometryNodeSampleIndex",
            9,
            y,
            {
                "Geometry": state,
                "Value": t.attribute(name, data_type, 8.5, y - 1),
                "Index": index,
            },
            data_type=data_type,
        ).outputs[0]

    same = t.math(
        "LESS_THAN",
        t.vmath(
            "DISTANCE",
            at("position", "FLOAT_VECTOR", -6),
            position,
            x=9.5,
            y=-6,
        ),
        MATCH,
        x=10,
        y=-6,
    )
    depth = t.node(
        "GeometryNodeSwitch",
        10,
        -8,
        {
            "Switch": inputs["Lasting"],
            "False": at(".imprint_live", "FLOAT", -8),
            "True": at(".imprint_kept", "FLOAT", -10),
        },
        input_type="FLOAT",
    ).outputs[0]
    depth = t.math("MULTIPLY", depth, same, x=11, y=-8)
    released = t.math("MULTIPLY", at(".imprint_released", "BOOLEAN", -12), same, x=11, y=-12)

    t.section("Displacement", row=True)
    geometry = t.store(geometry, ".imprint_released", "BOOLEAN", released, -3, 0)
    geometry = t.store(geometry, ".imprint_depth", "FLOAT", depth, -2, 0)
    depth = t.attribute(".imprint_depth", "FLOAT", -2, -2)
    depth = t.math("MAXIMUM", depth, shallowest_neighbor(t, depth, -2, -4), x=-1, y=-2)
    depth = t.node(
        "GeometryNodeBlurAttribute",
        0,
        -2,
        {"Value": depth, "Iterations": inputs["Smooth"]},
        data_type="FLOAT",
    ).outputs[0]
    geometry = t.store(geometry, ".imprint_depth", "FLOAT", depth, 1, 0)
    depth = t.attribute(".imprint_depth", "FLOAT", 2, -2)

    # The rim from the imprints blurred over its width, outside of them, by their edge length
    edges = t.node("GeometryNodeInputMeshEdgeVertices", 2, -6).outputs
    length = t.vmath(
        "DISTANCE",
        *(
            t.node(
                "FunctionNodeTransformPoint",
                3,
                -6 - i,
                {"Vector": edges[f"Position {i + 1}"], "Transform": to_world},
            ).outputs[0]
            for i in range(2)
        ),
        x=4,
        y=-6,
    )
    length = t.node(
        "GeometryNodeAttributeStatistic",
        5,
        -6,
        {
            "Geometry": geometry,
            "Selection": t.math("GREATER_THAN", depth, 0.0, x=4, y=-8),
            "Attribute": length,
        },
        domain="EDGE",
    ).outputs["Mean"]
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        10,
        -5,
        {
            "Value": depth,
            "Iterations": blur_iterations(t, inputs["Rim Width"], length, RIM_ITERATIONS, 6, -6),
        },
        data_type="FLOAT",
    ).outputs[0]
    rim = t.math(
        "MULTIPLY",
        t.math("MAXIMUM", t.math("SUBTRACT", blurred, depth, x=11, y=-5), 0.0, x=12, y=-5),
        inputs["Rim"],
        x=13,
        y=-5,
    )
    outside = t.math(
        "SUBTRACT",
        1.0,
        t.math(
            "DIVIDE",
            depth,
            t.math("MULTIPLY", inputs["Depth"], RIM_DEPTH, x=11, y=-7),
            x=12,
            y=-7,
        ),
        x=13,
        y=-7,
        clamp=True,
    )
    rim = t.math("MULTIPLY", rim, outside, x=13.5, y=-5)
    height = t.math("SUBTRACT", rim, depth, x=14, y=-4)

    noise = t.node(
        "ShaderNodeTexNoise",
        10,
        -9,
        {"Vector": world, "Scale": inputs["Noise Scale"], "Detail": 0.0},
    ).outputs["Fac"]
    noise = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", noise, 0.5, x=11, y=-9),
        t.math("MULTIPLY", inputs["Noise"], 2.0, x=11, y=-10),
        1.0,
        x=12,
        y=-9,
    )
    noise = t.math("MAXIMUM", noise, 0.0, x=13, y=-9)
    crisp = t.store(
        geometry,
        ".imprint_offset",
        "FLOAT_VECTOR",
        t.vmath("SCALE", normal, t.math("MULTIPLY", height, noise, x=14, y=-5), x=15, y=-4),
        15,
        -1,
    )
    soft = build_soft(t, inputs, geometry, colliders, box, world, normal, reach, depth, length)
    soft = t.store(
        soft,
        ".imprint_offset",
        "FLOAT_VECTOR",
        t.vmath(
            "SCALE", t.attribute(".imprint_offset", "FLOAT_VECTOR", 15, -7), noise, x=15.5, y=-6
        ),
        16,
        -6,
    )
    geometry = t.node(
        "GeometryNodeSwitch",
        16.5,
        0,
        {
            "Switch": t.math("GREATER_THAN", inputs["Softness"], 0.0, x=16, y=-2),
            "False": crisp,
            "True": soft,
        },
        input_type="GEOMETRY",
    ).outputs[0]
    offset = t.attribute(".imprint_offset", "FLOAT_VECTOR", 17, -2)

    # Smooth where displaced, not to show the faces of the imprints
    geometry = t.node(
        "GeometryNodeSetShadeSmooth",
        16,
        0,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "GREATER_THAN", t.vmath("LENGTH", offset, x=17, y=-3), 1e-6, x=17.5, y=-3
            ),
        },
        domain="FACE",
    ).outputs[0]
    offset = t.node(
        "FunctionNodeTransformDirection",
        16,
        -4,
        {"Direction": offset, "Transform": to_local},
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSetPosition", 17, 0, {"Geometry": geometry, "Offset": offset}
    ).outputs[0]

    # Strength and scale of the uneven color, for the shader
    detail = t.node(
        "ShaderNodeCombineXYZ",
        18,
        -6,
        {
            "X": t.math("MULTIPLY", inputs["Detail"], inputs["Tint"], x=17.5, y=-6),
            "Y": inputs["Detail Scale"],
        },
    ).outputs[0]
    debris = build_debris(t, inputs, geometry, colliders, to_world, to_local, length, detail)

    t.section("Attributes", row=True)
    # The amount left untinted in the alpha, 1 as read by the shaders without the attribute
    amount = t.math(
        "MULTIPLY",
        t.math(
            "DIVIDE",
            depth,
            t.math("MULTIPLY", inputs["Depth"], TINT_DEPTH, x=0, y=-3),
            x=0.5,
            y=-2,
            clamp=True,
        ),
        inputs["Tint"],
        x=1,
        y=-2,
    )
    rgb = t.node("FunctionNodeSeparateColor", 1, -4, {0: inputs["Color"]}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        2,
        -2,
        {
            "Red": rgb["Red"],
            "Green": rgb["Green"],
            "Blue": rgb["Blue"],
            "Alpha": t.math("SUBTRACT", 1.0, amount, x=2, y=-4),
        },
    ).outputs[0]
    geometry = t.store(geometry, "imprint", "FLOAT_COLOR", color, 3, 0)
    geometry = t.store(geometry, "imprint_detail", "FLOAT_VECTOR", detail, 3.25, 0)
    # The mesh first, the last link going first
    joined = t.node("GeometryNodeJoinGeometry", 4, -1)
    for part in (debris, geometry):
        t.connect(part, joined.inputs[0])
    # Their own material index, the join adding an empty material for them
    joined = t.node(
        "GeometryNodeSetMaterialIndex",
        4.25,
        -1,
        {
            "Geometry": joined.outputs[0],
            "Selection": t.math(
                "GREATER_THAN",
                t.attribute(".imprint_debris_size", "FLOAT", 3.5, -4),
                0.0,
                x=4,
                y=-4,
            ),
            "Material Index": t.attribute(".imprint_debris_material", "INT", 3.5, -5),
        },
    )
    geometry = t.node(
        "GeometryNodeSwitch",
        4.5,
        0,
        {
            "Switch": inputs["Debris"],
            "False": geometry,
            "True": joined.outputs[0],
        },
        input_type="GEOMETRY",
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeRemoveAttribute",
        4,
        0,
        {"Geometry": geometry, "Pattern Mode": "Wildcard", "Name": ".imprint_*"},
    ).outputs[0]
    output = t.node("GeometryNodeJoinGeometry", 4.5, 0)
    for name in ("Instances", "Volume", "Point Cloud", "Grease Pencil", "Curve"):
        t.connect(components[name], output.inputs[0])
    t.connect(geometry, output.inputs[0])
    t.node("NodeGroupOutput", 5, 0, {"Geometry": output.outputs[0]})
    t.arrange()
    return ng


def pressed_depth(t, colliders, position, normal, reach, limit, x, y, full=None):
    """Depth the Colliders press the surface at the position, up from under it to their lowest
    surface, only where they cover it; with the full reach, past a reach limited by the mesh
    thickness for a Collider going through the mesh from this side"""
    ray = t.node(
        "GeometryNodeRaycast",
        x + 1,
        y,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath(
                "SUBTRACT", position, t.vmath("SCALE", normal, reach, x=x, y=y), x=x + 0.5, y=y
            ),
            "Ray Direction": normal,
            "Ray Length": reach,
        },
    ).outputs
    depth = t.math(
        "MINIMUM",
        t.math("SUBTRACT", reach, ray["Hit Distance"], x=x + 2, y=y),
        limit,
        x=x + 3,
        y=y,
    )
    depth = t.math("MULTIPLY", depth, ray["Is Hit"], x=x + 4, y=y)
    if full is not None:
        # Through a mesh thinner than the full reach, e.g. a giant's foot through a road slab, from
        # its lowest surface with no Collider between it and the point, if it goes less deep from
        # this side than from the other side, which is twice the limited reach away
        lowest = t.node(
            "GeometryNodeRaycast",
            x + 1,
            y - 4,
            {
                "Target Geometry": colliders,
                "Source Position": t.vmath(
                    "SUBTRACT",
                    position,
                    t.vmath("SCALE", normal, full, x=x, y=y - 4),
                    x=x + 0.5,
                    y=y - 4,
                ),
                "Ray Direction": normal,
                "Ray Length": full,
            },
        ).outputs
        through = t.math("SUBTRACT", full, lowest["Hit Distance"], x=x + 2, y=y - 4)
        between = t.node(
            "GeometryNodeRaycast",
            x + 3,
            y - 6,
            {
                "Target Geometry": colliders,
                "Source Position": t.vmath(
                    "ADD",
                    lowest["Hit Position"],
                    t.vmath("SCALE", normal, SELF_OFFSET, x=x + 2, y=y - 7),
                    x=x + 2.5,
                    y=y - 6,
                ),
                "Ray Direction": normal,
                "Ray Length": t.math("SUBTRACT", through, SELF_OFFSET, x=x + 2.5, y=y - 8),
            },
        ).outputs["Is Hit"]
        other = t.node(
            "GeometryNodeRaycast",
            x + 1,
            y - 9,
            {
                "Target Geometry": colliders,
                "Source Position": t.vmath(
                    "ADD",
                    position,
                    t.vmath(
                        "SCALE",
                        normal,
                        t.math(
                            "SUBTRACT",
                            full,
                            t.math("MULTIPLY", reach, 2.0, x=x - 1, y=y - 10),
                            x=x - 0.5,
                            y=y - 10,
                        ),
                        x=x,
                        y=y - 9,
                    ),
                    x=x + 0.5,
                    y=y - 9,
                ),
                "Ray Direction": t.vmath("SCALE", normal, -1.0, x=x, y=y - 11),
                "Ray Length": full,
            },
        ).outputs
        deeper = t.math(
            "MULTIPLY",
            t.math(
                "MULTIPLY",
                other["Is Hit"],
                t.math("LESS_THAN", reach, full, x=x + 2, y=y - 11),
                x=x + 2.5,
                y=y - 10,
            ),
            t.math(
                "GREATER_THAN",
                t.math("ADD", through, 1e-6, x=x + 2.5, y=y - 9),
                t.math("SUBTRACT", full, other["Hit Distance"], x=x + 2, y=y - 9),
                x=x + 3,
                y=y - 9,
            ),
            x=x + 3.5,
            y=y - 10,
        )
        entered = t.math(
            "MULTIPLY",
            lowest["Is Hit"],
            t.math(
                "SUBTRACT",
                1.0,
                t.math("MAXIMUM", between, deeper, x=x + 4, y=y - 8),
                x=x + 4.5,
                y=y - 8,
            ),
            x=x + 5,
            y=y - 6,
        )
        depth = t.math(
            "MAXIMUM",
            depth,
            t.math(
                "MULTIPLY",
                entered,
                t.math("MINIMUM", through, limit, x=x + 4, y=y - 4),
                x=x + 5.5,
                y=y - 4,
            ),
            x=x + 6,
            y=y,
        )
    # Not seen through a mesh thinner than the reach
    covered = t.node(
        "GeometryNodeRaycast",
        x + 1,
        y - 2,
        {
            "Target Geometry": colliders,
            "Source Position": position,
            "Ray Direction": normal,
            "Ray Length": OUTSIDE,
        },
    ).outputs["Is Hit"]
    return t.math("MULTIPLY", depth, covered, x=x + 4.5, y=y)


def blur_iterations(t, distance, length, limit, x, y):
    """Blur iterations spreading a value over the distance, the edges being that long"""
    spread = t.math("DIVIDE", distance, length, x=x, y=y)
    iterations = t.math(
        "MINIMUM",
        t.math("MULTIPLY", t.math("MULTIPLY", spread, spread, x=x + 1, y=y), 2.0, x=x + 2, y=y),
        limit,
        x=x + 3,
        y=y,
    )
    return t.math("ROUND", iterations, x=x + 3.5, y=y)


def build_soft(t, inputs, geometry, colliders, box, world, normal, reach, depth, spacing):
    """Geometry with the offsets of the soft imprints: spread over the Softness keeping the
    pressed points as deep, on a coarser copy of the mesh, then the points moved into the
    Colliders pushed out of them"""
    inward = t.vmath("SCALE", normal, -1.0, x=0, y=-12)
    pressed = t.vmath("SCALE", inward, depth, x=0.5, y=-13)
    geometry = t.store(geometry, ".imprint_inward", "FLOAT_VECTOR", inward, 0.5, -11)
    geometry = t.store(geometry, ".imprint_offset", "FLOAT_VECTOR", pressed, 1, -11)
    # Each part of the mesh brought back from its own, its denser edges merged further away
    island = t.node("GeometryNodeInputMeshIsland", 0.5, -15).outputs["Island Index"]
    geometry = t.store(geometry, ".imprint_island", "INT", island, 1, -10)

    # Around the Colliders in world space, its points about a seventh of the Softness apart
    near = in_box(t, box, world, t.math("ADD", reach, inputs["Softness"], x=0, y=-16), 0.5, -16)
    coarse = t.node(
        "GeometryNodeDeleteGeometry",
        1,
        -12,
        {"Geometry": geometry, "Selection": t.math("SUBTRACT", 1.0, near, x=1, y=-15)},
        domain="POINT",
    ).outputs[0]
    coarse = t.node(
        "GeometryNodeSetPosition", 1.5, -12, {"Geometry": coarse, "Position": world}
    ).outputs[0]
    coarse = t.node(
        "GeometryNodeMergeByDistance",
        2,
        -12,
        {
            "Geometry": coarse,
            "Mode": "Connected",
            "Distance": t.math("DIVIDE", inputs["Softness"], COARSE, x=1.5, y=-14),
        },
    ).outputs[0]
    edges = t.node("GeometryNodeInputMeshEdgeVertices", 2, -16).outputs
    length = t.node(
        "GeometryNodeAttributeStatistic",
        2.5,
        -15,
        {
            "Geometry": coarse,
            "Attribute": t.vmath(
                "DISTANCE", edges["Position 1"], edges["Position 2"], x=2.5, y=-16
            ),
        },
        domain="EDGE",
    ).outputs["Mean"]
    rounds_in = t.node(
        "GeometryNodeRepeatInput",
        3,
        -12,
        {"Iterations": blur_iterations(t, inputs["Softness"], length, SOFT_ROUNDS, 2.5, -17)},
    )
    rounds_out = t.node("GeometryNodeRepeatOutput", 7, -12)
    rounds_in.pair_with_output(rounds_out)
    t.connect(coarse, rounds_in.inputs["Geometry"])
    coarse_inward = t.vmath(
        "NORMALIZE", t.attribute(".imprint_inward", "FLOAT_VECTOR", 3, -14), x=3.5, y=-14
    )
    # Sinking less and less away from the pressed points, as on an elastic foundation
    ratio = t.math("DIVIDE", length, inputs["Softness"], x=3, y=-18)
    keep = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", t.math("MULTIPLY", ratio, ratio, x=3.5, y=-18), FADE, x=4, y=-18),
        x=4.5,
        y=-18,
        clamp=True,
    )
    kept = keep_pressed(
        t,
        t.vmath(
            "SCALE",
            t.node(
                "GeometryNodeBlurAttribute",
                4,
                -13,
                {"Value": t.attribute(".imprint_offset", "FLOAT_VECTOR", 3, -13), "Iterations": 1},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
            keep,
            x=4.5,
            y=-13,
        ),
        coarse_inward,
        t.attribute(".imprint_depth", "FLOAT", 3, -15),
        5,
        -13,
    )
    t.connect(
        t.store(rounds_in.outputs["Geometry"], ".imprint_offset", "FLOAT_VECTOR", kept, 6, -12),
        rounds_out.inputs["Geometry"],
    )

    # Back on the mesh, the pressed points as deep
    spread = t.node(
        "GeometryNodeSampleNearestSurface",
        8,
        -13,
        {
            "Mesh": rounds_out.outputs["Geometry"],
            "Value": t.attribute(".imprint_offset", "FLOAT_VECTOR", 7, -14),
            "Group ID": t.attribute(".imprint_island", "INT", 7, -15),
            "Sample Position": world,
            "Sample Group ID": t.attribute(".imprint_island", "INT", 7, -16),
        },
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    geometry = t.node(
        "GeometryNodeStoreNamedAttribute",
        10,
        -11,
        {
            "Geometry": geometry,
            "Name": ".imprint_offset",
            "Value": spread,
            "Selection": near,
        },
        data_type="FLOAT_VECTOR",
        domain="POINT",
    ).outputs[0]

    # Smoothed over the size of the faces of the copy, not to show them, the pressed points as deep
    # along the normals smoothed as much, not to tear apart the finer details as the piping
    iterations = blur_iterations(t, length, spacing, SMOOTH_ITERATIONS, 9.5, -15)
    geometry = t.store(
        geometry,
        ".imprint_smooth",
        "FLOAT_VECTOR",
        t.vmath(
            "NORMALIZE",
            t.node(
                "GeometryNodeBlurAttribute",
                10,
                -16,
                {"Value": inward, "Iterations": iterations},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
            x=10.5,
            y=-16,
        ),
        10.5,
        -11,
    )
    smooth = t.attribute(".imprint_smooth", "FLOAT_VECTOR", 11, -16)
    smoothed = t.node(
        "GeometryNodeBlurAttribute",
        10.5,
        -12,
        {
            "Value": t.attribute(".imprint_offset", "FLOAT_VECTOR", 10, -13),
            "Iterations": iterations,
        },
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    geometry = t.store(
        geometry,
        ".imprint_offset",
        "FLOAT_VECTOR",
        keep_pressed(t, smoothed, smooth, depth, 11, -13),
        12,
        -11,
    )

    for i in range(PUSH_ROUNDS):
        offset = t.attribute(".imprint_offset", "FLOAT_VECTOR", 7 + 3 * i, -13)
        # In all at most as deep as the Depth
        left = t.math(
            "MAXIMUM",
            t.math(
                "SUBTRACT",
                inputs["Depth"],
                t.vmath("DOT_PRODUCT", offset, smooth, x=7 + 3 * i, y=-18),
                x=7.5 + 3 * i,
                y=-18,
            ),
            0.0,
            x=8 + 3 * i,
            y=-18,
        )
        deeper = pressed_depth(
            t,
            colliders,
            t.vmath("ADD", world, offset, x=7 + 3 * i, y=-14),
            t.vmath("SCALE", smooth, -1.0, x=7 + 3 * i, y=-17),
            reach,
            left,
            7 + 3 * i,
            -16,
        )
        geometry = t.store(
            geometry,
            ".imprint_offset",
            "FLOAT_VECTOR",
            t.vmath(
                "ADD",
                offset,
                t.vmath("SCALE", smooth, deeper, x=8 + 3 * i, y=-13),
                x=9 + 3 * i,
                y=-12,
            ),
            9 + 3 * i,
            -11,
        )
    # Bulging around the pressed points over the Rim Width, the Rim being the share of the pressed
    # volume moved into the ring around them
    offset = t.attribute(".imprint_offset", "FLOAT_VECTOR", 13, -13)
    iterations = blur_iterations(t, inputs["Rim Width"], spacing, RIM_ITERATIONS, 13, -18)
    pressed = t.math("GREATER_THAN", depth, 0.0, x=13, y=-17)

    def blur(value, y):
        return t.node(
            "GeometryNodeBlurAttribute",
            14,
            y,
            {"Value": value, "Iterations": iterations},
            data_type="FLOAT",
        ).outputs[0]

    # Rising from the pressed points, peaking at a third of the Rim Width: the pressed share of the
    # points around, a half next to them, from 1 there to 0 at the Rim Width
    out = t.math(
        "SUBTRACT",
        1.0,
        t.math("MULTIPLY", blur(pressed, -17), 2.0, x=14.5, y=-17),
        x=15,
        y=-17,
        clamp=True,
    )
    ring = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            out,
            t.math("POWER", t.math("SUBTRACT", 1.0, out, x=15, y=-19), 2.0, x=15.5, y=-19),
            x=16,
            y=-18,
        ),
        t.math("MULTIPLY", t.math("SUBTRACT", 1.0, pressed, x=14, y=-20), 6.75, x=15, y=-20),
        x=16.5,
        y=-17,
    )
    geometry = t.store(geometry, ".imprint_ring", "FLOAT", ring, 15, -11)
    ring = t.attribute(".imprint_ring", "FLOAT", 15.5, -17)
    bulge = t.math(
        "MULTIPLY",
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", ring, blur(depth, -14), x=15, y=-14),
            t.math("MAXIMUM", blur(ring, -15), 1e-6, x=15, y=-15),
            x=15.5,
            y=-14,
        ),
        inputs["Rim"],
        x=16,
        y=-14,
    )
    # Smoothed not to rise all at once next to the pressed points, then up to the Colliders above,
    # as against the body
    bulge = t.math(
        "MULTIPLY", blur(bulge, -16), t.math("SUBTRACT", 1.0, pressed, x=15, y=-21), x=16, y=-16
    )
    outward = t.vmath("SCALE", smooth, -1.0, x=16, y=-16)
    hit = t.node(
        "GeometryNodeRaycast",
        16.5,
        -16,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath("ADD", world, offset, x=16, y=-15),
            "Ray Direction": outward,
            "Ray Length": bulge,
        },
    ).outputs
    bulge = t.node(
        "GeometryNodeSwitch",
        17,
        -14,
        {"Switch": hit["Is Hit"], "False": bulge, "True": hit["Hit Distance"]},
        input_type="FLOAT",
    ).outputs[0]
    bulged = t.vmath("ADD", offset, t.vmath("SCALE", outward, bulge, x=17, y=-15), x=17.5, y=-13)
    return t.store(geometry, ".imprint_offset", "FLOAT_VECTOR", bulged, 18, -11)


def random(t, low, high, identifier, seed, x, y, data_type="FLOAT"):
    return t.node(
        "FunctionNodeRandomValue",
        x,
        y,
        {"Min": low, "Max": high, "ID": identifier, "Seed": seed},
        data_type=data_type,
    ).outputs[0]


def build_debris(t, inputs, geometry, colliders, to_world, to_local, spacing, detail):
    """Chunks of the mesh where the Colliders leave the imprints, sticking to them for a while,
    then falling, tumbling and bouncing onto the mesh, simulated from the Start Frame"""
    t.section("Debris", row=True)
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    world = t.node(
        "FunctionNodeTransformPoint",
        1,
        -5,
        {"Vector": t.node("GeometryNodeInputPosition", 0, -5).outputs[0], "Transform": to_world},
    ).outputs[0]
    ground = t.node(
        "GeometryNodeTransform",
        1,
        0,
        {"Geometry": geometry, "Mode": "Matrix", "Transform": to_world},
    ).outputs[0]
    # Of the material where they come from
    emitted = t.store(
        geometry,
        ".imprint_debris_material",
        "INT",
        t.node("GeometryNodeInputMaterialIndex", 1, -7).outputs[0],
        2,
        0,
    )
    emitted = t.node(
        "GeometryNodeMeshToPoints",
        3,
        0,
        {
            "Mesh": emitted,
            "Selection": t.math(
                "MULTIPLY",
                started,
                t.attribute(".imprint_released", "BOOLEAN", 1, -9),
                x=2,
                y=-9,
            ),
            "Position": world,
        },
    ).outputs[0]
    # As many chunks per area of the imprints however far apart their points, spread around them,
    # each frame different ones
    ids = t.node("GeometryNodeInputIndex", 3, -4).outputs[0]
    duplicate = t.node(
        "GeometryNodeDuplicateElements",
        3.5,
        0,
        {
            "Geometry": emitted,
            "Amount": t.math(
                "FLOOR",
                t.math(
                    "MULTIPLY_ADD",
                    inputs["Debris Amount"],
                    t.math("MULTIPLY", spacing, spacing, x=2, y=-12),
                    random(t, 0.0, 1.0, ids, frame, 2, -10),
                    x=3,
                    y=-12,
                ),
                x=3.5,
                y=-12,
            ),
        },
        domain="POINT",
    ).outputs["Geometry"]
    jitter = random(
        t,
        (-0.5, -0.5, 0.0),
        (0.5, 0.5, 0.0),
        t.node("GeometryNodeInputIndex", 3.5, -6).outputs[0],
        t.math("ADD", frame, 0.5, x=3.5, y=-7),
        4,
        -6,
        "FLOAT_VECTOR",
    )
    # On the surface, not under the walls of the imprints
    emitted = t.node(
        "GeometryNodeSetPosition",
        4,
        0,
        {
            "Geometry": duplicate,
            "Position": t.node(
                "GeometryNodeProximity",
                4.5,
                -6,
                {
                    "Geometry": ground,
                    "Sample Position": t.vmath(
                        "ADD",
                        t.node("GeometryNodeInputPosition", 4, -8).outputs[0],
                        t.vmath("SCALE", jitter, spacing, x=4, y=-7),
                        x=4.5,
                        y=-7,
                    ),
                },
                target_element="FACES",
            ).outputs["Position"],
        },
    ).outputs[0]
    seed = t.math("MULTIPLY", frame, 7.0, x=3, y=-14)
    ids = t.node("GeometryNodeInputIndex", 3, -15).outputs[0]
    stick = t.math("POWER", random(t, 0.0, 1.0, ids, seed, 4, -14), 2.0, x=5, y=-14)
    for i, (name, data_type, value) in enumerate(
        (
            (".imprint_debris_stick", "FLOAT", t.math("MULTIPLY", stick, DEBRIS_STICK, x=6, y=-14)),
            (
                ".imprint_debris_size",
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    inputs["Debris Size"],
                    random(t, 0.3, 1.0, ids, t.math("ADD", seed, 1, x=4, y=-16), 5, -16),
                    x=6,
                    y=-16,
                ),
            ),
            (
                ".imprint_debris_spin",
                "FLOAT_VECTOR",
                random(
                    t,
                    (-DEBRIS_SPIN,) * 3,
                    (DEBRIS_SPIN,) * 3,
                    ids,
                    t.math("ADD", seed, 2, x=4, y=-18),
                    5,
                    -18,
                    "FLOAT_VECTOR",
                ),
            ),
            (
                ".imprint_debris_rotation",
                "FLOAT_VECTOR",
                random(
                    t,
                    (-3.1416,) * 3,
                    (3.1416,) * 3,
                    ids,
                    t.math("ADD", seed, 3, x=4, y=-20),
                    5,
                    -20,
                    "FLOAT_VECTOR",
                ),
            ),
            (
                ".imprint_debris_shape",
                "INT",
                random(
                    t, 0, DEBRIS_SHAPES - 1, ids, t.math("ADD", seed, 4, x=4, y=-22), 5, -22, "INT"
                ),
            ),
            (
                ".imprint_debris_scale",
                "FLOAT_VECTOR",
                t.node(
                    "ShaderNodeCombineXYZ",
                    6,
                    -24,
                    {
                        "X": 1.0,
                        "Y": random(
                            t, *DEBRIS_FLAT[0], ids, t.math("ADD", seed, 5, x=4, y=-24), 5, -24
                        ),
                        "Z": random(
                            t, *DEBRIS_FLAT[1], ids, t.math("ADD", seed, 6, x=4, y=-26), 5, -26
                        ),
                    },
                ).outputs[0],
            ),
        )
    ):
        emitted = t.store(emitted, name, data_type, value, 4 + i * 0.5, 0)

    sim_in = t.node("GeometryNodeSimulationInput", 7, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 15, 0)
    sim_in.pair_with_output(sim_out)
    state = t.node("GeometryNodeJoinGeometry", 8.5, 0)
    t.connect(
        t.node(
            "GeometryNodeSwitch",
            8,
            0,
            {"Switch": started, "True": sim_in.outputs["Geometry"]},
            input_type="GEOMETRY",
        ).outputs[0],
        state.inputs[0],
    )
    t.connect(emitted, state.inputs[0])
    state = state.outputs[0]

    dt = t.math("MAXIMUM", sim_in.outputs["Delta Time"], 1e-6, x=8, y=-3)
    position = t.node("GeometryNodeInputPosition", 8, -4).outputs[0]
    velocity = t.attribute(".imprint_debris_velocity", "FLOAT_VECTOR", 8, -5)
    size = t.attribute(".imprint_debris_size", "FLOAT", 8, -6)
    # Lifted straight up, not along the slopes of the imprints
    lift = (0.0, 0.0, 1.0)
    left = t.attribute(".imprint_debris_stick", "FLOAT", 8, -8)
    rest = t.attribute(".imprint_debris_rest", "BOOLEAN", 8, -9)
    # Under the Colliders above, as they lift
    sole = t.node(
        "GeometryNodeRaycast",
        9,
        -6,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath(
                "SUBTRACT", position, t.vmath("SCALE", lift, size, x=8.5, y=-10), x=9, y=-10
            ),
            "Ray Direction": lift,
            "Ray Length": t.math("MULTIPLY", inputs["Depth"], DEBRIS_REACH, x=8.5, y=-11),
        },
    ).outputs
    stuck = t.math(
        "MULTIPLY",
        sole["Is Hit"],
        t.math("GREATER_THAN", left, 0.0, x=9, y=-12),
        x=10,
        y=-12,
    )
    held = t.vmath(
        "SUBTRACT",
        sole["Hit Position"],
        t.vmath("SCALE", lift, t.math("MULTIPLY", size, 0.5, x=9.5, y=-13), x=10, y=-13),
        x=10.5,
        y=-6,
    )
    # Falling, bouncing off the mesh and resting below a bounce of its size
    falling = t.vmath(
        "ADD",
        velocity,
        t.vmath("SCALE", (0.0, 0.0, -GRAVITY), dt, x=9, y=-15),
        x=9.5,
        y=-14,
    )
    speed = t.vmath("LENGTH", falling, x=10, y=-16)
    # From its size back, as it may be under the surface as the Colliders leave it
    land = t.node(
        "GeometryNodeRaycast",
        11,
        -15,
        {
            "Target Geometry": ground,
            "Source Position": t.vmath(
                "SUBTRACT",
                position,
                t.vmath("SCALE", t.vmath("NORMALIZE", falling, x=10, y=-20), size, x=10.5, y=-20),
                x=11,
                y=-20,
            ),
            "Ray Direction": falling,
            "Ray Length": t.math(
                "MULTIPLY_ADD", speed, dt, t.math("MULTIPLY", size, 1.5, x=10, y=-18), x=10.5, y=-17
            ),
        },
    ).outputs
    bounced = t.vmath(
        "SCALE",
        t.vmath("REFLECT", falling, land["Hit Normal"], x=12, y=-16),
        BOUNCE,
        x=12.5,
        y=-16,
    )
    settled = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            land["Is Hit"],
            t.math("SUBTRACT", 1.0, stuck, x=12.5, y=-20),
            x=13,
            y=-20,
        ),
        t.math(
            "LESS_THAN",
            t.vmath("LENGTH", bounced, x=12.5, y=-18),
            t.math("SQRT", t.math("MULTIPLY", size, 2.0 * GRAVITY, x=12, y=-19), x=12.5, y=-19),
            x=13,
            y=-18,
        ),
        x=13.5,
        y=-18,
    )

    def pick(data_type, *cases, y):
        """Value of the first case whose condition holds, the last one otherwise"""
        value = cases[-1]
        for condition, case in reversed(cases[:-1]):
            value = t.node(
                "GeometryNodeSwitch",
                14,
                y,
                {
                    "Switch": t.math("GREATER_THAN", condition, 0.5, x=13.5, y=y - 1),
                    "False": value,
                    "True": case,
                },
                input_type=data_type,
            ).outputs[0]
        return value

    zero = (0.0, 0.0, 0.0)
    capture = t.node("GeometryNodeCaptureAttribute", 14.5, 0, {"Geometry": state}, domain="POINT")
    values = {
        ("position", "VECTOR"): pick(
            "VECTOR",
            (rest, position),
            (stuck, held),
            (
                land["Is Hit"],
                t.vmath(
                    "ADD",
                    land["Hit Position"],
                    t.vmath(
                        "SCALE",
                        land["Hit Normal"],
                        t.math("MULTIPLY", size, 0.5, x=12, y=-21),
                        x=12.5,
                        y=-21,
                    ),
                    x=13,
                    y=-21,
                ),
            ),
            t.vmath("ADD", position, t.vmath("SCALE", falling, dt, x=12, y=-23), x=13, y=-23),
            y=-2,
        ),
        ("velocity", "VECTOR"): pick(
            "VECTOR",
            (t.math("MAXIMUM", rest, settled, x=13, y=-25), zero),
            # Dropping off, not thrown up by the Colliders lifting
            (
                stuck,
                t.vmath(
                    "MINIMUM",
                    t.vmath(
                        "DIVIDE",
                        t.vmath("SUBTRACT", held, position, x=12, y=-26),
                        dt,
                        x=12.5,
                        y=-26,
                    ),
                    (FAR, FAR, 0.0),
                    x=13,
                    y=-26,
                ),
            ),
            (land["Is Hit"], bounced),
            falling,
            y=-6,
        ),
        ("stick", "FLOAT"): t.math(
            "MULTIPLY",
            t.math("SUBTRACT", left, dt, x=12, y=-28),
            stuck,
            x=13,
            y=-28,
        ),
        ("rest", "BOOLEAN"): t.math("MAXIMUM", rest, settled, x=13, y=-29),
        ("rotation", "VECTOR"): t.vmath(
            "ADD",
            t.attribute(".imprint_debris_rotation", "FLOAT_VECTOR", 12, -31),
            t.vmath(
                "SCALE",
                t.attribute(".imprint_debris_spin", "FLOAT_VECTOR", 12, -32),
                t.math(
                    "MULTIPLY",
                    dt,
                    t.math(
                        "SUBTRACT",
                        1.0,
                        t.math("MAXIMUM", rest, stuck, x=12, y=-34),
                        x=12.5,
                        y=-34,
                    ),
                    x=13,
                    y=-33,
                ),
                x=13.5,
                y=-32,
            ),
            x=14,
            y=-31,
        ),
    }
    for (name, socket_type), value in values.items():
        capture.capture_items.new(socket_type, name)
        t.connect(value, capture.inputs[name])
    state = t.node(
        "GeometryNodeSetPosition",
        15,
        0,
        {"Geometry": capture.outputs["Geometry"], "Position": capture.outputs["position"]},
    ).outputs[0]
    for i, (name, data_type) in enumerate(
        (
            ("velocity", "FLOAT_VECTOR"),
            ("stick", "FLOAT"),
            ("rest", "BOOLEAN"),
            ("rotation", "FLOAT_VECTOR"),
        )
    ):
        state = t.store(
            state, f".imprint_debris_{name}", data_type, capture.outputs[name], 15.5 + i * 0.5, 0
        )
    # Gone if falling through the mesh
    bottom = t.node(
        "ShaderNodeSeparateXYZ",
        15.5,
        -4,
        {0: t.node("GeometryNodeBoundBox", 15, -4, {"Geometry": ground}).outputs["Min"]},
    ).outputs["Z"]
    state = t.node(
        "GeometryNodeDeleteGeometry",
        17.5,
        0,
        {
            "Geometry": state,
            "Selection": t.math(
                "LESS_THAN",
                t.node(
                    "ShaderNodeSeparateXYZ",
                    16,
                    -5,
                    {0: t.node("GeometryNodeInputPosition", 15.5, -5).outputs[0]},
                ).outputs["Z"],
                t.math(
                    "SUBTRACT",
                    bottom,
                    t.math("MULTIPLY", inputs["Depth"], DEBRIS_REACH, x=16, y=-6),
                    x=16.5,
                    y=-4,
                ),
                x=17,
                y=-4,
            ),
        },
        domain="POINT",
    ).outputs[0]
    t.connect(state, sim_out.inputs["Geometry"])

    # Dented flattened icospheres, as the mesh fully tinted, flat shaded
    shapes = t.node("GeometryNodeGeometryToInstance", 17, -4)
    sphere = t.node(
        "GeometryNodeMeshIcoSphere", 16, -4, {"Radius": 0.5, "Subdivisions": 1}
    ).outputs["Mesh"]
    for i in range(DEBRIS_SHAPES):
        t.connect(
            t.node(
                "GeometryNodeSetPosition",
                16.5,
                -4 - i,
                {
                    "Geometry": sphere,
                    "Offset": t.vmath(
                        "SCALE",
                        t.node("GeometryNodeInputNormal", 16, -5 - i).outputs["Normal"],
                        random(
                            t,
                            -DEBRIS_DENT * 0.5,
                            DEBRIS_DENT * 0.5,
                            t.node("GeometryNodeInputIndex", 15.5, -6 - i).outputs[0],
                            i,
                            16,
                            -6 - i,
                        ),
                        x=16.5,
                        y=-5 - i,
                    ),
                },
            ).outputs[0],
            shapes.inputs[0],
        )
    chunks = t.node(
        "GeometryNodeInstanceOnPoints",
        18,
        0,
        {
            "Points": sim_out.outputs["Geometry"],
            "Instance": shapes.outputs[0],
            "Pick Instance": True,
            "Instance Index": t.attribute(".imprint_debris_shape", "INT", 17, -2),
            "Rotation": t.node(
                "FunctionNodeEulerToRotation",
                17.5,
                -3,
                {0: t.attribute(".imprint_debris_rotation", "FLOAT_VECTOR", 17, -3)},
            ).outputs[0],
            "Scale": t.vmath(
                "SCALE",
                t.attribute(".imprint_debris_scale", "FLOAT_VECTOR", 17, -5),
                t.attribute(".imprint_debris_size", "FLOAT", 17, -6),
                x=17.5,
                y=-5,
            ),
        },
    ).outputs[0]
    chunks = t.node("GeometryNodeRealizeInstances", 19, 0, {"Geometry": chunks}).outputs[0]
    chunks = t.node(
        "GeometryNodeTransform",
        20,
        0,
        {"Geometry": chunks, "Mode": "Matrix", "Transform": to_local},
    ).outputs[0]
    chunks = t.node(
        "GeometryNodeSetShadeSmooth", 21, 0, {"Mesh": chunks, "Shade Smooth": False}, domain="FACE"
    ).outputs[0]
    rgb = t.node("FunctionNodeSeparateColor", 21, -2, {0: inputs["Color"]}).outputs
    tinted = t.node(
        "FunctionNodeCombineColor",
        22,
        -2,
        {
            "Red": rgb["Red"],
            "Green": rgb["Green"],
            "Blue": rgb["Blue"],
            "Alpha": t.math("SUBTRACT", 1.0, inputs["Tint"], x=21.5, y=-3),
        },
    ).outputs[0]
    chunks = t.store(chunks, "imprint", "FLOAT_COLOR", tinted, 22, 0)
    return t.store(chunks, "imprint_detail", "FLOAT_VECTOR", detail, 22.5, 0)


def in_box(t, box, position, margin, x, y):
    """Whether the position is in the bounding box grown by the margin"""
    low = t.vmath(
        "SUBTRACT", position, t.vmath("SUBTRACT", box["Min"], margin, x=x, y=y), x=x + 1, y=y
    )
    high = t.vmath(
        "SUBTRACT", t.vmath("ADD", box["Max"], margin, x=x, y=y - 1), position, x=x + 1, y=y - 1
    )
    xyz = t.node(
        "ShaderNodeSeparateXYZ", x + 2, y, {0: t.vmath("MINIMUM", low, high, x=x + 1.5, y=y)}
    ).outputs
    return t.math(
        "GREATER_THAN",
        t.math(
            "MINIMUM",
            t.math("MINIMUM", xyz["X"], xyz["Y"], x=x + 3, y=y),
            xyz["Z"],
            x=x + 4,
            y=y,
        ),
        0.0,
        x=x + 5,
        y=y,
    )


def keep_pressed(t, offset, inward, depth, x, y):
    """Offset moving the pressed points at least as deep along their inward normal"""
    short = t.math(
        "MAXIMUM",
        t.math("SUBTRACT", depth, t.vmath("DOT_PRODUCT", offset, inward, x=x, y=y), x=x + 0.5, y=y),
        0.0,
        x=x + 1,
        y=y,
    )
    return t.vmath("ADD", offset, t.vmath("SCALE", inward, short, x=x + 1, y=y - 1), x=x + 1.5, y=y)


def shallowest_neighbor(t, value, x, y):
    """Smallest value of the points next to each point, to fill the single points the rays pass
    by, as between the toes"""
    neighbor = t.node(
        "GeometryNodeFieldAtIndex",
        x + 2,
        y,
        {
            "Value": value,
            "Index": t.node(
                "GeometryNodeVertexOfCorner",
                x + 1,
                y - 1,
                {
                    "Corner Index": t.node(
                        "GeometryNodeOffsetCornerInFace", x, y - 1, {"Offset": 1}
                    ).outputs[0]
                },
            ).outputs[0],
        },
        data_type="FLOAT",
        domain="POINT",
    ).outputs[0]
    smallest = t.node(
        "GeometryNodeFieldMinAndMax",
        x + 3,
        y,
        {
            "Value": neighbor,
            "Group ID": t.node("GeometryNodeVertexOfCorner", x + 2, y - 2).outputs[0],
        },
        data_type="FLOAT",
        domain="CORNER",
    ).outputs["Min"]
    return t.node(
        "GeometryNodeFieldOnDomain",
        x + 4,
        y,
        {"Value": smallest},
        data_type="FLOAT",
        domain="CORNER",
    ).outputs[0]


def build_lasting(t, inputs, geometry, live):
    """Points pressed since the Start Frame at the positions of the mesh subdivided near the
    Colliders, the same at each frame: their deepest depth filling back, their depth now and
    whether the Colliders left them now"""
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
    # Filling back by the Depth in the Recovery, none without it
    fill = t.math(
        "MULTIPLY",
        t.math(
            "DIVIDE",
            t.math("MULTIPLY", sim_in.outputs["Delta Time"], inputs["Depth"], x=3, y=-4),
            inputs["Recovery"],
            x=4,
            y=-4,
        ),
        started,
        x=4.5,
        y=-4,
    )
    position = t.node("GeometryNodeInputPosition", 3, -6).outputs[0]
    index = t.node(
        "GeometryNodeSampleNearest", 4, -6, {"Geometry": state, "Sample Position": position}
    ).outputs[0]

    def at(name, y):
        return t.node(
            "GeometryNodeSampleIndex",
            5,
            y,
            {"Geometry": state, "Value": t.attribute(name, "FLOAT", 4.5, y - 1), "Index": index},
            data_type="FLOAT",
        ).outputs[0]

    same = t.math(
        "LESS_THAN",
        t.vmath(
            "DISTANCE",
            t.node(
                "GeometryNodeSampleIndex",
                5,
                -6,
                {"Geometry": state, "Value": position, "Index": index},
                data_type="FLOAT_VECTOR",
            ).outputs[0],
            position,
            x=5.5,
            y=-6,
        ),
        MATCH,
        x=6,
        y=-6,
    )
    kept = t.math(
        "MAXIMUM",
        live,
        t.math(
            "SUBTRACT",
            t.math("MULTIPLY", at(".imprint_kept", -8), same, x=5.5, y=-8),
            fill,
            x=6,
            y=-8,
        ),
        x=6.5,
        y=-8,
    )
    released = t.math(
        "MULTIPLY",
        t.math(
            "GREATER_THAN",
            t.math("MULTIPLY", at(".imprint_live", -10), same, x=5.5, y=-10),
            0.0,
            x=6,
            y=-10,
        ),
        t.math("LESS_THAN", live, 1e-9, x=6, y=-11),
        x=6.5,
        y=-10,
    )
    # The points of the mesh still pressed or left now, in place of those in the state
    for i, (name, data_type, value) in enumerate(
        (
            (".imprint_kept", "FLOAT", kept),
            (".imprint_released", "BOOLEAN", released),
        )
    ):
        geometry = t.store(geometry, name, data_type, value, 7 + i * 0.5, 0)
    kept = t.attribute(".imprint_kept", "FLOAT", 8, -2)
    released = t.attribute(".imprint_released", "BOOLEAN", 8, -3)
    pressed = t.node(
        "GeometryNodeMeshToPoints",
        9,
        0,
        {
            "Mesh": geometry,
            "Selection": t.math(
                "GREATER_THAN",
                t.math("MAXIMUM", t.math("MAXIMUM", kept, live, x=8.5, y=-2), released, x=9, y=-2),
                0.0,
                x=9.5,
                y=-2,
            ),
        },
    ).outputs[0]
    # The others filling back, left now if pressed before
    near = t.node(
        "GeometryNodeProximity",
        7,
        -14,
        {"Geometry": geometry, "Sample Position": position},
        target_element="POINTS",
    ).outputs
    others = t.node(
        "GeometryNodeDeleteGeometry",
        8,
        -13,
        {
            "Geometry": state,
            "Selection": t.math(
                "MULTIPLY",
                near["Is Valid"],
                t.math("LESS_THAN", near["Distance"], MATCH, x=7.5, y=-15),
                x=8,
                y=-15,
            ),
        },
        domain="POINT",
    ).outputs[0]
    left = t.attribute(".imprint_live", "FLOAT", 8, -17)
    for i, (name, data_type, value) in enumerate(
        (
            (
                ".imprint_kept",
                "FLOAT",
                t.math(
                    "SUBTRACT",
                    t.attribute(".imprint_kept", "FLOAT", 8, -18),
                    fill,
                    x=8.5,
                    y=-18,
                    clamp=True,
                ),
            ),
            (".imprint_released", "BOOLEAN", t.math("GREATER_THAN", left, 0.0, x=8.5, y=-17)),
            (".imprint_live", "FLOAT", 0.0),
        )
    ):
        others = t.store(others, name, data_type, value, 8.5 + i * 0.5, -13)
    others = t.node(
        "GeometryNodeDeleteGeometry",
        10,
        -13,
        {
            "Geometry": others,
            "Selection": t.math(
                "LESS_THAN",
                t.math(
                    "MAXIMUM",
                    t.attribute(".imprint_kept", "FLOAT", 9.5, -15),
                    t.attribute(".imprint_released", "BOOLEAN", 9.5, -16),
                    x=10,
                    y=-15,
                ),
                1e-9,
                x=10.5,
                y=-15,
            ),
        },
        domain="POINT",
    ).outputs[0]
    joined = t.node("GeometryNodeJoinGeometry", 11, 0)
    for part in (others, pressed):
        t.connect(part, joined.inputs[0])
    t.connect(joined.outputs[0], sim_out.inputs["Geometry"])
    return sim_out.outputs["Geometry"]


def refine(t, mesh, levels, to_world, box, margin, around, spread, x, y):
    """The mesh with its faces within the margin of the box, or the spread of the points around,
    subdivided again by the levels, welded to the others; the same points at each frame where
    subdivided"""
    start = t.node("GeometryNodeRepeatInput", x, y, {"Iterations": levels})
    end = t.node("GeometryNodeRepeatOutput", x + 6, y)
    start.pair_with_output(end)
    t.connect(mesh, start.inputs["Geometry"])
    position = t.node("GeometryNodeInputPosition", x, y - 2).outputs[0]
    center = t.node(
        "FunctionNodeTransformPoint",
        x + 1,
        y - 2,
        {
            "Vector": t.node(
                "GeometryNodeFieldOnDomain",
                x + 0.5,
                y - 2,
                {"Value": position},
                data_type="FLOAT_VECTOR",
                domain="FACE",
            ).outputs[0],
            "Transform": to_world,
        },
    ).outputs[0]
    # Farthest point of the faces from their center, at most their longest edge, halved each time
    ends = t.node("GeometryNodeInputMeshEdgeVertices", x - 1, y - 4).outputs
    longest = t.node(
        "GeometryNodeAttributeStatistic",
        x,
        y - 4,
        {
            "Geometry": mesh,
            "Attribute": t.vmath(
                "DISTANCE",
                *(
                    t.node(
                        "FunctionNodeTransformPoint",
                        x - 0.5,
                        y - 4 - i,
                        {"Vector": ends[f"Position {i + 1}"], "Transform": to_world},
                    ).outputs[0]
                    for i in range(2)
                ),
                x=x - 0.25,
                y=y - 4,
            ),
        },
        domain="EDGE",
    ).outputs["Max"]
    radius = t.math(
        "MULTIPLY",
        longest,
        t.math("POWER", 0.5, start.outputs["Iteration"], x=x + 1, y=y - 5),
        x=x + 1.5,
        y=y - 4,
    )
    reach = t.math("ADD", margin, radius, x=x + 2.5, y=y - 4)
    inside = in_box(t, box, center, reach, x + 2, y - 6)
    if around is not None:
        # Not near anything without points, as the distance to none is 0
        near = t.node(
            "GeometryNodeProximity",
            x + 2,
            y - 8,
            {"Geometry": around, "Sample Position": center},
            target_element="POINTS",
        ).outputs
        inside = t.math(
            "MAXIMUM",
            inside,
            t.math(
                "MULTIPLY",
                near["Is Valid"],
                t.math(
                    "LESS_THAN",
                    near["Distance"],
                    t.math("ADD", spread, radius, x=x + 2, y=y - 9),
                    x=x + 2.5,
                    y=y - 8,
                ),
                x=x + 3,
                y=y - 8,
            ),
            x=x + 3.5,
            y=y - 6,
        )
    geometry = t.store(
        start.outputs["Geometry"], ".imprint_refine", "FLOAT", inside, x + 3, y, domain="FACE"
    )
    # The points between subdivided faces and the others, welded back at the end
    share = t.attribute(".imprint_refine", "FLOAT", x + 3, y - 10)
    geometry = t.store(
        geometry,
        ".imprint_seam",
        "BOOLEAN",
        t.math(
            "MAXIMUM",
            t.attribute(".imprint_seam", "BOOLEAN", x + 3, y - 12),
            t.math(
                "MULTIPLY",
                t.math("GREATER_THAN", share, 0.001, x=x + 3.5, y=y - 10),
                t.math("LESS_THAN", share, 0.999, x=x + 3.5, y=y - 11),
                x=x + 4,
                y=y - 10,
            ),
            x=x + 4.5,
            y=y - 10,
        ),
        x + 3.5,
        y,
    )
    parts = t.node(
        "GeometryNodeSeparateGeometry",
        x + 4,
        y,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "GREATER_THAN",
                t.attribute(".imprint_refine", "FLOAT", x + 3.5, y - 12),
                0.5,
                x=x + 4,
                y=y - 12,
            ),
        },
        domain="FACE",
    ).outputs
    joined = t.node("GeometryNodeJoinGeometry", x + 5, y)
    for part in (
        t.node(
            "GeometryNodeSubdivideMesh", x + 4.5, y, {"Mesh": parts["Selection"], "Level": 1}
        ).outputs[0],
        parts["Inverted"],
    ):
        t.connect(part, joined.inputs[0])
    t.connect(joined.outputs[0], end.inputs["Geometry"])
    return t.node(
        "GeometryNodeMergeByDistance",
        x + 7,
        y,
        {
            "Geometry": end.outputs["Geometry"],
            "Selection": t.attribute(".imprint_seam", "BOOLEAN", x + 6.5, y - 2),
            "Distance": MATCH,
        },
    ).outputs[0]


def build_tint():
    """The color multiplied by the color of the imprints, from the attribute of the modifier"""
    ng = bpy.data.node_groups.new(TINT, "ShaderNodeTree")
    add_input(ng, "Color", "NodeSocketColor", default_value=(0.8, 0.8, 0.8, 1.0))
    add_output(ng, "Color", "NodeSocketColor")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    imprint = t.node(
        "ShaderNodeAttribute", 0, -2, attribute_type="GEOMETRY", attribute_name="imprint"
    ).outputs
    # Uneven by the noise of the strength and scale of the detail, none without the attribute
    detail = t.node(
        "ShaderNodeSeparateXYZ",
        -1,
        -8,
        {
            0: t.node(
                "ShaderNodeAttribute",
                -2,
                -8,
                attribute_type="GEOMETRY",
                attribute_name="imprint_detail",
            ).outputs["Vector"]
        },
    ).outputs
    noise = t.node(
        "ShaderNodeTexNoise",
        0,
        -8,
        {
            "Vector": t.vmath(
                "SCALE",
                t.node("ShaderNodeTexCoord", -1, -10).outputs["Object"],
                detail["Y"],
                x=-0.5,
                y=-10,
            ),
            "Scale": 1.0,
            "Detail": DETAIL_OCTAVES,
            "Roughness": 0.6,
        },
    ).outputs["Fac"]
    uneven = t.math(
        "MULTIPLY_ADD",
        t.math("SUBTRACT", noise, 0.5, x=0.5, y=-8),
        t.math("MULTIPLY", detail["X"], DETAIL_CONTRAST, x=0.5, y=-9),
        1.0,
        x=1,
        y=-8,
    )
    tinted = t.node(
        "ShaderNodeMix",
        2,
        0,
        {
            "Factor": t.math("SUBTRACT", 1.0, imprint["Alpha"], x=1, y=-3, clamp=True),
            "A": inputs["Color"],
            "B": t.vmath(
                "SCALE",
                imprint["Color"],
                t.math("MAXIMUM", uneven, 0.0, x=1.5, y=-8),
                x=1.5,
                y=-6,
            ),
        },
        data_type="RGBA",
        blend_type="MULTIPLY",
    ).outputs
    t.node("NodeGroupOutput", 3, 0, {"Color": next(s for s in tinted if s.type == "RGBA")})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_tint()), fake_user=True)
