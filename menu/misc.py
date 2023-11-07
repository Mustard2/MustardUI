def mustardui_custom_properties_print(arm, settings, rig_settings, custom_properties, box, icons_show):
    box2 = box.box()
    for prop in [x for x in custom_properties if not x.hidden]:
        row2 = box2.row(align=True)
        if icons_show:
            row2.label(text=prop.name, icon=prop.icon if prop.icon != "NONE" else "DOT")
        else:
            row2.label(text=prop.name)
        if not prop.is_animatable:
            try:
                row2.prop(eval(prop.rna), prop.path, text="")
            except:
                row2.prop(settings, 'custom_properties_error_nonanimatable', icon="ERROR", text="", icon_only=True,
                          emboss=False)
        else:
            if prop.prop_name in arm.keys():
                row2.prop(arm, '["' + prop.prop_name + '"]', text="")
            else:
                row2.prop(settings, 'custom_properties_error', icon="ERROR", text="", icon_only=True, emboss=False)

    return