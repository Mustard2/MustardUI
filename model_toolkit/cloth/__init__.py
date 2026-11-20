from . import ops_cloth, ops_interactive, ops_timeline, settings, ui_list


def register():
    settings.register()
    ops_cloth.register()
    ops_interactive.register()
    ops_timeline.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_timeline.unregister()
    ops_interactive.unregister()
    ops_cloth.unregister()
    settings.unregister()
