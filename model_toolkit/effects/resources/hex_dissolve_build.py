# Build hex_dissolve.blend: the Hex Dissolve shader node group
# Usage: Blender --background --factory-startup --python hex_dissolve_build.py [-- out.blend]
import os
import sys

import bpy

sys.path.append(os.path.dirname(__file__))
from build_utils import Tree, add_input, add_output, write

RESOURCE = "hex_dissolve.blend"
NODE_GROUP = "MustardUI Hex Dissolve"
HEXAGON = "MustardUI Hexagon"

# Size and half size of the cells of the hexagonal grid
CELL = (1.0, 1.732, 0.0)
HALF = (0.5, 0.866, 0.0)


def build_hexagon():
    """Hexagonal cells: distance from the cell border and a random value per cell"""
    ng = bpy.data.node_groups.new(HEXAGON, "ShaderNodeTree")
    add_input(ng, "Vector", "NodeSocketVector", hide_value=True)
    add_input(ng, "Scale", "NodeSocketFloat", default_value=10.0)
    add_output(ng, "Edge", "NodeSocketFloat")
    add_output(ng, "Random", "NodeSocketFloat")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs
    p = t.vmath("ADD", inputs["Vector"], (17.0, 17.0, 17.0), x=1, y=0)
    p = t.vmath("SCALE", p, inputs["Scale"], x=2, y=0)

    # Position in the two staggered grids, and which one has the closest cell center
    a = t.vmath("ADD", p, HALF, x=3, y=1)
    a = t.vmath("MODULO", a, CELL, x=4, y=1)
    a = t.vmath("SUBTRACT", a, HALF, x=5, y=1)
    b = t.vmath("MODULO", p, CELL, x=3, y=-1)
    b = t.vmath("SUBTRACT", b, HALF, x=4, y=-1)
    distance = t.vmath("DOT_PRODUCT", t.vmath("ABSOLUTE", b, x=5, y=-1), HALF, x=6, y=-1)
    in_b = t.math("LESS_THAN", distance, 0.5, x=7, y=-1)
    local = t.node(
        "ShaderNodeMix", 8, 0, {"Factor": in_b, "A": a, "B": b}, data_type="VECTOR"
    ).outputs[1]

    # Hexagonal distance from the cell center, 1 at the center and 0 at the border
    local = t.vmath("ABSOLUTE", local, x=9, y=0)
    x = t.node("ShaderNodeSeparateXYZ", 10, 0, {0: local}).outputs["X"]
    diagonal = t.vmath("DOT_PRODUCT", local, HALF, x=10, y=-1)
    distance = t.math("MAXIMUM", x, diagonal, x=11, y=0)
    edge = t.math("MULTIPLY_ADD", distance, -2.0, 1.0, x=12, y=0, clamp=True)

    # Random value from the center of the cell
    center_a = t.vmath("SNAP", t.vmath("ADD", p, (2.5, 6.0, 0.0), x=3, y=-3), CELL, x=4, y=-3)
    center_b = t.vmath("SNAP", p, CELL, x=4, y=-4)
    center = t.node(
        "ShaderNodeMix", 8, -3, {"Factor": in_b, "A": center_a, "B": center_b}, data_type="VECTOR"
    ).outputs[1]
    random = t.node("ShaderNodeTexWhiteNoise", 9, -3, {0: center}, noise_dimensions="3D")

    t.node("NodeGroupOutput", 13, -1, {"Edge": edge, "Random": random.outputs["Value"]})
    return ng


def build_node_group(hexagon):
    """The shader, transparent inside the distorted sphere of the Control, glowing on its border"""
    ng = bpy.data.node_groups.new(NODE_GROUP, "ShaderNodeTree")
    add_input(ng, "Shader", "NodeSocketShader")
    add_input(
        ng,
        "Control",
        "NodeSocketVector",
        hide_value=True,
        description="Object coordinates of the Control",
    )
    add_input(ng, "Edge Color", "NodeSocketColor", default_value=(0.16, 0.62, 1.0, 1.0))
    add_input(
        ng,
        "Edge Strength",
        "NodeSocketFloat",
        default_value=3.0,
        min_value=0.0,
        description="Emission strength of the edge",
    )
    add_input(
        ng,
        "Edge Width",
        "NodeSocketFloat",
        default_value=0.1,
        min_value=0.0,
        max_value=1.0,
        description="Width of the edge, relative to the Control radius",
    )
    add_input(
        ng,
        "Hexagon Scale",
        "NodeSocketFloat",
        default_value=150.0,
        min_value=0.0,
        description="Number of hexagons along the UV map",
    )
    add_input(
        ng,
        "Distortion",
        "NodeSocketFloat",
        default_value=0.5,
        min_value=0.0,
        description="Distortion of the sphere of the Control",
    )
    add_output(ng, "Shader", "NodeSocketShader")

    t = Tree(ng, spacing=(200, 180))
    inputs = t.node("NodeGroupInput", 0, 0).outputs

    # Distance from the Control, distorted by noise
    noise = t.node(
        "ShaderNodeTexNoise", 1, -3, {"Vector": inputs["Control"], "Scale": 1.0, "Detail": 3.0}
    )
    offset = t.vmath("MULTIPLY_ADD", noise.outputs["Color"], (2.0,) * 3, (-1.0,) * 3, x=2, y=-3)
    offset = t.vmath("MULTIPLY_ADD", offset, inputs["Distortion"], inputs["Control"], x=3, y=-3)
    distance = t.vmath("LENGTH", offset, x=4, y=-3)

    # Large and small hexagons, the small ones with a random offset each
    uv = t.node("ShaderNodeTexCoord", 1, -5).outputs["UV"]
    large_scale = t.math("DIVIDE", inputs["Hexagon Scale"], 30.0, x=1, y=-6)
    small = t.node(
        "ShaderNodeGroup", 2, -5, {0: uv, 1: inputs["Hexagon Scale"]}, node_tree=hexagon
    ).outputs
    large = t.node("ShaderNodeGroup", 2, -7, {0: uv, 1: large_scale}, node_tree=hexagon).outputs
    random = t.math("MULTIPLY_ADD", small["Random"], 2.0, -1.0, x=3, y=-5)
    pattern = t.math("MULTIPLY_ADD", random, 0.633, small["Edge"], x=4, y=-5)
    pattern = t.node(
        "ShaderNodeMix", 5, -6, {"Factor": 0.733, "A": large["Edge"], "B": pattern}
    ).outputs[0]
    pattern = t.math("MULTIPLY_ADD", pattern, 2.0, -1.0, x=6, y=-6)
    distance = t.math("MULTIPLY_ADD", pattern, 0.17, distance, x=7, y=-4)

    # Visible outside the sphere, glowing near its border
    border = t.math("SUBTRACT", distance, 1.0, x=8, y=-4)
    visible = t.math("GREATER_THAN", border, 0.0, x=9, y=-3)
    glow = t.node(
        "ShaderNodeMapRange",
        9,
        -5,
        {"Value": border, "From Max": inputs["Edge Width"], "To Min": 1.0, "To Max": 0.0},
        clamp=True,
    ).outputs[0]
    glow = t.math("MULTIPLY", glow, visible, x=10, y=-4)
    transparent = t.node("ShaderNodeBsdfTransparent", 10, -1).outputs[0]
    shader = t.node(
        "ShaderNodeMixShader", 11, -1, {0: visible, 1: transparent, 2: inputs["Shader"]}
    ).outputs[0]
    emission = t.node(
        "ShaderNodeEmission",
        11,
        -2,
        {"Color": inputs["Edge Color"], "Strength": inputs["Edge Strength"]},
    ).outputs[0]
    shader = t.node("ShaderNodeMixShader", 12, -1, {0: glow, 1: shader, 2: emission}).outputs[0]
    t.node("NodeGroupOutput", 13, -1, {"Shader": shader})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(build_hexagon()),), fake_user=True)
