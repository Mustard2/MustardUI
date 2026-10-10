import bpy

from ..misc.icons import mustardui_icon_list
from .settings_morph import MustardUI_Morph, cp_source


class MustardUI_Morph_Section(bpy.types.PropertyGroup):
    # UI Settings
    name: bpy.props.StringProperty(name="Name")
    icon: bpy.props.EnumProperty(items=mustardui_icon_list, name="Icon", description="Section Icon")

    # Collection for storing Morphs
    morphs: bpy.props.CollectionProperty(type=MustardUI_Morph)

    # Types for GENERIC type section
    string: bpy.props.StringProperty(
        default="",
        name="String",
        description="String to search for adding Morphs.\nSeveral strings can be added "
        "if separated by commas.\nNote: spaces and order are considered",
    )
    shape_keys: bpy.props.BoolProperty(
        default=False,
        name="Shape Keys",
        description="Search shape keys to be added as Morphs",
    )
    custom_properties: bpy.props.BoolProperty(
        default=False,
        name="Custom Properties",
        description="Search custom properties to be added as Morphs",
    )
    custom_properties_source: bpy.props.EnumProperty(
        items=cp_source,
        default="ARMATURE_OBJ",
        description="Object to look for Morphs",
        name="Morphs Source",
    )

    can_disable: bpy.props.BoolProperty(
        default=True,
        name="Can Be Disabled",
        description="Disable the morphs in this section when the Morphs are disabled.\n"
        "If off, these morphs and the drivers depending on them stay active",
    )
    hidden: bpy.props.BoolProperty(
        default=False,
        name="Hidden",
        description="Hide the section for the UI.\nCan be useful to use the Morphs in "
        "the list as just targets for the Disable Morphs feature",
    )

    # Collapse button
    collapse: bpy.props.BoolProperty(name="", default=True)

    # Internal
    # Property for sections generated automatically that can not be modified
    is_internal: bpy.props.BoolProperty(default=False)
    # TYPE: 0: Emotion Units, 1: Emotions, 2: FACS Emotion Units, 3: FACS Emotions,
    # 4: Body Morphs
    diffeomorphic_id: bpy.props.IntProperty(default=-1)


def register():
    bpy.utils.register_class(MustardUI_Morph_Section)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morph_Section)
