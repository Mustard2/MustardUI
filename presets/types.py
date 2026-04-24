import bpy


PRESET_TYPES = {
    "MORPHS": "Morphs",
    "PHYSICS": "Physics",
}


def mustardui_preset_type_items(self, context):
    return [(key, label, "") for key, label in PRESET_TYPES.items()]
