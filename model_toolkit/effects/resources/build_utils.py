# Helpers of the *_build.py scripts, which build the effect resources in this folder
#
# Usage, from this folder:
#   Blender --background --factory-startup --python disintegration_build.py
#     writes disintegration.blend next to it
#   Blender --background --factory-startup --python ripple_build.py -- /tmp/test.blend
#     writes to any path, e.g. to compare with the committed file
import os
import sys

import bpy


def socket(sockets, name):
    """Socket by name or identifier, the enabled one as typed nodes reuse names"""
    matches = [s for s in sockets if name in (s.name, s.identifier)]
    return next((s for s in matches if s.enabled), matches[0])


def add_input(tree, name, socket_type, parent=None, **settings):
    item = tree.interface.new_socket(name, in_out="INPUT", socket_type=socket_type, parent=parent)
    for key, value in settings.items():
        setattr(item, key, value)
    return item


def add_output(tree, name, socket_type):
    return tree.interface.new_socket(name, in_out="OUTPUT", socket_type=socket_type)


class Tree:
    """Node tree builder, placing the nodes on a grid"""

    def __init__(self, tree, spacing=(200, 200)):
        self.tree = tree
        self.spacing = spacing
        self.frame = None
        self.rows = set()

    def section(self, label, row=False):
        """Frame with the label, holding the nodes added next, starting a row of frames"""
        self.frame = self.tree.nodes.new("NodeFrame")
        self.frame.label = label
        self.frame.label_size = 32
        if row:
            self.rows.add(self.frame)

    def node(self, idname, x, y, inputs=None, **props):
        """Node with the props set, and the inputs (by index or name) set or linked"""
        node = self.tree.nodes.new(idname)
        node.location = (x * self.spacing[0], y * self.spacing[1])
        if idname != "NodeFrame":
            node.parent = self.frame
        for key, value in props.items():
            setattr(node, key, value)
        for key, value in (inputs or {}).items():
            self.connect(
                value, node.inputs[key] if isinstance(key, int) else socket(node.inputs, key)
            )
        return node

    def connect(self, value, target):
        if isinstance(value, bpy.types.NodeSocket):
            self.tree.links.new(value, target)
        elif value is not None:
            target.default_value = value

    def math(self, operation, *values, x, y, vector=False, clamp=False):
        """Output of a (Vector) Math node, the values linked or set in its inputs in order"""
        node = self.node(
            "ShaderNodeVectorMath" if vector else "ShaderNodeMath", x, y, operation=operation
        )
        if not vector:
            node.use_clamp = clamp
        targets = [s for s in node.inputs if s.enabled]
        for value, target in zip(values, targets, strict=False):
            self.connect(value, target)
        scalar = vector and operation in {"LENGTH", "DOT_PRODUCT", "DISTANCE"}
        return node.outputs["Value" if scalar else 0]

    def vmath(self, operation, *values, x, y):
        return self.math(operation, *values, x=x, y=y, vector=True)

    def attribute(self, name, data_type, x, y):
        node = self.node(
            "GeometryNodeInputNamedAttribute", x, y, {"Name": name}, data_type=data_type
        )
        return socket(node.outputs, "Attribute")

    def store(self, geometry, name, data_type, value, x, y, domain="POINT"):
        """Geometry with the value stored in the named attribute"""
        node = self.node(
            "GeometryNodeStoreNamedAttribute",
            x,
            y,
            {"Geometry": geometry, "Name": name, "Value": value},
            data_type=data_type,
            domain=domain,
        )
        return node.outputs["Geometry"]

    def arrange(self):
        """Layout of the section frames in rows, with the nodes in columns by their depth, and
        copies of the input nodes in each section using them, not to link them across"""
        nodes, links = self.tree.nodes, self.tree.links
        inputs = [
            n
            for n in nodes
            if n.bl_idname in INPUT_NODES and not any(s.is_linked for s in n.inputs)
        ]
        copies = {}
        for node in inputs:
            for link in [k for k in links if k.from_node == node]:
                user = link.to_node
                if user.parent == node.parent or link.to_socket.is_multi_input:
                    continue
                if (node, user.parent) not in copies:
                    copy = nodes.new(node.bl_idname)
                    copy.parent = user.parent
                    copy.location_absolute = user.location_absolute
                    if hasattr(node, "data_type"):
                        copy.data_type = node.data_type
                    for a, b in zip(node.inputs, copy.inputs, strict=True):
                        b.default_value = a.default_value
                    copies[node, user.parent] = copy
                output = list(node.outputs).index(link.from_socket)
                links.new(copies[node, user.parent].outputs[output], link.to_socket)
        for node in inputs:
            if not any(s.is_linked for s in node.outputs):
                nodes.remove(node)
        for node in [n for n in nodes if n.bl_idname == "NodeGroupInput"]:
            for output in node.outputs:
                output.hide = not output.is_linked

        x = top = bottom = 0
        for frame in [n for n in nodes if n.bl_idname == "NodeFrame"]:
            # By the hand placed height, kept in each column
            members = sorted(
                [n for n in nodes if n.parent == frame], key=lambda n: -n.location_absolute.y
            )
            if not members:
                continue
            if frame in self.rows:
                x, top = 0, bottom - 600
            inner = [k for k in links if k.from_node.parent == k.to_node.parent == frame]
            # Longest path from the section start
            depth = dict.fromkeys(members, 0)
            for _ in members:
                for link in inner:
                    depth[link.to_node] = max(depth[link.to_node], depth[link.from_node] + 1)
            # Nodes without previous ones in the section right before their first user
            for node in [n for n in members if not any(k.to_node == n for k in inner)]:
                users = [depth[k.to_node] for k in inner if k.from_node == node]
                depth[node] = min(users, default=1) - 1
            columns = {}
            for node in members:
                columns.setdefault(depth[node], []).append(node)
            for d in sorted(columns):
                y = top
                for node in columns[d]:
                    node.location_absolute = (x, y)
                    y -= node_height(node) + 40
                bottom = min(bottom, y)
                x += max(n.width for n in columns[d]) + 80
            x += 400


def node_height(node):
    """Height of the node as drawn, estimated from its sockets and options"""
    rows = sum(
        4 if s.type == "VECTOR" and not s.is_linked and not s.is_output else 1
        for s in (*node.inputs, *node.outputs)
        if s.enabled and not s.hide
    )
    options = [
        p
        for p in node.bl_rna.properties
        if p.type in {"ENUM", "BOOLEAN"}
        and not p.is_readonly
        and p.identifier not in bpy.types.Node.bl_rna.properties
    ]
    return 40 + 22 * (rows + len(options))


# Nodes reading a value, the same in their copies anywhere in the tree
INPUT_NODES = {
    "NodeGroupInput",
    "GeometryNodeInputIndex",
    "GeometryNodeInputNamedAttribute",
    "GeometryNodeInputNormal",
    "GeometryNodeInputPosition",
    "GeometryNodeSplineLength",
    "GeometryNodeSplineParameter",
}


def write(name, datablocks, fake_user=False):
    """Write the datablocks to <name>.blend in this folder, or to the path after --"""
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    path = os.path.abspath(args[0] if args else os.path.join(os.path.dirname(__file__), name))
    bpy.data.libraries.write(path, set(datablocks), fake_user=fake_user, compress=True)
    print("Written", path)
