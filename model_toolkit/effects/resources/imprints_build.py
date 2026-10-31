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
# Depth of the points counted in the imprints for the cracks and the debris, relative to the Depth
PRESSED = 0.05
# Steps of the cracks, turning by up to the wiggle (radians) at each, spreading from the edges by
# up to the spread around the way out of the imprints
CRACK_STEPS = 24
WIGGLE = 0.35
SPREAD = 0.5
# Blur iterations of the way out of the imprints, not to follow the faces
AWAY_SMOOTH = 8
# Cracks over the imprints per edge crack and meter of Crack Length, their length and width
# relative to the edge ones
INNER = 1.0
INNER_LENGTH = 0.35
INNER_WIDTH = 0.6
# Branches of each crack, turning by 20 to 50 degrees, and their width relative to the crack
BRANCHES = 1.5
BRANCH_ANGLE = (0.35, 0.9)
BRANCH_WIDTH = 0.7
# Narrowing of the cracks to their end, their depth relative to their width, and the width of the
# groove at least, in edges, not to fall between the points
TAPER = 0.6
CRACK_DEPTH = 1.5
GROOVE = 1.5
# Length of the vector to the cracks for the shader out of them, and the edges it is stored within
FAR = 1000.0
CRACK_BAND = 2.0
# Extra tilt (relative to the slab height over its size) and lift of the slabs, heights of the
# imprints and rim (relative to the Depth) starting to open their gaps and opening them by the
# Crack Width, and the depth of the gaps relative to their width
SLAB_TILT = 0.5
SLAB_JOLT = 0.3
OPEN_START = 0.05
OPEN_DEPTH = 0.3
GAP_DEPTH = 1.0
# Distance of the sides of the Chunks to the slab edges snapped onto them, in edges
SNAP_EDGES = 2.0
# Octaves and contrast of the uneven color of the imprints
DETAIL_OCTAVES = 4.0
DETAIL_CONTRAST = 2.5
# Shade of the cracks, and the sharpness of their sides in the shader
CRACK_SHADE = 0.05
CRACK_EDGE = 4.0
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
        "Cracks",
        "NodeSocketBool",
        default_value=False,
        description="Break the surface around the imprints into tilted slabs opening apart, with "
        "cracks spreading from them, as asphalt",
    )
    add_input(
        ng,
        "Crack Amount",
        "NodeSocketFloat",
        default_value=15.0,
        min_value=0.0,
        description="Cracks spreading from each meter of the imprint edges",
    )
    add_input(
        ng,
        "Crack Length",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.3,
        min_value=0.0,
        description="Length of the cracks of the deepest imprints",
    )
    add_input(
        ng,
        "Crack Width",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.006,
        min_value=0.0,
        description="Width of the cracks at their start, and of the gaps between the slabs",
    )
    add_input(
        ng,
        "Slab Size",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.06,
        min_value=0.001,
        description="Size of the slabs the surface breaks into around the imprints, tilted by "
        "the Rim",
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
    add_input(
        ng,
        "Chunks",
        "NodeSocketBool",
        default_value=False,
        description="Make the slabs separate pieces as thick as the Thickness, their sides showing "
        "where they tilt",
    )
    add_input(
        ng,
        "Thickness",
        "NodeSocketFloat",
        subtype="DISTANCE",
        default_value=0.03,
        min_value=0.0,
        description="Thickness of the Chunks, the surface under them sunk as much",
    )
    # After Smooth, added last to keep the identifiers of the inputs before it
    ng.interface.move(
        softness, list(ng.interface.items_tree).index(ng.interface.items_tree["Smooth"]) + 1
    )
    arrange_interface(
        ng,
        [
            (None, "Tint", True, "Tint", ["Color", "Detail", "Detail Scale"]),
            (
                None,
                "Cracks",
                True,
                "Cracks",
                ["Crack Amount", "Crack Length", "Crack Width", "Slab Size", "Chunks", "Thickness"],
            ),
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
    depth = pressed_depth(t, colliders, world, normal, limited, inputs["Depth"], 4, -5)
    depth = t.math("MULTIPLY", depth, inputs["Mask"], x=9, y=-5)
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
    # Subdivided where the Colliders may press it and around the imprints, as far as their rim and
    # slabs spread, the cracks drawn by the shader on any faces
    spread = t.math(
        "ADD",
        t.math("MULTIPLY", inputs["Rim Width"], RIM_SPREAD, x=0, y=-4),
        inputs["Softness"],
        x=1,
        y=-4,
    )
    spread = t.math(
        "ADD",
        spread,
        t.math(
            "MULTIPLY",
            inputs["Cracks"],
            t.math("MULTIPLY", inputs["Slab Size"], 2.0, x=0, y=-6),
            x=1,
            y=-6,
        ),
        x=2,
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
    # Stored once, for the rim and the cracks
    smoothed, blurred = blurred, t.attribute(".imprint_blurred", "FLOAT", 10.5, -4)
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
    crisp = t.store(geometry, ".imprint_blurred", "FLOAT", smoothed, 11, -1)
    noisy = t.math("MULTIPLY", height, noise, x=14, y=-5)
    crisp = t.node(
        "GeometryNodeSwitch",
        14,
        -1,
        {
            "Switch": inputs["Cracks"],
            "False": crisp,
            "True": build_cracks(
                t,
                inputs,
                build_slabs(t, inputs, crisp, to_world, world, normal, noisy, depth, length),
                mesh,
                to_world,
                world,
                normal,
                depth,
                blurred,
                length,
            ),
        },
        input_type="GEOMETRY",
    ).outputs[0]
    # Broken into slabs with the cracks
    noisy = t.node(
        "GeometryNodeSwitch",
        14.5,
        -6,
        {
            "Switch": inputs["Cracks"],
            "False": noisy,
            "True": t.attribute(".imprint_slab", "FLOAT", 14, -7),
        },
        input_type="FLOAT",
    ).outputs[0]
    crisp = t.store(
        crisp,
        ".imprint_offset",
        "FLOAT_VECTOR",
        t.vmath(
            "SCALE",
            normal,
            t.math(
                "SUBTRACT",
                noisy,
                t.attribute(".imprint_crack", "FLOAT", 14, -8),
                x=15,
                y=-5,
            ),
            x=15,
            y=-4,
        ),
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
    # Sharp between the slabs
    ends = t.node("GeometryNodeInputMeshEdgeVertices", 15.5, -6).outputs
    cells = [
        t.node(
            "GeometryNodeFieldAtIndex",
            16,
            -6 - i,
            {
                "Value": t.attribute(".imprint_slab_cell", "INT", 15.5, -8),
                "Index": ends[f"Vertex Index {i + 1}"],
            },
            data_type="INT",
            domain="POINT",
        ).outputs[0]
        for i in range(2)
    ]
    geometry = t.node(
        "GeometryNodeSetShadeSmooth",
        16.25,
        0,
        {
            "Mesh": geometry,
            "Selection": t.math(
                "MULTIPLY",
                inputs["Cracks"],
                t.node(
                    "FunctionNodeCompare",
                    16.5,
                    -6,
                    {"A": cells[0], "B": cells[1]},
                    data_type="INT",
                    operation="NOT_EQUAL",
                ).outputs[0],
                x=17,
                y=-6,
            ),
            "Shade Smooth": False,
        },
        domain="EDGE",
    ).outputs[0]
    offset = t.node(
        "FunctionNodeTransformDirection",
        16,
        -4,
        {"Direction": offset, "Transform": to_local},
    ).outputs[0]
    # The normal before, for the Chunks
    geometry = t.store(geometry, ".imprint_up", "FLOAT_VECTOR", normal, 16.5, 0)
    geometry = t.node(
        "GeometryNodeSetPosition", 17, 0, {"Geometry": geometry, "Offset": offset}
    ).outputs[0]
    geometry = t.node(
        "GeometryNodeSwitch",
        17.5,
        0,
        {
            "Switch": t.math("MULTIPLY", inputs["Cracks"], inputs["Chunks"], x=17, y=-5),
            "False": geometry,
            "True": build_chunks(t, inputs, geometry, to_world, to_local, length),
        },
        input_type="GEOMETRY",
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
    # Out of the cracks without them, the attribute always there not to be zero-filled by the debris
    crack = t.node(
        "GeometryNodeInputNamedAttribute",
        2,
        -6,
        {"Name": ".imprint_crack_color"},
        data_type="FLOAT_COLOR",
    ).outputs
    crack = t.node(
        "GeometryNodeSwitch",
        3,
        -6,
        {"Switch": crack["Exists"], "False": (0.0, 0.0, 0.0, 1.0), "True": crack["Attribute"]},
        input_type="RGBA",
    ).outputs[0]
    geometry = t.store(geometry, "imprint_crack", "FLOAT_COLOR", crack, 3.5, 0)
    slab = t.node(
        "GeometryNodeInputNamedAttribute",
        2,
        -8,
        {"Name": ".imprint_slab_color"},
        data_type="FLOAT_COLOR",
    ).outputs
    slab = t.node(
        "GeometryNodeSwitch",
        3,
        -8,
        {"Switch": slab["Exists"], "False": (0.0, 0.0, 0.0, 1.0), "True": slab["Attribute"]},
        input_type="RGBA",
    ).outputs[0]
    geometry = t.store(geometry, "imprint_slab", "FLOAT_COLOR", slab, 3.75, 0)
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


def pressed_depth(t, colliders, position, normal, reach, limit, x, y):
    """Depth the Colliders press the surface at the position, up from under it to their lowest
    surface, only where they cover it"""
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


def build_slabs(t, inputs, geometry, to_world, world, normal, height, depth, spacing):
    """Geometry with the surface around the imprints broken into slabs, each the plane of the
    height over it tilted a little more, opening apart as much as they move: their height in
    .imprint_slab, the slab coordinates and gap width in .imprint_slab_color for the shader"""
    frame = t.frame
    t.section("Slabs", row=True)
    coords = t.vmath(
        "SCALE",
        world,
        t.math("DIVIDE", 1.0, inputs["Slab Size"], x=0, y=-3),
        x=0.5,
        y=-2,
    )
    geometry = t.store(geometry, ".imprint_slab_coords", "FLOAT_VECTOR", coords, 1, 0)
    coords = t.attribute(".imprint_slab_coords", "FLOAT_VECTOR", 1, -2)
    cell = t.node(
        "ShaderNodeTexVoronoi",
        1.5,
        -2,
        {"Vector": coords, "Scale": 1.0},
        voronoi_dimensions="3D",
        feature="F1",
    ).outputs["Position"]
    cell = t.node("FunctionNodeHashValue", 2, -2, {"Value": cell}, data_type="VECTOR").outputs[0]
    geometry = t.store(geometry, ".imprint_slab_cell", "INT", cell, 2, 0)
    geometry = t.store(geometry, ".imprint_height", "FLOAT", height, 2.5, 0)
    cell = t.attribute(".imprint_slab_cell", "INT", 3, -2)
    height = t.attribute(".imprint_height", "FLOAT", 3, -3)

    # Slope of the height, averaged over the edges of each point, as the edges in two directions
    edges = t.node("GeometryNodeInputMeshEdgeVertices", 3, -6).outputs
    ends = [
        (
            t.node(
                "FunctionNodeTransformPoint",
                3.5,
                -6 - i,
                {
                    "Vector": edges[f"Position {i + 1}"],
                    "Transform": to_world,
                },
            ).outputs[0],
            t.node(
                "GeometryNodeFieldAtIndex",
                3.5,
                -9 - i,
                {"Value": height, "Index": edges[f"Vertex Index {i + 1}"]},
                data_type="FLOAT",
                domain="POINT",
            ).outputs[0],
        )
        for i in range(2)
    ]
    along = t.vmath("SUBTRACT", ends[1][0], ends[0][0], x=4, y=-6)
    slope = t.vmath(
        "SCALE",
        along,
        t.math(
            "DIVIDE",
            t.math(
                "MULTIPLY", t.math("SUBTRACT", ends[1][1], ends[0][1], x=4, y=-9), 2.0, x=4.5, y=-9
            ),
            t.math("MAXIMUM", t.vmath("DOT_PRODUCT", along, along, x=4.5, y=-7), 1e-12, x=5, y=-7),
            x=5,
            y=-9,
        ),
        x=5.5,
        y=-6,
    )
    slope = t.node(
        "GeometryNodeFieldOnDomain",
        6,
        -6,
        {"Value": slope},
        data_type="FLOAT_VECTOR",
        domain="EDGE",
    ).outputs[0]
    geometry = t.store(
        geometry, ".imprint_slope", "FLOAT_VECTOR", tangent(t, slope, normal, 6.5, -6), 7, 0
    )

    # Planes fit to the points of each slab out of the imprints
    free = t.math("LESS_THAN", depth, 1e-9, x=7, y=-3)
    side = t.node(
        "FunctionNodeHashValue",
        7.5,
        -2,
        {"Value": cell, "Seed": free},
        data_type="INT",
    ).outputs[0]

    def total(value, data_type, y, group=side):
        return t.node(
            "GeometryNodeAccumulateField",
            8,
            y,
            {"Value": value, "Group ID": group},
            data_type=data_type,
            domain="POINT",
        ).outputs["Total"]

    count = total(1.0, "FLOAT", -3)
    for i, (name, data_type, value) in enumerate(
        (
            (".imprint_slab_center", "FLOAT_VECTOR", world),
            (".imprint_slab_height", "FLOAT", height),
            (
                ".imprint_slab_slope",
                "FLOAT_VECTOR",
                t.attribute(".imprint_slope", "FLOAT_VECTOR", 7, -8),
            ),
        )
    ):
        mean = t.math(
            "DIVIDE",
            total(value, data_type, -5 - i * 2),
            count,
            x=8.5,
            y=-5 - i * 2,
            vector=data_type == "FLOAT_VECTOR",
        )
        geometry = t.store(geometry, name, data_type, mean, 9 + i * 0.5, 0)
    # Moved as much as the imprints and the rim of all its points
    moved = t.math(
        "DIVIDE",
        total(t.math("ABSOLUTE", height, x=7.5, y=-12), "FLOAT", -12, cell),
        total(1.0, "FLOAT", -13, cell),
        x=9,
        y=-12,
    )
    geometry = t.store(geometry, ".imprint_slab_moved", "FLOAT", moved, 10.5, 0)

    center = t.attribute(".imprint_slab_center", "FLOAT_VECTOR", 11, -2)
    level = t.attribute(".imprint_slab_height", "FLOAT", 11, -3)
    # Tilted and lifted a little more by the slab, the more it moves
    tilt = t.vmath(
        "ADD",
        t.attribute(".imprint_slab_slope", "FLOAT_VECTOR", 11, -4),
        t.vmath(
            "SCALE",
            tangent(
                t,
                random(t, (-1.0,) * 3, (1.0,) * 3, cell, 11, 11, -6, "FLOAT_VECTOR"),
                normal,
                11.5,
                -6,
            ),
            t.math(
                "DIVIDE",
                t.math("MULTIPLY", level, SLAB_TILT, x=11.5, y=-8),
                inputs["Slab Size"],
                x=12,
                y=-8,
            ),
            x=12.5,
            y=-6,
        ),
        x=13,
        y=-4,
    )
    plane = t.math(
        "ADD",
        t.math(
            "MULTIPLY",
            level,
            t.math("ADD", 1.0, random(t, -SLAB_JOLT, SLAB_JOLT, cell, 12, 12, -10), x=12.5, y=-10),
            x=13,
            y=-10,
        ),
        t.vmath("DOT_PRODUCT", tilt, t.vmath("SUBTRACT", world, center, x=13, y=-3), x=13.5, y=-4),
        x=14,
        y=-4,
    )
    # Opening apart as much as they move, in the gaps between the slabs
    moved = t.attribute(".imprint_slab_moved", "FLOAT", 11, -12)
    gap = t.math(
        "MULTIPLY",
        inputs["Crack Width"],
        t.math(
            "DIVIDE",
            t.math(
                "SUBTRACT",
                moved,
                t.math("MULTIPLY", inputs["Depth"], OPEN_START, x=11, y=-14),
                x=11.5,
                y=-13,
            ),
            t.math("MULTIPLY", inputs["Depth"], OPEN_DEPTH, x=11.5, y=-14),
            x=12,
            y=-13,
            clamp=True,
        ),
        x=12.5,
        y=-12,
    )
    edge = t.math(
        "MULTIPLY",
        t.node(
            "ShaderNodeTexVoronoi",
            11.5,
            -16,
            {"Vector": coords, "Scale": 1.0},
            voronoi_dimensions="3D",
            feature="DISTANCE_TO_EDGE",
        ).outputs["Distance"],
        inputs["Slab Size"],
        x=12,
        y=-16,
    )
    groove = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("MULTIPLY", gap, GAP_DEPTH, x=12.5, y=-11),
            t.math("DIVIDE", gap, spacing, x=12.5, y=-10, clamp=True),
            x=13,
            y=-11,
        ),
        t.math(
            "SUBTRACT",
            1.0,
            t.math(
                "DIVIDE",
                edge,
                t.math(
                    "MAXIMUM", gap, t.math("MULTIPLY", spacing, GROOVE, x=12.5, y=-18), x=13, y=-17
                ),
                x=13.5,
                y=-16,
            ),
            x=14,
            y=-16,
            clamp=True,
        ),
        x=14.5,
        y=-12,
    )
    # The imprints as they are, the gaps showing the slabs broken in them
    slab = t.node(
        "GeometryNodeSwitch",
        15,
        -4,
        {"Switch": free, "False": height, "True": plane},
        input_type="FLOAT",
    ).outputs[0]
    geometry = t.store(
        geometry, ".imprint_slab", "FLOAT", t.math("SUBTRACT", slab, groove, x=15.5, y=-4), 16, 0
    )
    xyz = t.node("ShaderNodeSeparateXYZ", 15, -8, {0: coords}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        16,
        -8,
        {
            "Red": xyz["X"],
            "Green": xyz["Y"],
            "Blue": xyz["Z"],
            "Alpha": t.math(
                "SUBTRACT",
                1.0,
                t.math("DIVIDE", gap, inputs["Slab Size"], x=15, y=-10),
                x=15.5,
                y=-10,
            ),
        },
    ).outputs[0]
    geometry = t.store(geometry, ".imprint_slab_color", "FLOAT_COLOR", color, 16.5, 0)
    t.frame = frame
    return geometry


def build_chunks(t, inputs, geometry, to_world, to_local, spacing):
    """The mesh with the slabs out of the imprints that move as separate pieces, their sides on
    the slab edges apart by the gaps, as thick as the Thickness down to the surface sunk under them
    """
    frame = t.frame
    t.section("Chunks", row=True)
    coords = t.attribute(".imprint_slab_coords", "FLOAT_VECTOR", 0, -2)
    # Of the slab of their center, out of the imprints, where the slabs move
    feature = t.node(
        "ShaderNodeTexVoronoi",
        1,
        -2,
        {
            "Vector": t.node(
                "GeometryNodeFieldOnDomain",
                0.5,
                -2,
                {"Value": coords},
                data_type="FLOAT_VECTOR",
                domain="FACE",
            ).outputs[0],
            "Scale": 1.0,
        },
        voronoi_dimensions="3D",
        feature="F1",
    ).outputs["Position"]
    geometry = t.store(geometry, ".imprint_feature", "FLOAT_VECTOR", feature, 1.5, 0, "FACE")

    def on_faces(name, y):
        return t.node(
            "GeometryNodeFieldOnDomain",
            1,
            y,
            {"Value": t.attribute(name, "FLOAT", 0.5, y)},
            data_type="FLOAT",
            domain="FACE",
        ).outputs[0]

    chunk = t.math(
        "MULTIPLY",
        t.math("LESS_THAN", on_faces(".imprint_depth", -4), 1e-9, x=1.5, y=-4),
        t.math(
            "GREATER_THAN",
            on_faces(".imprint_slab_moved", -5),
            t.math("MULTIPLY", inputs["Depth"], OPEN_START, x=1, y=-6),
            x=1.5,
            y=-5,
        ),
        x=2,
        y=-4,
    )
    geometry = t.store(geometry, ".imprint_chunk", "FLOAT", chunk, 2, 0, "FACE")
    # The surface under them sunk, where all the faces around are pieces
    normal = t.attribute(".imprint_up", "FLOAT_VECTOR", 2.5, -8)
    down = t.node(
        "FunctionNodeTransformDirection",
        3.5,
        -8,
        {
            "Direction": t.vmath(
                "SCALE",
                normal,
                t.math("MULTIPLY", inputs["Thickness"], -1.0, x=3, y=-10),
                x=3.5,
                y=-9,
            ),
            "Transform": to_local,
        },
    ).outputs[0]
    sunk = t.node(
        "GeometryNodeSetPosition",
        3,
        0,
        {
            "Geometry": geometry,
            "Selection": t.math(
                "GREATER_THAN",
                t.attribute(".imprint_chunk", "FLOAT", 2.5, -3),
                0.999,
                x=3,
                y=-3,
            ),
            "Offset": down,
        },
    ).outputs[0]

    # Each slab apart
    pieces = t.node(
        "GeometryNodeSeparateGeometry",
        3,
        2,
        {"Geometry": geometry, "Selection": t.math("GREATER_THAN", chunk, 0.5, x=2.5, y=2)},
        domain="FACE",
    ).outputs["Selection"]
    pieces = t.node(
        "GeometryNodeSplitToInstances",
        4,
        2,
        {
            "Geometry": pieces,
            "Group ID": t.node(
                "FunctionNodeHashValue",
                3.5,
                3,
                {"Value": t.attribute(".imprint_feature", "FLOAT_VECTOR", 3, 3)},
                data_type="VECTOR",
            ).outputs[0],
        },
        domain="FACE",
    ).outputs["Instances"]
    pieces = t.node("GeometryNodeRealizeInstances", 5, 2, {"Geometry": pieces}).outputs[0]

    # Their sides on the edge to the next slab, the nearest other one, half the gap in
    own = t.attribute(".imprint_feature", "FLOAT_VECTOR", 5, -2)
    nearest = [
        t.node(
            "ShaderNodeTexVoronoi",
            5.5,
            -3 - i,
            {"Vector": coords, "Scale": 1.0},
            voronoi_dimensions="3D",
            feature=feature_type,
        ).outputs["Position"]
        for i, feature_type in enumerate(("F1", "F2"))
    ]
    other = t.node(
        "GeometryNodeSwitch",
        6,
        -3,
        {
            "Switch": t.math(
                "LESS_THAN",
                t.vmath("DISTANCE", nearest[0], own, x=5.5, y=-6),
                1e-4,
                x=6,
                y=-6,
            ),
            "False": nearest[0],
            "True": nearest[1],
        },
        input_type="VECTOR",
    ).outputs[0]
    across = t.vmath("NORMALIZE", t.vmath("SUBTRACT", other, own, x=6.5, y=-4), x=7, y=-4)
    middle = t.vmath("SCALE", t.vmath("ADD", other, own, x=6.5, y=-5), 0.5, x=7, y=-5)
    past = t.math(
        "ADD",
        t.vmath("DOT_PRODUCT", t.vmath("SUBTRACT", coords, middle, x=7.5, y=-5), across, x=8, y=-5),
        t.math(
            "MULTIPLY",
            t.math(
                "SUBTRACT",
                1.0,
                t.node(
                    "FunctionNodeSeparateColor",
                    7,
                    -7,
                    {0: t.attribute(".imprint_slab_color", "FLOAT_COLOR", 6.5, -7)},
                ).outputs["Alpha"],
                x=7.5,
                y=-7,
            ),
            0.5,
            x=8,
            y=-7,
        ),
        x=8.5,
        y=-5,
    )
    along = t.vmath("NORMALIZE", tangent(t, across, normal, 8, -9), x=8.5, y=-9)
    move = t.math(
        "DIVIDE",
        t.math("MULTIPLY", past, -1.0, x=9, y=-5),
        t.math("MAXIMUM", t.vmath("DOT_PRODUCT", along, across, x=9, y=-9), 0.2, x=9.5, y=-9),
        x=10,
        y=-5,
    )
    # Only the points on the sides of the pieces near an edge of the slabs
    side = t.node(
        "GeometryNodeFieldOnDomain",
        9.5,
        -11,
        {
            "Value": t.math(
                "LESS_THAN",
                t.node("GeometryNodeInputMeshEdgeNeighbors", 9, -11).outputs["Face Count"],
                1.5,
                x=9.25,
                y=-11,
            )
        },
        data_type="FLOAT",
        domain="EDGE",
    ).outputs[0]
    snap = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", side, 0.0, x=10, y=-11),
        t.math(
            "LESS_THAN",
            t.math("ABSOLUTE", move, x=10, y=-12),
            t.math(
                "DIVIDE",
                t.math("MULTIPLY", spacing, SNAP_EDGES, x=9.5, y=-13),
                inputs["Slab Size"],
                x=10,
                y=-13,
            ),
            x=10.5,
            y=-12,
        ),
        x=11,
        y=-11,
    )
    pieces = t.node(
        "GeometryNodeSetPosition",
        11,
        2,
        {
            "Geometry": pieces,
            "Selection": t.math("GREATER_THAN", snap, 0.5, x=11, y=-10),
            "Offset": t.node(
                "FunctionNodeTransformDirection",
                11,
                -8,
                {
                    "Direction": t.vmath(
                        "SCALE",
                        along,
                        t.math("MULTIPLY", move, inputs["Slab Size"], x=10.5, y=-6),
                        x=11,
                        y=-6,
                    ),
                    "Transform": to_local,
                },
            ).outputs[0],
        },
    ).outputs[0]
    # As thick as the Thickness, extruded back up from the sunk surface, the sides flat
    pieces = t.node(
        "GeometryNodeSetPosition", 11.5, 2, {"Geometry": pieces, "Offset": down}
    ).outputs[0]
    extruded = t.node(
        "GeometryNodeExtrudeMesh",
        12,
        2,
        {
            "Mesh": pieces,
            "Offset": t.vmath("SCALE", down, -1.0, x=11.5, y=0),
            "Individual": False,
        },
        mode="FACES",
    ).outputs
    pieces = t.node(
        "GeometryNodeSetShadeSmooth",
        13,
        2,
        {"Mesh": extruded["Mesh"], "Selection": extruded["Side"], "Shade Smooth": False},
        domain="FACE",
    ).outputs[0]
    # The mesh first, the last link going first
    joined = t.node("GeometryNodeJoinGeometry", 14, 0)
    for part in (pieces, sunk):
        t.connect(part, joined.inputs[0])
    t.frame = frame
    return joined.outputs[0]


def random(t, low, high, identifier, seed, x, y, data_type="FLOAT"):
    return t.node(
        "FunctionNodeRandomValue",
        x,
        y,
        {"Min": low, "Max": high, "ID": identifier, "Seed": seed},
        data_type=data_type,
    ).outputs[0]


def tangent(t, vector, normal, x, y):
    """The vector along the surface of the normal"""
    return t.vmath(
        "SUBTRACT",
        vector,
        t.vmath("SCALE", normal, t.vmath("DOT_PRODUCT", vector, normal, x=x, y=y - 1), x=x, y=y),
        x=x + 0.5,
        y=y,
    )


def build_cracks(t, inputs, geometry, surface, to_world, world, normal, depth, blurred, spacing):
    """Geometry with the cracks from the edges of the imprints and over them, as curves wandering
    away from them and branching: their depth in .imprint_crack, the vector to them relative to
    their width in .imprint_crack_color, for the shader to draw them finer than the faces"""
    frame = t.frame
    t.section("Cracks", row=True)
    # By position, the same points at each frame where the indices change with the subdivisions
    index = t.node(
        "FunctionNodeHashValue",
        0,
        -30,
        {"Value": t.node("GeometryNodeInputPosition", -0.5, -30).outputs[0]},
        data_type="VECTOR",
    ).outputs[0]
    # Away from the imprints, against the gradient of their blurred depth, from the edges
    edges = t.node("GeometryNodeInputMeshEdgeVertices", 0, -20).outputs
    ends = [
        (
            t.node(
                "FunctionNodeTransformPoint",
                1,
                -20 - i,
                {"Vector": edges[f"Position {i + 1}"], "Transform": to_world},
            ).outputs[0],
            t.node(
                "GeometryNodeFieldAtIndex",
                1,
                -22 - i,
                {"Value": blurred, "Index": edges[f"Vertex Index {i + 1}"]},
                data_type="FLOAT",
                domain="POINT",
            ).outputs[0],
        )
        for i in range(2)
    ]
    slope = t.vmath(
        "SCALE",
        t.vmath("SUBTRACT", ends[1][0], ends[0][0], x=2, y=-20),
        t.math("SUBTRACT", ends[0][1], ends[1][1], x=2, y=-22),
        x=3,
        y=-20,
    )
    slope = t.node(
        "GeometryNodeFieldOnDomain",
        4,
        -20,
        {"Value": slope},
        data_type="FLOAT_VECTOR",
        domain="EDGE",
    ).outputs[0]
    slope = t.node(
        "GeometryNodeBlurAttribute",
        5,
        -20,
        {"Value": slope, "Iterations": AWAY_SMOOTH},
        data_type="FLOAT_VECTOR",
    ).outputs[0]
    away = t.vmath("NORMALIZE", tangent(t, slope, normal, 6, -20), x=7, y=-20)

    # From the edges of the imprints, and fewer shorter ones over them, longer where deeper
    limit = t.math("MULTIPLY", inputs["Depth"], PRESSED, x=0, y=-25)
    pressed = t.math("GREATER_THAN", depth, limit, x=1, y=-24)
    edge = t.math(
        "MULTIPLY",
        pressed,
        t.math("LESS_THAN", shallowest_neighbor(t, depth, 0, -27), limit, x=5, y=-26),
        x=6,
        y=-24,
    )
    chance = random(t, 0.0, 1.0, index, 0, 1, -29)
    per_edge = t.math("MULTIPLY", inputs["Crack Amount"], spacing, x=1, y=-31)
    per_point = t.math(
        "DIVIDE",
        t.math("MULTIPLY", per_edge, t.math("MULTIPLY", spacing, INNER, x=1, y=-33), x=2, y=-32),
        inputs["Crack Length"],
        x=3,
        y=-32,
    )
    seed = t.node(
        "GeometryNodeSwitch",
        4,
        -30,
        {
            "Switch": t.math("GREATER_THAN", edge, 0.5, x=3, y=-29),
            "False": t.math(
                "MULTIPLY",
                pressed,
                t.math("LESS_THAN", chance, per_point, x=3.5, y=-32),
                x=4,
                y=-32,
            ),
            "True": t.math("LESS_THAN", chance, per_edge, x=3.5, y=-31),
        },
        input_type="FLOAT",
    ).outputs[0]
    pressure = t.math(
        "DIVIDE",
        t.math("MULTIPLY", blurred, 2.0, x=1, y=-35),
        inputs["Depth"],
        x=2,
        y=-35,
        clamp=True,
    )
    spread = tangent(
        t, random(t, (-1.0,) * 3, (1.0,) * 3, index, 1, 6, -23, "FLOAT_VECTOR"), normal, 7, -23
    )
    direction = t.vmath(
        "NORMALIZE",
        t.vmath(
            "ADD",
            t.vmath("SCALE", away, edge, x=8, y=-21),
            t.vmath("SCALE", spread, SPREAD, x=8, y=-23),
            x=8.5,
            y=-21,
        ),
        x=9,
        y=-21,
    )
    share = t.math("MULTIPLY_ADD", edge, 1.0 - INNER_LENGTH, INNER_LENGTH, x=7, y=-36)
    length = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Crack Length"], pressure, x=7, y=-35),
        t.math("MULTIPLY", share, random(t, 0.5, 1.0, index, 2, 7, -37), x=8, y=-36),
        x=9,
        y=-35,
    )
    share = t.math("MULTIPLY_ADD", edge, 1.0 - INNER_WIDTH, INNER_WIDTH, x=7, y=-39)
    width = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", inputs["Crack Width"], pressure, x=7, y=-38),
        t.math("MULTIPLY", share, random(t, 0.6, 1.0, index, 3, 7, -40), x=8, y=-39),
        x=9,
        y=-38,
    )
    # Stored once, read by the stores below
    cracks = t.store(
        geometry,
        ".imprint_crack_seed",
        "BOOLEAN",
        t.math("GREATER_THAN", seed, 0.5, x=5, y=-30),
        9.5,
        -18,
    )
    seed = t.attribute(".imprint_crack_seed", "BOOLEAN", 9.5, -20)
    for i, (name, data_type, value) in enumerate(
        (
            (".imprint_crack_dir", "FLOAT_VECTOR", direction),
            (".imprint_crack_normal", "FLOAT_VECTOR", normal),
            (".imprint_crack_length", "FLOAT", length),
            (".imprint_crack_width", "FLOAT", width),
            (".imprint_crack_id", "INT", index),
        )
    ):
        cracks = t.store(cracks, name, data_type, value, 10 + i * 0.5, -18, selection=seed)
    cracks = t.node(
        "GeometryNodeMeshToPoints",
        13,
        -18,
        {"Mesh": cracks, "Selection": seed, "Position": world},
    ).outputs[0]

    # Along the surface, the input mesh as the subdivided one, the branches from points along the
    # cracks turning away from them
    step = t.math("DIVIDE", inputs["Crack Length"], CRACK_STEPS, x=13, y=-24)
    cracks, curves = trace(t, cracks, surface, step, 14, -18)
    k = t.attribute(".imprint_crack_k", "INT", 18, -22)
    ids = t.attribute(".imprint_crack_id", "INT", 18, -23)
    reached = t.math("MULTIPLY", k, step, x=19, y=-22)
    total = t.attribute(".imprint_crack_length", "FLOAT", 18, -24)
    branch = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("GREATER_THAN", k, 0.5, x=19, y=-25),
            t.math("LESS_THAN", reached, t.math("MULTIPLY", total, 0.8, x=19, y=-27), x=20, y=-26),
            x=21,
            y=-25,
        ),
        t.math(
            "LESS_THAN",
            random(t, 0.0, 1.0, ids, t.math("ADD", k, 1000, x=19, y=-29), 20, -28),
            BRANCHES / CRACK_STEPS,
            x=21,
            y=-28,
        ),
        x=22,
        y=-25,
    )
    branches = t.node(
        "GeometryNodeSeparateGeometry",
        22,
        -18,
        {"Geometry": cracks, "Selection": branch},
        domain="POINT",
    ).outputs["Selection"]
    side = t.math(
        "MULTIPLY_ADD",
        t.math(
            "GREATER_THAN",
            random(t, 0.0, 1.0, ids, t.math("ADD", k, 2000, x=22, y=-31), 23, -30),
            0.5,
            x=24,
            y=-30,
        ),
        2.0,
        -1.0,
        x=25,
        y=-30,
    )
    angle = t.math(
        "MULTIPLY",
        side,
        random(t, *BRANCH_ANGLE, ids, t.math("ADD", k, 3000, x=22, y=-33), 23, -32),
        x=26,
        y=-30,
    )
    along = t.attribute(".imprint_crack_dir", "FLOAT_VECTOR", 23, -34)
    up = t.attribute(".imprint_crack_normal", "FLOAT_VECTOR", 23, -35)
    turned = t.vmath(
        "ADD",
        t.vmath("SCALE", along, t.math("COSINE", angle, x=27, y=-30), x=27.5, y=-34),
        t.vmath(
            "SCALE",
            t.vmath("CROSS_PRODUCT", up, along, x=26, y=-35),
            t.math("SINE", angle, x=27, y=-31),
            x=27.5,
            y=-35,
        ),
        x=28,
        y=-34,
    )
    for i, (name, data_type, value) in enumerate(
        (
            (".imprint_crack_dir", "FLOAT_VECTOR", turned),
            (
                ".imprint_crack_length",
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    t.math("SUBTRACT", total, reached, x=27, y=-37),
                    random(t, 0.3, 0.7, ids, t.math("ADD", k, 4000, x=26, y=-39), 27, -38),
                    x=28,
                    y=-37,
                ),
            ),
            (
                ".imprint_crack_width",
                "FLOAT",
                t.math(
                    "MULTIPLY",
                    t.attribute(".imprint_crack_w", "FLOAT", 27, -40),
                    BRANCH_WIDTH,
                    x=28,
                    y=-40,
                ),
            ),
            (
                ".imprint_crack_id",
                "INT",
                t.math("MULTIPLY_ADD", ids, CRACK_STEPS + 1, k, x=28, y=-42),
            ),
        )
    ):
        branches = t.store(branches, name, data_type, value, 29 + i * 0.5, -18)
    _, branched = trace(t, branches, surface, step, 31, -18)
    joined = t.node("GeometryNodeJoinGeometry", 35, -18)
    for part in (curves, branched):
        t.connect(part, joined.inputs[0])
    lines = t.node("GeometryNodeCurveToMesh", 36, -18, {"Curve": joined.outputs[0]}).outputs[0]

    # Grooves along the cracks, at least a few faces wide, and the vector to them near them
    near = t.node(
        "GeometryNodeProximity",
        37,
        -20,
        {"Geometry": lines, "Sample Position": world},
        target_element="EDGES",
    ).outputs
    nearest = t.node(
        "GeometryNodeSampleNearest",
        37,
        -23,
        {"Geometry": lines, "Sample Position": world},
        domain="EDGE",
    ).outputs[0]
    width = t.node(
        "GeometryNodeSampleIndex",
        38,
        -22,
        {
            "Geometry": lines,
            "Value": t.attribute(".imprint_crack_w", "FLOAT", 37, -25),
            "Index": nearest,
        },
        data_type="FLOAT",
        domain="EDGE",
    ).outputs[0]
    groove = t.math(
        "MULTIPLY",
        t.math("MULTIPLY", width, CRACK_DEPTH, x=39, y=-21),
        t.math(
            "SUBTRACT",
            1.0,
            t.math(
                "DIVIDE",
                near["Distance"],
                t.math(
                    "MAXIMUM",
                    width,
                    t.math("MULTIPLY", spacing, GROOVE, x=38, y=-24),
                    x=39,
                    y=-24,
                ),
                x=40,
                y=-23,
            ),
            x=41,
            y=-23,
            clamp=True,
        ),
        x=42,
        y=-21,
    )
    geometry = t.store(geometry, ".imprint_crack", "FLOAT", groove, 43, -18)
    # Within a few of the longest edges around, all the points of the faces crossing them near
    corner_edge = t.node("GeometryNodeEdgesOfCorner", 37, -31).outputs["Next Edge Index"]
    ends = t.node("GeometryNodeInputMeshEdgeVertices", 37, -32).outputs
    local = t.node(
        "GeometryNodeFieldMinAndMax",
        38.5,
        -31,
        {
            "Value": t.node(
                "GeometryNodeFieldAtIndex",
                38,
                -31,
                {
                    "Value": t.vmath(
                        "DISTANCE",
                        *(
                            t.node(
                                "FunctionNodeTransformPoint",
                                37.5,
                                -32 - i,
                                {"Vector": ends[f"Position {i + 1}"], "Transform": to_world},
                            ).outputs[0]
                            for i in range(2)
                        ),
                        x=37.75,
                        y=-32,
                    ),
                    "Index": corner_edge,
                },
                data_type="FLOAT",
                domain="EDGE",
            ).outputs[0],
            "Group ID": t.node("GeometryNodeVertexOfCorner", 38, -33).outputs[0],
        },
        data_type="FLOAT",
        domain="CORNER",
    ).outputs["Max"]
    close = t.math(
        "MULTIPLY",
        t.math("GREATER_THAN", width, 0.0, x=39, y=-27),
        t.math(
            "LESS_THAN",
            near["Distance"],
            t.math("MULTIPLY_ADD", local, CRACK_BAND, width, x=39, y=-29),
            x=40,
            y=-28,
        ),
        x=41,
        y=-27,
    )
    vector = t.node(
        "GeometryNodeSwitch",
        42,
        -26,
        {
            "Switch": t.math("GREATER_THAN", close, 0.5, x=41.5, y=-29),
            "False": t.vmath("SCALE", normal, FAR, x=41, y=-31),
            "True": t.vmath(
                "DIVIDE",
                t.vmath("SUBTRACT", near["Position"], world, x=40, y=-25),
                t.math("MAXIMUM", width, 1e-6, x=40, y=-26),
                x=41,
                y=-25,
            ),
        },
        input_type="VECTOR",
    ).outputs[0]
    xyz = t.node("ShaderNodeSeparateXYZ", 43, -26, {0: vector}).outputs
    color = t.node(
        "FunctionNodeCombineColor",
        44,
        -26,
        {
            "Red": xyz["X"],
            "Green": xyz["Y"],
            "Blue": xyz["Z"],
            "Alpha": t.math("SUBTRACT", 1.0, close, x=43, y=-28),
        },
    ).outputs[0]
    geometry = t.store(geometry, ".imprint_crack_color", "FLOAT_COLOR", color, 45, -18)
    t.frame = frame
    return geometry


def trace(t, points, ground, step, x, y):
    """The points of each crack and the crack curves, from their first point stepping along the
    surface by the step up to their length, turning a little at each step"""
    duplicate = t.node(
        "GeometryNodeDuplicateElements",
        x,
        y,
        {"Geometry": points, "Amount": CRACK_STEPS + 1},
        domain="POINT",
    ).outputs
    points = t.store(
        duplicate["Geometry"], ".imprint_crack_k", "INT", duplicate["Duplicate Index"], x + 0.5, y
    )
    start = t.node("GeometryNodeRepeatInput", x + 1, y, {"Iterations": CRACK_STEPS})
    end = t.node("GeometryNodeRepeatOutput", x + 3, y)
    start.pair_with_output(end)
    t.connect(points, start.inputs["Geometry"])
    i = start.outputs["Iteration"]
    k = t.attribute(".imprint_crack_k", "INT", x + 1, y - 2)
    ahead = t.math("GREATER_THAN", k, i, x=x + 1.5, y=y - 2)
    moving = t.math(
        "MULTIPLY",
        ahead,
        t.math(
            "LESS_THAN",
            t.math("MULTIPLY", t.math("ADD", i, 1.0, x=x + 1, y=y - 4), step, x=x + 1.5, y=y - 4),
            t.math(
                "ADD",
                t.attribute(".imprint_crack_length", "FLOAT", x + 1, y - 5),
                1e-6,
                x=x + 1.5,
                y=y - 5,
            ),
            x=x + 2,
            y=y - 4,
        ),
        x=x + 2,
        y=y - 2,
    )
    along = t.attribute(".imprint_crack_dir", "FLOAT_VECTOR", x + 1, y - 6)
    turned = t.vmath(
        "NORMALIZE",
        t.vmath(
            "ADD",
            along,
            t.vmath(
                "SCALE",
                t.vmath(
                    "CROSS_PRODUCT",
                    t.attribute(".imprint_crack_normal", "FLOAT_VECTOR", x + 1, y - 7),
                    along,
                    x=x + 1.5,
                    y=y - 7,
                ),
                random(
                    t,
                    -WIGGLE,
                    WIGGLE,
                    t.attribute(".imprint_crack_id", "INT", x + 1, y - 8),
                    i,
                    x + 1.5,
                    y - 8,
                ),
                x=x + 2,
                y=y - 7,
            ),
            x=x + 2,
            y=y - 6,
        ),
        x=x + 2.5,
        y=y - 6,
    )
    position = t.node("GeometryNodeInputPosition", x + 1, y - 9).outputs[0]
    snapped = t.node(
        "GeometryNodeProximity",
        x + 2.5,
        y - 8,
        {
            "Geometry": ground,
            "Sample Position": t.vmath(
                "ADD",
                position,
                t.vmath("SCALE", turned, step, x=x + 2, y=y - 9),
                x=x + 2.5,
                y=y - 9,
            ),
        },
        target_element="FACES",
    ).outputs["Position"]
    # Moved before turning the direction, the move reading it as it was
    moved = t.node(
        "GeometryNodeSetPosition",
        x + 2,
        y,
        {
            "Geometry": start.outputs["Geometry"],
            "Selection": t.math("GREATER_THAN", moving, 0.5, x=x + 2.5, y=y - 3),
            "Position": snapped,
        },
    ).outputs[0]
    t.connect(
        t.store(moved, ".imprint_crack_dir", "FLOAT_VECTOR", turned, x + 2.5, y, selection=ahead),
        end.inputs["Geometry"],
    )
    # Narrowing to their end
    reached = t.math(
        "DIVIDE",
        t.math(
            "MULTIPLY",
            t.attribute(".imprint_crack_k", "INT", x + 3, y - 2),
            step,
            x=x + 3.5,
            y=y - 2,
        ),
        t.attribute(".imprint_crack_length", "FLOAT", x + 3, y - 3),
        x=x + 4,
        y=y - 2,
    )
    width = t.math(
        "MULTIPLY",
        t.attribute(".imprint_crack_width", "FLOAT", x + 4, y - 4),
        t.math(
            "POWER",
            t.math("SUBTRACT", 1.0, reached, x=x + 4.5, y=y - 2, clamp=True),
            TAPER,
            x=x + 5,
            y=y - 2,
        ),
        x=x + 5.5,
        y=y - 3,
    )
    points = t.store(end.outputs["Geometry"], ".imprint_crack_w", "FLOAT", width, x + 4, y)
    curves = t.node(
        "GeometryNodePointsToCurves",
        x + 5,
        y,
        {
            "Points": points,
            "Curve Group ID": t.attribute(".imprint_crack_id", "INT", x + 4.5, y - 5),
            "Weight": t.attribute(".imprint_crack_k", "INT", x + 4.5, y - 6),
        },
    ).outputs[0]
    return points, curves


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

    # Dented flattened icospheres, as the mesh fully tinted out of the cracks, flat shaded
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
    chunks = t.store(chunks, "imprint_detail", "FLOAT_VECTOR", detail, 22.5, 0)
    chunks = t.store(chunks, "imprint_crack", "FLOAT_COLOR", (0.0, 0.0, 0.0, 1.0), 23, 0)
    return t.store(chunks, "imprint_slab", "FLOAT_COLOR", (0.0, 0.0, 0.0, 1.0), 23.5, 0)


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
    # Darkened in the cracks, within the unit length of the vector to them
    crack = t.node(
        "ShaderNodeAttribute", 0, -5, attribute_type="GEOMETRY", attribute_name="imprint_crack"
    ).outputs
    line = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math("SUBTRACT", 1.0, t.vmath("LENGTH", crack["Vector"], x=1, y=-5), x=1.5, y=-5),
            CRACK_EDGE,
            x=2,
            y=-5,
            clamp=True,
        ),
        t.math("SUBTRACT", 1.0, crack["Alpha"], x=1.5, y=-7, clamp=True),
        x=2.5,
        y=-5,
    )
    # And in the gaps between the slabs, within their width of the slab edges
    slab = t.node(
        "ShaderNodeAttribute", 0, -12, attribute_type="GEOMETRY", attribute_name="imprint_slab"
    ).outputs
    gap = t.math("SUBTRACT", 1.0, slab["Alpha"], x=1, y=-13, clamp=True)
    edge = t.node(
        "ShaderNodeTexVoronoi",
        1,
        -12,
        {"Vector": slab["Vector"], "Scale": 1.0},
        voronoi_dimensions="3D",
        feature="DISTANCE_TO_EDGE",
    ).outputs["Distance"]
    gaps = t.math(
        "MULTIPLY",
        t.math(
            "MULTIPLY",
            t.math(
                "SUBTRACT",
                1.0,
                t.math("DIVIDE", edge, t.math("MAXIMUM", gap, 1e-6, x=1.5, y=-14), x=2, y=-12),
                x=2.5,
                y=-12,
            ),
            CRACK_EDGE,
            x=3,
            y=-12,
            clamp=True,
        ),
        t.math("GREATER_THAN", gap, 0.0, x=2, y=-14),
        x=3.5,
        y=-12,
    )
    cracked = t.node(
        "ShaderNodeMix",
        3,
        0,
        {
            "Factor": t.math("MAXIMUM", line, gaps, x=4, y=-6),
            "A": next(s for s in tinted if s.type == "RGBA"),
            "B": (CRACK_SHADE, CRACK_SHADE, CRACK_SHADE, 1.0),
        },
        data_type="RGBA",
        blend_type="MULTIPLY",
    ).outputs
    t.node("NodeGroupOutput", 5, 0, {"Color": next(s for s in cracked if s.type == "RGBA")})
    return ng


if __name__ == "__main__":
    write(RESOURCE, (build_node_group(), build_tint()), fake_user=True)
