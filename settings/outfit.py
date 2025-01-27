import bpy
from bpy.props import *


# Outfit information
class MustardUI_Outfit(bpy.types.PropertyGroup):
    # Collection storing the outfit pieces
    collection: PointerProperty(name="Outfit Collection",
                                type=bpy.types.Collection)


def register():
    bpy.utils.register_class(MustardUI_Outfit)

    # Properties and model_selection specific to objects
    bpy.types.Object.MustardUI_additional_options_show = BoolProperty(default=False,
                                                                      name="",
                                                                      description="Show additional properties for the "
                                                                                  "selected object")
    bpy.types.Object.MustardUI_additional_options_show_lock = BoolProperty(default=False,
                                                                           name="",
                                                                           description="Show additional properties for "
                                                                                       "the selected object")
    bpy.types.Object.MustardUI_outfit_visibility = BoolProperty(default=False, name="")
    bpy.types.Object.MustardUI_outfit_lock = BoolProperty(default=False,
                                                          name="",
                                                          description="Lock/unlock the outfit")


def unregister():
    del bpy.types.Object.MustardUI_outfit_visibility
    del bpy.types.Object.MustardUI_additional_options_show_lock
    del bpy.types.Object.MustardUI_additional_options_show

    bpy.utils.unregister_class(MustardUI_Outfit)
