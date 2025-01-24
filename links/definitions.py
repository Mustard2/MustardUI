import bpy
from bpy.props import *


class MustardUI_Link(bpy.types.PropertyGroup):
    # Internal stored properties
    name: StringProperty(name="RNA")
    url: StringProperty(name="Path")


def register():
    bpy.utils.register_class(MustardUI_Link)
    bpy.types.Armature.MustardUI_Links = CollectionProperty(type=MustardUI_Link)


def unregister():
    del bpy.types.Armature.MustardUI_Links
    bpy.utils.unregister_class(MustardUI_Link)
