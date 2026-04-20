from . import definitions, ops_assign, ops_default, ui_list


def register():
    definitions.register()
    ops_assign.register()
    ops_default.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_default.unregister()
    ops_assign.unregister()
    definitions.unregister()
