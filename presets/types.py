from ..morphs.settings_presets import (
    apply_morphs_preset,
    morphs_to_json,
)
from ..physics.settings_presets import (
    apply_physics_preset,
    physics_post_import,
    physics_preset_poll,
    physics_to_json,
    set_physics_preset,
    warning_physics_preset,
)

# PRESETS Development Guide
#
# All the presets data are stored in JSON file according to the builder function
# (see below).
#
# To add a new Preset type do the following:
#
# - Create a bpy.types.PropertyGroup (e.g.MustardUI_Physics_Preset) to store at least:
#   * name: bpy.types.StringProperty
#   * data: bpy.props.StringProperty, where the JSON string is saved
#
# - Add the presets entry as a bpy.props.CollectionProperty with the type as the newly
#   created group. E.g., bpy.props.CollectionProperty(type=MustardUI_Physics_Preset)
#   This can be added to the appropriate settings, e.g., MustardUI_PhysicsSettings
#   for the Physics presets.
#   NOTE: The name of this new Collection entry should be exactly presets!
#
# - Create the bpy.types.UIList (e.g. MUSTARDUI_UL_Physics_Presets_UIList) to show
#   the presets inside the preset menu.
#
# - Create an entry in MUSTARDUI_PRESETS with at least:
#   * name
#   * ui_list
#   * index_prop
#   * file_prefix
#   * builder: function to create the JSON string to store when a preset is created
#   * applier: function to read and apply preset from JSON string
#
# - Add an entry in get_context.py with the new preset settings.
#
# - Add the preset menu with the correct preset_type as input (same name as the key
#   in MUSTARDUI_PRESETS).
#
# Some adjustments might be necessary also in the ops_* files, depending on the
# complexity of the presets to be added.

MUSTARDUI_PRESETS = {
    "MORPHS": {
        "name": "Morphs",
        "ui_list": "MUSTARDUI_UL_Morphs_Presets_UIList",
        "index_prop": "mustardui_morphs_preset_uilist_index",
        "file_prefix": "MustardUI_MorphsPreset",
        "has_flags": False,
        "poll": None,
        "builder": morphs_to_json,
        "applier": apply_morphs_preset,
        "preset_set": None,
        "warnings": None,
        "post_import_set": None,
    },
    "PHYSICS": {
        "name": "Physics",
        "ui_list": "MUSTARDUI_UL_Physics_Presets_UIList",
        "index_prop": "mustardui_physics_preset_uilist_index",
        "file_prefix": "MustardUI_PhysicsPreset",
        "has_flags": True,
        "poll": physics_preset_poll,
        "builder": physics_to_json,
        "applier": apply_physics_preset,
        "preset_set": set_physics_preset,
        "warnings": warning_physics_preset,
        "post_import_set": physics_post_import,
    },
}


def get_preset_definition(preset_type):
    preset = MUSTARDUI_PRESETS.get(preset_type)
    if not preset:
        raise ValueError(f"Invalid preset type: {preset_type}")
    return preset


def preset_type_items(self, context):
    return [(key, data["name"], "") for key, data in MUSTARDUI_PRESETS.items()]
