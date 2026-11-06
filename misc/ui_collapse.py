def ui_collapse_panel(layout, idname, label, icon="NONE", default_closed=True):
    """Body of a native layout panel, None when closed"""
    header, body = layout.panel(idname, default_closed=default_closed)
    header.label(text=label, icon=icon)
    return body
