import bpy
from . import ops_viewport_panel


def register():
    ops_viewport_panel.register()


def unregister():
    ops_viewport_panel.unregister()
