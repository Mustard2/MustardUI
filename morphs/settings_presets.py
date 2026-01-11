import bpy
from .settings_morph import MustardUI_PresetMorph


class MustardUI_Morph_Preset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")

    # Collection for storing Morphs
    morphs: bpy.props.CollectionProperty(type=MustardUI_PresetMorph)


def register():
    bpy.utils.register_class(MustardUI_Morph_Preset)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morph_Preset)
