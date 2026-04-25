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
