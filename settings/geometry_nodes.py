import bpy
from bpy.props import BoolProperty


def register():
    bpy.types.NodeTree.MustardUI_collapse = BoolProperty(name="", default=True)


def unregister():
    del bpy.types.NodeTree.MustardUI_collapse
