import bpy


def get_unique_preset_name(presets, base_name):
    names = {p.name for p in presets}

    new_name = base_name
    counter = 1

    while new_name in names:
        new_name = f"{base_name}.{counter:03d}"
        counter += 1

    return new_name


def check_preset_type(preset_type, data, name):
    try:
        preset_type_data = data.get("type", "")
        if preset_type_data != preset_type:
            return "ERROR", f"MustardUI - The Preset type is not {name}"
    except:
        return (
            "ERROR",
            "MustardUI - Cannot determine the Preset type",
        )
    return "", ""
