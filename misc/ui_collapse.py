import bpy


def ui_collapse_prop(layout, settings, prop_str, label, icon="", align=True, use_layout=False, emboss=False,
                     invert_checkbox=False) -> bool:
    prop = getattr(settings, prop_str)

    if use_layout:
        row = layout
    else:
        row = layout.row(align=align)
    row.prop(settings, prop_str,
             icon="DOWNARROW_HLT" if not prop else "RIGHTARROW", icon_only=True,
             emboss=emboss, invert_checkbox=invert_checkbox)

    if label != "":
        if icon != "":
            row.label(text=label, icon=icon)
        else:
            row.label(text=label)

    return not prop
