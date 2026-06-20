from . import definitions, ops_preset, ui_list


def register():
    definitions.register()
    ops_preset.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_preset.unregister()
    definitions.unregister()
