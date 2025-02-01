import bpy


def ui_collapse_prop(layout, settings, prop_str, label, icon="", align=True) -> bool:
    prop = getattr(settings, prop_str)

    row = layout.row(align=align)
    row.prop(settings, prop_str,
                icon="TRIA_DOWN" if not prop else "TRIA_RIGHT", icon_only=True,
                emboss=False)
    if icon != "":
        row.label(text=label, icon=icon)
    else:
        row.label(text=label)
    return not prop
