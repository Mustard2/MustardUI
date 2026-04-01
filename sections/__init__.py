from . import definitions
from . import ops_assign
from . import ui_list


def register():
    definitions.register()
    ops_assign.register()
    ui_list.register()


def unregister():
    ui_list.unregister()
    ops_assign.unregister()
    definitions.unregister()
