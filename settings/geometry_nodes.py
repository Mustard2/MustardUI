import bpy
from bpy.props import *


def register():
    bpy.types.NodeTree.MustardUI_collapse = BoolProperty(name="", default=True)


def unregister():
    pass
