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

    def node(self, idname, x, y, inputs=None, **props):
        """Node with the props set, and the inputs (by index or name) set or linked"""
        node = self.tree.nodes.new(idname)
        node.location = (x * self.spacing[0], y * self.spacing[1])
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


def write(name, datablocks, fake_user=False):
    """Write the datablocks to <name>.blend in this folder, or to the path after --"""
    args = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    path = os.path.abspath(args[0] if args else os.path.join(os.path.dirname(__file__), name))
    bpy.data.libraries.write(path, set(datablocks), fake_user=fake_user, compress=True)
    print("Written", path)
