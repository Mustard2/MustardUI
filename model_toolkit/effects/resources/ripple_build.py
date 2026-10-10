# Build ripple.blend: the Ripple node group
# Usage: Blender --background --factory-startup --python ripple_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "ripple.blend"
NODE_GROUP = "MustardUI Ripple"


def build_node_group():
    ng = bpy.data.node_groups.new(NODE_GROUP, "GeometryNodeTree")
    ng.is_modifier = True
    ng.description = (
        "Bulge the mesh along its normals where the flattened sphere of the Control cuts it"
    )

    add_output(ng, "Geometry", "NodeSocketGeometry")
    add_input(ng, "Geometry", "NodeSocketGeometry")
    add_input(
        ng,
        "Control",
        "NodeSocketObject",
        description="Empty whose flattened sphere defines where the ripple appears",
    )
    add_input(
        ng,
        "Strength",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Strength of the ripple",
    )
    add_input(
        ng,
        "Height",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.02,
        min_value=-1.0,
        max_value=1.0,
        description="Displacement along the normals, negative to dent the mesh",
    )
    add_input(
        ng,
        "Smooth",
        "NodeSocketInt",
        default_value=0,
        min_value=0,
        max_value=100,
        description="Iterations smoothing the ripple over the mesh",
    )
    add_input(
        ng,
        "Mask",
        "NodeSocketFloat",
        subtype="FACTOR",
        default_value=1.0,
        min_value=0.0,
        max_value=1.0,
        description="Vertex Group limiting the ripple, e.g. to the soft parts",
    )

    t = Tree(ng, spacing=(200, 160))
    inputs = t.node("NodeGroupInput", -6, 0).outputs

    # Squared distance from the center of the Control, in its space
    info = t.node(
        "GeometryNodeObjectInfo", -5, -2, {"Object": inputs["Control"]}, transform_space="RELATIVE"
    )
    invert = t.node("FunctionNodeInvertMatrix", -4, -2, {"Matrix": info.outputs["Transform"]})
    position = t.node("GeometryNodeInputPosition", -4, -3).outputs["Position"]
    local = t.node(
        "FunctionNodeTransformPoint",
        -3,
        -2,
        {"Vector": position, "Transform": invert.outputs["Matrix"]},
    ).outputs[0]
    distance = t.node(
        "ShaderNodeVectorMath",
        -2,
        -2,
        {0: local, 1: local},
        operation="DOT_PRODUCT",
        label="Squared Distance",
    ).outputs["Value"]

    # Smooth falloff inside the sphere, scaled by the inputs and smoothed over the mesh
    inside = t.math("SUBTRACT", 1.0, distance, x=-1, y=-2, clamp=True)
    falloff = t.node(
        "ShaderNodeMath", 0, -2, {0: inside, 1: 2.0}, operation="POWER", label="Falloff"
    ).outputs[0]
    height = t.math("MULTIPLY", falloff, inputs["Height"], x=1, y=-2)
    height = t.math("MULTIPLY", height, inputs["Strength"], x=1.5, y=-2)
    height = t.math("MULTIPLY", height, inputs["Mask"], x=2, y=-2)
    blur = t.node(
        "GeometryNodeBlurAttribute",
        2.5,
        -2,
        {"Value": height, "Iterations": inputs["Smooth"]},
        data_type="FLOAT",
    )

    normal = t.node("GeometryNodeInputNormal", 2, -3).outputs["Normal"]
    offset = t.vmath("SCALE", normal, blur.outputs["Value"], x=3, y=-2)
    ripple = t.node(
        "GeometryNodeSetPosition", 3, 0, {"Geometry": inputs["Geometry"], "Offset": offset}
    )
    t.node("NodeGroupOutput", 4, 0, {0: ripple.outputs["Geometry"]})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(),), fake_user=True)
