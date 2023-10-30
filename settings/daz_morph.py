import bpy
from bpy.props import *


# Daz Morphs information
class MustardUI_DazMorph(bpy.types.PropertyGroup):
    name: StringProperty(name="Name")
    path: StringProperty(name="Path")
    # 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions, 4: Body Morphs
    type: IntProperty(name="Type")


def register():
    bpy.utils.register_class(MustardUI_DazMorph)


def unregister():
    bpy.utils.unregister_class(MustardUI_DazMorph)
