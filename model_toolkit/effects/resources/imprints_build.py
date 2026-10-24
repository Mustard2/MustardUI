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
# Blur iterations of the rim, at most
RIM_ITERATIONS = 200
# Depth of the imprints tinted fully, relative to the Depth
TINT_DEPTH = 0.4
# Depth of the imprints the rim fades out to, relative to the Depth, not to rise inside them
RIM_DEPTH = 0.1


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
        max_value=8,
        description="Subdivisions of the mesh before the imprints, for detailed ones",
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
        description="Height of the rim pushed up around the imprints, relative to their depth, "
        "negative for a soft surface sinking around them",
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
    arrange_interface(ng, [(None, "Lasting", False, "Lasting", ["Start Frame", "Recovery"])])

    t = Tree(ng)
    t.section("Colliders")
    inputs = t.node("NodeGroupInput", -2, 0).outputs
    geometry = t.node(
        "GeometryNodeSubdivideMesh",
        -1,
        0,
        {"Mesh": inputs["Geometry"], "Level": inputs["Subdivisions"]},
    ).outputs[0]
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

    t.section("Imprint")
    reach = t.math("MULTIPLY", inputs["Depth"], REACH, x=3, y=-6)
    # Only the points near the Colliders cast a ray
    box = t.node("GeometryNodeBoundBox", 3, -8, {"Geometry": colliders}).outputs
    low = t.vmath("SUBTRACT", world, t.vmath("SUBTRACT", box["Min"], reach, x=4, y=-9), x=5, y=-8)
    high = t.vmath("SUBTRACT", t.vmath("ADD", box["Max"], reach, x=4, y=-10), world, x=5, y=-10)
    xyz = t.node(
        "ShaderNodeSeparateXYZ", 6, -9, {0: t.vmath("MINIMUM", low, high, x=5.5, y=-9)}
    ).outputs
    near = t.math(
        "GREATER_THAN",
        t.math("MINIMUM", t.math("MINIMUM", xyz["X"], xyz["Y"], x=7, y=-9), xyz["Z"], x=8, y=-9),
        0.0,
        x=9,
        y=-9,
    )
    # Up from under the surface, to the lowest Collider surface below it
    ray = t.node(
        "GeometryNodeRaycast",
        5,
        -5,
        {
            "Target Geometry": colliders,
            "Source Position": t.vmath(
                "SUBTRACT", world, t.vmath("SCALE", normal, reach, x=4, y=-5), x=4.5, y=-5
            ),
            "Ray Direction": normal,
            "Ray Length": reach,
        },
    ).outputs
    depth = t.math(
        "MINIMUM",
        t.math("SUBTRACT", reach, ray["Hit Distance"], x=6, y=-5),
        inputs["Depth"],
        x=7,
        y=-5,
    )
    depth = t.math("MULTIPLY", depth, ray["Is Hit"], x=8, y=-5)
    depth = t.math("MULTIPLY", depth, inputs["Mask"], x=9, y=-5)
    store = t.node(
        "GeometryNodeStoreNamedAttribute",
        10,
        0,
        {"Geometry": geometry, "Name": ".imprint_live", "Value": depth, "Selection": near},
        data_type="FLOAT",
        domain="POINT",
    )
    geometry = store.outputs["Geometry"]
    live = t.attribute(".imprint_live", "FLOAT", 11, -2)

    t.section("Lasting", row=True)
    depth = build_lasting(t, inputs, geometry, live)

    t.section("Displacement", row=True)
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
    spread = t.math("DIVIDE", inputs["Rim Width"], length, x=6, y=-6)
    iterations = t.math(
        "MINIMUM",
        t.math("MULTIPLY", t.math("MULTIPLY", spread, spread, x=7, y=-6), 2.0, x=8, y=-6),
        RIM_ITERATIONS,
        x=9,
        y=-6,
    )
    blurred = t.node(
        "GeometryNodeBlurAttribute",
        10,
        -5,
        {"Value": depth, "Iterations": t.math("ROUND", iterations, x=9.5, y=-7)},
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
    height = t.math("MULTIPLY", height, t.math("MAXIMUM", noise, 0.0, x=13, y=-9), x=15, y=-4)
    geometry = t.store(geometry, ".imprint_height", "FLOAT", height, 15.5, 0)
    height = t.attribute(".imprint_height", "FLOAT", 15.5, -2)

    # Smooth where displaced, not to show the faces of the imprints
    geometry = t.node(
        "GeometryNodeSetShadeSmooth",
        16,
        0,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "GREATER_THAN", t.math("ABSOLUTE", height, x=15.5, y=-1), 1e-6, x=16, y=-1
            ),
        },
        domain="FACE",
    ).outputs[0]
    offset = t.node(
        "FunctionNodeTransformDirection",
        16,
        -4,
        {"Direction": t.vmath("SCALE", normal, height, x=15, y=-3), "Transform": to_local},
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSetPosition", 17, 0, {"Geometry": geometry, "Offset": offset}
    ).outputs[0]

    t.section("Attributes", row=True)
    # The amount left untinted in the alpha, 1 as read by the shaders without the attribute
    amount = t.math(
        "DIVIDE",
        depth,
        t.math("MULTIPLY", inputs["Depth"], TINT_DEPTH, x=0, y=-3),
        x=1,
        y=-2,
        clamp=True,
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
    geometry = t.node(
        "GeometryNodeRemoveAttribute",
        4,
        0,
        {"Geometry": geometry, "Pattern Mode": "Wildcard", "Name": ".imprint_*"},
    ).outputs[0]
    t.node("NodeGroupOutput", 5, 0, {"Geometry": geometry})
    t.arrange()
    return ng


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
    """Depth of each point, the deepest since the Start Frame filling back, simulated on points
    by index"""
    frame = t.node("GeometryNodeInputSceneTime", 0, -2).outputs["Frame"]
    started = t.math("GREATER_THAN", frame, inputs["Start Frame"], x=1, y=-2)
    count = t.node("GeometryNodeAttributeDomainSize", 0, 0, {0: geometry}).outputs["Point Count"]
    points = t.node("GeometryNodePoints", 1, 0, {"Count": count}).outputs[0]
    sim_in = t.node("GeometryNodeSimulationInput", 2, 0)
    sim_out = t.node("GeometryNodeSimulationOutput", 6, 0)
    sim_in.pair_with_output(sim_out)
    t.connect(points, sim_in.inputs["Geometry"])
    state = t.node(
        "GeometryNodeSwitch",
        3,
        0,
        {"Switch": started, "False": points, "True": sim_in.outputs["Geometry"]},
        input_type="GEOMETRY",
    ).outputs[0]
    index = t.node("GeometryNodeInputIndex", 3, -2).outputs[0]
    current = t.node(
        "GeometryNodeSampleIndex",
        4,
        -2,
        {"Geometry": geometry, "Value": live, "Index": index},
        data_type="FLOAT",
    ).outputs[0]
    # Filling back by the Depth in the Recovery, none without it
    fill = t.math(
        "DIVIDE",
        t.math("MULTIPLY", sim_in.outputs["Delta Time"], inputs["Depth"], x=3, y=-4),
        inputs["Recovery"],
        x=4,
        y=-4,
    )
    kept = t.math(
        "SUBTRACT",
        t.attribute(".imprint_kept", "FLOAT", 3, -3),
        t.math("MULTIPLY", fill, started, x=4.5, y=-4),
        x=5,
        y=-3,
        clamp=True,
    )
    state = t.store(
        state, ".imprint_kept", "FLOAT", t.math("MAXIMUM", current, kept, x=5.5, y=-2), 5, 0
    )
    t.connect(state, sim_out.inputs["Geometry"])

    # Back on the mesh by index, without Lasting the live depth
    result = t.node(
        "GeometryNodeSampleIndex",
        8,
        -2,
        {
            "Geometry": sim_out.outputs["Geometry"],
            "Value": t.attribute(".imprint_kept", "FLOAT", 7, -3),
            "Index": t.node("GeometryNodeInputIndex", 7, -4).outputs[0],
        },
        data_type="FLOAT",
    ).outputs[0]
    return t.node(
        "GeometryNodeSwitch",
        9,
        -2,
        {"Switch": inputs["Lasting"], "False": live, "True": result},
        input_type="FLOAT",
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
    tinted = t.node(
        "ShaderNodeMix",
        2,
        0,
        {
            "Factor": t.math("SUBTRACT", 1.0, imprint["Alpha"], x=1, y=-3, clamp=True),
            "A": inputs["Color"],
            "B": imprint["Color"],
        },
        data_type="RGBA",
        blend_type="MULTIPLY",
    ).outputs
    t.node("NodeGroupOutput", 3, 0, {"Color": next(s for s in tinted if s.type == "RGBA")})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_tint()), fake_user=True)
