import bpy
from bpy.props import BoolProperty

from . import armature, images, mesh, model, optimization, physics


def register():
    bpy.types.Object.MustardUI_tools_creators_is_created = BoolProperty(default=False)

    physics.register()
    armature.register()
    model.register()
    mesh.register()
    optimization.register()
    images.register()


def unregister():
    images.unregister()
    optimization.unregister()
    mesh.unregister()
    model.unregister()
    armature.unregister()
    physics.unregister()

    del bpy.types.Object.MustardUI_tools_creators_is_created
