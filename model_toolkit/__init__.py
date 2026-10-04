import bpy
from bpy.props import BoolProperty, StringProperty

from . import armature, effects, images, mesh, model, optimization, outfits, physics


def register():
    bpy.types.Object.MustardUI_tools_creators_is_created = BoolProperty(default=False)
    # Model Toolkit tool which created the object, to remove it with its physics
    bpy.types.Object.MustardUI_tools_creators_type = StringProperty(default="")

    physics.register()
    armature.register()
    model.register()
    mesh.register()
    # After mesh, which registers the preview of the outfits tools
    outfits.register()
    optimization.register()
    images.register()
    effects.register()


def unregister():
    effects.unregister()
    images.unregister()
    optimization.unregister()
    outfits.unregister()
    mesh.unregister()
    model.unregister()
    armature.unregister()
    physics.unregister()

    del bpy.types.Object.MustardUI_tools_creators_type
    del bpy.types.Object.MustardUI_tools_creators_is_created
