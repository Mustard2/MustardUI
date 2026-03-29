import bpy
from ..misc.prop_utils import *


def mustardui_custom_properties_print(arm, settings, custom_properties, layout, icons_show, boxed=True):
    if boxed:
        box = layout.box()
    else:
        box = layout
    for prop in [x for x in custom_properties if not x.hidden]:
        row = box.row(align=True)
        if icons_show:
            row.label(text=prop.name, icon=prop.icon if prop.icon != "NONE" else "DOT")
        else:
            row.label(text=prop.name)
        if not prop.is_animatable:
            try:
                row.prop(evaluate_rna(prop.rna), prop.path, text="")
            except:
                row.prop(settings, 'custom_properties_error_nonanimatable', icon="ERROR", text="", icon_only=True,
                          emboss=False)
        else:
            if prop.prop_name in arm.keys():
                row.prop(arm, f'["{prop.prop_name}"]', text="")
            else:
                row.prop(settings, 'custom_properties_error', icon="ERROR", text="", icon_only=True, emboss=False)

    return
