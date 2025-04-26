import bpy
from .settings_morph import *
from .settings_section import *

morphs_check_items = [("GENERIC", "Generic", "Generic"),
                      ("DIFFEO_GENESIS_8", "Diffeomorphic Genesis 8", "Diffeomorphic Genesis 8"),
                      ("DIFFEO_GENESIS_9", "Diffeomorphic Genesis 9", "Diffeomorphic Genesis 9")]


class MustardUI_MorphsSettings(bpy.types.PropertyGroup):
    # CONFIGURATION

    enable_ui: bpy.props.BoolProperty(default=False,
                                      name="Diffeomorphic",
                                      description="Enable Diffeomorphic support.\nIf enabled, standard "
                                                  "morphs from Diffomorphic will be added to the UI")

    type: bpy.props.EnumProperty(items=morphs_check_items,
                                 default="DIFFEO_GENESIS_8",
                                 description="Type of Morphs to add.\nIf Morphs are already available, this setting can not be changed. Clear the Morphs before changing this setting",
                                 name="Morphs Type")

    show_type_icon: bpy.props.BoolProperty(default=False,
                                           name="Show Type Icon",
                                           description="Show Morph type icon in the UI")

    # INTERNAL

    is_diffeomorphic: bpy.props.BoolProperty(default=False)
    diffeomorphic_genesis_version: bpy.props.IntProperty(default=0)
    sections: bpy.props.CollectionProperty(type=MustardUI_Morph_Section)


def register():
    bpy.utils.register_class(MustardUI_MorphsSettings)
    bpy.types.Armature.MustardUI_MorphsSettings = bpy.props.PointerProperty(type=MustardUI_MorphsSettings)


def unregister():
    del bpy.types.Armature.MustardUI_MorphsSettings
    bpy.utils.unregister_class(MustardUI_MorphsSettings)
