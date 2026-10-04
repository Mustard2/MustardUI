# Build wrap.blend: the Rope and Tape node groups and materials
# Usage: Blender --background --factory-startup --python wrap_build.py [-- out.blend]
import math
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "wrap.blend"
ROPE = "MustardUI Rope"
TAPE = "MustardUI Tape"


def push_out(t, geometry, target, rest, x, y, reach=None):
    """Geometry with the points closer than reach (rest by default) to the target, moved to rest"""
    position = t.node("GeometryNodeInputPosition", x, y - 1).outputs["Position"]
    nearest = t.node("GeometryNodeProximity", x + 1, y - 1, {"Geometry": target})
    normal = t.node("GeometryNodeInputNormal", x, y - 2).outputs["Normal"]
    normal = t.node(
        "GeometryNodeSampleNearestSurface",
        x + 1,
        y - 2,
        {"Mesh": target, "Value": normal},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    normal = t.vmath("NORMALIZE", normal, x=x + 2, y=y - 2)

    away = t.vmath("SUBTRACT", position, nearest.outputs["Position"], x=x + 2, y=y - 1)
    distance = t.vmath("DOT_PRODUCT", away, normal, x=x + 3, y=y - 1)
    inside = t.math("LESS_THAN", distance, reach or rest, x=x + 4, y=y - 1)
    inside = t.node(
        "FunctionNodeBooleanMath",
        x + 5,
        y - 1,
        {0: inside, 1: nearest.outputs["Is Valid"]},
        operation="AND",
    ).outputs[0]
    position = t.node(
        "ShaderNodeVectorMath",
        x + 4,
        y - 2,
        {0: normal, 1: rest, 2: nearest.outputs["Position"]},
        operation="MULTIPLY_ADD",
    ).outputs[0]
    return t.node(
        "GeometryNodeSetPosition",
        x + 6,
        y,
        {"Geometry": geometry, "Selection": inside, "Position": position},
    ).outputs["Geometry"]


def new_wrap_group(name, description):
    """Node group with the inputs of the wrapping, and the panel for the ones of its shape"""
    ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = description

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")

    panel = ng.interface.new_panel("Target")
    add_input(ng, "Target", "NodeSocketObject", panel, description="Mesh to wrap around")
    add_input(
        ng,
        "Target Collection",
        "NodeSocketCollection",
        panel,
        description="Meshes to wrap around, with the Target",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        panel,
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Parts of the targets to wrap around, ignoring the ones with no weight. "
        "Set to a Vertex Group of the targets with the attribute toggle",
    )

    panel = ng.interface.new_panel("Wrap")
    add_input(
        ng,
        "Sample Length",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.02,
        min_value=0.001,
        description="Length of the segments wrapped on the targets, longer to bridge their details",
    )
    add_input(
        ng,
        "Iterations",
        "NodeSocketInt",
        panel,
        default_value=30,
        min_value=0,
        max_value=1000,
        description="Iterations tightening the wrap, sliding it on the targets",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        panel,
        default_value=0,
        min_value=0,
        max_value=100,
        description="Iterations smoothing the tightened wrap, rounding its corners",
    )
    add_input(
        ng,
        "Offset",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.0,
        min_value=-1.0,
        max_value=1.0,
        description="Distance from the targets, negative to sink in",
    )

    panel = ng.interface.new_panel(name.removeprefix("MustardUI "))
    add_input(ng, "Material", "NodeSocketMaterial", panel, description="Material of the wrap")
    return ng, panel


def wrap(t, inputs, rest, spacing):
    """Targets, and the curve wrapped and tightened on them, then smoothed and resampled"""
    # Targets in the space of the curve, without the masked parts
    info = t.node(
        "GeometryNodeObjectInfo", -9, -3, {"Object": inputs["Target"]}, transform_space="RELATIVE"
    )
    collection = t.node(
        "GeometryNodeCollectionInfo",
        -9,
        -5,
        {"Collection": inputs["Target Collection"]},
        transform_space="RELATIVE",
    )
    realize = t.node("GeometryNodeRealizeInstances", -8, -5, {"Geometry": collection.outputs[0]})
    target = t.node("GeometryNodeJoinGeometry", -8, -3)
    for geometry in (realize.outputs[0], info.outputs["Geometry"]):
        t.connect(geometry, target.inputs[0])
    outside = t.math("LESS_THAN", inputs["Mask"], 0.001, x=-7, y=-6)
    target = t.node(
        "GeometryNodeDeleteGeometry",
        -6,
        -3,
        {"Geometry": target.outputs[0], "Selection": outside},
        domain="POINT",
    ).outputs[0]

    resample = t.node(
        "GeometryNodeResampleCurve",
        -6,
        0,
        {"Curve": inputs["Geometry"], "Mode": "Length", "Length": inputs["Sample Length"]},
    )

    # Wrap on the targets, casting rays toward them along smoothed directions to keep the order
    position = t.node("GeometryNodeInputPosition", -6, -1).outputs["Position"]
    nearest = t.node("GeometryNodeProximity", -5, -1, {"Geometry": target})
    toward = t.vmath("SUBTRACT", nearest.outputs["Position"], position, x=-4, y=-1)
    toward = t.vmath("NORMALIZE", toward, x=-3, y=-1)
    toward = t.node(
        "GeometryNodeBlurAttribute",
        -2,
        -1,
        {"Value": toward, "Iterations": 2},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    reach = t.math("MULTIPLY", nearest.outputs["Distance"], 1.5, x=-3, y=-2)
    ray = t.node(
        "GeometryNodeRaycast",
        -1,
        -1,
        {"Target Geometry": target, "Ray Direction": toward, "Ray Length": reach},
    )
    hit = t.node(
        "GeometryNodeBlurAttribute",
        0,
        -1,
        {"Value": ray.outputs["Hit Position"], "Iterations": 2},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    hit = t.node(
        "ShaderNodeVectorMath",
        1,
        -1,
        {0: ray.outputs["Hit Normal"], 1: rest, 2: hit},
        operation="MULTIPLY_ADD",
    ).outputs[0]
    wrapped = t.node(
        "GeometryNodeSetPosition",
        2,
        0,
        {"Geometry": resample.outputs[0], "Selection": ray.outputs["Is Hit"], "Position": hit},
    )

    # Tighten, pulling the points toward their neighbors and out of the targets
    repeat_in = t.node("GeometryNodeRepeatInput", 3, 0, {"Iterations": inputs["Iterations"]})
    repeat_out = t.node("GeometryNodeRepeatOutput", 12, 0)
    repeat_in.pair_with_output(repeat_out)
    t.connect(wrapped.outputs[0], repeat_in.inputs["Geometry"])
    position = t.node("GeometryNodeInputPosition", 3, -2).outputs["Position"]
    blur = t.node(
        "GeometryNodeBlurAttribute",
        4,
        -2,
        {"Value": position, "Weight": 0.5},
        data_type="FLOAT_VECTOR",
    )
    pulled = t.node(
        "GeometryNodeSetPosition",
        5,
        0,
        {"Geometry": repeat_in.outputs["Geometry"], "Position": blur.outputs["Value"]},
    ).outputs["Geometry"]
    t.connect(push_out(t, pulled, target, rest, 5, 0), repeat_out.inputs["Geometry"])

    # Smooth and fine, kept out of the targets
    position = t.node("GeometryNodeInputPosition", 12, -2).outputs["Position"]
    blur = t.node(
        "GeometryNodeBlurAttribute",
        12,
        -1,
        {"Value": position, "Iterations": inputs["Smooth"]},
        data_type="FLOAT_VECTOR",
    )
    smooth = t.node(
        "GeometryNodeSetPosition",
        13,
        -1,
        {"Geometry": repeat_out.outputs["Geometry"], "Position": blur.outputs["Value"]},
    )
    smooth = t.node(
        "GeometryNodeCurveSplineType",
        13,
        0,
        {"Curve": smooth.outputs[0]},
        spline_type="CATMULL_ROM",
    )
    fine = t.node(
        "GeometryNodeResampleCurve",
        14,
        0,
        {"Curve": smooth.outputs[0], "Mode": "Length", "Length": spacing},
    ).outputs[0]
    return target, push_out(t, fine, target, rest, 15, 0)


def finish(t, mesh, inputs, x):
    """Smooth mesh with the Material, to the output"""
    smooth = t.node("GeometryNodeSetShadeSmooth", x, 0, {"Mesh": mesh})
    material = t.node(
        "GeometryNodeSetMaterial",
        x + 1,
        0,
        {"Geometry": smooth.outputs[0], "Material": inputs["Material"]},
    )
    t.node("NodeGroupOutput", x + 2, 0, {0: material.outputs[0]})


def build_rope():
    ng, panel = new_wrap_group(
        ROPE, "Wrap the curve on the targets as a tight rope of twisted strands"
    )
    add_input(
        ng,
        "Radius",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.004,
        min_value=0.0005,
        description="Radius of the rope",
    )
    add_input(
        ng,
        "Twist",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.03,
        description="Length of a full twist of the strands, negative to twist them the other way",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        panel,
        default_value=6,
        min_value=3,
        max_value=64,
        description="Vertices around each strand",
    )

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -10, 0).outputs
    rest = t.math("ADD", inputs["Radius"], inputs["Offset"], x=-7, y=-8)
    spacing = t.math("MULTIPLY", inputs["Radius"], 0.5, x=-7, y=-9)
    _, curve = wrap(t, inputs, rest, spacing)

    # Whole twists along each spline, to join them on cyclic splines
    spline_length = t.node("GeometryNodeSplineLength", 21, -2).outputs["Length"]
    turns = t.math("DIVIDE", spline_length, inputs["Twist"], x=22, y=-2)
    turns = t.math("ROUND", turns, x=23, y=-2)
    factor = t.node("GeometryNodeSplineParameter", 23, -3).outputs["Factor"]
    tilt = t.math("MULTIPLY", turns, factor, x=24, y=-2)
    tilt = t.math("MULTIPLY", tilt, 2 * math.pi, x=25, y=-2)
    tilted = t.node("GeometryNodeSetCurveTilt", 26, 0, {"Curve": curve, "Tilt": tilt})

    # Three strands, touching in the middle of the rope
    strand = t.math("MULTIPLY", inputs["Radius"], 0.5, x=24, y=-5)
    centers = t.node("GeometryNodeMeshCircle", 25, -5, {"Vertices": 3, "Radius": strand})
    circle = t.node(
        "GeometryNodeCurvePrimitiveCircle",
        25,
        -6,
        {"Resolution": inputs["Resolution"], "Radius": strand},
    )
    strands = t.node(
        "GeometryNodeInstanceOnPoints",
        26,
        -5,
        {"Points": centers.outputs[0], "Instance": circle.outputs[0]},
    )
    profile = t.node("GeometryNodeRealizeInstances", 27, -5, {"Geometry": strands.outputs[0]})

    mesh = t.node(
        "GeometryNodeCurveToMesh",
        28,
        0,
        {"Curve": tilted.outputs[0], "Profile Curve": profile.outputs[0], "Fill Caps": True},
    )
    finish(t, mesh.outputs[0], inputs, 29)
    return ng


def build_tape():
    ng, panel = new_wrap_group(TAPE, "Wrap the curve on the targets as a tight tape, flat on them")
    add_input(
        ng,
        "Width",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.03,
        min_value=0.001,
        description="Width of the tape",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        panel,
        subtype="DISTANCE",
        default_value=0.001,
        min_value=0.0,
        description="Thickness of the tape",
    )
    add_input(
        ng,
        "Resolution",
        "NodeSocketInt",
        panel,
        default_value=4,
        min_value=1,
        max_value=64,
        description="Segments across the tape, more to follow the targets closely",
    )

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -10, 0).outputs
    spacing = t.math("DIVIDE", inputs["Width"], inputs["Resolution"], x=-7, y=-9)
    target, curve = wrap(t, inputs, inputs["Offset"], spacing)

    # Flat on the targets, along their smoothed normals
    normal = t.node("GeometryNodeInputNormal", 21, -3).outputs["Normal"]
    normal = t.node(
        "GeometryNodeSampleNearestSurface",
        22,
        -3,
        {"Mesh": target, "Value": normal},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    normal = t.node(
        "GeometryNodeBlurAttribute",
        23,
        -3,
        {"Value": normal, "Iterations": 4},
        data_type="FLOAT_VECTOR",
    ).outputs["Value"]
    normal = t.vmath("NORMALIZE", normal, x=24, y=-3)
    flat = t.node(
        "GeometryNodeSetCurveNormal",
        25,
        0,
        {"Curve": curve, "Mode": "Free", "Normal": normal},
    )

    # Across the curve, as the X of the profile follows its normals, facing out of the targets
    half = t.math("MULTIPLY", inputs["Width"], 0.5, x=23, y=-5)
    start = t.node(
        "ShaderNodeCombineXYZ", 24, -5, {"Y": t.math("MULTIPLY", half, -1.0, x=23, y=-6)}
    )
    end = t.node("ShaderNodeCombineXYZ", 24, -6, {"Y": half})
    line = t.node(
        "GeometryNodeCurvePrimitiveLine",
        25,
        -5,
        {"Start": start.outputs[0], "End": end.outputs[0]},
    )
    count = t.math("ADD", inputs["Resolution"], 1.0, x=25, y=-7)
    profile = t.node(
        "GeometryNodeResampleCurve",
        26,
        -5,
        {"Curve": line.outputs[0], "Mode": "Count", "Count": count},
    )
    ribbon = t.node(
        "GeometryNodeCurveToMesh",
        27,
        0,
        {"Curve": flat.outputs[0], "Profile Curve": profile.outputs[0]},
    ).outputs[0]

    # Conformed to the targets where close to them, then thick away from them
    reach = t.math("MULTIPLY_ADD", inputs["Width"], 0.25, inputs["Offset"], x=27, y=-2)
    ribbon = push_out(t, ribbon, target, inputs["Offset"], 28, 0, reach)
    tape = t.node(
        "GeometryNodeExtrudeMesh",
        34,
        0,
        {"Mesh": ribbon, "Offset Scale": inputs["Thickness"], "Individual": False},
        mode="FACES",
    )
    finish(t, tape.outputs["Mesh"], inputs, 35)
    return ng


def build_material(name, color, roughness, metallic, sheen, scale, strength):
    material = bpy.data.materials.new(name)
    material.node_tree.nodes.clear()
    t = Tree(material.node_tree)

    # Fine fibers
    noise = t.node("ShaderNodeTexNoise", -3, -1, {"Scale": scale, "Detail": 4.0})
    bump = t.node("ShaderNodeBump", -2, -1, {"Strength": strength, "Height": noise.outputs["Fac"]})
    bsdf = t.node(
        "ShaderNodeBsdfPrincipled",
        -1,
        0,
        {
            "Base Color": color,
            "Roughness": roughness,
            "Metallic": metallic,
            "Sheen Weight": sheen,
            "Normal": bump.outputs["Normal"],
        },
    )
    t.node("ShaderNodeOutputMaterial", 1, 0, {"Surface": bsdf.outputs[0]})
    return material


if __name__ == "__main__":
    write(
        RESOURCE,
        (
            build_rope(),
            build_tape(),
            build_material(ROPE, (0.8, 0.74, 0.62, 1.0), 0.85, 0.0, 0.5, 600.0, 0.3),
            build_material(TAPE, (0.5, 0.51, 0.53, 1.0), 0.45, 0.5, 0.0, 300.0, 0.05),
        ),
    )
