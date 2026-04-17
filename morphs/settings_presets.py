import bpy

from ..model_selection.active_object import mustardui_active_object
from .settings_morph import MustardUI_PresetMorph


def morph_preset_default_update(self, context):
    if not self.default:
        return

    res, arm = mustardui_active_object(context, config=0)
    morphs_settings = arm.MustardUI_MorphsSettings

    for preset in morphs_settings.presets:
        if preset is None:
            continue
        if preset != self and preset.default:
            preset.default = False


class MustardUI_Morph_Preset(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty(name="Name")

    default: bpy.props.BoolProperty(
        name="",
        description="Flag this preset as Default.\nWhen Morphs are reset in the Morphs "
        "panel, the values will be restored to this preset morph rather than 0",
        update=morph_preset_default_update,
    )

    # Collection for storing Morphs
    morphs: bpy.props.CollectionProperty(type=MustardUI_PresetMorph)


def register():
    bpy.utils.register_class(MustardUI_Morph_Preset)


def unregister():
    bpy.utils.unregister_class(MustardUI_Morph_Preset)
