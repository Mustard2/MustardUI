import bpy
from .settings_morph import MustardUI_Morph
from ..misc.icons_list import mustardui_icon_list


class MustardUI_Morph_Section(bpy.types.PropertyGroup):
    # UI Settings
    name: bpy.props.StringProperty(name="Name")
    icon: bpy.props.EnumProperty(items=mustardui_icon_list,
                                 name="Icon",
                                 description="Section Icon")

    # Collection for storing Morphs
    morphs: bpy.props.CollectionProperty(type=MustardUI_Morph)

    # Types for GENERIC type section
    string: bpy.props.StringProperty(default="",
                                     name="String",
                                     description="String to search for adding Morphs.\nSeveral strings can be added if separated by commas.\nNote: spaces and order are considered")
    shape_keys: bpy.props.BoolProperty(default=False,
                                       name="Shape Keys",
                                       description="Search shape keys to be added as Morphs")
    custom_properties: bpy.props.BoolProperty(default=False,
                                              name="Custom Properties",
                                              description="Search custom properties to be added as Morphs")

    # Collapse button
    collapse: bpy.props.BoolProperty(name="", default=True)

    # Internal
    # Prpperty for sections generated automatically that can not be modified
    is_internal: bpy.props.BoolProperty(default=False)
    # TYPE: 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions, 4: Body Morphs
    diffeomorphic_id: bpy.props.IntProperty(default=-1)


def register():
    bpy.utils.register_class(MustardUI_Morph_Section)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morph_Section)
