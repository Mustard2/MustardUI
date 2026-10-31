# Build jiggle_dynamics.blend: the Jiggle Dynamics node group, out of the source jiggle node group
# Usage: Blender --background source.blend --factory-startup --python jiggle_dynamics_build.py
#        -- <source node group> [out.blend]
import os
import re
import sys

import bpy

RESOURCE = "jiggle_dynamics.blend"
NODE_GROUP = "MustardUI Jiggle Dynamics"
# Raised at every change, so that files with an older one load it (JIGGLE_DYNAMICS_VERSION)
VERSION = 3
PREFIX = "MustardUI Jiggle"

# Extra rings of still points simulated around the zone: the solver moves them slightly, and
# with fewer rings the result differs from the one of the whole mesh
ANCHOR_RINGS = 12

args = sys.argv[sys.argv.index("--") + 1 :]
core = bpy.data.node_groups[args[0]]
source = core.name.split()[0]


def dependencies(tree, found):
    for node in tree.nodes:
        group = getattr(node, "node_tree", None)
        if group is not None and group not in found:
            found.add(group)
            dependencies(group, found)
    return found


def rename(text):
    text = text.replace(source, "Jiggle").replace(source.lower(), "jiggle")
    return text.replace("Jiggle Jiggle", "Jiggle")


# Names: every group gets the prefix, so that none clashes with the Blender assets it copies
for group in dependencies(core, set()):
    name = re.sub(r"\.\d{3}$", "", group.name).replace(source + " ", "")
    group.name = rename(f"{PREFIX} {name}")
core.name = NODE_GROUP + " Core"

for group in dependencies(core, {core}):
    for node in group.nodes:
        node.label, node.name = rename(node.label), rename(node.name)
        if node.bl_idname == "FunctionNodeInputString":
            node.string = rename(node.string)
        for socket in node.inputs:
            if isinstance(getattr(socket, "default_value", None), str):
                socket.default_value = rename(socket.default_value)
    for item in group.interface.items_tree:
        if item.item_type == "SOCKET":
            item.description = rename(item.description)

# Names and tooltips of the inputs, by their identifier in the source node group
INPUTS = {
    "Socket_0": ("Geometry", "Mesh from the modifier stack, deformed by its armature"),
    "Socket_61": (
        "Simulate",
        "Run the simulation. Off, the mesh follows the animation, still with Squeeze and Smoothing",
    ),
    "Socket_2": (
        "Zone",
        "Vertex group of what jiggles: weight 1 is fully soft, 0 follows the animation. Add a "
        "modifier for each part with its own settings (breasts, belly, buttocks...)",
    ),
    "Socket_122": (
        "Edge Fade",
        "Rings of points over which the Zone fades into the rest of the mesh, for groups "
        "assigned in Edit Mode without a gradient. 0 uses the weights as they are",
    ),
    "Socket_67": ("Influence", "Blend from the plain animation (0) to the full simulation (1)"),
    "Socket_33": (
        "Softness",
        "How loosely the Zone is held to the animation, scaled by its weight. Very steep: 0.5 "
        "holds about 100 times less than 0.2",
    ),
    "Socket_31": (
        "Mass",
        "Mass of a point (of an average one with Mass by Area). Heavier swings further and "
        "longer, and with a low Softness sags more under Gravity",
    ),
    "Socket_102": (
        "Mass by Area",
        "Spread the mass by surface area instead of per point, so that the denser parts of the "
        "mesh are not heavier. Keep it on for meshes of uneven density",
    ),
    "Socket_8": (
        "Damping",
        "How quickly the motion calms down. Higher also drags the Zone behind fast animation",
    ),
    "Socket_126": (
        "Wobble",
        "Springiness after a push or a stop: 1 keeps every rebound, lower settles sooner "
        "without the drag of Damping, 0 settles without rebounds",
    ),
    "Socket_123": (
        "Max Distance",
        "Furthest a point may move from its animated position, against very hard moves and "
        "cuts (0.1 - 0.2 m on a person). 0 is no limit",
    ),
    "Socket_6": ("Stretching", "How much the surface may stretch. Higher is more elastic"),
    "Socket_30": ("Bending", "How easily the surface bends and shears. Higher creases more"),
    "Socket_118": (
        "Preserve Volume",
        "How much each soft part keeps its volume: pressed flesh bulges around the contact "
        "instead of flattening. 0 is off",
    ),
    "Socket_119": (
        "Sway",
        "How much each soft part moves as one mass keeping its shape, swinging about its base "
        "instead of rippling. Higher looks heavier and firmer",
    ),
    "Socket_5": (
        "Gravity",
        "Pull the Zone down. It sags less with a lower Softness, Mass or Time Scale",
    ),
    "Socket_3": ("Acceleration", "Direction and strength of gravity, in world space"),
    "Socket_7": (
        "Colliders",
        "Collection of the colliders and force fields. Every collider needs Blender's Collider "
        "Geometry Nodes modifier: a closed mesh is solid, an open one pushes along its normals",
    ),
    "Socket_24": ("Contact Thickness", "Distance the Zone keeps from the colliders"),
    "Socket_28": ("Collider Friction", "Friction against the colliders"),
    "Socket_128": (
        "Push Aside",
        "Distance over which the skin around a pushing collider moves aside with it, opening a "
        "smooth way instead of a pit. For soft objects, 0 on characters. 0 is off",
    ),
    "Socket_129": (
        "Cling",
        "Skin closer than this to a collider is drawn onto it, wrapping around it. 0 is off",
    ),
    "Socket_130": (
        "Grip",
        "How much the touching skin is carried along by a moving collider: 1 sticks, 0 slides",
    ),
    "Socket_104": (
        "Self Collision",
        "Collide the Zone with the rest of its mesh: the soft parts with each other and with "
        "the rigid ones. Slow, bake the result",
    ),
    "Socket_124": ("Collide With", "Part of the mesh the Zone collides with"),
    "Socket_120": (
        "Collider Group",
        "Vertex group of the part to collide with in the Group modes, e.g. the hands (weight "
        "above 0.5)",
    ),
    "Socket_105": ("Gap", "Gap kept between touching parts of the mesh"),
    "Socket_109": ("Self Friction", "How much touching parts of the mesh grip each other"),
    "Socket_108": (
        "Separation Speed",
        "Speed in meters per second at which overlaps are pushed apart. Lower parts the skin "
        "more gently",
    ),
    "Socket_106": (
        "Max Overlap",
        "Deepest overlap still pushed apart. Raise it if parts of the model sink deep into each "
        "other in the animation",
    ),
    "Socket_107": (
        "Overlap Steps",
        "Steps per frame pushing apart the overlaps of the animated pose. More gives smoother "
        "dents",
    ),
    "Socket_34": ("Squeeze", "Squeeze the Squeeze Area before the simulation"),
    "Socket_37": ("Squeeze Area", "Vertex group of what gets squeezed"),
    "Socket_35": ("Squeeze Strength", "Overall strength of the squeeze"),
    "Socket_36": ("Squeeze Depth", "How deep the surface is pressed in"),
    "Socket_98": ("Smoothing", "Smooth the deformation after the simulation"),
    "Socket_99": ("Smoothing Area", "Vertex group of where to smooth"),
    "Socket_100": ("Smoothing Strength", "How much of the smoothing is applied"),
    "Socket_101": ("Smoothing Passes", "Blur passes: more smooths over a larger area"),
    "Socket_14": (
        "Substeps",
        "Solver steps per frame. More is steadier in fast motion and keeps fast colliders from "
        "passing through. The motion follows the steps per second: retune after changing them",
    ),
    "Socket_15": (
        "Iterations",
        "Constraint iterations per substep. More holds Stretching and Bending more precisely",
    ),
    "Socket_127": (
        "Time Scale",
        "How fast the simulated time runs. Below 1 the jiggle is slower and the motion counts "
        "more than gravity, as in the slow motion of Cloth. 1 is real time",
    ),
    "Socket_29": (
        "Simulation Space",
        "Transform from simulation space to world space. Leave it unless the rig is offset or "
        "scaled",
    ),
}
for item in core.interface.items_tree:
    if item.item_type == "SOCKET" and item.in_out == "INPUT":
        item.name, item.description = INPUTS[item.identifier]
core.description = (
    "Jiggle of the soft parts on Blender's XPBD solver: pick the Zone, add the Colliders and "
    "play. One modifier for each part"
)

# The node group: the core on the zone only, the rest of the mesh passed through
ng = core.copy()
ng.name = NODE_GROUP
ng["MustardUI Version"] = VERSION
ng.nodes.clear()
invert = ng.interface.new_socket("Invert Zone", in_out="INPUT", socket_type="NodeSocketBool")
invert.description = "Soft where the Zone weight is 0 and still where it is 1, as a Pin group"
zone_item = next(x for x in ng.interface.items_tree if getattr(x, "identifier", "") == "Socket_2")
ng.interface.move(invert, zone_item.position + 1)
# On/off switch of the Collisions panel
panel = next(
    x for x in ng.interface.items_tree if x.item_type == "PANEL" and x.name == "Collisions"
)
collisions = ng.interface.new_socket(
    "Collisions", in_out="INPUT", socket_type="NodeSocketBool", parent=panel
)
collisions.default_value = True
collisions.is_panel_toggle = True
collisions.description = "Collide with the Colliders"
ng.interface.move_to_parent(collisions, panel, 0)
N, L = ng.nodes, ng.links


def node(kind, **props):
    n = N.new(kind)
    for k, v in props.items():
        setattr(n, k, v)
    return n


def math(operation, a, b, kind="ShaderNodeMath"):
    n = node(kind, operation=operation)
    for socket, value in zip(n.inputs, (a, b), strict=False):
        if isinstance(value, bpy.types.NodeSocket):
            L.new(value, socket)
        else:
            socket.default_value = value
    return n.outputs[0]


def compare(operation, a, b):
    n = node("FunctionNodeCompare", data_type="FLOAT", operation=operation)
    L.new(a, n.inputs[0])
    n.inputs[1].default_value = b
    return n.outputs[0]


def boolean(operation, a, b):
    n = node("FunctionNodeBooleanMath", operation=operation)
    L.new(a, n.inputs[0])
    L.new(b, n.inputs[1])
    return n.outputs[0]


gi, go = node("NodeGroupInput"), node("NodeGroupOutput")
inp = {s.identifier: s for s in gi.outputs}
inner = node("GeometryNodeGroup", node_tree=core)

zone = node("GeometryNodeSwitch", input_type="FLOAT")
L.new(inp[invert.identifier], zone.inputs["Switch"])
L.new(inp["Socket_2"], zone.inputs["False"])
L.new(math("SUBTRACT", 1.0, inp["Socket_2"]), zone.inputs["True"])
zone = zone.outputs[0]
colliders = node("GeometryNodeSwitch", input_type="COLLECTION")
L.new(inp[collisions.identifier], colliders.inputs["Switch"])
L.new(inp["Socket_7"], colliders.inputs["True"])
for s in inner.inputs:
    if s.identifier == "Socket_2":
        L.new(zone, s)
    elif s.identifier == "Socket_7":
        L.new(colliders.outputs[0], s)
    elif s.identifier != "Socket_0" and s.identifier in inp:
        L.new(inp[s.identifier], s)

# Points the simulation moves: the zone, and the Squeeze and Smoothing areas when they are on
squeeze = boolean("AND", inp["Socket_34"], compare("GREATER_THAN", inp["Socket_37"], 0.0))
smooth = boolean("AND", inp["Socket_98"], compare("GREATER_THAN", inp["Socket_99"], 0.0))
moving = boolean("OR", boolean("OR", compare("GREATER_THAN", zone, 0.0), squeeze), smooth)

# Grown by the rings Edge Fade and the Smoothing passes reach, and by the anchor rings
passes = node("GeometryNodeSwitch", input_type="INT")
L.new(inp["Socket_98"], passes.inputs["Switch"])
passes.inputs["False"].default_value = 0
L.new(inp["Socket_101"], passes.inputs["True"])
rings = math("MAXIMUM", inp["Socket_122"], passes.outputs[0], "FunctionNodeIntegerMath")
rings = math("ADD", rings, ANCHOR_RINGS, "FunctionNodeIntegerMath")
blur = node("GeometryNodeBlurAttribute", data_type="FLOAT")
L.new(moving, blur.inputs[0])
L.new(rings, blur.inputs["Iterations"])
keep = compare("GREATER_THAN", blur.outputs[0], 0.0)
# Self Collision and Squeeze read the rest of the mesh: nothing is cropped
keep = boolean("OR", keep, boolean("OR", inp["Socket_104"], inp["Socket_34"]))

capture = node("GeometryNodeCaptureAttribute")
capture.capture_items.new("BOOLEAN", "Keep")
L.new(inp["Socket_0"], capture.inputs[0])
L.new(keep, capture.inputs[1])
crop = node("GeometryNodeSeparateGeometry", domain="POINT")
L.new(capture.outputs[0], crop.inputs["Geometry"])
L.new(capture.outputs[1], crop.inputs["Selection"])
L.new(crop.outputs[0], inner.inputs["Socket_0"])

# Separate Geometry keeps the point order: the index in the crop is the count of kept points before
accumulate = node("GeometryNodeAccumulateField", data_type="INT")
L.new(capture.outputs[1], accumulate.inputs[0])
index = math("SUBTRACT", accumulate.outputs["Leading"], 1, "FunctionNodeIntegerMath")
sample = node("GeometryNodeSampleIndex", data_type="FLOAT_VECTOR", domain="POINT")
L.new(inner.outputs[0], sample.inputs["Geometry"])
L.new(node("GeometryNodeInputPosition").outputs[0], sample.inputs["Value"])
L.new(index, sample.inputs["Index"])
position = node("GeometryNodeSetPosition")
L.new(capture.outputs[0], position.inputs["Geometry"])
L.new(capture.outputs[1], position.inputs["Selection"])
L.new(sample.outputs[0], position.inputs["Position"])
L.new(position.outputs[0], go.inputs[0])

path = os.path.abspath(
    args[1] if len(args) > 1 else os.path.join(os.path.dirname(__file__), RESOURCE)
)
bpy.data.libraries.write(path, {ng}, compress=True)
print("Written", path)
