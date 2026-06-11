def store_current_hair(rig_settings):
    """Return the name of the currently visible hair object, or '' if none found."""
    if rig_settings.hair_collection is None:
        return ""
    for obj in rig_settings.hair_collection.objects:
        if (
            obj is not None
            and not obj.hide_viewport
            and not obj.hide_render
            and obj.type in ["MESH", "CURVES"]
        ):
            return obj.name
    return ""


def set_selected_hair(context, rig_settings, object_active):
    """Set hair_list to object_active, falling back to the first element if needed."""
    hlist = rig_settings.hair_list_make(context)
    if not hlist:
        return
    if object_active:
        try:
            rig_settings.hair_list = object_active
        except Exception:
            rig_settings.hair_list = hlist[0][0]
    else:
        rig_settings.hair_list = hlist[0][0]
