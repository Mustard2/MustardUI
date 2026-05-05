# Checks if there are some conditions blocking the menus to be drawn
def can_draw_ui():
    import bpy

    # Check presence of old UI scripts
    for file in bpy.data.texts:
        if "mustard_ui.py" in file.name:
            return True
    return False
