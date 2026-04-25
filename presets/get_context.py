import bpy


def get_preset_context(arm, preset_type):
    if preset_type == "MORPHS":
        settings = arm.MustardUI_MorphsSettings
        index_prop = "mustardui_morphs_preset_uilist_index"

    elif preset_type == "PHYSICS":
        settings = arm.MustardUI_PhysicsSettings
        index_prop = "mustardui_physics_preset_uilist_index"

    else:
        raise ValueError(f"Invalid preset_type: {preset_type}")

    presets = settings.presets
    index = getattr(arm, index_prop)

    preset = presets[index] if 0 <= index < len(presets) else None

    return settings, presets, preset, index, index_prop
