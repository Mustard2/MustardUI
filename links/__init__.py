from . import definitions, ops_link, ops_preset, ui_list


def register():
    definitions.register()
    ops_link.register()
    ops_preset.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_preset.unregister()
    ops_link.unregister()
    definitions.unregister()
